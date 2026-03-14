# Task 4: Extract health_alerts.py (Agent B) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Execute Task 4: Extract health_alerts.py (Agent B) as part of the Phase 3 parallel extraction stage.

**Architecture:** Extract specific domain logic from `weather_processor.py` into a new focused module.

**Tech Stack:** Python, Pytest

---

## Task 4: Extract `data/health_alerts.py` (A1 — Agent B)

> **Parallel with Tasks 3, 5, 6.**

**Extract from `weather_processor.py`:**

| Symbol | Description |
|--------|-------------|
| `_cardiac_alert()` | Cardiac risk detection |
| `_detect_menieres_alert()` | Ménière's pressure/humidity detection |
| `_compute_heads_ups()` | Priority heads-up generator |

All three functions are self-contained given `segmented`, `current_processed`, and `history`.

**New file: `data/health_alerts.py`**

**Tests (`tests/test_health_alerts.py`):**
```python
from data.health_alerts import _cardiac_alert, _detect_menieres_alert

COLD_MORNING = {"Morning": {"AT": 8.0, "RH": 85.0, "WS": 5.0, "PoP6h": 60.0, "Wx": 10}}

def test_cardiac_triggers_cold_wet():
    alert = _cardiac_alert(COLD_MORNING)
    assert alert["triggered"] is True

def test_cardiac_no_trigger_mild():
    mild = {"Morning": {"AT": 22.0, "RH": 65.0, "WS": 2.0, "PoP6h": 10.0, "Wx": 1}}
    alert = _cardiac_alert(mild)
    assert alert["triggered"] is False

def test_menieres_returns_dict():
    alert = _detect_menieres_alert({"PRES": 1005}, [], {})
    assert "triggered" in alert
```

**Commit:** `refactor(health): extract cardiac and menieres alert logic to data/health_alerts.py (A1-partial)`

---
