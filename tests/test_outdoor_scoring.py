"""tests/test_outdoor_scoring.py — Unit tests for data/outdoor_scoring.py (TS3)."""
from data.outdoor_scoring import _grade_score, _score_conditions, OUTDOOR_WEIGHTS_GENERAL, OUTDOOR_WEIGHTS_BY_ACTIVITY

# ── _grade_score ──────────────────────────────────────────────────────────────

def test_grade_excellent(): assert _grade_score(85) == ("A", "Go out")
def test_grade_good():       assert _grade_score(70) == ("B", "Good to go")
def test_grade_boundary_b(): assert _grade_score(65) == ("B", "Good to go")
def test_grade_fair():       assert _grade_score(55) == ("C", "Manageable")
def test_grade_poor():       assert _grade_score(40) == ("D", "Think twice")
def test_grade_avoid():      assert _grade_score(10) == ("F", "Stay in")
def test_grade_zero():       assert _grade_score(0) == ("F", "Stay in")
def test_grade_perfect():    assert _grade_score(100) == ("A", "Go out")

# ── _score_conditions — heavy rain ────────────────────────────────────────────

HEAVY_RAIN = {
    "rain": 10.0, "pop": 50, "at": 22.0, "rh": 70.0,
    "ws": 2.0, "aqi": 40, "uvi": 3, "ground_wet": True, "vis": 20.0,
}

def test_score_heavy_rain_below_60():
    score, blockers, _ = _score_conditions(HEAVY_RAIN, OUTDOOR_WEIGHTS_GENERAL)
    assert score < 60

def test_score_heavy_rain_active_blocker():
    _, blockers, _ = _score_conditions(HEAVY_RAIN, OUTDOOR_WEIGHTS_GENERAL)
    assert "active_rain" in blockers

# ── _score_conditions — perfect day ──────────────────────────────────────────

PERFECT_DAY = {
    "rain": 0, "pop": 5, "at": 22.0, "rh": 60.0,
    "ws": 3.0, "aqi": 35, "uvi": 4, "ground_wet": False, "vis": 25.0,
}

def test_score_perfect_day_above_80():
    score, _, _ = _score_conditions(PERFECT_DAY, OUTDOOR_WEIGHTS_GENERAL)
    assert score > 80

def test_score_perfect_day_no_blockers():
    _, blockers, _ = _score_conditions(PERFECT_DAY, OUTDOOR_WEIGHTS_GENERAL)
    assert blockers == []

# ── _score_conditions — edge cases ────────────────────────────────────────────

def test_score_max_is_100():
    score, _, _ = _score_conditions(PERFECT_DAY, OUTDOOR_WEIGHTS_GENERAL)
    assert score <= 100

def test_score_min_is_0():
    bad = {"rain": 50, "pop": 95, "at": 42.0, "rh": 95.0,
           "ws": 25.0, "aqi": 300, "uvi": 12, "ground_wet": True, "vis": 0.1}
    score, _, _ = _score_conditions(bad, OUTDOOR_WEIGHTS_GENERAL)
    assert score == 0

def test_score_empty_conditions_is_100():
    """No conditions triggered → clean slate = 100."""
    score, blockers, cautions = _score_conditions({}, OUTDOOR_WEIGHTS_GENERAL)
    assert score == 100
    assert blockers == []
    assert cautions == []

# ── kite_flying activity ───────────────────────────────────────────────────────

KITE_WEIGHTS = {**OUTDOOR_WEIGHTS_GENERAL, **OUTDOOR_WEIGHTS_BY_ACTIVITY["kite_flying"]}

CALM_DAY = {
    "rain": 0, "pop": 5, "at": 22.0, "rh": 60.0,
    "ws": 0.5,  # Beaufort 0 — dead calm
    "aqi": 35, "uvi": 4, "ground_wet": False, "vis": 25.0,
}

BREEZY_DAY = {
    "rain": 0, "pop": 5, "at": 22.0, "rh": 60.0,
    "ws": 5.0,  # Beaufort 3 — gentle/moderate breeze, ideal for kites
    "aqi": 35, "uvi": 4, "ground_wet": False, "vis": 25.0,
}

def test_kite_calm_wind_penalized():
    """Beaufort 0 triggers calm_wind caution and drops score significantly."""
    score, _, cautions = _score_conditions(CALM_DAY, KITE_WEIGHTS)
    assert "calm_wind" in cautions
    assert score < 75

def test_kite_ideal_wind_high_score():
    """Beaufort 3 (5 m/s) is ideal kite wind — should score ≥80."""
    score, _, cautions = _score_conditions(BREEZY_DAY, KITE_WEIGHTS)
    assert "calm_wind" not in cautions
    assert score >= 80

def test_kite_wind_low_zero_in_general():
    """wind_low has no penalty in general weights (only kite_flying overrides it)."""
    assert OUTDOOR_WEIGHTS_GENERAL["wind_low"] == 0


# ── _extract_recent_activities ───────────────────────────────────────────────
from data.outdoor_scoring import _extract_recent_activities

def test_extract_recent_activities_empty():
    assert _extract_recent_activities([], days=7) == []

def test_extract_recent_activities_reads_metadata():
    history = [{"metadata": {"activity_suggested": "hiking"}}]
    assert "hiking" in _extract_recent_activities(history, days=7)

def test_extract_recent_activities_respects_window():
    history = [
        {"metadata": {"activity_suggested": "old_act"}},
        {"metadata": {"activity_suggested": "new_act"}},
    ]
    result = _extract_recent_activities(history, days=1)
    assert "new_act" in result
    assert "old_act" not in result

def test_extract_recent_activities_skips_missing():
    history = [{"metadata": {}}, {"metadata": {"activity_suggested": "cycling"}}]
    result = _extract_recent_activities(history, days=7)
    assert result == ["cycling"]
