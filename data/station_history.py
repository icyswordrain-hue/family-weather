"""
station_history.py — Read-side access to station_history.jsonl.

Provides time-windowed queries and trend calculations over the local
observation cache written by fetch_cwa.fetch_current_conditions().
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from config import STATION_HISTORY_PATH

logger = logging.getLogger(__name__)
_TZ8 = timezone(timedelta(hours=8))


def load_recent_station_history(hours: int = 24) -> list[dict]:
    """Return JSONL records from the last `hours` hours, oldest first."""
    if not STATION_HISTORY_PATH.exists():
        return []
    cutoff = datetime.now(_TZ8) - timedelta(hours=hours)
    records = []
    with STATION_HISTORY_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                ts = r.get("fetched_at") or r.get("obs_time")
                if ts and datetime.fromisoformat(ts) >= cutoff:
                    records.append(r)
            except Exception:
                pass
    return sorted(records, key=lambda r: r.get("fetched_at", ""))


def pressure_change_24h(history: list[dict]) -> float | None:
    """hPa change from oldest to newest record in the list.
    Positive = rising, negative = falling.
    Returns None if fewer than 2 records have a PRES reading."""
    pressures = [r["PRES"] for r in history if r.get("PRES") is not None]
    if len(pressures) < 2:
        return None
    return round(pressures[-1] - pressures[0], 1)
