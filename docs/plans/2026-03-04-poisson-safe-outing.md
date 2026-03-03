# Poisson Safe-Outing Window Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace PoP likelihood labels (`Dry / Very Unlikely / Likely / …`) with a Poisson-derived "safe outing window" — the maximum minutes you can be outside before your risk of getting rained on exceeds a per-intensity threshold.

**Architecture:** A new `pop_to_safe_minutes()` helper in `scales.py` computes the window using the Poisson inversion formula. The processor calls this in place of `_val_to_scale(pop, PRECIP_SCALE_5)` for both 24h segments and 7-day slots. The frontend displays the derived minute value with a 3-stop color level (1/3/5).

**Tech Stack:** Python (`math` stdlib only), existing `scales.py` / `weather_processor.py` / `app.js` patterns.

---

## Background

**CWA data resolution:**
- 24h forecast (`F-D0047-069`): `PoP6h` — one value per 6-hour segment (360 min window)
- 7-day forecast (`F-D0047-071`): `PoP12h` — one value per 12-hour day/night bucket (720 min window)

**Formula** (Poisson inversion):
```
safe_minutes = log(1 - risk_threshold) / log(1 - pop/100) × window_minutes
```
Edge cases: `pop=0` → full window safe. `pop=100` → 0 minutes.

**Risk thresholds by rain intensity** (from `Wx` weather code):

| Wx range | Intensity | Risk threshold |
|---|---|---|
| ≤ 10 | No rain / overcast | N/A — return full window |
| 11–12 | Drizzle | 25% |
| 13–14 | Moderate rain | 15% |
| 15+ | Heavy / thunder | 8% |

**Output levels** (3-stop, reuses CSS `lvl-1/3/5`):

| safe_minutes | text | level |
|---|---|---|
| ≥ 120 | "All clear" | 1 |
| 20–119 | "~X min" | 3 |
| < 20 | "Stay in" | 5 |

---

## Task 1: Add helpers to `scales.py`

**Files:**
- Modify: `data/scales.py`
- Test: `tests/test_scales.py`

**Step 1: Write the failing tests**

Add to `tests/test_scales.py`:

```python
from data.scales import pop_to_safe_minutes, safe_minutes_to_level

# pop_to_safe_minutes
def test_safe_no_rain():
    assert pop_to_safe_minutes(0, 360) == 360

def test_safe_full_rain():
    assert pop_to_safe_minutes(100, 360) == 0

def test_safe_drizzle_50pop():
    # 25% threshold, 6h window, PoP=50
    # log(0.75)/log(0.5) * 360 ≈ 151 min
    result = pop_to_safe_minutes(50, 360, risk_pct=25)
    assert 140 <= result <= 165

def test_safe_heavy_50pop():
    # 8% threshold, 6h window, PoP=50
    # log(0.92)/log(0.5) * 360 ≈ 45 min
    result = pop_to_safe_minutes(50, 360, risk_pct=8)
    assert 40 <= result <= 55

def test_safe_none_pop():
    assert pop_to_safe_minutes(None, 360) is None

# safe_minutes_to_level
def test_level_all_clear():   assert safe_minutes_to_level(120) == (1, "All clear")
def test_level_short():       assert safe_minutes_to_level(60)  == (3, "~60 min")
def test_level_stay_in():     assert safe_minutes_to_level(10)  == (5, "Stay in")
def test_level_none():        assert safe_minutes_to_level(None) == (0, "Unknown")
```

**Step 2: Run to verify fail**
```
pytest tests/test_scales.py::test_safe_no_rain tests/test_scales.py::test_level_all_clear -v
```
Expected: `ImportError` — functions not yet defined.

**Step 3: Implement in `data/scales.py`**

Add after `_aqi_to_level` (around line 129):

```python
import math as _math

# Risk threshold config — tunable per intensity class
_RISK_DRIZZLE  = 0.25   # Wx 11-12: annoying but tolerable
_RISK_MODERATE = 0.15   # Wx 13-14: meaningfully uncomfortable
_RISK_HEAVY    = 0.08   # Wx 15+:   dangerous / damage to belongings

def _wx_to_rain_risk(wx: int | None) -> float | None:
    """Map Wx code to acceptable rain-exposure risk threshold.
    Returns None when Wx indicates no rain (skip safe-window calc)."""
    if wx is None or wx <= 10:
        return None          # no rain forecast — full window is safe
    if wx <= 12: return _RISK_DRIZZLE
    if wx <= 14: return _RISK_MODERATE
    return _RISK_HEAVY


def pop_to_safe_minutes(
    pop: float | None,
    window_minutes: int = 360,
    risk_pct: float = 15,
) -> int | None:
    """Poisson-derived safe outing window in minutes.

    Args:
        pop:            Probability of Precipitation (0–100).
        window_minutes: Length of the forecast block (360 for 6h, 720 for 12h).
        risk_pct:       Acceptable chance (%) of getting rained on during outing.

    Returns max minutes outside such that P(rain during outing) <= risk_pct/100.
    Returns None when pop is None. Returns window_minutes when pop==0.
    Returns 0 when pop==100.
    """
    if pop is None:
        return None
    if pop <= 0:
        return window_minutes
    if pop >= 100:
        return 0
    p = pop / 100.0
    r = risk_pct / 100.0
    safe_frac = _math.log(1.0 - r) / _math.log(1.0 - p)
    return round(min(max(safe_frac * window_minutes, 0), window_minutes))


def safe_minutes_to_level(minutes: int | None) -> tuple[int, str]:
    """Map safe outing minutes to (level, display_text).

    Levels use the existing CSS lvl-N scheme: 1=green, 3=yellow, 5=red.
    """
    if minutes is None:
        return (0, "Unknown")
    if minutes >= 120:
        return (1, "All clear")
    if minutes >= 20:
        return (3, f"~{minutes} min")
    return (5, "Stay in")
```

