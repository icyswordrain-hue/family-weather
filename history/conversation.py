"""
conversation.py — Read and write conversation history JSON (local file / Modal Volume).

History format v2 (one file, keyed by date):
{
  "YYYY-MM-DD": {
    "generated_at": "ISO-8601 datetime",
    "schema_version": 2,
    "raw_data": { ... },
    "processed_data": { ... },
    "tts_generated_at": "ISO-8601 datetime or null",
    "langs": {
      "en": {
        "narration_text": "...",
        "paragraphs": { "p1_current": "...", ... },
        "metadata": { ... },
        "summaries": { ... },
        "audio_urls": { "full_audio_url": "..." }
      },
      "zh-TW": { ... }
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

from config import LOCAL_DATA_DIR

logger = logging.getLogger(__name__)

_TAIPEI_TZ = timezone(timedelta(hours=8))


# ── Schema Migration ─────────────────────────────────────────────────────────

def _normalize_broadcast(entry: dict) -> dict:
    """Ensure a broadcast entry is in v2 (langs) format.

    V1 entries have flat narration_text/paragraphs/metadata/audio_urls/summaries.
    V2 entries nest these under langs[lang].
    """
    if not entry or entry.get("schema_version") == 2:
        return entry

    # V1 → V2 migration: assume old entries are zh-TW (the historical default)
    lang_data = {
        "narration_text": entry.get("narration_text", ""),
        "paragraphs": entry.get("paragraphs", {}),
        "metadata": entry.get("metadata", {}),
        "summaries": entry.get("summaries", {}),
        "audio_urls": entry.get("audio_urls", {}),
    }
    return {
        "generated_at": entry.get("generated_at"),
        "schema_version": 2,
        "raw_data": entry.get("raw_data", {}),
        "processed_data": entry.get("processed_data", {}),
        "tts_generated_at": entry.get("generated_at"),  # assume TTS was generated at same time
        "langs": {"zh-TW": lang_data},
    }


def get_lang_data(broadcast: dict, lang: str) -> dict:
    """Extract language-specific sub-dict from a v2 broadcast.

    Falls back to any available language if the requested one is missing.
    """
    if not broadcast:
        return {}
    langs = broadcast.get("langs", {})
    if lang in langs:
        return langs[lang]
    # Fallback: return whichever language exists
    if langs:
        return next(iter(langs.values()))
    return {}


# ── Load / Save ──────────────────────────────────────────────────────────────

def load_history(days: int = 3) -> list[dict]:
    """
    Load the conversation history JSON and return the last N days.

    Returns a list of day dicts (oldest first), each being the value from
    the top-level date key. Returns [] if the history file does not exist.
    All entries are normalized to v2 schema.
    """
    history_map = _load_history_map()
    if not history_map:
        return []

    # Sort dates and return the last N
    sorted_dates = sorted(history_map.keys())
    recent_dates = sorted_dates[-days:] if len(sorted_dates) >= days else sorted_dates
    return [_normalize_broadcast(history_map[d]) for d in recent_dates]


def _load_history_map() -> dict[str, dict]:
    """Load the full history map from local/volume storage."""
    return _load_history_map_local()


def save_day(
    date_str: str,
    raw_data: dict,
    processed_data: dict,
    langs: dict[str, dict],
    tts_generated_at: str | None = None,
) -> None:
    """
    Save today's broadcast record (v2 schema) to the history JSON.
    Merges with existing history (keeps all previous days).
    Prunes entries older than 30 days to keep file size small.

    Args:
        langs: {"en": {"narration_text":..., "paragraphs":..., "metadata":...,
                        "summaries":..., "audio_urls":...}, "zh-TW": {...}}
        tts_generated_at: ISO-8601 timestamp of last TTS synthesis (or None).
    """
    history_map = _load_history_map_local()

    # Build today's entry (v2 schema)
    history_map[date_str] = {
        "generated_at": datetime.now(_TAIPEI_TZ).isoformat(),
        "schema_version": 2,
        "raw_data": raw_data,
        "processed_data": processed_data,
        "tts_generated_at": tts_generated_at,
        "langs": langs,
    }

    # Prune entries older than 30 days
    cutoff = _date_str_offset(-30)
    history_map = {k: v for k, v in history_map.items() if k >= cutoff}

    _save_history_local(history_map)
    logger.info("Saved conversation history for %s", date_str)


def get_today_broadcast(date_str: str | None = None) -> Optional[dict]:
    """
    Return today's already-generated broadcast record, or None if not found.
    Used by the dashboard API to serve cached results without regenerating.
    Always returns v2-normalized entries.
    """
    date_str = date_str or _today_str()
    history_map = _load_history_map()
    entry = history_map.get(date_str)
    return _normalize_broadcast(entry) if entry else None


def load_broadcast(date_str: str, slot: str = "morning") -> Optional[dict]:
    """
    Alias for get_today_broadcast to support legacy midday skip check in app.py.
    Currently ignore 'slot' as storage schema is date-keyed.
    Always returns v2-normalized entries.
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
