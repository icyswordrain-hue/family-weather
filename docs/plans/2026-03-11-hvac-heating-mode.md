# HVAC Heating Mode + Consistency Fix

**Goal:** Add heating recommendations to the HVAC suggestion and ensure all
surfaces (narration, lifestyle cards, frontend) derive from the same single
source of truth without conflicting.

**Status:** Fully implemented.

---

## Problem

`_climate_control()` in `data/weather_processor.py` had no cold-weather branch.
The mode selection ladder was:

```
temp ≥ 26°C  → cooling
dew ≥ 21°C   → dehumidify
windows open → fan
else         → Off   ← heating never reached
```

Two additional issues:
1. The function used the **Afternoon** (hottest) segment only, missing days
   where the afternoon is mild but overnight drops to 12°C.
2. `"heating_optional"` was handled in `fallback_narrator.py` and `routes.py`
   but `_climate_control()` never emitted it — dead code.

---

## Architecture Principle

`_climate_control()` is the **single source of truth**. All surfaces read
`processed_data["climate_control"]["mode"]`:

```
_climate_control()
  └── climate_control.mode
        ├── llm_prompt_builder.py HINTS → LLM narration P4 + hvac card
        │       ↓ broadcast["summaries"]["hvac"]  (authoritative if present)
        ├── routes.py _slice_lifestyle() → lifestyle["hvac"].text
        │   (LLM summary first; fallback text from mode if LLM absent)
        └── app.js data.hvac.mode → icon + label
```

Fixing the source propagates to all surfaces automatically.

---

## Changes

### `data/weather_processor.py`

Added named thresholds above `_climate_control()`:

```python
_COOLING_TEMP_C  = 26   # afternoon temp ≥ this → cooling
_HUMID_DEW_PT_C  = 21   # afternoon dew point ≥ this → dehumidify
_HEATING_TEMP_C  = 16   # coldest-segment temp < this → heating
_HEAT_OPT_TEMP_C = 18   # coldest-segment temp < this (≥ 16) → heating_optional
```

Added a second segment scan for the **coldest** point of the day (reverse
segment order: Overnight → Morning → Evening → Afternoon). Cooling/dehumidify
still assessed from the afternoon peak; heating from the overnight trough.

Updated mode selection:

```python
if t_f >= _COOLING_TEMP_C:       mode = "cooling"
elif dp_f >= _HUMID_DEW_PT_C:    mode = "dehumidify"
elif cold_t < _HEATING_TEMP_C:   mode = "heating"
elif cold_t < _HEAT_OPT_TEMP_C:  mode = "heating_optional"
elif windows == "open":           mode = "fan"
else:                             mode = "Off"
```

Heating reason appended to `dew_reasons`, e.g.:
`"coldest segment 13°C — heating recommended"`

### `narration/llm_prompt_builder.py`

HVAC HINT enriched with the first `dew_reasons` entry so the LLM has
context and is less likely to override the mode:

```
- HVAC mode to recommend: heating (coldest segment 13°C — heating recommended)
```

### `web/static/app.js`

Made `heating` and `heating_optional` explicit in the icon map (both use
`hvac.webp`) instead of falling through to `window-advice`:

```javascript
hvacMode === 'heating'          ? 'hvac' :
hvacMode === 'heating_optional' ? 'hvac' :
'window-advice'
```

### `web/routes.py`

Added `"heating_optional"` to both the zh and en fallback mode label maps
(lines ~327, ~342). `fallback_narrator.py` already handled it correctly.

---

## Thresholds

| Mode | Trigger | Rationale |
|------|---------|-----------|
| `heating` | coldest segment < 16°C | Genuinely cold — Taiwan winter nights |
| `heating_optional` | coldest segment 16–18°C | Chilly but not urgent |
| `cooling` | afternoon peak ≥ 26°C | Hot enough to need AC |
| `dehumidify` | afternoon dew point ≥ 21°C | Muggy without being hot |
| `fan` | window advice = open | Mild, ventilation sufficient |
| `Off` | otherwise | Comfortable, no action needed |
