# Phase 3 Remediation Implementation Plan

**Goal:** Resolve architectural tech debt — split the 1,561-line `weather_processor.py` God module into focused domain modules, extract the pipeline, make `_segment_forecast` deterministic, and build a proper test suite.

**Audit items addressed:** A1, A2, A5, SM3, TS3

> **For Execution Agents:** Use `superpowers:test-driven-development`. Implement one module at a time. Do NOT start until `_segment_forecast` (Task 1) is done — everything downstream depends on it.

---

## Multi-Agent Breakdown

Phase 3 has two **sequential stages**:

```
Stage 1 (prerequisite, sequential):
  Task 1: Make _segment_forecast deterministic (SM3)
  Task 2: Extract OUTDOOR_LOCATIONS to locations.json (A5)
  
Stage 2 (parallel, after Stage 1 complete):
  [Agent A] Task 3: Extract scales.py
  [Agent B] Task 4: Extract health_alerts.py
  [Agent C] Task 5: Extract meal_classifier.py
  [Agent D] Task 6: Extract outdoor_scoring.py

Stage 3 (after Stage 2 complete, sequential):
  Task 7: Extract pipeline.py (A2)
  Task 8: Test suite (TS3)
```

**Why sequential for Stage 1?** `_segment_forecast` with `now` injection is a prerequisite for all deterministic tests. Agents should not write tests against the non-deterministic version.

---

## Task 1: Make `_segment_forecast` Deterministic (SM3)

**File:** `data/weather_processor.py:535–604`

**Problem:** `datetime.now()` called on line 546. Results vary by time of day. Not unit-testable.

**Step 1 — Failing test:**
```python
# tests/test_processor_segmentation.py
from datetime import datetime
from data.weather_processor import _segment_forecast

SLOTS = [
    {"start_time": "2026-02-22T06:00:00+08:00", "end_time": "2026-02-22T12:00:00+08:00",
     "AT": 18.0, "RH": 65.0, "WS": 2.0, "WD": 90.0, "PoP6h": 10.0, "Wx": 1},
    {"start_time": "2026-02-22T12:00:00+08:00", "end_time": "2026-02-22T18:00:00+08:00",
     "AT": 24.0, "RH": 55.0, "WS": 3.0, "WD": 180.0, "PoP6h": 20.0, "Wx": 2},
]

def test_segmentation_morning_anchor():
    now = datetime(2026, 2, 22, 9, 0, 0)  # 9 AM
    result = _segment_forecast(SLOTS, now=now)
    assert "Morning" in result
    assert result["Morning"] is not None

def test_segmentation_afternoon_anchor():
    now = datetime(2026, 2, 22, 14, 0, 0)  # 2 PM
    result = _segment_forecast(SLOTS, now=now)
    assert "Afternoon" in result
```

**Step 2 — Implementation:**
```python
# weather_processor.py:535
def _segment_forecast(
    slots: list[dict],
    now: datetime | None = None,          # ← add this parameter
) -> dict[str, Optional[dict]]:
    ...
    now_dt = now or datetime.now()         # ← replace bare datetime.now()
    ...
```

**Step 3 — Verify:** `pytest tests/test_processor_segmentation.py -v` → PASS

**Step 4 — Commit:** `fix(processor): inject now parameter into _segment_forecast for deterministic testing (SM3)`

---

## Task 2: Extract `OUTDOOR_LOCATIONS` to `data/locations.json` (A5)

**Files:**
- DELETE from: `data/weather_processor.py:198–279`
- CREATE: `data/locations.json`
- CREATE: `data/location_loader.py`
- MODIFY: `data/weather_processor.py` (import and use loader)

**Step 1 — Create `data/locations.json`:**

Move the `OUTDOOR_LOCATIONS` dict literally — same keys (`"Nice"`, `"Warm"`, `"Cloudy & Breezy"`, `"Stay In"`), same list-of-dict values. Pure data move, zero logic change.

**Step 2 — Create `data/location_loader.py`:**
```python
"""location_loader.py — Loads OUTDOOR_LOCATIONS from the canonical JSON data file."""
import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "locations.json")

def load_outdoor_locations() -> dict[str, list[dict]]:
    with open(_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

OUTDOOR_LOCATIONS = load_outdoor_locations()
```

**Step 3 — Update `weather_processor.py`:**
```python
# Remove: OUTDOOR_LOCATIONS: dict[str, list[dict]] = { ... } (lines 201–279)
# Add at top imports:
from data.location_loader import OUTDOOR_LOCATIONS
```

**Step 4 — Failing test:**
```python
# tests/test_location_loader.py
from data.location_loader import OUTDOOR_LOCATIONS

def test_loads_all_moods():
    assert set(OUTDOOR_LOCATIONS.keys()) == {"Nice", "Warm", "Cloudy & Breezy", "Stay In"}

def test_each_mood_has_locations():
    for mood, locs in OUTDOOR_LOCATIONS.items():
        assert len(locs) > 0, f"Mood '{mood}' has no locations"

def test_location_has_required_fields():
    for mood, locs in OUTDOOR_LOCATIONS.items():
        for loc in locs:
            assert "name" in loc
            assert "activity" in loc
            assert "parkinsons" in loc
```

