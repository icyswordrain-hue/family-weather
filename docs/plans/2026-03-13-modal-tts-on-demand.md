# Modal On-Demand TTS Endpoint

**Date:** 2026-03-13

## Problem

`/api/tts` (on-demand synthesis, called by the player when `full_audio_url` is null) ran on Cloud Run with `RUN_MODE=CLOUD`. The CLOUD branch in `tts_client.synthesise_with_cache` uploads to GCS and returns `blob.public_url`. However the audio file was never actually accessible — the volume-stored audio from Modal and the GCS path were disconnected: Modal writes to `/data/audio/...` on the volume, while Cloud Run tried to write to GCS and return a raw GCS URL.

The result: clicking play on a midday or evening broadcast (where `full_audio_url = None`) would call `/api/tts`, Cloud Run would attempt TTS synthesis and GCS upload, and the returned URL either 404'd or 403'd depending on bucket ACLs.

## Solution

Route `/api/tts` through Modal so all TTS synthesis and storage stays on the volume, consistent with how morning TTS runs. Cloud Run becomes a pure proxy for `/api/tts` just as it is for `/api/refresh`, `/api/broadcast`, and `/api/audio`.

## Changes

### `backend/modal_app.py` — new `tts` endpoint

```python
@app.function(image=image, secrets=secrets, volumes={"/data": volume}, timeout=60)
@modal.fastapi_endpoint(method="POST")
def tts(payload: dict = None):
    """On-demand TTS synthesis. Writes to Modal volume and returns /api/audio/... URL."""
```

- Receives `{script, lang, date, slot}`
- Runs `synthesise_with_cache` with `RUN_MODE=MODAL` → writes to `/data/audio/{date}/{slot}_{lang}_{hash}.mp3`
- Calls `volume.commit()` before returning
- Returns `{"url": "/api/audio/{date}/{slot}_{lang}_{hash}.mp3"}`

### `app.py` — CLOUD proxy in `/api/tts`

```python
if RUN_MODE == "CLOUD":
    modal_tts_url = os.environ.get("MODAL_TTS_URL")
    if not modal_tts_url:
        return jsonify({"error": "MODAL_TTS_URL not configured"}), 500
    resp = requests.post(modal_tts_url, json={...}, timeout=60)
    return jsonify(resp.json())
```

LOCAL and MODAL modes are unchanged — they still call `synthesise_with_cache` directly.

## Deployment Steps

1. Deploy the updated Modal app:
   ```
   modal deploy backend/modal_app.py
   ```
2. Copy the new `tts` endpoint URL printed by Modal.
3. Set `MODAL_TTS_URL` on Cloud Run (alongside the existing `MODAL_REFRESH_URL`, `MODAL_BROADCAST_URL`, `MODAL_AUDIO_URL`).

## Audio URL Flow (CLOUD mode, after fix)

```
Player play click (full_audio_url = null)
  → POST Cloud Run /api/tts
  → POST MODAL_TTS_URL {script, lang, date, slot}
  → Modal tts() writes /data/audio/{date}/{slot}_{lang}_{hash}.mp3
  → volume.commit()
  → returns {"url": "/api/audio/{date}/{slot}_{lang}_{hash}.mp3"}
  → Cloud Run returns same JSON to browser
  → browser sets audio.src = "/api/audio/..."
  → GET Cloud Run /api/audio/{path}
  → GET MODAL_AUDIO_URL?filename={path}
  → Modal audio() reads /data/audio/{path} → streams bytes
```

## Required Cloud Run Env Vars

| Variable | Description |
|---|---|
| `MODAL_REFRESH_URL` | Modal `refresh` endpoint |
| `MODAL_BROADCAST_URL` | Modal `broadcast` endpoint |
| `MODAL_AUDIO_URL` | Modal `audio` endpoint |
| `MODAL_TTS_URL` | Modal `tts` endpoint (new) |
