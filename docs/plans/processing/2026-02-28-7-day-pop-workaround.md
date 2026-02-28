# 7-Day PoP Missing Workaround Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Provide a fallback probability of precipitation (PoP) in the 7-day forecast using Wx codes when actual PoP12h data is missing after day 3.

**Architecture:** Add a new `wx_to_pop` fallback helper in `data/scales.py` to map weather codes to estimated PoP percentages. Apply it in `weather_processor.py` when `PoP12h` is `None` for 7-day forecast slots.

**Tech Stack:** Python, pytest

---

### Task 1: Add `wx_to_pop` helper in `data/scales.py`

**Files:**
- Modify: `c:\Users\User\.gemini\antigravity\scratch\family-weather\data\scales.py`
- Modify: `c:\Users\User\.gemini\antigravity\scratch\family-weather\tests\test_scales.py`

**Step 1: Write the failing test**

```python
def test_wx_to_pop():
    assert wx_to_pop(1) == 0      # Sunny/Clear
    assert wx_to_pop(4) == 20     # Cloudy
    assert wx_to_pop(8) == 50     # Showers
    assert wx_to_pop(15) == 80    # Thunderstorms
    assert wx_to_pop(None) is None
```
*(Add to `tests/test_scales.py`, import `wx_to_pop` at the top)*

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_scales.py::test_wx_to_pop -v`
Expected: FAIL with ImportError "cannot import name 'wx_to_pop'" or "function not defined"

**Step 3: Write minimal implementation**

*(Append to `data/scales.py`)*
```python
def wx_to_pop(wx_code: int | None) -> int | None:
    """Map Wx code to estimated PoP fallback percentage."""
    if wx_code is None: return None
    if wx_code <= 3: return 0     # Clear/Fair
    if wx_code <= 7: return 20    # Cloudy/Overcast
    if wx_code <= 14: return 50   # Showers
    return 80                     # Thunderstorms (15+)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_scales.py::test_wx_to_pop -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_scales.py data/scales.py
git commit -m "feat: add wx_to_pop fallback helper for 7-day forecast"
```

---

### Task 2: Apply fallback in `weather_processor.py`

**Files:**
- Modify: `c:\Users\User\.gemini\antigravity\scratch\family-weather\data\weather_processor.py`

**Step 1: Write the minimal implementation**

*(In `data/weather_processor.py`, import `wx_to_pop` at the top from `data.scales`, then modify loop inside `process` around line 138)*

```python
# Change from:
    for slot in primary_7day_slots:
        slot["wind_text"] = wind_ms_to_beaufort(slot.get("WS"))
        slot["precip_text"], slot["precip_level"] = _val_to_scale(slot.get("PoP12h"), PRECIP_SCALE_5)
        slot["cloud_cover"] = wx_to_cloud_cover(slot.get("Wx"))

# Change to:
    for slot in primary_7day_slots:
        slot["wind_text"] = wind_ms_to_beaufort(slot.get("WS"))
        
        pop = slot.get("PoP12h")
        if pop is None:
            pop = wx_to_pop(slot.get("Wx"))
            
        slot["precip_text"], slot["precip_level"] = _val_to_scale(pop, PRECIP_SCALE_5)
        slot["cloud_cover"] = wx_to_cloud_cover(slot.get("Wx"))
```

**Step 2: Dry Run or Test Payload Structure**

Run: `python data/weather_processor.py` (or run full pipeline in app)
Expected: The 7-day (weekly) timeline correctly generates `precip_text` and `precip_level` for Days 4-7 instead of showing "Unknown".

**Step 3: Commit**

```bash
git add data/weather_processor.py
git commit -m "fix: apply wx_to_pop fallback for missing 7-day PoP data"
```