**Step 5 — Commit:** `refactor(data): extract OUTDOOR_LOCATIONS to locations.json (A5)`

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

## Task 7: Extract `backend/pipeline.py` (A2)

> **Must run AFTER Tasks 3–6 are merged.**

**Problem:** `_pipeline_steps()` in `app.py:170–364` is 195 lines mixing orchestration, regen logic, narration fallback, parallel submission, and persistence.

**New file: `backend/pipeline.py`**

```python
"""pipeline.py — Isolated orchestration functions for the broadcast pipeline."""

def check_regen_cycle(history: list[dict], date_str: str, cycle_days: int) -> bool:
    """Returns True if a database regeneration should be triggered today."""
    ...

def generate_narration_with_fallback(
    provider: str,
    processed: dict,
    history: list[dict],
    date_str: str,
) -> tuple[str, str]:
    """Returns (narration_text, source_label). Falls back to template on LLM error."""
    ...

def run_parallel_summarization(
    paragraphs: dict,
    aqi_forecast_raw: str,
) -> tuple[dict, str | None]:
    """Returns (lifestyle_summaries, aqi_summary_en)."""
    ...
```

**`app.py` after refactor:**
```python
from backend.pipeline import check_regen_cycle, generate_narration_with_fallback, run_parallel_summarization

def _pipeline_steps(date_str, provider_override=None):
    ...
    should_regen = check_regen_cycle(history, date_str, REGEN_CYCLE_DAYS)
    narration_text, source = generate_narration_with_fallback(provider, processed, history, date_str)
    ...
```

**Tests (`tests/test_pipeline.py`):**
```python
from unittest.mock import patch
from backend.pipeline import check_regen_cycle, generate_narration_with_fallback

def test_regen_triggers_on_first_run():
    assert check_regen_cycle([], "2026-02-22", 14) is True

def test_regen_skips_if_recent():
    history = [{"generated_at": "2026-02-20T00:00:00+08:00",
                "metadata": {"regen": True}}]
    assert check_regen_cycle(history, "2026-02-22", 14) is False

def test_regen_triggers_after_cycle():
    history = [{"generated_at": "2026-02-01T00:00:00+08:00",
                "metadata": {"regen": True}}]
    assert check_regen_cycle(history, "2026-02-22", 14) is True

@patch("backend.pipeline.build_prompt")
@patch("backend.pipeline.generate_gemini")
def test_narration_gemini_success(mock_gemini, mock_prompt):
    mock_prompt.return_value = []
    mock_gemini.return_value = "Today is nice."
    text, source = generate_narration_with_fallback("GEMINI", {}, [], "2026-02-22")
    assert text == "Today is nice."
    assert source == "gemini"

@patch("backend.pipeline.build_prompt", side_effect=Exception("API error"))
def test_narration_falls_back_on_error(mock_prompt):
    text, source = generate_narration_with_fallback("GEMINI", {}, [], "2026-02-22")
    assert source == "template"
    assert len(text) > 0
```

**Commit:** `refactor(pipeline): extract _pipeline_steps logic to backend/pipeline.py (A2)`

---

## Task 8: Comprehensive Test Suite (TS3)

> **Final stage — extend coverage after all modules extracted.**

| Test file | Coverage target |
|-----------|----------------|
| `tests/test_scales.py` | All scale tables + lookup functions |
| `tests/test_health_alerts.py` | Cardiac + Ménière's + heads-up |
| `tests/test_meal_classifier.py` | All 4 meal moods + history extraction |
| `tests/test_outdoor_scoring.py` | Grade thresholds + rule engine + per-activity |
| `tests/test_processor_segmentation.py` | Deterministic segmentation anchors |
| `tests/test_location_loader.py` | JSON load + field validation |
| `tests/test_pipeline.py` | Regen cycle + narration fallback (mocked) |

**Acceptance criteria:**
- `pytest tests/ -v` → all pass
- No real API calls made in tests
- `_segment_forecast` tested with at least 4 time-of-day anchors

**Commit:** `test(suite): build comprehensive Phase 3 test coverage (TS3)`

---

## Verification Plan

```bash
# End of each stage
$env:PYTHONPATH="."; pytest tests/ -v

# After Stage 2 — smoke test import chain
python -c "from data.weather_processor import process; print('OK')"

# After Stage 3 — integration
python app.py &
curl -X POST http://localhost:5001/api/refresh -H 'Content-Type: application/json' -d '{}'
```

**Final targets:**
- `pytest tests/ -v` → all green (50+ tests)
- `weather_processor.py` reduced from 1,561 → ≤ 400 lines
- No circular imports

---

## File Dependency Graph

```
data/helpers.py          (done — Phase 4)
data/scales.py           ← no local deps
data/health_alerts.py    ← imports scales
data/meal_classifier.py  ← imports config only
data/location_loader.py  ← no local deps
data/outdoor_scoring.py  ← imports scales, location_loader
data/weather_processor.py ← imports all above; exports process()
backend/pipeline.py      ← imports weather_processor, narration/*
app.py                   ← imports pipeline, web/routes
```
