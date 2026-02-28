# Outdoor Index Rule Engine Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the outdoor suitability index to use a Declarative Rule Engine and introduce an independent 'Solar Load' metric to approximate radiant heat (UTCI/PET).

**Architecture:** 
1. Move hardcoded thresholds to `config.py`.
2. Rewrite `_score_conditions` to iterate over a list of declarative rule tuples (metric, value, condition_lambda, penalty, type, label) instead of `if/else` ladders.
3. Compute a 0-100 `solar_load` metric based on UV Index and Cloud Cover (Wx), and add it as a new rule parameter.

**Tech Stack:** Python, Pytest

---

### Task 1: Centralize Configuration

**Files:**
- Modify: `config.py`

**Step 1: Write the failing test**
(No test required for config constant definition).

**Step 2: Write minimal implementation**
Append the following to `config.py`:
```python
# ── Outdoor Index Rules ───────────────────────────────────────────────────────
OUTDOOR_TEMP_EXTREME_HOT = 36
OUTDOOR_TEMP_HOT = 32
OUTDOOR_TEMP_COLD = 12
OUTDOOR_TEMP_EXTREME_COLD = 8
OUTDOOR_RH_VERY_HIGH = 90
OUTDOOR_RH_HIGH = 85
OUTDOOR_AQI_UNHEALTHY = 150
OUTDOOR_AQI_SENSITIVE = 100
OUTDOOR_UVI_EXTREME = 11
OUTDOOR_UVI_VERY_HIGH = 8
OUTDOOR_VIS_VERY_POOR = 1.0
OUTDOOR_VIS_POOR = 2.0
```

**Step 3: Commit**
```bash
git add config.py
git commit -m "feat: centralize outdoor index thresholds in config"
```

---

### Task 2: Implement Solar Load Calculator

**Files:**
- Modify: `data/processor.py`
- Test: `data/test_solar_load.py` (Create)

**Step 1: Write the failing test**
Create `data/test_solar_load.py`:
```python
from data.processor import _compute_solar_load

def test_solar_load_clear():
    # UVI 8, Wx "Sunny" (code "01") -> High solar load
    assert _compute_solar_load(uvi=8, wx_name="多雲時晴") > 70

def test_solar_load_cloudy():
    # UVI 8, Wx "Overcast" (code "07") -> Reduced solar load
    assert _compute_solar_load(uvi=8, wx_name="陰天") < 40
```

**Step 2: Run test to verify it fails**
Run: `pytest data/test_solar_load.py`
Expected: FAIL with "ImportError"

**Step 3: Write minimal implementation**
Add to `data/processor.py` (above `_score_conditions`):
```python
def _compute_solar_load(uvi: int | None, wx_name: str | None) -> int:
    """Approximate radiant heat impact (0-100)."""
    if not uvi or not wx_name:
        return 0
    
    # Simple heuristic: High UV + Clear Sky = High Load
    # Wx strings containing "晴" (Clear/Sunny) imply low cloud cover
    is_sunny = "晴" in wx_name
    is_cloudy = "陰" in wx_name or "雨" in wx_name
    
    base_load = min(100, uvi * 10)
    
    if is_sunny:
        return min(100, base_load + 20)
    elif is_cloudy:
        return max(0, base_load - 40)
    return base_load
```

**Step 4: Run test to verify it passes**
Run: `pytest data/test_solar_load.py`
Expected: PASS

**Step 5: Commit**
```bash
git add data/test_solar_load.py data/processor.py
git commit -m "feat: implement solar load calculation heuristic"
```

---

### Task 3: Refactor Scoring to Rule Engine

**Files:**
- Modify: `data/processor.py` (`_score_conditions` function)
- Test: `data/test_outdoor_mod.py` (Existing, must remain passing to ensure behavioral parity).

**Step 1: Write the failing test**
Run the existing `test_outdoor_mod.py` to ensure it passes on the old logic. The "test" here is maintaining parity.

**Step 2: Write minimal implementation**
Rewrite `_score_conditions` in `data/processor.py`.
- Import configuration constants.
- Replace `if/else` with a `rules` list definition exactly as described in Phase 2 of the Architect blueprint, utilizing lambdas.
- Add the new solar rule: `("solar", c.get("solar_load"), lambda v: v is not None and v > 80, "solar_extreme", "caution", "harsh_sunlight")`

**Step 3: Run test to verify it passes**
Run: `python data/test_outdoor_mod.py`  (or pytest if configured)
Expected: PASS

**Step 4: Commit**
```bash
git add data/processor.py
git commit -m "refactor: convert outdoor scoring to declarative rule engine"
```

---

### Task 4: Base Score Memoization & Pipeline Integration

**Files:**
- Modify: `data/processor.py` (`_compute_outdoor_index` function)

**Step 1: Write minimal implementation**
Update `_compute_outdoor_index` in `data/processor.py`:
1. Calculate `solar_load` per segment using the new helper. Include it in the `conds` dict.
2. Only run `_score_conditions(conds, OUTDOOR_WEIGHTS_GENERAL)` ONCE per segment. Store the result in `segment_scores_base`.
3. When iterating `OUTDOOR_WEIGHTS_BY_ACTIVITY`, retrieve the memoized `best_conds` instead of rebuilding the dictionary.

**Step 2: Run test to verify it passes**
Run: `python data/test_outdoor_mod.py`
Expected: PASS

**Step 3: Commit**
```bash
git add data/processor.py
git commit -m "perf: memoize base weather conditions for activity scoring"
```
