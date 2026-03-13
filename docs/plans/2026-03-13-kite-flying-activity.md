# Kite Flying Activity Scoring

**Date:** 2026-03-13
**Status:** Implemented

## Problem

The outdoor scoring system scored 7 activities (strolling, cycling, hiking, picnic, swimming, sports, photography). Kite flying was a natural missing entry — it has unique wind requirements that no existing activity captures.

## Key Design Challenge

All existing activities are *penalised* by excessive wind. Kite flying uniquely requires a *minimum* wind speed (Beaufort ≥ 3, ~3.4 m/s) to work at all. The penalty framework needed a new `wind_low` condition type.

## Changes

### `data/outdoor_scoring.py`

1. **New `wind_low` key** added to `OUTDOOR_WEIGHTS_GENERAL` with value `0` — neutral for all existing activities.

2. **New rule** in `_score_conditions()`:
   ```python
   ("ws", c.get("ws"), lambda v: v is not None and _beaufort_index(v) < 3, "wind_low", "caution", "calm_wind"),
   ```

3. **`kite_flying` entry** added to `OUTDOOR_WEIGHTS_BY_ACTIVITY`:

| Key | Value | Reason |
|-----|-------|--------|
| `wind_low` | -40 | Beaufort 0-2: too calm to fly |
| `wind_moderate` | 0 | Beaufort 5-6: good kite wind (overrides general -10) |
| `wind_strong` | -30 | Beaufort 7+: dangerous (slightly softer than general -35) |
| `rain_light` | -15 | Wet lines manageable but annoying |
| `wet_ground` | -5 | Minor penalty for wet grass |

**Wind scoring summary:**

| Beaufort | Speed | Key triggered | Kite penalty |
|---------|-------|---------------|-------------|
| 0–2 | <3.4 m/s | `wind_low` | -40 |
| 3–4 | 3.4–7.9 m/s | *(none)* | 0 (ideal) |
| 5–6 | 8–13.8 m/s | `wind_moderate` | 0 (overridden) |
| 7+ | ≥13.9 m/s | `wind_strong` | -30 |

### `tests/test_outdoor_scoring.py`

Three new tests:
- `test_kite_calm_wind_penalized` — Beaufort 0 → `calm_wind` in cautions, score < 75
- `test_kite_ideal_wind_high_score` — Beaufort 3 (5 m/s) → score ≥ 80
- `test_kite_wind_low_zero_in_general` — `wind_low` is 0 in general weights

## Downstream behaviour

`kite_flying` slots naturally into the existing pipeline:
- `_compute_outdoor_index()` iterates `OUTDOOR_WEIGHTS_BY_ACTIVITY` automatically
- `llm_prompt_builder.py` picks `top_activity` from `activity_scores` dynamically — no changes needed
- `web/routes.py` passes `activity_scores` through as-is — no changes needed
- `app.js` does not enumerate activities by name — no changes needed
