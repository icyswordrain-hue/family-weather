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
      "full_audio_url": "..."
    }
  }
}
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from google.cloud import storage
from google.api_core.exceptions import NotFound

from config import (
    GCS_BUCKET_NAME,
    GCS_HISTORY_KEY,
    RUN_MODE,
    LOCAL_DATA_DIR,
)

logger = logging.getLogger(__name__)

_TAIPEI_TZ = timezone(timedelta(hours=8))


def load_history(days: int = 3) -> list[dict]:
    """
    Load the conversation history JSON from GCS and return the last N days.

    Returns a list of day dicts (oldest first), each being the value from
    the top-level date key. Returns [] if the history file does not exist.
    """
    history_map = _load_history_map()
    if not history_map:
        return []

    # Sort dates and return the last N
    sorted_dates = sorted(history_map.keys())
    recent_dates = sorted_dates[-days:] if len(sorted_dates) >= days else sorted_dates
    return [history_map[d] for d in recent_dates]


def _load_history_map() -> dict[str, dict]:
    """Unified helper to load the full history map from GCS or Local."""
    try:
        if RUN_MODE in ("LOCAL", "MODAL"):
            return _load_history_map_local()

        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(GCS_HISTORY_KEY)
        raw = blob.download_as_text(encoding="utf-8")
        return json.loads(raw)
    except (NotFound, FileNotFoundError):
        logger.info(f"No conversation history found ({RUN_MODE}) — starting fresh")
        return {}
    except Exception as exc:
        logger.warning("Could not load conversation history: %s", exc)
        return {}


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
    # Load existing history
    try:
        if RUN_MODE in ("LOCAL", "MODAL"):
            history_map = _load_history_map_local()
        else:
            client = storage.Client()
            bucket = client.bucket(GCS_BUCKET_NAME)
            blob = bucket.blob(GCS_HISTORY_KEY)
            
            try:
                raw = blob.download_as_text(encoding="utf-8")
                history_map: dict[str, dict] = json.loads(raw)
            except NotFound:
                history_map = {}

    except Exception as exc:
        logger.warning("Could not load existing history for merge: %s — starting fresh", exc)
        history_map = {}
        # Ensure blob is defined for the subsequent upload if we are in non-local mode
        if RUN_MODE not in ("LOCAL", "MODAL"):
            try:
                client = storage.Client()
                bucket = client.bucket(GCS_BUCKET_NAME)
                blob = bucket.blob(GCS_HISTORY_KEY)
            except Exception:
                # If we still can't get a blob, we might have to just log it 
                # but for simplicity of this fix we'll let it be handled later or just define it as None
                blob = None

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
    if RUN_MODE in ("LOCAL", "MODAL"):
        _save_history_local(history_map)
    else:
        # history_map contains everything
        if blob:
            blob.upload_from_string(json.dumps(history_map, indent=2, ensure_ascii=False), content_type="application/json")
        else:
            logger.error("Could not save history: blob is not initialized")
    logger.info("Saved conversation history for %s (%s)", date_str, RUN_MODE)


def get_today_broadcast(date_str: str | None = None) -> Optional[dict]:
    """
    Return today's already-generated broadcast record, or None if not found.
    Used by the dashboard API to serve cached results without regenerating.
    """
    date_str = date_str or _today_str()
    history_map = _load_history_map()
    return history_map.get(date_str)


def load_broadcast(date_str: str, slot: str = "morning") -> Optional[dict]:
    """
    Alias for get_today_broadcast to support legacy midday skip check in app.py.
    Currently ignore 'slot' as storage schema is date-keyed.
    """
    return get_today_broadcast(date_str)


def _today_str() -> str:
    return datetime.now(_TAIPEI_TZ).strftime("%Y-%m-%d")


def _date_str_offset(days: int) -> str:
    """Return a date string N days from today (negative = past)."""
    from datetime import timedelta
    d = datetime.now(_TAIPEI_TZ) + timedelta(days=days)
    return d.strftime("%Y-%m-%d")


# ── Local Storage Helpers ─────────────────────────────────────────────────────

def _get_local_history_path() -> str:
    import os
    os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
    return os.path.join(LOCAL_DATA_DIR, "history.json")


def _load_history_local() -> list[dict]:
    """
    Load all history entries from the local JSON file, sorted chronologically.

    Returns the full history list; callers that need a slice (e.g. last N days)
    should truncate the result themselves using ``history[-n:]``.
    """
    history_map = _load_history_map_local()
    return [history_map[d] for d in sorted(history_map.keys())]



def _load_history_map_local() -> dict[str, dict]:
    path = _get_local_history_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Failed to read local history: %s", exc)
        return {}


def _save_history_local(history_map: dict[str, dict]) -> None:
    path = _get_local_history_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history_map, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.error("Failed to write local history: %s", exc)
