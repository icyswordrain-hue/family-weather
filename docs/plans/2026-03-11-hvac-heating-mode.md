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

---

## Follow-up: Explicit AC Advice + Air Quality Action Tips (2026-03-13)

### Gaps addressed

Two UX gaps remained after the initial implementation:

1. **HVAC fallback text was terse** — `"System: AC."` gave no action or context.
   The LLM hint only passed `mode + one dew_reason`, missing `ac_mode`
   (dry/cool), `dehumidifier` severity, and `windows`, so the LLM card
   couldn't incorporate all relevant advice.

2. **Air quality card had no action item** — users saw AQI numbers but no
   explicit "close windows" or "run air purifier" guidance.

### Files changed

#### `narration/llm_prompt_builder.py`

Expanded `climate_hint` to include all sub-fields from `climate_control`:

```
cooling (temp 30°C — AC cool mode appropriate) [cool mode] dehumidifier: consider windows: close
```

Updated card instructions:

- `hvac`: 1–2 sentences; require dehumidifier mention and window guidance if present in HINTS.
- `air_quality`: now asks the LLM to recommend an air purifier for Moderate+ AQI (EN + ZH).

#### `web/routes.py`

Fallback HVAC text rewritten with action verbs and `dew_reasons[0]` context:

| Before | After |
|--------|-------|
| `System: AC.` | `Run the AC in cool mode — temp 30°C.` |
| `System: heating.` | `Turn on the heater — coldest segment 13°C.` |
| `建議：除濕機。` | `請開除濕機。——露點偏高。` |

Also removed the stale `aqi_val > 100 → air purifier` branch from the HVAC
fallback (air quality now has its own dedicated `purifier_advice` field).

Added `purifier_advice` to the `air_quality` slice payload:

| AQI | English | Chinese |
|-----|---------|---------|
| ≥ 150 | Close windows and run the air purifier. | 關閉窗戶並開啟空氣清淨機。 |
| 100–149 | Consider closing windows and running the air purifier. | 建議關窗，可考慮開啟空氣清淨機。 |
| 51–99 | Sensitive groups: consider running the air purifier indoors. | 敏感族群可考慮開啟空氣清淨機。 |
| ≤ 50 | `null` (no chip shown) | — |

#### `web/static/app.js`

Air quality card renders `purifier_advice` as an insight chip (same
`air-quality` icon) beneath the AQI peak window chip when present.
