from __future__ import annotations

import json
import logging
import os
import sys
import time
import requests
from datetime import datetime, timezone, timedelta

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("server.log", mode="w", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

from flask import Flask, jsonify, render_template, request, abort, Response, stream_with_context

from config import RUN_MODE

import config
from config import LOCAL_DATA_DIR, HISTORY_DAYS, REGEN_CYCLE_DAYS, CST
from data.fetch_cwa import fetch_current_conditions, fetch_all_forecasts, fetch_all_forecasts_7day
from data.helpers import _dew_point as _calc_dew_point  # pyre-ignore[21]
from data.station_history import load_recent_station_history
from data.fetch_moenv import fetch_all_aqi
from data.weather_processor import process
from narration.fallback_narrator import build_narration
from narration.llm_prompt_builder import build_prompt, parse_narration_response
from narration.tts_client import synthesise_with_cache

from history.conversation import load_history, save_day, get_today_broadcast
from web.routes import build_slices
from backend.pipeline import (
    check_regen_cycle,
    generate_narration_with_fallback,
)

_regen_cache = {}
_broadcast_cache: dict[str, dict] = {}  # keyed by date; populated by /api/broadcast in CLOUD mode
_chat_context_cache: dict[str, tuple[str, float]] = {}  # keyed by "date:lang"; (prompt, timestamp)

def _persist_regen(payload: dict) -> None:
    regen = payload.get("regen")
    if not regen:
        return
    if RUN_MODE == "CLOUD":
        from google.cloud import storage
        blob = storage.Client().bucket(config.GCS_BUCKET_NAME).blob(config.GCS_REGEN_PATH)
        blob.upload_from_string(
            json.dumps(regen, ensure_ascii=False, indent=2),
            content_type="application/json",
        )
    else:  # LOCAL and MODAL both use local file (MODAL → /data/regen.json)
        from pathlib import Path
        p = Path(f"{LOCAL_DATA_DIR}/regen.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(regen, ensure_ascii=False, indent=2)
        )

def _restore_regen_from_gcs() -> None:
    """Call on container startup before first request."""
    if RUN_MODE == "MODAL":
        from pathlib import Path
        p = Path(f"{LOCAL_DATA_DIR}/regen.json")
        if p.exists():
            try:
                _regen_cache.update(json.loads(p.read_text(encoding="utf-8")))
                logger.info("regen.json restored from Modal volume")
            except Exception as e:
                logger.warning("Could not restore regen from volume: %s", e)
        return
    if RUN_MODE != "CLOUD":
        return
    try:
        from google.cloud import storage
        blob = storage.Client().bucket(config.GCS_BUCKET_NAME).blob(config.GCS_REGEN_PATH)
        if blob.exists():
            _regen_cache.update(json.loads(blob.download_as_text()))
            logger.info("regen.json restored from GCS")
    except Exception as e:
        logger.warning(f"Could not restore regen from GCS: {e}")

_restore_regen_from_gcs()

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder="web/templates",
    static_folder="web/static",
)

_TAIPEI_TZ = timezone(timedelta(hours=8))
_refresh_counter = 0  # Track refreshes for periodic meal list regeneration

if RUN_MODE == "LOCAL":
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    
    @app.after_request
    def add_header(response):
        """Disable caching in local mode to force browser to load latest changes."""
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


# ── Routes ────────────────────────────────────────────────────────────────────


@app.route("/")
def index():
    """Serve the family dashboard."""
    return render_template("dashboard.html")


if RUN_MODE == "LOCAL":
    @app.route("/local_assets/<path:filename>")
    def local_assets(filename):
        from flask import send_from_directory
        # filename might contain slashes (broadcasts/2023-10-27/broadcast.mp3)
        return send_from_directory(LOCAL_DATA_DIR, filename)



@app.route("/api/health")
def health():
    """Health check endpoint required by Cloud Run."""
    return jsonify({"status": "ok", "timestamp": datetime.now(_TAIPEI_TZ).isoformat()})

