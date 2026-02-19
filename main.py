"""
main.py — Flask application entry point for the Family Weather Dashboard.

Routes:
  GET  /                → serves the dashboard HTML
  GET  /api/broadcast   → returns today's broadcast JSON (cached or fresh)
  POST /api/refresh     → triggers a full data fetch + narration + TTS pipeline
  GET  /api/health      → health check for Cloud Run
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone, timedelta

from flask import Flask, jsonify, render_template, request, abort

import config
from data.fetch_cwa import fetch_current_conditions, fetch_all_forecasts
from data.fetch_moenv import fetch_all_aqi
from data.processor import process
from narration.prompt_builder import build_prompt
from narration.gemini_client import generate_narration, extract_paragraphs, extract_metadata
from narration.tts_client import synthesize_and_upload
from history.conversation import load_history, save_day, get_today_broadcast
from web.slices import build_slices

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder="web/templates",
    static_folder="web/static",
)

_TAIPEI_TZ = timezone(timedelta(hours=8))


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the family dashboard."""
    return render_template("dashboard.html")


@app.route("/api/health")
def health():
    """Health check endpoint required by Cloud Run."""
    return jsonify({"status": "ok", "timestamp": datetime.now(_TAIPEI_TZ).isoformat()})


@app.route("/api/broadcast")
def get_broadcast():
    """
    Return today's broadcast as JSON.
    Includes the full narration text, per-paragraph text, audio URLs,
    and pre-built per-profile slices.

    Query params:
      date (optional): YYYY-MM-DD — defaults to today (Taipei time)
    """
    date_str = request.args.get("date") or datetime.now(_TAIPEI_TZ).strftime("%Y-%m-%d")

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
    Scheduled endpoint (called by Cloud Scheduler at 05:30, 11:30, 17:30).
    Runs the full pipeline and returns the new broadcast JSON.
    """
    # Optionally accept a date override in the JSON body (useful for back-filling)
    body = request.get_json(silent=True) or {}
    date_str = body.get("date") or datetime.now(_TAIPEI_TZ).strftime("%Y-%m-%d")

    try:
        result = _run_pipeline(date_str)
        return jsonify(result)
    except Exception as exc:
        logger.error("Pipeline error: %s", exc, exc_info=True)
        return jsonify({"error": str(exc)}), 500


# ── Core pipeline ─────────────────────────────────────────────────────────────

def _run_pipeline(date_str: str) -> dict:
    """
    Full data-fetch → process → narrate → TTS → save pipeline.
    Returns the complete broadcast dict.
    """
    logger.info("Starting pipeline for %s", date_str)

    # 1. Fetch raw data
    logger.info("Fetching CWA current conditions...")
    current = fetch_current_conditions()

    logger.info("Fetching CWA forecasts...")
    forecasts = fetch_all_forecasts()

    logger.info("Fetching MOENV AQI...")
    aqi = fetch_all_aqi()

    # 2. Load history for context
    history = load_history(days=3)

    # 3. Process data
    logger.info("Processing data...")
    processed = process(current, forecasts, aqi, history)

    # 4. Build Gemini prompt
    logger.info("Building narration prompt...")
    messages = build_prompt(processed, history, today_date=date_str)

    # 5. Generate narration
    logger.info("Generating narration via Gemini...")
    narration_text = generate_narration(messages)

    # 6. Extract paragraphs and metadata
    paragraphs = extract_paragraphs(narration_text)
    meal_suggestions = processed.get("meal_mood", {}).get("all_suggestions", [])
    metadata = extract_metadata(narration_text, meal_suggestions)

    # 7. TTS + upload
    logger.info("Synthesizing speech and uploading to GCS...")
    audio_urls = synthesize_and_upload(narration_text, date_str=date_str)

    # 8. Save to history
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

    # 9. Build and return full result
    result = {
        "date": date_str,
        "generated_at": datetime.now(_TAIPEI_TZ).isoformat(),
        "narration_text": narration_text,
        "paragraphs": paragraphs,
        "metadata": metadata,
        "audio_urls": audio_urls,
        "slices": build_slices({
            "paragraphs": paragraphs,
            "metadata": metadata,
            "processed_data": processed,
        }),
    }

    logger.info("Pipeline complete for %s", date_str)
    return result


def _serialize_forecasts(forecasts: dict) -> dict:
    """Make forecast data JSON-serializable (convert any non-serializable types)."""
    return json.loads(json.dumps(forecasts, default=str))


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
    )
