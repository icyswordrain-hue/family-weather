# Cloud Execution & Smart Pipeline Design
_2026-03-01_

---

## Architecture

`RUN_MODE=CLOUD`: Flask on Cloud Run is a lightweight proxy. Modal runs the pipeline.
`RUN_MODE=LOCAL`: Flask runs the full pipeline in-process. No Modal, no GCS.

```
GCP Cloud Scheduler → POST /api/refresh (06:15 / 11:15 / 17:15 CST)
    │
Cloud Run — Flask (app.py)
    │
    ├─ [midday] lightweight CWA fetch → skip check → if unchanged, return morning broadcast
    │
    └─ [morning / evening / midday-changed] → invoke Modal
            ├─ fetch_cwa + fetch_moenv
            ├─ weather_processor + outdoor_score + health_alerts
            ├─ llm_prompt_builder → Claude
            ├─ NO TTS pre-render (all TTS is on-demand)
            └─ broadcast JSON (narration script text, audio_url: null) → GCS → Flask
```

---

## Pipeline Schedule

| Slot | Cron (Asia/Taipei) | CWA observation |
|---|---|---|
| `morning` | `15 6 * * *` | 06:00 |
| `midday` | `15 11 * * *` | 11:00 |
| `evening` | `15 17 * * *` | 17:00 |

Slot is passed explicitly in the Cloud Scheduler request body — do not infer from clock alone.

```python
# config.py
from datetime import timezone, timedelta
CST = timezone(timedelta(hours=8))
```

---

## GCS Layout

```
{bucket}/
  broadcasts/
    {date}/
      morning.json
      midday.json
      evening.json
  audio/
    {date}/
      {slot}_{lang}_{hash12}.mp3
  regen/
    regen.json
```

Bucket is **public**. Audio paths use a 12-char MD5 hash of the script text.

GCS lifecycle rule (set on bucket, not in code): delete `audio/*` objects older than 30 days.

---

## 1. TTS — On-Demand Only

The pipeline never pre-renders audio. Broadcast JSON carries the narration script text
and `audio_url: null`. Audio is rendered when the user clicks Play.

### `narration/tts_client.py`

```python
import hashlib, io, asyncio, logging
from pathlib import Path
from config import RUN_MODE, GCS_BUCKET_NAME, GCS_AUDIO_PREFIX

log = logging.getLogger(__name__)

VOICES = {
    "zh-TW": "zh-TW-HsiaoChenNeural",
    "en":    "en-US-GuyNeural",
}

def tts_cache_key(text: str, lang: str, date: str, slot: str) -> str:
    h = hashlib.md5(text.strip().encode()).hexdigest()[:12]
    return f"{GCS_AUDIO_PREFIX}/{date}/{slot}_{lang}_{h}.mp3"


def _upload_to_gcs(audio_bytes: bytes, gcs_path: str) -> str:
    from google.cloud import storage
    blob = storage.Client().bucket(GCS_BUCKET_NAME).blob(gcs_path)
    blob.upload_from_string(audio_bytes, content_type="audio/mpeg")
    blob.make_public()
    return blob.public_url


def _render_edge_tts(text: str, lang: str) -> bytes:
    import edge_tts
    buf = io.BytesIO()
    async def _collect():
        communicate = edge_tts.Communicate(text, VOICES[lang])
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
    asyncio.run(_collect())
    return buf.getvalue()


def synthesise_with_cache(text: str, lang: str, date: str, slot: str) -> str:
    """Returns public GCS URL (cloud) or local path (local). Checks cache first."""
    gcs_path = tts_cache_key(text, lang, date, slot)

    if RUN_MODE in ("CLOUD", "MODAL"):
        from google.cloud import storage
        blob = storage.Client().bucket(GCS_BUCKET_NAME).blob(gcs_path)
        if blob.exists():
            log.info(f"TTS cache hit: {gcs_path}")
            return blob.public_url

    audio = _render_edge_tts(text, lang)

    if RUN_MODE in ("CLOUD", "MODAL"):
        return _upload_to_gcs(audio, gcs_path)

    out = Path("local_data/audio") / Path(gcs_path).name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(audio)
    return f"/local_assets/audio/{out.name}"
```

### `app.py` — `/api/tts` and `/api/warmup`

```python
@app.route("/api/tts", methods=["POST"])
def tts_on_demand():
    data   = request.json
    script = data["script"]
    lang   = data.get("lang", "zh-TW")
    date   = data.get("date", today())
    slot   = data.get("slot", "midday")
    url    = synthesise_with_cache(script, lang, date, slot)
    return jsonify({"url": url})


@app.route("/api/warmup")
def warmup():
    return jsonify({"status": "warm"}), 200
```

### `web/static/app.js`

```javascript
// On page load — warms Cloud Run instance before user clicks Play
fetch('/api/warmup').catch(() => {});

async function handlePlay(script, lang, date, slot) {
    showSpinner();
    const res = await fetch('/api/tts', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({script, lang, date, slot}),
    });
    const {url} = await res.json();
    hideSpinner();
    new Audio(url).play();
}
```

---

## 2. Smart Midday Skip

### `app.py`

