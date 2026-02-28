# Dashboard-Narration Decoupling Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove all narration-sourced content from the dashboard view so it renders purely from structured weather data, and relocate that content (heads_up LLM alert) into the lifestyle view.

**Architecture:** The single coupling point is `alerts.heads_up` in `_slice_overview()` (`web/routes.py`), which reads from LLM `paragraphs`. This will be removed from the overview slice and instead surfaced in the lifestyle slice as a new `alert` card. The `heads_ups` list (already structured/data-driven) stays on the dashboard — it comes from `processed_data`, not from narration paragraphs. The JS alert-dot logic in `app.js` will stop checking `heads_up` and only check `cardiac.triggered` + `menieres.triggered`.

**Tech Stack:** Python (Flask), vanilla JS, pytest.

---

## Audit Summary: What's Narration-Dependent in Dashboard View?

| Item | Source | Location | Action |
|------|--------|----------|--------|
| `alerts.heads_up` | `paragraphs.get("heads_up") or paragraphs.get("p1_summary")` | `routes.py:151` | Remove from `_slice_overview`; add to `_slice_lifestyle` |
| `alerts.cardiac` | `processed_data.cardiac_alert` | `routes.py:148` | Keep — already structured |
| `alerts.menieres` | `processed_data.menieres_alert` | `routes.py:149` | Keep — already structured |
| `alerts.heads_ups` | `processed_data.heads_ups` | `routes.py:152` | Keep — already structured |
| `alerts.commute_hazards` | `processed_data.commute` | `routes.py:153` | Keep — already structured |
| Timeline, 7-day, AQI forecast | `processed_data.*` | `routes.py:124-154` | Keep — already structured |

Only ONE item needs to move: `alerts.heads_up`.

---

## Task 1: Backend — Remove `heads_up` from `_slice_overview`, add to `_slice_lifestyle`

**Files:**
- Modify: `web/routes.py:104-155` (`_slice_overview`)
- Modify: `web/routes.py:158-266` (`_slice_lifestyle`)

**Step 1: Write failing test**

Add to a new file `tests/test_slices.py`:

```python
"""tests/test_slices.py — Unit tests for web/routes.py build_slices."""
from web.routes import build_slices

MINIMAL_BROADCAST = {
    "paragraphs": {
        "heads_up": "Watch for afternoon storms.",
        "p1_conditions": "Sunny morning.",
        "p2_garden_commute": "Garden is fine.",
        "p3_outdoor": "Great for walking.",
        "p4_meal_climate": "Light meals recommended.",
    },
    "metadata": {},
    "processed_data": {
        "current": {"AT": 25, "RH": 60, "WDSD": 3, "PRES": 1013, "UVI": 5,
                    "Wx": "1", "aqi": 50, "aqi_status": "Good", "aqi_level": 1,
                    "hum_text": "Normal", "hum_level": 2, "wind_text": "Light",
                    "wind_level": 1, "uv_text": "Low", "uv_level": 1,
                    "pres_text": "Normal", "pres_level": 3, "vis_text": "Good",
                    "vis_level": 1, "ground_state": "Dry", "ground_level": 1},
        "forecast_segments": {},
        "forecast_7day": [],
        "climate_control": {"mode": "Off"},
        "cardiac_alert": None,
        "menieres_alert": None,
        "commute": {},
        "aqi_realtime": {},
        "aqi_forecast": {},
        "transitions": [],
        "heads_ups": [],
        "outdoor_index": {},
    },
    "summaries": {},
}

def test_overview_has_no_heads_up_from_paragraphs():
    """Dashboard overview slice must NOT contain heads_up sourced from LLM paragraphs."""
    slices = build_slices(MINIMAL_BROADCAST)
    assert "heads_up" not in slices["overview"]["alerts"]

def test_lifestyle_has_heads_up_card():
    """Lifestyle slice must expose heads_up text from LLM paragraphs as alert card."""
    slices = build_slices(MINIMAL_BROADCAST)
    assert slices["lifestyle"]["alert"] == "Watch for afternoon storms."

def test_lifestyle_alert_is_none_when_no_paragraphs():
    """Lifestyle alert field is None when paragraphs are absent."""
    broadcast = dict(MINIMAL_BROADCAST)
    broadcast["paragraphs"] = {}
    slices = build_slices(broadcast)
    assert slices["lifestyle"]["alert"] is None
```

**Step 2: Run to verify it FAILS**

```bash
pytest tests/test_slices.py -v
```
Expected: `FAILED` (KeyError or AssertionError — `heads_up` still in overview, `alert` not in lifestyle)

**Step 3: Implement**

In `web/routes.py`, in `_slice_overview()` remove the `heads_up` line from the `alerts` dict:

```python
# BEFORE (line ~151):
"alerts": {
    "cardiac": cardiac,
    "menieres": menieres,
    "heads_up": paragraphs.get("heads_up") or paragraphs.get("p1_summary"),  # ← DELETE this line
    "heads_ups": heads_ups,
    "commute_hazards": commute_hazards,
},

# AFTER:
"alerts": {
    "cardiac": cardiac,
    "menieres": menieres,
    "heads_ups": heads_ups,
    "commute_hazards": commute_hazards,
},
```

