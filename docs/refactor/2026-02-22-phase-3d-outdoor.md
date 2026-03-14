# Task 6: Extract outdoor_scoring.py (Agent D) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Execute Task 6: Extract outdoor_scoring.py (Agent D) as part of the Phase 3 parallel extraction stage.

**Architecture:** Extract specific domain logic from `weather_processor.py` into a new focused module.

**Tech Stack:** Python, Pytest

---

## Task 6: Extract `data/outdoor_scoring.py` (A1 — Agent D)

> **Parallel with Tasks 3, 4, 5.**

**Extract from `weather_processor.py`:**

| Symbol | Lines | Description |
|--------|-------|-------------|
| `GRADE_THRESHOLDS` | 120–126 | Score → letter grade |
| `OUTDOOR_WEIGHTS_GENERAL` | 128–142 | Default penalty weights |
| `OUTDOOR_WEIGHTS_BY_ACTIVITY` | 145–195 | Per-activity overrides |
| `_grade_score()` | 906–911 | Score → (grade, label) |
| `_score_conditions()` | 914–976 | Declarative rule engine |
| `_compute_outdoor_index()` | 979+ | Main orchestrator |
| `_compute_solar_load()` | 877–893 | UV + cloud → radiant load |
| `_classify_outdoor_mood()` | (grep for it) | Mood → location recs |
| `_extract_recent_locations()` | (grep for it) | Recent location history |

**New file: `data/outdoor_scoring.py`**
- Imports `OUTDOOR_LOCATIONS` from `data.location_loader`
- Imports scales from `data.scales`

**Tests (`tests/test_outdoor_scoring.py`):**
```python
from data.outdoor_scoring import _grade_score, _score_conditions, OUTDOOR_WEIGHTS_GENERAL

def test_grade_excellent(): assert _grade_score(85) == ("A", "Excellent")
def test_grade_fail():       assert _grade_score(10) == ("F", "Avoid")
def test_grade_boundary():   assert _grade_score(65) == ("B", "Good")

def test_score_heavy_rain():
    conditions = {"rain": 10.0, "pop": 50, "at": 22.0, "rh": 70.0,
                  "ws": 2.0, "aqi": 40, "uvi": 3, "ground_wet": True, "vis": 20.0}
    score, blockers, _ = _score_conditions(conditions, OUTDOOR_WEIGHTS_GENERAL)
    assert score < 60
    assert "active_rain" in blockers

def test_score_perfect_day():
    conditions = {"rain": 0, "pop": 5, "at": 22.0, "rh": 60.0,
                  "ws": 3.0, "aqi": 35, "uvi": 4, "ground_wet": False, "vis": 25.0}
    score, blockers, cautions = _score_conditions(conditions, OUTDOOR_WEIGHTS_GENERAL)
    assert score > 80
    assert blockers == []
```

**Commit:** `refactor(outdoor): extract outdoor scoring to data/outdoor_scoring.py (A1-partial)`

---