```python
from datetime import datetime
from config import CST

def classify_run_slot(body: dict) -> str:
    if "slot" in body:
        return body["slot"]
    h = datetime.now(CST).hour
    return "morning" if h < 9 else "midday" if h < 14 else "evening"


def _aqi_category(aqi: int) -> str:
    if aqi <= 50:  return "good"
    if aqi <= 100: return "moderate"
    if aqi <= 150: return "unhealthy_sensitive"
    if aqi <= 200: return "unhealthy"
    return "very_unhealthy"


def _conditions_changed(current: dict, morning: dict) -> tuple[bool, list[str]]:
    reasons = []
    if abs(current["temp_c"] - morning["temp_c"]) >= 3:
        reasons.append(f"temp {morning['temp_c']}→{current['temp_c']}°C")
    if (current["precip_mm"] > 0) != (morning["precip_mm"] > 0):
        reasons.append("rain status changed")
    if set(current.get("alerts", [])) != set(morning.get("alerts", [])):
        reasons.append("alert state changed")
    if _aqi_category(current["aqi"]) != _aqi_category(morning["aqi"]):
        reasons.append("AQI category crossed boundary")
    if current.get("score_label") != morning.get("score_label"):
        reasons.append(f"outdoor score {morning.get('score_label')}→{current.get('score_label')}")
    if abs(current.get("dew_point_c", 0) - morning.get("dew_point_c", 0)) >= 3:
        reasons.append("dew point shift ≥3°C")
    return bool(reasons), reasons


@app.route("/api/refresh", methods=["POST"])
def refresh():
    body = request.json or {}
    slot = classify_run_slot(body)

    if slot == "midday":
        try:
            current = fetch_cwa.fetch_current_conditions()
            morning = history.load_broadcast(date=today(), slot="morning")
            if morning:
                changed, reasons = _conditions_changed(current, morning)
                if not changed:
                    log.info("Midday skip: conditions unchanged")
                    return jsonify({"status": "skipped", "broadcast": morning}), 200
                log.info(f"Midday proceeding: {reasons}")
        except Exception as e:
            log.warning(f"Midday skip check failed ({e}), running full pipeline")

    return _run_pipeline(slot)
```

Failure behaviour: any exception in the skip check → full pipeline runs.

---

## 3. Regen Persistence

### `app.py`

```python
def _persist_regen(payload: dict) -> None:
    regen = payload.get("regen")
    if not regen:
        return
    if RUN_MODE in ("CLOUD", "MODAL"):
        from google.cloud import storage
        blob = storage.Client().bucket(GCS_BUCKET_NAME).blob("regen/regen.json")
        blob.upload_from_string(
            json.dumps(regen, ensure_ascii=False, indent=2),
            content_type="application/json",
        )
    else:
        Path("local_data/regen.json").write_text(
            json.dumps(regen, ensure_ascii=False, indent=2)
        )


def _restore_regen_from_gcs() -> None:
    """Call on container startup before first request."""
    if RUN_MODE not in ("CLOUD", "MODAL"):
        return
    try:
        from google.cloud import storage
        blob = storage.Client().bucket(GCS_BUCKET_NAME).blob("regen/regen.json")
        if blob.exists():
            _regen_cache.update(json.loads(blob.download_as_text()))
            log.info("regen.json restored from GCS")
    except Exception as e:
        log.warning(f"Could not restore regen from GCS: {e}")
```

---

## 4. Config Additions

```python
# config.py
GCS_AUDIO_PREFIX   = os.getenv("GCS_AUDIO_PREFIX", "audio")
GCS_REGEN_PATH     = os.getenv("GCS_REGEN_PATH", "regen/regen.json")
DESKTOP_TTS_URL    = os.getenv("DESKTOP_TTS_URL")
DESKTOP_TTS_SECRET = os.getenv("DESKTOP_TTS_SECRET")
DESKTOP_TTS_TIMEOUT = int(os.getenv("DESKTOP_TTS_TIMEOUT", "8"))
```

---

## 5. GCP Cloud Scheduler

```
weather-morning  →  15 6  * * *  Asia/Taipei  body: {"slot": "morning"}
weather-midday   →  15 11 * * *  Asia/Taipei  body: {"slot": "midday"}
weather-evening  →  15 17 * * *  Asia/Taipei  body: {"slot": "evening"}
```

Target: `POST https://<cloud-run-url>/api/refresh`

---

## 6. Files Modified

| File | Changes |
|---|---|
| `config.py` | Add `GCS_AUDIO_PREFIX`, `GCS_REGEN_PATH`, `DESKTOP_TTS_*`, `CST` |
| `narration/tts_client.py` | Replace existing render/save with `synthesise_with_cache`, `tts_cache_key`, `_upload_to_gcs`, `_render_edge_tts` |
| `app.py` | Add `classify_run_slot`, `_conditions_changed`, midday skip in `/api/refresh`, `/api/tts`, `/api/warmup`, `_persist_regen`, `_restore_regen_from_gcs` |
| `backend/pipeline.py` | Accept `slot` param; remove TTS pre-render; set `audio_url: null` in broadcast payload |
| `history/conversation.py` | Add `load_broadcast(date, slot)` supporting GCS and local paths |
| `web/static/app.js` | Warmup ping on load; Play handler POSTs to `/api/tts` when `audio_url` is null |
| GCS bucket | Lifecycle rule: delete `audio/*` after 30 days |
