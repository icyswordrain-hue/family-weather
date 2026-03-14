# Task 5: Extract meal_classifier.py (Agent C) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Execute Task 5: Extract meal_classifier.py (Agent C) as part of the Phase 3 parallel extraction stage.

**Architecture:** Extract specific domain logic from `weather_processor.py` into a new focused module.

**Tech Stack:** Python, Pytest

---

## Task 5: Extract `data/meal_classifier.py` (A1 — Agent C)

> **Parallel with Tasks 3, 4, 6.**

**Extract from `weather_processor.py`:**

| Symbol | Lines | Description |
|--------|-------|-------------|
| `_classify_meal_mood()` | 804–874 | Maps temperature+RH to mood + suggestion list |
| `_extract_recent_meals()` | 896–903 | Reads meal history |

**New file: `data/meal_classifier.py`**

**Tests (`tests/test_meal_classifier.py`):**
```python
from data.meal_classifier import _classify_meal_mood, _extract_recent_meals

HOT_HUMID = {"Morning": {"AT": 34.0, "RH": 90.0, "PoP6h": 10.0},
             "Afternoon": {"AT": 36.0, "RH": 90.0, "PoP6h": 10.0},
             "Evening": {"AT": 33.0, "RH": 88.0, "PoP6h": 10.0}}

COLD_RAINY = {"Morning": {"AT": 12.0, "RH": 90.0, "PoP6h": 80.0},
              "Afternoon": {"AT": 13.0, "RH": 85.0, "PoP6h": 70.0},
              "Evening": {"AT": 11.0, "RH": 92.0, "PoP6h": 65.0}}

def test_hot_humid_mood():
    result = _classify_meal_mood(HOT_HUMID)
    assert result["mood"] == "Hot & Humid"
    assert len(result["all_suggestions"]) > 0

def test_cold_rainy_mood():
    result = _classify_meal_mood(COLD_RAINY)
    assert result["is_rainy"] is True
    assert result["mood"] in ("Cool & Damp", "Cold")

def test_extract_recent_meals_empty():
    assert _extract_recent_meals([], days=3) == []

def test_extract_recent_meals_reads_metadata():
    history = [{"metadata": {"meals_suggested": ["牛肉麵"]}}]
    assert "牛肉麵" in _extract_recent_meals(history, days=3)
```

**Commit:** `refactor(meals): extract meal classification to data/meal_classifier.py (A1-partial)`

---
