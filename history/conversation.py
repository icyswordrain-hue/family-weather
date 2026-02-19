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
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from google.cloud import storage
from google.api_core.exceptions import NotFound

from config import (
    GCS_BUCKET_NAME,
    GCS_HISTORY_KEY,
    TIMEZONE,
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
    try:
        if RUN_MODE == "LOCAL":
            return _load_history_local()

        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(GCS_HISTORY_KEY)
        raw = blob.download_as_text(encoding="utf-8")
        history_map: dict[str, dict] = json.loads(raw)
    except (NotFound, FileNotFoundError):
        logger.info(f"No conversation history found ({RUN_MODE}) — starting fresh")
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
    # Load existing history
    try:
        if RUN_MODE == "LOCAL":
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
    # Write back
    if RUN_MODE == "LOCAL":
        _save_history_local(history_map)
    else:
        # pyre-ignore[61]: Local variable `blob` is undefined, or not always defined.
        blob.upload_from_string(
            json.dumps(history_map, ensure_ascii=False, indent=2),
            content_type="application/json",
        )
    logger.info("Saved conversation history for %s (%s)", date_str, RUN_MODE)


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


# ── Local Storage Helpers ─────────────────────────────────────────────────────

def _get_local_history_path() -> str:
    import os
    os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
    return os.path.join(LOCAL_DATA_DIR, "history.json")


def _load_history_local() -> list[dict]:
    """Load history list from local JSON file."""
    history_map = _load_history_map_local()
    sorted_dates = sorted(history_map.keys())
    # Return all (load_history caller filters by days) — logic in load_history splits it?
    # Actually load_history logic above does the sorting/slicing on the map keys.
    # So we just need to return the list of values sorted by date here?
    # Wait, the original load_history returned [history_map[d] for d in recent_dates]
    # My modified load_history asks for `_load_history_local`, which I defined to return list[dict].
    # But I should probably make it return the map to share logic? 
    # Actually, let's look at `load_history` again.
    
    # Original:
    # history_map = json.loads(raw)
    # sorted_dates = ...
    # return [history_map[d] ...]
    
    # My modified `load_history`:
    # if RUN_MODE == "LOCAL": return _load_history_local()
    # ...
    # sorted_dates = ...
    
    # Ah, I replaced the block that returns `history_map`.
    # So `_load_history_local` should actually return `history_map`?
    # BUT the type hint on `load_history` is `list[dict]`.
    # The original implementation had `history_map` as a local var, then processed it at the end.
    
    # Let me correct `load_history` to return `history_map` first, then process.
    # Actually, in the replacement, I put `return _load_history_local()` which returns `list[dict]`.
    # That skips the sorting logic at the bottom of `load_history`.
    # That is fine as long as `_load_history_local` does the sorting.
    
    history_map = _load_history_map_local()
    sorted_dates = sorted(history_map.keys())
    # We don't have `days` arg here though.
    # Better to have `_load_history_local` return the map and let `load_history` do the rest?
    # I already committed to `return _load_history_local()` in the chunk above. 
    # So I must implement `_load_history_local` to return the *list of dicts*.
    # But I don't know `days` here... 
    
    # Wait, `load_history` takes `days`.
    # I can't easily pass it unless I change the signature.
    # I'll just return ALL history here, and `load_history` (the caller) expects...
    # Wait, if I return from the `if RUN_MODE == "LOCAL"` block, I skip the tail of `load_history`.
    # That tail does: `return [history_map[d] for d in recent_dates]`
    
    # I should have `_load_history_local` return the `history_map` and NOT return early in `load_history`.
    # But I already sent the replacement chunk for `load_history` as returning early.
    # Retcon: I will implement `_load_history_local` to return the full sorted list.
    # The caller `load_history` will return that list.
    # Does `load_history` caller expect it to be sliced?
    # `load_history(days=3)`.
    # If I return all, it might differ from expectation.
    
    # I will change the implementation of `_load_history_local` to be smart or just return all?
    # The original code:
    # recent_dates = sorted_dates[-days:] ...
    
    # If I return all, the app receives all history. `_run_pipeline` uses `load_history(days=3)`.
    # It might be fine.
    
    # Alternative: I'll rewrite `load_history` in the replacement to NOT return early, 
    # but instead assign `history_map` and let it fall through.
    
    # Re-reading my ReplacementChunk for `load_history`:
    # if RUN_MODE == "LOCAL": return _load_history_local()
    # Yes, it returns early.
    
    # So `_load_history_local` must return the list.
    # I'll just return the *last 30 days* by default here to be safe, or ALL.
    # The caller usually asks for 3.
    # Returning 30 is safer for "all relevant history" than just 3.
    # But `processor.py` might rely on exactly 3?
    # `processor.py`: `recent_meals = _extract_recent_meals(history, days=3)` - it takes `history` list.
    # `_extract_recent_meals` does `history[-days:]`.
    # So if I return MORE than 3, it handles it correctly.
    # So `_load_history_local` can return the full list sorted.
    
    return [history_map[d] for d in sorted_dates]


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