@app.route("/api/tts", methods=["POST"])
def tts_on_demand():
    data   = request.json or {}
    script = data["script"]
    lang   = data.get("lang", "zh-TW")
    date   = data.get("date", datetime.now(_TAIPEI_TZ).strftime("%Y-%m-%d"))
    slot   = data.get("slot", "midday")

    if RUN_MODE == "CLOUD":
        modal_tts_url = os.environ.get("MODAL_TTS_URL")
        if not modal_tts_url:
            return jsonify({"error": "MODAL_TTS_URL not configured"}), 500
        try:
            resp = requests.post(
                modal_tts_url,
                json={"script": script, "lang": lang, "date": date, "slot": slot},
                timeout=60,
            )
            return jsonify(resp.json())
        except Exception as exc:
            logger.error("TTS proxy to Modal failed: %s", exc)
            return jsonify({"error": str(exc)}), 502

    from narration.tts_client import synthesise_with_cache
    url = synthesise_with_cache(script, lang, date, slot)
    return jsonify({"url": url})

def _get_broadcast_for_chat(date_str: str) -> dict | None:
    """Return today's broadcast dict for the chat context.

    In CLOUD mode the Flask process doesn't have local history, so we check
    the in-memory cache first (populated by /api/broadcast) then fall back to
    a direct HTTP request to Modal's broadcast endpoint.
    """
    if RUN_MODE == "CLOUD":
        if date_str in _broadcast_cache:
            return _broadcast_cache[date_str]
        modal_url = os.environ.get("MODAL_BROADCAST_URL")
        if not modal_url:
            return None
        try:
            resp = requests.get(modal_url, params={"date": date_str}, timeout=15)
            data = resp.json()
            if data and not data.get("error"):
                _broadcast_cache[date_str] = data
                return data
        except Exception as exc:
            logger.warning("Chat broadcast fetch failed: %s", exc)
        return None
    # LOCAL or MODAL — history is on-disk
    return get_today_broadcast(date_str)


@app.route("/api/chat", methods=["POST"])
def chat():
    """Answer a weather question using today's broadcast as context (Haiku 4.5)."""
    body = request.get_json(silent=True) or {}
    user_message = (body.get("message") or "").strip()
    if not user_message or len(user_message) > 500:
        return jsonify({"error": "Invalid message", "code": "bad_request"}), 400

    date_str = body.get("date") or datetime.now(_TAIPEI_TZ).strftime("%Y-%m-%d")
    lang = body.get("lang", "en")
    prior_turns = (body.get("messages") or [])[-config.CHAT_HISTORY_MAX_TURNS:]

    broadcast = _get_broadcast_for_chat(date_str)
    if not broadcast:
        return jsonify({"error": f"No broadcast available for {date_str}", "code": "no_broadcast"}), 503

    from narration.chat_context import build_chat_context
    from narration.claude_client import _get_client

    _ctx_key = f"{date_str}:{lang}"
    _ctx_cached = _chat_context_cache.get(_ctx_key)
    if _ctx_cached and (time.time() - _ctx_cached[1]) < 300:
        system_prompt = _ctx_cached[0]
    else:
        system_prompt = build_chat_context(broadcast, date_str, lang)
        _chat_context_cache[_ctx_key] = (system_prompt, time.time())
    messages = [*prior_turns, {"role": "user", "content": user_message}]

    try:
        client = _get_client()
        response = client.messages.create(
            model=config.CLAUDE_CHAT_MODEL,
            max_tokens=config.CLAUDE_CHAT_MAX_TOKENS,
            system=system_prompt,
            messages=messages,
            timeout=15.0,
        )
        reply = response.content[0].text.strip()
        turn = len(prior_turns) // 2 + 1
        return jsonify({"reply": reply, "turn": turn})
    except Exception as exc:
        logger.error("Chat failed: %s", exc)
        return jsonify({"error": str(exc), "code": "upstream_error"}), 503


@app.route("/api/warmup")
def warmup():
    return jsonify({"status": "warm"}), 200


