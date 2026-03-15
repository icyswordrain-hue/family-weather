"""backend/cache.py — Simple TTL-based narration cache."""
from __future__ import annotations
from cachetools import TTLCache

_WX_BUCKETS = {
    "sunny": "Sunny", "clear": "Sunny",
    "rain": "Rain", "shower": "Rain", "drizzle": "Rain", "storm": "Rain",
    "cloudy": "Cloudy", "overcast": "Cloudy", "fog": "Cloudy", "mist": "Cloudy",
}

def _classify_wx(weather_text: str) -> str:
    low = weather_text.lower()
    for kw, bucket in _WX_BUCKETS.items():
        if kw in low:
            return bucket
    return "Other"

def _classify_time(hour: int) -> str:
    if 6 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"

def _temp_bucket(temp_c: float) -> int:
    """Round temperature to nearest 3°C bucket (matches ±3°C change threshold)."""
    return round(temp_c / 3) * 3

def make_cache_key(lang: str, city: str, weather_text: str, time_of_day: str,
                   temp_c: float = 0, rain: bool = False) -> str:
    """
    Conditions-aware cache key: invalidates when weather actually changes.
    temp_c bucketed to 3°C intervals (matches the old ±3°C condition-change threshold).
    rain flag captures precipitation onset/cessation.
    """
    wx = _classify_wx(weather_text)
    tb = _temp_bucket(temp_c) if temp_c else 0
    rf = "rain" if rain else "dry"
    return f"{lang}_{city}_{wx}_{tb}c_{rf}_{time_of_day}".lower()

class NarrationCache:
    def __init__(self, ttl_seconds: int = 1800):
        self._store: TTLCache = TTLCache(maxsize=128, ttl=ttl_seconds)

    def get(self, key: str) -> tuple[str, str] | None:
        return self._store.get(key)

    def set(self, key: str, value: tuple[str, str]) -> None:
        self._store[key] = value

    def clear(self) -> None:
        self._store.clear()
