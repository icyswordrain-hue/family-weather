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
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

from flask import Flask, jsonify, render_template, request, abort, Response, stream_with_context

from config import RUN_MODE

import config
from config import LOCAL_DATA_DIR, HISTORY_DAYS, REGEN_CYCLE_DAYS
from data.fetch_cwa import fetch_current_conditions, fetch_all_forecasts, fetch_all_forecasts_7day
from data.fetch_moenv import fetch_all_aqi
from data.weather_processor import process
from narration.fallback_narrator import build_narration
from narration.llm_prompt_builder import build_prompt

from narration.tts_client import synthesize_and_upload
from history.conversation import load_history, save_day, get_today_broadcast
from web.routes import build_slices
from backend.pipeline import (
    check_regen_cycle,
    generate_narration_with_fallback,
    run_parallel_summarization,
)

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

    if RUN_MODE == "CLOUD":
        # Proxy to Modal
        modal_url = os.environ.get("MODAL_BROADCAST_URL")
        if not modal_url:
            return jsonify({"error": "MODAL_BROADCAST_URL not configured"}), 500
        
        try:
            resp = requests.get(modal_url, params={"date": date_str})
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
    slices = build_slices(cached)
    return jsonify({**cached, "slices": slices})


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

    if RUN_MODE == "CLOUD":
        # Proxy to Modal
        modal_url = os.environ.get("MODAL_REFRESH_URL")
        if not modal_url:
            return jsonify({"error": "MODAL_REFRESH_URL not configured"}), 500
            
        try:
            # Proxy the streaming response from Modal
            resp = requests.post(modal_url, json={"date": date_str, "provider": provider}, stream=True)
            return Response(
                stream_with_context(resp.iter_lines()),
                content_type=resp.headers.get('content-type', 'application/x-ndjson')
            )
        except Exception as e:
            logger.error("Failed to proxy refresh to Modal: %s", e)
            return jsonify({"error": str(e)}), 500

    def generate():
        try:
            for step in _pipeline_steps(date_str, provider_override=provider):
                yield json.dumps(step) + "\n"
        except Exception as exc:
            logger.error("Pipeline error: %s", exc, exc_info=True)
            yield json.dumps({"type": "error", "message": str(exc)}) + "\n"

    return Response(stream_with_context(generate()), mimetype='application/x-ndjson')


# ── Core pipeline ─────────────────────────────────────────────────────────────

def _pipeline_steps(date_str: str, provider_override: str | None = None):
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
        narration_provider, processed, history, date_str
    )
    yield {"type": "log", "message": "Narration generated."}

    # 5. Extract paragraphs and metadata using v6 parser
    yield {"type": "log", "message": "Parsing narration structure & metadata (v6)..."}
    from narration.llm_prompt_builder import parse_narration_response
    
    parsed = parse_narration_response(narration_text)
    paragraphs = parsed["paragraphs"]
    metadata = parsed["metadata"]
    regen_data = parsed["regen"]

    # Reconstruct "clean" narration text from parsed paragraphs to sync with TTS
    # This removes any LLM preamble or leftover markers like "P1:"
    narration_text = "\n\n".join(paragraphs.values())

    metadata["narration_source"] = narration_source
    metadata["narration_model"] = config.GEMINI_PRO_MODEL if narration_source == "gemini" else (config.CLAUDE_MODEL if narration_source == "claude" else "Template")

    # 5.5 Parallel Processing: Lifestyle Summaries, AQI Summary, and TTS
    yield {"type": "log", "message": "Parallel processing: Summarization & TTS..."}
    from concurrent.futures import ThreadPoolExecutor
    from narration.tts_client import synthesize_and_upload as _synth

    aqi_forecast_raw = aqi.get("forecast", {}).get("content", "")

    with ThreadPoolExecutor(max_workers=2) as _tts_exec:
        future_tts = _tts_exec.submit(_synth, narration_text, date_str=date_str)
        yield {"type": "log", "message": "Collecting Summarization..."}
        summaries, aqi_summary_en = run_parallel_summarization(paragraphs, aqi_forecast_raw)
        yield {"type": "log", "message": "Collecting TTS audio..."}
        audio_urls = future_tts.result()

    if aqi_summary_en:
        yield {"type": "log", "message": "AQI summary collected."}
        aqi["forecast"]["summary_en"] = aqi_summary_en
        if "aqi_forecast" in processed:
            processed["aqi_forecast"]["summary_en"] = aqi_summary_en

    yield {"type": "log", "message": "Parallel processing complete."}

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
        regen_path = os.path.join(LOCAL_DATA_DIR, "regen.json")
        try:
            os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
            with open(regen_path, "w", encoding="utf-8") as _f:
                json.dump({
                    **regen_data,
                    "updated_at": datetime.now(_TAIPEI_TZ).isoformat(),
                }, _f, ensure_ascii=False, indent=2)
            logger.info("Regen data written to %s", regen_path)
        except Exception as exc:
            logger.warning("Failed to write regen.json: %s", exc)

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