@app.route("/debug/log", methods=["POST"])
def debug_log():
    """Receive and log frontend messages."""
    if RUN_MODE != "LOCAL":
        abort(403)
    data = request.get_json(silent=True) or {}
    type_ = data.get("type", "info").upper()
    msg = data.get("msg", "")
    ts = data.get("ts", "")
    logger.info(f"[BROWSER][{type_}][{ts}] {msg}")
    return jsonify({"status": "ok"})


@app.route("/api/broadcast")
def get_broadcast():
    """
    Return today's broadcast as JSON.
    Query params:
      date (optional): YYYY-MM-DD — defaults to today (Taipei time)
    """
    date_str = request.args.get("date") or datetime.now(_TAIPEI_TZ).strftime("%Y-%m-%d")
    lang = request.args.get("lang") or "en"

    if RUN_MODE == "CLOUD":
        # Proxy to Modal
        modal_url = os.environ.get("MODAL_BROADCAST_URL")
        if not modal_url:
            return jsonify({"error": "MODAL_BROADCAST_URL not configured"}), 500

        try:
            resp = requests.get(modal_url, params={"date": date_str, "lang": lang}, timeout=30)
            # Cache parsed broadcast so /api/chat can access context without a second hop
            try:
                data = resp.json()
                if data and not data.get("error"):
                    _broadcast_cache[date_str] = data
            except Exception:
                pass
            return (resp.text, resp.status_code, resp.headers.items())
        except Exception as e:
            logger.error("Failed to proxy broadcast to Modal: %s", e)
            return jsonify({"error": str(e)}), 500

    cached = get_today_broadcast(date_str)
    if not cached:
        # Trigger a refresh if there is no broadcast for today yet
        try:
            result = _run_pipeline(date_str)
        except Exception as exc:
            logger.error("Pipeline failed on-demand: %s", exc)
            return jsonify({"error": str(exc)}), 500
        return jsonify(result)

    # Attach slices for the dashboard
    slices = build_slices(cached, lang=lang)
    return jsonify({**cached, "slices": slices})


@app.route("/api/audio/<path:filename>")
def serve_audio(filename):
    """Serve TTS audio from Modal volume (proxied via Cloud Run in CLOUD mode)."""
    if RUN_MODE == "CLOUD":
        modal_audio_url = os.environ.get("MODAL_AUDIO_URL", "")
        if not modal_audio_url:
            return jsonify({"error": "MODAL_AUDIO_URL not configured"}), 500
        try:
            resp = requests.get(modal_audio_url, params={"filename": filename}, timeout=30)
            return Response(resp.content, mimetype="audio/mpeg", status=resp.status_code)
        except Exception as exc:
            logger.error("Audio proxy failed: %s", exc)
            return jsonify({"error": str(exc)}), 502
    # LOCAL or MODAL — serve directly from the filesystem
    from pathlib import Path
    from flask import send_file
    audio_path = Path(LOCAL_DATA_DIR) / "audio" / filename
    if not audio_path.exists():
        return jsonify({"error": "not found"}), 404
    return send_file(audio_path, mimetype="audio/mpeg")


