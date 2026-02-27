# Task 3: Extract scales.py (Agent A) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Execute Task 3: Extract scales.py (Agent A) as part of the Phase 3 parallel extraction stage.

**Architecture:** Extract specific domain logic from `weather_processor.py` into a new focused module.

**Tech Stack:** Python, Pytest

---

## Task 3: Extract `data/scales.py` (A1 — Agent A)

> **Can run in parallel with Tasks 4, 5, 6 after Tasks 1+2 are complete.**

**Extract from `weather_processor.py`:**

| Symbol | Lines | Description |
|--------|-------|-------------|
| `BEAUFORT_SCALE_5` | 51–57 | 5-level wind text |
| `BEAUFORT_SCALE` | 58–72 | 13-level Beaufort |
| `UV_SCALE` | 76–82 | 5-level UV |
| `HUM_SCALE_5` | 84–90 | 5-level humidity |
| `PRES_SCALE_5` | 92–98 | 5-level pressure |
| `VIS_SCALE_5` | 100–106 | 5-level visibility |
| `PRECIP_SCALE_5` | 108–115 | 6-level precipitation |
| `_val_to_scale()` | 507–514 | Scale lookup helper |
| `_wind_to_level()` | 516–523 | Wind m/s → 1-5 |
| `_aqi_to_level()` | 525–532 | AQI → 1-5 |
| `_beaufort_index()` | (grep for usage) | Beaufort index lookup |
| `wind_ms_to_beaufort()` | (grep for usage) | Text label |
| `wx_to_cloud_cover()` | (grep for usage) | Wx code → cloud text |
| `degrees_to_cardinal()` | (grep for usage) | Wind direction |
| `pop_to_text()` | (grep for usage) | PoP % → text |
| `translate_aqi_status()` | (grep for usage) | AQI string translate |
| `translate_pollutant()` | (grep for usage) | Pollutant translate |

**New file: `data/scales.py`** — pure functions, no side effects, no imports from other local modules.

**Tests (`tests/test_scales.py`):**
```python
from data.scales import _val_to_scale, UV_SCALE, PRECIP_SCALE_5, wind_ms_to_beaufort, _aqi_to_level

def test_uv_low():        assert _val_to_scale(1, UV_SCALE) == ("Low", 1)
def test_uv_extreme():    assert _val_to_scale(12, UV_SCALE) == ("Extreme", 5)
def test_precip_dry():    assert _val_to_scale(0, PRECIP_SCALE_5)[0] == "Dry"
def test_wind_calm():     assert wind_ms_to_beaufort(0.2) == "Calm"
def test_aqi_good():      assert _aqi_to_level(40) == 1
def test_aqi_hazardous(): assert _aqi_to_level(350) == 5
```

**Commit:** `refactor(scales): extract scale tables and lookup functions to data/scales.py (A1-partial)`

---
