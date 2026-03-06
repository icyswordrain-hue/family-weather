from __future__ import annotations

import json
import logging
import os
import sys
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

def _persist_regen(payload: dict) -> None:
    regen = payload.get("regen")
    if not regen:
        return
    if RUN_MODE in ("CLOUD", "MODAL"):
        from google.cloud import storage
        blob = storage.Client().bucket(config.GCS_BUCKET_NAME).blob(config.GCS_REGEN_PATH)
        blob.upload_from_string(
            json.dumps(regen, ensure_ascii=False, indent=2),
            content_type="application/json",
        )
    else:
        from pathlib import Path
        p = Path(f"{LOCAL_DATA_DIR}/regen.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(regen, ensure_ascii=False, indent=2)
        )

def _restore_regen_from_gcs() -> None:
    """Call on container startup before first request."""
    if RUN_MODE not in ("CLOUD", "MODAL"):
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
    from narration.tts_client import synthesise_with_cache
    url    = synthesise_with_cache(script, lang, date, slot)
    return jsonify({"url": url})

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
            resp = requests.get(modal_url, params={"date": date_str, "lang": lang})
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

    if slot == "midday":
        try:
            from data.fetch_cwa import fetch_current_conditions
            from history.conversation import load_broadcast
            current = fetch_current_conditions()
            m_broadcast = load_broadcast(date=date_str, slot="morning")
            morning = m_broadcast.get("processed_data", {}).get("current", {}) if m_broadcast else {}
            if morning:
                changed, reasons = _conditions_changed(current, morning)
                if not changed:
                    logger.info("Midday skip: conditions unchanged")
                    return jsonify({"status": "skipped", "broadcast": m_broadcast}), 200
                logger.info(f"Midday proceeding: {reasons}")
        except Exception as e:
            logger.warning(f"Midday skip check failed ({e}), running full pipeline")

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
    reasons = []
    c_temp = current.get("temp", 0)
    m_temp = morning.get("temp", 0)
    if abs(c_temp - m_temp) >= 3:
        reasons.append(f"temp {m_temp}→{c_temp}°C")
    if (current.get("precip_mm", 0) > 0) != (morning.get("precip_mm", 0) > 0):
        reasons.append("rain status changed")
    if set(current.get("alerts", [])) != set(morning.get("alerts", [])):
        reasons.append("alert state changed")
    if _aqi_category(current.get("aqi", 0)) != _aqi_category(morning.get("aqi", 0)):
        reasons.append("AQI category crossed boundary")
    if current.get("score_label") != morning.get("score_label"):
        reasons.append(f"outdoor score {morning.get('score_label')}→{current.get('score_label')}")
    if abs(current.get("dew_point", 0) - morning.get("dew_point", 0)) >= 3:
        reasons.append("dew point shift ≥3°C")
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

    # 1. Fetch raw data
    try:
        yield {"type": "log", "message": "Fetching CWA current conditions..."}
        logger.info("Fetching CWA current conditions...")
        current = fetch_current_conditions()

        yield {"type": "log", "message": "Fetching CWA forecasts..."}
        logger.info("Fetching CWA forecasts...")
        forecasts = fetch_all_forecasts()

        yield {"type": "log", "message": "Fetching CWA 7-day forecasts..."}
        logger.info("Fetching CWA 7-day forecasts...")
        forecasts_7day = fetch_all_forecasts_7day()

        yield {"type": "log", "message": "Fetching MOENV AQI..."}
        logger.info("Fetching MOENV AQI...")
        aqi = fetch_all_aqi()
    except Exception as exc:
        logger.error("Data fetch failed: %s", exc)
        yield {"type": "error", "message": f"Data Fetch Failed: {exc}"}
        return

    # 2. Load history
    yield {"type": "log", "message": "Loading conversation history..."}
    history = load_history(days=HISTORY_DAYS)

    # 3. Process data
    yield {"type": "log", "message": "Processing weather data & logic..."}
    logger.info("Processing data...")
    processed = process(current, forecasts, aqi, history, forecasts_7day)

    # 3b. Meal/Location Database Regen (14-day cycle)
    should_regen = check_regen_cycle(history, date_str, REGEN_CYCLE_DAYS)

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

    # 5. Extract paragraphs and metadata using v6 parser
    yield {"type": "log", "message": "Parsing narration structure & metadata (v6)..."}
    parsed = parse_narration_response(narration_text)
    paragraphs = parsed["paragraphs"]
    metadata = parsed["metadata"]
    regen_data = parsed["regen"]

    # Reconstruct "clean" narration text from parsed paragraphs to sync with TTS
    # This removes any LLM preamble or leftover markers like "P1:"
    narration_text = "\n\n".join(paragraphs.values())

    metadata["narration_source"] = narration_source
    metadata["narration_model"] = config.GEMINI_PRO_MODEL if narration_source == "gemini" else (config.CLAUDE_MODEL if narration_source == "claude" else "Template")

    # 5.5 Synthesize TTS (LOCAL: eager; MODAL morning: eager; others: on-demand)
    summaries = parsed.get("cards", {})
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
        raw_data={"current": current, "forecasts": _serialize_forecasts(forecasts), "aqi": aqi},
        processed_data=processed,
        narration_text=narration_text,
        paragraphs=paragraphs,
        metadata=metadata,
        audio_urls=audio_urls,
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
        }),
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