@app.route("/api/refresh", methods=["POST"])
def refresh():
    """
    Triggers a full data fetch + narration + TTS pipeline.
    Returns an NDJSON stream of log events and the final result.
    """
    # Optionally accept a date/provider override in the JSON body
    body = request.get_json(silent=True) or {}
    date_str = body.get("date") or datetime.now(_TAIPEI_TZ).strftime("%Y-%m-%d")
    provider = body.get("provider") # Optional: "GEMINI" or "CLAUDE"
    lang = body.get("lang", "zh-TW")
    logger.info("DEBUG: Received refresh request. Body: %s, Provider: %s, Lang: %s", body, provider, lang)

    slot = classify_run_slot(body)

    if RUN_MODE == "CLOUD":
        # Proxy to Modal
        modal_url = os.environ.get("MODAL_REFRESH_URL")
        if not modal_url:
            return jsonify({"error": "MODAL_REFRESH_URL not configured"}), 500
            
        try:
            # Proxy the streaming response from Modal
            resp = requests.post(modal_url, json={"date": date_str, "provider": provider, "lang": lang, "slot": slot}, stream=True, timeout=290)
            return Response(
                stream_with_context(resp.iter_content(chunk_size=None)),
                content_type=resp.headers.get('content-type', 'application/x-ndjson')
            )
        except Exception as e:
            logger.error("Failed to proxy refresh to Modal: %s", e)
            return jsonify({"error": str(e)}), 500

    def generate():
        try:
            for step in _pipeline_steps(date_str, provider_override=provider, lang=lang, slot=slot):
                yield json.dumps(step) + "\n"
        except Exception as exc:
            logger.error("Pipeline error: %s", exc, exc_info=True)
            yield json.dumps({"type": "error", "message": str(exc)}) + "\n"

    return Response(stream_with_context(generate()), mimetype='application/x-ndjson')


# ── Core pipeline ─────────────────────────────────────────────────────────────

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
    """
    Lightweight check: does the live current reading differ enough from the
    morning broadcast to warrant a full midday pipeline run?

    `current`  — raw dict from fetch_current_conditions() (CWA keys: AT, RH, RAIN …)
    `morning`  — processed_data["current"] from the morning broadcast (enriched keys)
    """
    reasons = []

    # Temperature — CWA raw key is AT (apparent temp)
    c_temp = current.get("AT") or 0
    m_temp = morning.get("AT") or 0
    if abs(c_temp - m_temp) >= 3:
        reasons.append(f"temp {m_temp}→{c_temp}°C")

    # Precipitation — CWA raw key is RAIN
    if (current.get("RAIN", 0) > 0) != (morning.get("RAIN", 0) > 0):
        reasons.append("rain status changed")

    # Dew point — not pre-computed on the raw station dict; derive inline
    c_dp: float | None = (
        _calc_dew_point(current["AT"], current["RH"])
        if current.get("AT") is not None and current.get("RH") is not None
        else None
    )
    m_dp: float | None = morning.get("dew_point")
    if c_dp is not None and m_dp is not None and abs(c_dp - m_dp) >= 3:
        reasons.append("dew point shift ≥3°C")

    # AQI, alerts, and outdoor score_label require a full pipeline run;
    # they are not available from the raw CWA station fetch.

    return bool(reasons), reasons

