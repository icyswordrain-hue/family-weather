# Backend Code Review: Family Weather Dashboard

**Last reviewed:** 2026-02-20 (round 2 — post tasks 1–9 + Ménière's rewrite)
**Codebase root:** `C:\Users\User\.gemini\antigravity\scratch\family-weather`

---

## Executive Summary

1. **Ménière's alert schema fully computed but only partially exposed** — new `{triggered, severity, triggers[], pressure_current, pressure_change_24h, max_rh, message}` dict is passed as a blob to slices; `pressure_change_24h` and `max_rh` should be promoted as first-class fields.
2. **Schema mismatch: `meal_mood` key** — `slices.py:190` accesses `.get("suggestions")` but processor returns `top_suggestions` / `all_suggestions` (KeyError at runtime).
3. **Null guards missing in slices.py** — `int(rh)` and `int(aqi)` on lines 181/183 raise `TypeError` when RH or AQI is None.
4. **Dead code accumulation** — `utils.py::extract_paragraphs/extract_metadata` never called (v6 uses `prompt_builder`); `_extract_heads_up()` in slices.py; dangling `from narration.utils import …` in both `gemini_client.py` and `claude_client.py`.
5. **Hardcoded thresholds scattered across processor.py** — AQI > 100, humidity > 80, temperature breakpoints should live in `config.py`.

---

## 1. Data Sources

### CWA (Central Weather Administration)

**Current conditions** (`O-A0003-001`, Banqiao station 466881) — `data/fetch_cwa.py::fetch_current_conditions()`

| Field | Description |
|---|---|
| `station_id`, `station_name`, `obs_time` | Station identity + observation timestamp |
| `AT` | Air temperature (°C) |
| `RH` | Relative humidity (%) |
| `WDSD` | Wind speed (m/s) |
| `WDIR` | Wind direction (degrees) |
| `RAIN` | Precipitation (mm) |
| `Wx` | Weather code (int) |
| `WxText` | Weather description (e.g. "陰") — fetched but not propagated |
| `visibility` | Visibility (km) — fetched but not incorporated into risk assessment |
| `PRES` | Atmospheric pressure (hPa) |
| `UVI` | UV Index |

**36-hour forecast** (`F-D0047-071`) for 三峽區 and 板橋區

Each time slot dict: `start_time`, `end_time`, `AT`, `RH`, `WS`, `WD`, `PoP6h`, `Wx`

### MOENV (Ministry of Environment)

**Real-time AQI** (`aqx_p_432`, Tucheng station) — `fetch_realtime_aqi()`

Returns: `station_name`, `aqi`, `status`, `pm25`, `pm10`, `publish_time`
⚠️ `pm25` and `pm10` are available but **lost in fetch_moenv → processor pipeline**.

**AQI 3-day forecast** (`AQF_P_01`, Northern zone) — `fetch_forecast_aqi()`

Returns: `area`, `aqi`, `status`, `forecast_date`, `content`

---

## 2. Data Processing Pipeline

`data/processor.py::process()` enriches raw data through 10 steps:

1. **Current conditions enrichment** — feels-like AT, 5-level text/level fields: `uv`, `hum`, `pres`, `wind`, `vis`, `ground_state/level`, `aqi`
2. **Primary forecast selection** — prefers Sanxia, falls back to Banqiao
3. **Forecast segmentation** — Morning/Afternoon/Evening/Overnight by local time
4. **Segment enrichment** — `AT`, `wind_text/level`, `wind_dir_text`, `precip_text/level`, `cloud_cover`, `beaufort_desc`
5. **Transition detection** — adjacent segment deltas: AT >5°C, PoP category >1, RH >20%, Beaufort >1, wind dir >90°, cloud cover change
6. **Commute windows** — 07:00–08:30 and 17:00–18:30 with AT/precipitation/wind/visibility/hazards
7. **Meal mood** — classifies into 4 categories, picks one dish avoiding recent 3 days; fallback hardcoded `"Sandwich"` (should be in config)
8. **Outdoor locations** — classifies weather, rotates through 20+ curated venues `{name, lat, lng, activity, surface, parkinsons, notes}`
9. **Climate control** — recommends `mode`, `set_temp`, `estimated_hours`, `windows_open`, `notes[]`
10. **Heads-ups** — up to 3 priority alerts: cardiac, Ménière's (new schema), rain (PoP ≥61%), AQI >100

**Top-level `processed` dict keys:**
`current`, `forecast_segments`, `transitions`, `heads_ups`, `commute`, `meal_mood`, `recent_meals`, `location_rec`, `recent_locations`, `climate_control`, `cardiac_alert`, `menieres_alert`, `aqi_realtime`, `aqi_forecast`

---

## 3. Ménière's Alert — Current Schema (v2)

Computed in `_detect_menieres_alert(current, history, segments)`:

```python
{
  "triggered": bool,
  "severity": "moderate" | "high" | None,
  "triggers": [str, ...],       # list of active trigger descriptions
  "pressure_current": float,
  "pressure_change_24h": float, # negative = pressure dropped (sign convention: drop is negative)
  "max_rh": float,
  "message": str | None
}
```

**Triggers:**
1. Pressure drop ≥ 6 hPa / 24h
2. Typhoon proximity: drop ≥ 10 hPa (forces severity = "high")
3. Absolute pressure < 1,005 hPa
4. RH ≥ 90% across 2+ forecast segments

**⚠️ Sign convention note:** `pressure_change_24h` stores `-(drop)` so a 7 hPa fall is stored as `-7.0`. This is non-intuitive; document clearly or flip sign.

---

## 4. Narration / Broadcast Pipeline

### Provider selection (`config.NARRATION_PROVIDER`, default `CLAUDE`)

| Provider | Primary model | Fallback |
|---|---|---|
| Claude | `claude-sonnet-4-6` | `claude-haiku-4-5-20251001` |
| Gemini | `gemini-2.0-pro-exp` | `gemini-1.5-flash` |
| Template | deterministic | (none) |

### Prompt v6 (`narration/prompt_builder.py`)

6 paragraphs + `---METADATA---` JSON block (12 keys) + optional `---REGEN---` block.

**Paragraph keys:** `p1_conditions`, `p2_garden_commute`, `p3_outdoor`, `p4_meal_climate`, `p5_forecast`, `p6_accuracy`

**Metadata keys:** `wardrobe`, `rain_gear`, `commute_am`, `commute_pm`, `meal`, `outdoor`, `garden`, `climate`, `cardiac_alert`, `menieres_alert`, `forecast_oneliner`, `accuracy_grade`

### Summarizer (`narration/summarizer.py`)

Second Claude Haiku call → 7 card-sized fields: `wardrobe`, `rain_gear`, `commute`, `meals`, `hvac`, `garden`, `outdoor`.

**⚠️ Returns empty dict on error; slices.py `.get()` calls will silently return None.**

### TTS (`narration/tts_client.py`)

Google Cloud TTS (Edge TTS fallback). Produces `broadcast.mp3` + `broadcast_kids.mp3`.

**Known bugs:**
- Duplicate `RUN_MODE` import (line 30-31)
- `_generate_dummy_audio()` defined but never called (dead code)
- Regex sentence splitter creates odd-length list; loop assumes pairs (line 167) — fragile
- Hard split at `MAX_CHARS=4000` doesn't preserve word boundaries (comment says limit is 5000)

---

## 5. Web API (`web/slices.py`)

### `build_slices()` output — 4 slices (context removed)

**`current`:** `temp`, `obs_time`, `location`, `weather_code/text`, `ground_state/level`, `hum/wind/aqi/vis/uv/pres` (each with `val/text/level`); `aqi` also has `pm25`, `pm10`

**`overview`:** `timeline[]` (segments with `display_name`, `AT`, `precip_text/level`, `wind_text/level`, `cloud_cover`, `Wx`), `aqi_forecast`, `transitions[]`, `alerts {cardiac, menieres, heads_up, heads_ups[], commute_hazards[]}`

**`lifestyle`:** `wardrobe {text, feels_like}`, `rain_gear {text}`, `commute {text, hazards[]}`, `hvac {text, mode}`, `meals {text, mood}`, `garden {text}`, `outdoor {text, location}`

**`narration`:** `paragraphs[]`, `meta {model, source}`

---

## 6. Confirmed Bugs & Schema Issues

| # | Severity | File | Issue |
|---|----------|------|-------|
| B1 | **CRITICAL** | `slices.py:190` | `meal_mood.get("suggestions")` → key doesn't exist; processor returns `top_suggestions` / `all_suggestions` |
| B2 | **HIGH** | `slices.py:181,183` | `int(rh)` / `int(aqi)` raise `TypeError` when value is None |
| B3 | **HIGH** | `slices.py:209` | `activity_suggested` accessed but never computed by processor — always None |
| B4 | **HIGH** | `slices.py:214` | No null check before `top_locations[0]` — IndexError if list empty |
| B5 | **MEDIUM** | `gemini_client.py:114` | Dangling `from narration.utils import …` — dead import |
| B6 | **MEDIUM** | `claude_client.py:17` | Same dangling utils import |
| B7 | **MEDIUM** | `slices.py:278–290` | `_extract_heads_up()` function defined but never called |
| B8 | **MEDIUM** | `tts_client.py:30` | `RUN_MODE` imported twice (typo) |
| B9 | **MEDIUM** | `main.py:159` | Global `_refresh_counter` not thread-safe under concurrent requests |
| B10 | **LOW** | `processor.py:1009` | `pressure_change_24h` sign convention: negative = pressure fell (non-intuitive) |
| B11 | **LOW** | `fetch_cwa.py:488` | `except Exception: continue` swallows all slot-matching errors silently |
| B12 | **LOW** | `tts_client.py:326,342` | Edge TTS failures return `b""` without logging — silent audio loss |

---

## 7. Data Gaps Still Open

| # | Gap | Where Data Lives | Status |
|---|-----|-----------------|--------|
| G1 | **pm25 / pm10** from MOENV not passed from `fetch_moenv` to `processor` | `fetch_moenv.py:61-62` | ⚠️ Available but lost before processor |
| G2 | **WxText** from fetch_cwa never propagated | `fetch_cwa.py:121` | ⚠️ Unused |
| G3 | **visibility** not incorporated into any risk metric | `fetch_cwa.py:122` | ⚠️ Station 466881 doesn't report it anyway |
| G4 | **cardiac alert** not exposed in lifestyle slice | `processor.py` | ⚠️ Only in overview alerts |
| G5 | **Ménière's `pressure_change_24h` / `max_rh`** buried in alert object | `slices.py:138` | ⚠️ Not first-class lifestyle fields |
| G6 | **14-day regen output** never persisted | `main.py` | Task #14 |
| G7 | **`aqi_range`** computed in fetch_moenv but never returned | `fetch_moenv.py:119` | Dead code |

---

## 8. Hardcoded Values to Move to config.py

```python
# processor.py
MEAL_FALLBACK_DISH = "Sandwich"
OUTDOOR_MOOD_AQI_THRESHOLD = 100
CLIMATE_HUMIDITY_THRESHOLD = 80
CLIMATE_TEMP_HOT = 30
CLIMATE_TEMP_WARM = 26
CLIMATE_TEMP_COLD_UPPER = 18
CLIMATE_TEMP_COLD_LOWER = 14
HISTORY_DAYS = 3         # main.py:178
REGEN_CYCLE_DAYS = 14    # main.py:200
```

---

## 9. Priority Fixes

1. **Fix `meal_mood.get("suggestions")` → `top_suggestions`** in `slices.py:190` *(KeyError in production)*
2. **Add `or 0` guard to `int(rh)` / `int(aqi)`** in `slices.py:181,183` *(TypeError in production)*
3. **Null-guard `top_locations[0]`** in `slices.py:214` *(IndexError if no location computed)*
4. **Remove dead imports** in `gemini_client.py:114` and `claude_client.py:17`
5. **Promote Ménière's granular fields** — expose `pressure_change_24h` and `max_rh` as direct keys in the overview `menieres` dict in `slices.py`
