"""meal_classifier.py — Weather-based meal mood classification using flat meals.json catalogue."""

import json
import os
from typing import Optional

try:
    from config import (
        MEAL_FALLBACK_DISH,
        CLIMATE_TEMP_HOT,
        CLIMATE_RH_HOT,
    )
except ImportError:
    MEAL_FALLBACK_DISH = "滷肉飯 (lǔ ròu fàn)"
    CLIMATE_TEMP_HOT = 30
    CLIMATE_RH_HOT = 70

_MEALS_PATH = os.path.join(os.path.dirname(__file__), "meals.json")
_ALL_MEALS: list[dict] = []


def _load_meals() -> list[dict]:
    global _ALL_MEALS
    if not _ALL_MEALS:
        with open(_MEALS_PATH, "r", encoding="utf-8") as f:
            _ALL_MEALS = json.load(f)
    return _ALL_MEALS


def _classify_meal_mood(segmented: dict[str, Optional[dict]]) -> dict:
    """
    Classify the day into one of four meal moods using daytime segments.
    Uses Afternoon as the primary driver, with Morning as secondary.
    Returns all matching meals from the flat catalogue for the detected mood.
    """
    ats = []
    rhs = []
    is_rainy = False

    for seg_name in ["Morning", "Afternoon", "Evening"]:
        seg = segmented.get(seg_name)
        if seg:
            if seg.get("AT") is not None:
                ats.append(seg["AT"])
            if seg.get("RH") is not None:
                rhs.append(seg["RH"])
            if (seg.get("PoP6h") or 0) >= 61:
                is_rainy = True

    avg_at = sum(ats) / len(ats) if ats else 20.0
    avg_rh = sum(rhs) / len(rhs) if rhs else 60.0

    if avg_at >= CLIMATE_TEMP_HOT and avg_rh >= CLIMATE_RH_HOT:
        mood = "Hot & Humid"
    elif avg_at >= 22 and avg_rh < CLIMATE_RH_HOT:
        mood = "Warm & Pleasant"
    elif avg_at >= 15 or is_rainy:
        mood = "Cool & Damp"
    else:
        mood = "Cold"

    all_meals = _load_meals()
    mood_meals = [m for m in all_meals if mood in m.get("moods", [])]

    # Backward-compatible flat string list for existing code + tests
    suggestions = [m["name"] for m in mood_meals]

    return {
        "mood": mood,
        "avg_at": round(float(avg_at), 1),
        "avg_rh": round(float(avg_rh), 1),
        "is_rainy": is_rainy,
        "all_suggestions": suggestions,
        "all_meals_detail": mood_meals,
    }


def _extract_recent_meals(history: list[dict], days: int = 3) -> list[str]:
    """Extract meal suggestions from the last N days of history."""
    meals = []
    for day in history[-days:]:
        day_meals = day.get("metadata", {}).get("meals_suggested", [])
        meals.extend(day_meals)
    return meals