**Step 4: Run tests to verify pass**
```
pytest tests/test_scales.py -v
```
Expected: all pass.

**Step 5: Commit**
```
git add data/scales.py tests/test_scales.py
git commit -m "feat: add Poisson safe-outing helpers to scales.py"
```

---

## Task 2: Wire into `weather_processor.py`

**Files:**
- Modify: `data/weather_processor.py:32-36` (imports), `line 178` (7-day loop), `line 213` (24h segment loop)
- Test: `tests/test_processor.py`

**Step 1: Write failing tests**

In `tests/test_processor.py`, find or add a test that checks a processed segment has the new fields:

```python
def test_segment_has_safe_minutes(minimal_forecast_fixture):
    # minimal_forecast_fixture should be an existing fixture or a dict with
    # PoP6h=50, Wx=13 (moderate rain)
    result = process(current_fixture, {"三峽區": [minimal_forecast_fixture]}, aqi_fixture)
    seg = result["forecast_segments"].get("Morning") or result["forecast_segments"].get("Afternoon")
    assert seg is not None
    assert "safe_minutes" in seg
    assert "precip_level" in seg
    assert seg["precip_level"] in (0, 1, 3, 5)
```

**Step 2: Run to verify fail**
```
pytest tests/test_processor.py::test_segment_has_safe_minutes -v
```
Expected: `AssertionError` — `safe_minutes` not in seg.

**Step 3: Update imports in `weather_processor.py`**

Line 32–35, add to existing import block:
```python
from data.scales import (
    ...,                         # existing imports
    pop_to_safe_minutes, safe_minutes_to_level, _wx_to_rain_risk,
)
```

**Step 4: Replace 24h segment enrichment (processor line 213)**

Current:
```python
seg["precip_text"], seg["precip_level"] = _val_to_scale(seg.get("PoP6h"), PRECIP_SCALE_5)
```

Replace with:
```python
pop6h = seg.get("PoP6h")
wx    = seg.get("Wx")
risk  = _wx_to_rain_risk(wx)
if risk is None:
    # No rain in forecast — full window safe
    safe_min = 360
else:
    safe_min = pop_to_safe_minutes(pop6h, window_minutes=360, risk_pct=risk * 100)
seg["safe_minutes"] = safe_min
seg["precip_level"], seg["precip_text"] = safe_minutes_to_level(safe_min)
```

**Step 5: Replace 7-day slot enrichment (processor line 178)**

Current:
```python
slot["precip_text"], slot["precip_level"] = _val_to_scale(pop, PRECIP_SCALE_5)
```

Replace with:
```python
wx   = slot.get("Wx")
risk = _wx_to_rain_risk(wx)
if risk is None:
    safe_min = 720
else:
    safe_min = pop_to_safe_minutes(pop, window_minutes=720, risk_pct=risk * 100)
slot["safe_minutes"]  = safe_min
slot["precip_level"], slot["precip_text"] = safe_minutes_to_level(safe_min)
```

**Step 6: Run tests**
```
pytest tests/test_processor.py tests/test_scales.py -v
```
Expected: all pass.

**Step 7: Commit**
```
git add data/weather_processor.py
git commit -m "feat: replace PRECIP_SCALE_5 with Poisson safe-outing window in processor"
```

---

## Task 3: Update frontend display (`app.js`)

**Files:**
- Modify: `web/static/app.js` — two locations

**Step 1: Fix the `|| 1` fallback bug (two places)**

Search for `precip_level || 1` — appears at lines 489 and 650. Change both to `|| 0`:

```js
// line 489
addRow(T.rain, ..., seg.precip_level || 0);

// line 650
rain.className = `wk-rain lvl-${item.precip_level || 0}`;
```

**Step 2: Add zh-TW translation for "All clear" and "Stay in"**

In the `metrics` object in the `zh-TW` translation block (around line 254):

```js
'All clear': '完全安全', 'Stay in': '建議待室內',
```

**Step 3: Manual verification**

1. Run the dev server: `python app.py` (or `flask run`)
2. Open the browser to the dashboard
3. Navigate to **Overview** tab
4. The rain row in each 24h timeline card should now display one of:
   - Green `All clear`
   - Yellow `~X min`
   - Red `Stay in`
5. Check the 7-day weekly cards — rain percentage should also carry the new color level
6. Confirm no cards show the old text (`Dry`, `Very Unlikely`, `Possible`, etc.)

**Step 4: Commit**
```
git add web/static/app.js
git commit -m "feat: display Poisson safe-outing window in timeline and weekly cards"
```

---

## Task 4: Cleanup

**Files:**
- Modify: `data/scales.py` — remove `PRECIP_SCALE_5` if no longer referenced
- Modify: `data/weather_processor.py` — remove `PRECIP_SCALE_5` from import

**Step 1: Check for remaining references**
```
grep -rn "PRECIP_SCALE_5" .
```
Expected: zero results after the processor changes above. If any remain, trace and remove.

**Step 2: Check `pop_to_text` is still needed**

`pop_to_text` is used in `_detect_transitions` (line 542) for the transition breach labels — keep it.

**Step 3: Run full test suite**
```
pytest tests/ -v
```
Expected: all pass.

**Step 4: Final commit**
```
git add -A
git commit -m "chore: remove unused PRECIP_SCALE_5 after Poisson migration"
```
