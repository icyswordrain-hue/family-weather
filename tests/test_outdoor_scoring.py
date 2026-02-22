"""tests/test_outdoor_scoring.py — Unit tests for data/outdoor_scoring.py (TS3)."""
from data.outdoor_scoring import _grade_score, _score_conditions, OUTDOOR_WEIGHTS_GENERAL

# ── _grade_score ──────────────────────────────────────────────────────────────

def test_grade_excellent(): assert _grade_score(85) == ("A", "Excellent")
def test_grade_good():       assert _grade_score(70) == ("B", "Good")
def test_grade_boundary_b(): assert _grade_score(65) == ("B", "Good")
def test_grade_fair():       assert _grade_score(55) == ("C", "Fair")
def test_grade_poor():       assert _grade_score(40) == ("D", "Poor")
def test_grade_avoid():      assert _grade_score(10) == ("F", "Avoid")
def test_grade_zero():       assert _grade_score(0) == ("F", "Avoid")
def test_grade_perfect():    assert _grade_score(100) == ("A", "Excellent")

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
