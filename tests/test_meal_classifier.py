"""tests/test_meal_classifier.py — Unit tests for data/meal_classifier.py"""
from data.meal_classifier import _classify_meal_mood, _extract_recent_meals

# ── Fixtures ──────────────────────────────────────────────────────────────────

HOT_HUMID = {
    "Morning":   {"AT": 34.0, "RH": 90.0, "PoP6h": 10.0},
    "Afternoon": {"AT": 36.0, "RH": 90.0, "PoP6h": 10.0},
    "Evening":   {"AT": 33.0, "RH": 88.0, "PoP6h": 10.0},
}

WARM_PLEASANT = {
    "Morning":   {"AT": 24.0, "RH": 55.0, "PoP6h":  5.0},
    "Afternoon": {"AT": 27.0, "RH": 50.0, "PoP6h": 10.0},
    "Evening":   {"AT": 25.0, "RH": 55.0, "PoP6h":  5.0},
}

COLD_RAINY = {
    "Morning":   {"AT": 12.0, "RH": 90.0, "PoP6h": 80.0},
    "Afternoon": {"AT": 13.0, "RH": 85.0, "PoP6h": 70.0},
    "Evening":   {"AT": 11.0, "RH": 92.0, "PoP6h": 65.0},
}

VERY_COLD = {
    "Morning":   {"AT":  8.0, "RH": 65.0, "PoP6h": 10.0},
    "Afternoon": {"AT": 10.0, "RH": 60.0, "PoP6h":  5.0},
    "Evening":   {"AT":  7.0, "RH": 70.0, "PoP6h": 10.0},
}

# ── Meal Mood ─────────────────────────────────────────────────────────────────

def test_hot_humid_mood():
    result = _classify_meal_mood(HOT_HUMID)
    assert result["mood"] == "Hot & Humid"
    assert len(result["all_suggestions"]) > 0

def test_warm_pleasant_mood():
    result = _classify_meal_mood(WARM_PLEASANT)
    assert result["mood"] == "Warm & Pleasant"

def test_cold_rainy_mood_rainy():
    result = _classify_meal_mood(COLD_RAINY)
    assert result["is_rainy"] is True
    assert result["mood"] in ("Cool & Damp", "Cold")

def test_very_cold_mood():
    result = _classify_meal_mood(VERY_COLD)
    assert result["mood"] == "Cold"
    assert len(result["all_suggestions"]) > 0

def test_result_has_avg_fields():
    result = _classify_meal_mood(WARM_PLEASANT)
    assert "avg_at" in result
    assert "avg_rh" in result
    assert isinstance(result["avg_at"], float)

def test_empty_segments():
    result = _classify_meal_mood({})
    # Should still return a dict with a mood (defaulting to cold)
    assert "mood" in result

# ── Recent Meals ──────────────────────────────────────────────────────────────

def test_extract_recent_meals_empty():
    assert _extract_recent_meals([], days=3) == []

def test_extract_recent_meals_reads_metadata():
    history = [{"metadata": {"meals_suggested": ["牛肉麵"]}}]
    assert "牛肉麵" in _extract_recent_meals(history, days=3)

def test_extract_recent_meals_respects_window():
    history = [
        {"metadata": {"meals_suggested": ["old meal"]}},
        {"metadata": {"meals_suggested": ["new meal"]}},
    ]
    # With days=1, only last entry
    result = _extract_recent_meals(history, days=1)
    assert "new meal" in result
    assert "old meal" not in result

def test_extract_recent_meals_missing_metadata():
    history = [{"no_metadata_key": {}}]
    assert _extract_recent_meals(history, days=3) == []
