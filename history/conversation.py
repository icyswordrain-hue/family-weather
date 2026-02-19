"""
conversation.py — Read and write conversation history JSON in Cloud Storage.

History format (one file, keyed by date):
{
  "YYYY-MM-DD": {
    "generated_at": "ISO-8601 datetime",
    "raw_data": { ... },
    "processed_data": { ... },
    "narration_text": "...",
    "paragraphs": {
      "p1_current": "...",
      ...
      "p7_accountability": "..."
    },
    "metadata": {
      "meals_suggested": ["dish1", "dish2"],
      "gardening_tip_topic": "...",
      "location_suggested": "...",
      "activity_suggested": "..."
    },
    "audio_urls": {
      "full_audio_url": "...",
      "kids_audio_url": "..."
    }
  }
}
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from google.cloud import storage
from google.api_core.exceptions import NotFound

from config import GCS_BUCKET_NAME, GCS_HISTORY_KEY, TIMEZONE

logger = logging.getLogger(__name__)

_TAIPEI_TZ = timezone(timedelta(hours=8))


def load_history(days: int = 3) -> list[dict]:
    """
    Load the conversation history JSON from GCS and return the last N days.

    Returns a list of day dicts (oldest first), each being the value from
    the top-level date key. Returns [] if the history file does not exist.
    """
    try:
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(GCS_HISTORY_KEY)
        raw = blob.download_as_text(encoding="utf-8")
        history_map: dict[str, dict] = json.loads(raw)
    except NotFound:
        logger.info("No conversation history found in GCS — starting fresh")
        return []
    except Exception as exc:
        logger.warning("Could not load conversation history: %s", exc)
        return []

    # Sort dates and return the last N
    sorted_dates = sorted(history_map.keys())
    recent_dates = sorted_dates[-days:] if len(sorted_dates) >= days else sorted_dates
    return [history_map[d] for d in recent_dates]


def save_day(
    date_str: str,
    raw_data: dict,
    processed_data: dict,
    narration_text: str,
    paragraphs: dict[str, str],
    metadata: dict,
    audio_urls: dict[str, str],
) -> None:
    """
    Save today's broadcast record to the GCS history JSON.
    Merges with existing history (keeps all previous days).
    Prunes entries older than 30 days to keep file size small.
    """
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(GCS_HISTORY_KEY)

    # Load existing history
    try:
        raw = blob.download_as_text(encoding="utf-8")
        history_map: dict[str, dict] = json.loads(raw)
    except NotFound:
        history_map = {}
    except Exception as exc:
        logger.warning("Could not load existing history for merge: %s — starting fresh", exc)
        history_map = {}

    # Build today's entry
    history_map[date_str] = {
        "generated_at": datetime.now(_TAIPEI_TZ).isoformat(),
        "raw_data": raw_data,
        "processed_data": processed_data,
        "narration_text": narration_text,
        "paragraphs": paragraphs,
        "metadata": metadata,
        "audio_urls": audio_urls,
    }

    # Prune entries older than 30 days
    cutoff = _date_str_offset(-30)
    history_map = {k: v for k, v in history_map.items() if k >= cutoff}

    # Write back
    blob.upload_from_string(
        json.dumps(history_map, ensure_ascii=False, indent=2),
        content_type="application/json",
    )
    logger.info("Saved conversation history for %s", date_str)


def get_today_broadcast(date_str: str | None = None) -> Optional[dict]:
    """
    Return today's already-generated broadcast record, or None if not found.
    Used by the dashboard API to serve cached results without regenerating.
    """
    date_str = date_str or _today_str()
    history = load_history(days=30)
    for day in history:
        if day.get("generated_at", "")[:10] == date_str:
            return day
    return None


def _today_str() -> str:
    return datetime.now(_TAIPEI_TZ).strftime("%Y-%m-%d")


def _date_str_offset(days: int) -> str:
    """Return a date string N days from today (negative = past)."""
    from datetime import timedelta
    d = datetime.now(_TAIPEI_TZ) + timedelta(days=days)
    return d.strftime("%Y-%m-%d")