Also remove `paragraphs` from `_slice_overview`'s signature and call-site (it will no longer be needed there). Update `build_slices` to stop passing `paragraphs` to `_slice_overview`:

```python
# In build_slices(), change:
"overview": _slice_overview(forecast_segs, cardiac, menieres, paragraphs, commute, heads_ups, aqi_forecast, transitions, outdoor_index, forecast_7day),
# To:
"overview": _slice_overview(forecast_segs, cardiac, menieres, commute, heads_ups, aqi_forecast, transitions, outdoor_index, forecast_7day),
```

Update `_slice_overview` signature (remove `paragraphs: dict` parameter):

```python
def _slice_overview(
    segments: dict,
    cardiac: dict | None,
    menieres: dict | None,
    commute: dict | None = None,
    heads_ups: list | None = None,
    aqi_forecast: dict | None = None,
    transitions: list | None = None,
    outdoor_index: dict | None = None,
    forecast_7day: list | None = None,
) -> dict:
```

In `_slice_lifestyle()`, add `paragraphs: dict` parameter and return `alert` key:

```python
# Change signature from:
def _slice_lifestyle(current, commute, climate, paragraphs, processed, summaries=None, outdoor_index=None):
# No change needed — paragraphs already a param. Just add to return dict:

return {
    ...,
    "alert": paragraphs.get("heads_up") or paragraphs.get("p1_summary") or None,
}
```

**Step 4: Run test to verify PASS**

```bash
pytest tests/test_slices.py -v
```
Expected: 3 tests PASS.

**Step 5: Run full test suite to catch regressions**

```bash
pytest --tb=short -q
```
Expected: all existing tests still PASS.

**Step 6: Commit**

```bash
git add web/routes.py tests/test_slices.py
git commit -m "refactor: move heads_up alert from overview slice to lifestyle slice"
```

---

## Task 2: Frontend — Remove `heads_up` from dashboard alert logic, add to lifestyle card

**Files:**
- Modify: `web/static/app.js` — `renderOverviewView()` and `renderLifestyleView()`

**Step 1: Update `renderOverviewView` in `app.js`**

The alert-dot check (line ~362) currently reads:
```js
const hasAlerts = data.alerts && (
  (data.alerts.cardiac && data.alerts.cardiac.triggered) ||
  (data.alerts.menieres && data.alerts.menieres.triggered) ||
  data.alerts.heads_up   // ← DELETE this line
);
```

Remove `data.alerts.heads_up` from `hasAlerts`:
```js
const hasAlerts = data.alerts && (
  (data.alerts.cardiac && data.alerts.cardiac.triggered) ||
  (data.alerts.menieres && data.alerts.menieres.triggered)
);
```

In the items array construction (~line 392), remove the `heads_up` block:
```js
// DELETE these lines:
if (data.alerts.heads_up) {
  items.push({ type: 'narrative', icon: '📢', title: T.heads_up_title, text: data.alerts.heads_up });
}
```

**Step 2: Update `renderLifestyleView` to render the alert card**

After the existing card additions in `renderLifestyleView` (after line ~693), add:
```js
// 8. Heads Up alert (from narration, if present)
if (data.alert) {
  add('📢', T.heads_up_title, data.alert);
}
```

No new translation keys needed — `T.heads_up_title` already exists in both `en` and `zh-TW` translations.

**Step 3: Verify no regressions**

This is frontend-only; there are no automated JS tests. Manual verification (see Verification Plan below).

**Step 4: Commit**

```bash
git add web/static/app.js
git commit -m "feat: move heads_up card from dashboard alerts to lifestyle view"
```

---

## Verification Plan

### Automated Tests

```bash
# Run new slice tests
pytest tests/test_slices.py -v

# Run full suite to check no regressions
pytest --tb=short -q
```

Expected: all pass, `test_slices.py` adds 3 new passing tests.

### Manual Verification

Start the local server:
```bash
python app.py
```
Then open `http://localhost:5000` in a browser.

1. **Dashboard view is heads_up-free:** Click the 📊 Dashboard nav button. Scroll to the alerts section below the 7-day forecast. Confirm that the 📢 "Heads Up / 注意事項" card does **not** appear there.
2. **Lifestyle view shows the alert card:** Click the 🚲 Lifestyle nav button. Confirm a 📢 card titled "Heads Up" (EN) or "注意事項" (ZH) appears at the bottom, containing the narration-generated advisory text.
3. **Alert dot on dashboard nav:** Confirm the red alert dot (`.nav-alert-dot`) on the Dashboard nav button only appears when cardiac or Ménière's alerts are triggered, not just because a heads_up exists.
4. **Language toggle:** Toggle between EN and ZH. Confirm the "Heads Up" card title updates correctly in both languages in the lifestyle view.