def _pipeline_steps(date_str: str, provider_override: str | None = None, lang: str = "zh-TW", slot: str = "midday"):
    """
    Generator that yields log messages and finally the result dict.
    Yields: {"type": "log", "message": str} OR {"type": "result", "payload": dict}
    """
    global _refresh_counter
    # pyre-ignore[41]: Module-level mutation
    _refresh_counter += 1
    yield {"type": "log", "message": f"Starting pipeline for {date_str} (refresh #{_refresh_counter})"}
    logger.info("Starting pipeline for %s (refresh #%d)", date_str, _refresh_counter)

    # 0. Midday skip check — runs inside the pipeline so it uses the correct
    #    storage backend (local file in LOCAL/MODAL, GCS in CLOUD).
    if slot == "midday":
        try:
            from history.conversation import load_broadcast
            current_obs = fetch_current_conditions()
            m_broadcast = load_broadcast(date_str, slot="morning")
            morning = m_broadcast.get("processed_data", {}).get("current", {}) if m_broadcast else {}
            if morning:
                changed, reasons = _conditions_changed(current_obs, morning)
                if not changed:
                    logger.info("Midday skip: conditions unchanged")
                    yield {"type": "log", "message": "Midday skip: conditions unchanged since morning"}
                    yield {"type": "result", "payload": {"status": "skipped", "broadcast": m_broadcast}}
                    return
                logger.info("Midday proceeding: %s", reasons)
                yield {"type": "log", "message": f"Midday proceeding: {', '.join(reasons)}"}
        except Exception as e:
            logger.warning("Midday skip check failed (%s), running full pipeline", e)

    # 1. Fetch raw data
    try:
        yield {"type": "log", "message": "Fetching CWA current conditions..."}
        logger.info("Fetching CWA current conditions...")
        current = fetch_current_conditions()
        if current.get("_stale"):
            yield {"type": "log", "message": "⚠ CWA unavailable — using cached observation"}

        yield {"type": "log", "message": "Fetching CWA forecasts..."}
        logger.info("Fetching CWA forecasts...")
        _fc_errors: dict = {}
        forecasts = fetch_all_forecasts(_fc_errors)
        _failed_36h = [loc for loc, v in forecasts.items() if not v]
        _stale_36h  = [loc for loc, v in forecasts.items()
                       if v and _fc_errors.get(loc, "").startswith("(cached")]
        if _failed_36h:
            parts = [f"{loc} ({_fc_errors.get(loc, '?')})" for loc in _failed_36h]
            yield {"type": "log", "message": f"⚠ 36h forecast failed: {', '.join(parts)}"}
        if _stale_36h:
            yield {"type": "log", "message": f"⚠ 36h forecast stale: using cache for {', '.join(_stale_36h)} ({_fc_errors[_stale_36h[0]]})"}

        yield {"type": "log", "message": "Fetching CWA 7-day forecasts..."}
        logger.info("Fetching CWA 7-day forecasts...")
        _7d_errors: dict = {}
        forecasts_7day = fetch_all_forecasts_7day(_7d_errors)
        _failed_7d = [loc for loc, v in forecasts_7day.items() if not v]
        _stale_7d  = [loc for loc, v in forecasts_7day.items()
                      if v and _7d_errors.get(loc, "").startswith("(cached")]
        if _failed_7d:
            parts = [f"{loc} ({_7d_errors.get(loc, '?')})" for loc in _failed_7d]
            yield {"type": "log", "message": f"⚠ 7-day forecast failed: {', '.join(parts)}"}
        if _stale_7d:
            yield {"type": "log", "message": f"⚠ 7-day forecast stale: using cache for {', '.join(_stale_7d)} ({_7d_errors[_stale_7d[0]]})"}

        yield {"type": "log", "message": "Fetching MOENV AQI..."}
        logger.info("Fetching MOENV AQI...")
        aqi = fetch_all_aqi()
    except Exception as exc:
        logger.error("Data fetch failed: %s", exc)
        yield {"type": "error", "message": f"Data Fetch Failed: {exc}"}
        return

    # Fetch status summary
    _n_total = len(config.CWA_FORECAST_LOCATIONS)
    _aqi_ok  = bool(aqi.get("realtime") or aqi.get("forecast"))

    def _chip_state(results: dict, errs: dict, n: int) -> tuple[str, str]:
        n_ok    = sum(1 for loc, v in results.items() if v and not errs.get(loc, "").startswith("(cached"))
        n_stale = sum(1 for loc, v in results.items() if v and errs.get(loc, "").startswith("(cached"))
        if n_ok == n:           return "ok",    f"{n_ok}/{n}"
        if n_stale and not (n - n_ok - n_stale): return "stale", f"{n_ok+n_stale}/{n}"
        if n_ok + n_stale > 0:  return "warn",  f"{n_ok+n_stale}/{n}"
        return "fail", f"0/{n}"

    _36h_state, _36h_detail = _chip_state(forecasts,      _fc_errors, _n_total)
    _7d_state,  _7d_detail  = _chip_state(forecasts_7day, _7d_errors, _n_total)

    yield {"type": "status", "sources": [
        {
            "name": "CWA",
            "state": "stale" if current.get("_stale") else "ok",
            "detail": "stale" if current.get("_stale") else current.get("station_name", "?"),
        },
        {
            "name": "24h",
            "state": _36h_state,
            "detail": _36h_detail,
        },
        {
            "name": "7d",
            "state": _7d_state,
            "detail": _7d_detail,
        },
        {
            "name": "AQI",
            "state": "ok" if _aqi_ok else "warn",
            "detail": "✓" if _aqi_ok else "—",
        },
    ]}

    # 2. Load history
    yield {"type": "log", "message": "Loading conversation history..."}
    history = load_history(days=HISTORY_DAYS)
    station_history = load_recent_station_history(hours=24)

    # 3. Process data
    yield {"type": "log", "message": "Processing weather data & logic..."}
    logger.info("Processing data...")
    processed = process(current, forecasts, aqi, history, forecasts_7day, station_history=station_history)

    # 3b. Meal/Location Database Regen (14-day cycle)
    # Use a wider window than HISTORY_DAYS (LLM context) so the check can find
    # regen events that predate the prompt-history window.
    regen_history = load_history(days=REGEN_CYCLE_DAYS + 1)
    should_regen = check_regen_cycle(regen_history, date_str, REGEN_CYCLE_DAYS)

    # Fallback: history entries lose the regenerate_meal_lists marker when
    # same-day runs overwrite them.  regen.json persists updated_at independently.
    if should_regen:
        from pathlib import Path
        regen_path = Path(LOCAL_DATA_DIR) / "regen.json"
        if regen_path.exists():
            try:
                regen_info = json.loads(regen_path.read_text(encoding="utf-8"))
                last_updated = (regen_info.get("updated_at") or "")[:10]
                if last_updated:
                    days_since = (datetime.strptime(date_str, "%Y-%m-%d") - datetime.strptime(last_updated, "%Y-%m-%d")).days
                    if days_since < REGEN_CYCLE_DAYS:
                        should_regen = False
                        yield {"type": "log", "message": f"Regen skipped (last regen {days_since}d ago per regen.json)"}
            except Exception:
                pass

    if should_regen:
        yield {"type": "log", "message": f"Triggering periodic database regeneration ({REGEN_CYCLE_DAYS}-day cycle)..."}
        logger.info("Regen cycle triggered for %s", date_str)
        processed["regenerate_meal_lists"] = True

    # 4. Generate narration
    narration_provider = (provider_override or config.NARRATION_PROVIDER).upper()
    yield {"type": "log", "message": f"Building narration via {narration_provider}..."}
    logger.info("Building narration via %s...", narration_provider)

    narration_text, narration_source = generate_narration_with_fallback(
        narration_provider, processed, history, date_str, lang=lang
    )
    yield {"type": "log", "message": "Narration generated."}

    # 5. Extract paragraphs and metadata using v7 parser
    yield {"type": "log", "message": "Parsing narration structure & metadata (v7)..."}
    parsed = parse_narration_response(narration_text)
    paragraphs = parsed["paragraphs"]
    metadata = parsed["metadata"]
    regen_data = parsed["regen"]

    # Diagnostic: warn if metadata extraction failed
    if not metadata:
        yield {"type": "log", "message": "⚠ No ---METADATA--- block found in LLM response. Lifestyle cards will use fallbacks."}
    else:
        _card_keys = [k for k, v in parsed.get("cards", {}).items() if v and k != "alert"]
        yield {"type": "log", "message": f"Metadata OK: {len(_card_keys)} card fields populated."}

    # Reconstruct "clean" narration text from parsed paragraphs to sync with TTS
    # This removes any LLM preamble or leftover markers like "P1:"
    narration_text = "\n\n".join(paragraphs.values())

    metadata["narration_source"] = narration_source
    metadata["narration_model"] = config.GEMINI_PRO_MODEL if narration_source == "gemini" else (config.CLAUDE_MODEL if narration_source == "claude" else "Template")

    # 5.5 Synthesize TTS (LOCAL: eager; MODAL morning: eager; others: on-demand)
    summaries = parsed.get("cards", {})

    # Pin broadcast-time top_activity + best_window so the insight row and LLM
    # card text always reference the same point-in-time outdoor conditions.
    _oi = processed.get("outdoor_index", {})
    _segs = _oi.get("segments", {})
    _bw = max(_segs, key=lambda k: _segs[k]["score"]) if _segs else None
    _acts = _oi.get("activities", {})
    if _acts:
        _mx = max(v["score"] for v in _acts.values())
        _tied = [k for k, v in _acts.items() if v["score"] == _mx]
        _ta: str | None = "photography" if ("photography" in _tied and _mx >= 80) else _tied[0]
    else:
        _ta = None
    if _bw is not None:
        summaries["_best_window"] = _bw
    if _ta is not None:
        summaries["_top_activity"] = _ta

    if RUN_MODE == "LOCAL" or (RUN_MODE == "MODAL" and slot == "morning"):
        yield {"type": "log", "message": "Synthesising TTS audio\u2026"}
        try:
            full_audio_url = synthesise_with_cache(narration_text, lang, date_str, slot)
        except Exception as exc:
            logger.warning("TTS failed (%s) \u2014 player will fall back to on-demand.", exc)
            full_audio_url = None
        audio_urls = {"full_audio_url": full_audio_url}
    else:
        yield {"type": "log", "message": "Audio briefing TTS (deferred to on-demand)..."}
        audio_urls = {"full_audio_url": None}

    # 7. Save
    yield {"type": "log", "message": "Saving broadcast to history..."}
    logger.info("Saving to conversation history...")
    save_day(
        date_str=date_str,
        raw_data={
            "current":        current,
            "forecasts":      _serialize_forecasts(forecasts),
            "forecasts_7day": _serialize_forecasts(forecasts_7day),
            "aqi":            aqi,
        },
        processed_data=processed,
        narration_text=narration_text,
        paragraphs=paragraphs,
        metadata=metadata,
        audio_urls=audio_urls,
        summaries=summaries,
    )

    # Persist regen data to regen.json
    if regen_data:
        yield {"type": "log", "message": "Persisting regenerated meal/location database..."}
        logger.info("Regen data received, writing to regen.json")
        _persist_regen({"regen": {**regen_data, "updated_at": datetime.now(_TAIPEI_TZ).isoformat()}})

    # 8. Result
    result = {
        "date": date_str,
        "generated_at": datetime.now(_TAIPEI_TZ).isoformat(),
        "narration_source": narration_source,
        "narration_text": narration_text,
        "paragraphs": paragraphs,
        "metadata": metadata,
        "audio_urls": audio_urls,
        "processed_data": processed,
        "regen": regen_data,
        "slices": build_slices({
            "paragraphs": paragraphs,
            "metadata": metadata,
            "processed_data": processed,
            "summaries": summaries,
        }, lang=lang),
    }
    
    yield {"type": "log", "message": "Pipeline complete."}
    yield {"type": "result", "payload": result}


def _run_pipeline(date_str: str) -> dict:
    """Synchronous wrapper for on-demand calls."""
    last_result = None
    for step in _pipeline_steps(date_str):
        if step["type"] == "result":
            last_result = step["payload"]
    
    if not last_result:
        raise RuntimeError("Pipeline finished without result")
    return last_result


def validate_config():
    """Verify that all required API keys are present."""
    required_keys = {
        "CWA_API_KEY": config.CWA_API_KEY,
        "MOENV_API_KEY": config.MOENV_API_KEY,
        "GEMINI_API_KEY": config.GEMINI_API_KEY,
        "ANTHROPIC_API_KEY": config.ANTHROPIC_API_KEY,
    }
    missing = [k for k, v in required_keys.items() if not v]
    if missing:
        logger.warning(f"Startup Warning: Missing API keys for: {', '.join(missing)}")
    else:
        logger.info("Config validation: All required API keys present.")


def _serialize_forecasts(forecasts: dict) -> dict:
    """Make forecast data JSON-serializable (convert any non-serializable types)."""
    return json.loads(json.dumps(forecasts, default=str))


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    validate_config()
    app.run(
        host="0.0.0.0",
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
    )
