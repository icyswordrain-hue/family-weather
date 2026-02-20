# Backend Research: Family Weather Dashboard

**Date of analysis:** 2026-02-20
**Codebase root:** `C:\Users\User\.gemini\antigravity\scratch\family-weather`

---

## 1. Data Sources

### CWA (Central Weather Administration)

**Current conditions** (`O-A0003-001`, Banqiao station 466881) — `data/fetch_cwa.py::fetch_current_conditions()`

| Field | Description |
|---|---|
| `station_id`, `station_name`, `obs_time` | Station identity and observation timestamp |
| `AT` | Air temperature (°C) |
| `RH` | Relative humidity (%) |
| `WDSD` | Wind speed (m/s) |
| `WDIR` | Wind direction (degrees) |
| `RAIN` | Precipitation (mm, from `Now.Precipitation`) |
| `Wx` | Weather code (int) |
| `WxText` | Weather description (e.g. "陰") |
| `visibility` | Visibility (km) |
| `PRES` | Atmospheric pressure (hPa) |
| `UVI` | UV Index |

**36-hour forecast** (`F-D0047-071`) — `fetch_all_forecasts()` for `三峽區` and `板橋區`

Each time slot dict: `start_time`, `end_time`, `AT`, `RH`, `WS`, `WD`, `PoP6h`, `Wx`

### MOENV (Ministry of Environment)

**Real-time AQI** (`aqx_p_432`, Tucheng station) — `fetch_realtime_aqi()`

Returns: `station_name`, `aqi` (int), `status` (Chinese category), `pm25`, `pm10`, `publish_time`

**AQI 3-day forecast** (`AQF_P_01`, Northern zone) — `fetch_forecast_aqi()`

Returns: `area`, `aqi`, `status` (major pollutant), `forecast_date`, `content` (free-text)

---

## 2. Data Processing Pipeline

`data/processor.py::process()` enriches raw data through 10 steps:

1. **Current conditions enrichment** — adds feels-like AT (`Ta + 0.33*e - 0.70*ws - 4.00`), all 5-level text/level fields: `uv_text/level`, `hum_text/level`, `pres_text/level`, `wind_text/level`, `wind_dir_text`, `aqi`, `aqi_status`, `aqi_level`, `vis_text/level`, `ground_state/level`
2. **Primary forecast selection** — prefers Sanxia, falls back to Banqiao
3. **Forecast segmentation** — Morning/Afternoon/Evening/Overnight based on current local time
4. **Segment enrichment** — adds `AT` (feels-like), `wind_text/level`, `wind_dir_text`, `precip_text/level`, `cloud_cover`, `beaufort_desc`
5. **Transition detection** — compares adjacent segments for AT delta >5°C, PoP category >1, RH delta >20%, Beaufort delta >1, wind direction delta >90°, cloud cover changes
6. **Commute windows** — 07:00–08:30 and 17:00–18:30 with AT/precipitation/wind/visibility/hazards
7. **Meal mood** — classifies into Hot & Humid / Warm & Pleasant / Cool & Damp / Cold, picks single dish avoiding recent 3 days
8. **Outdoor locations** — classifies into Nice/Warm/Cloudy & Breezy/Stay In, rotates through 20+ curated locations (name, lat, lng, activity, surface, parkinsons suitability, notes)
9. **Climate control** — recommends cooling/heating/dehumidify/fan mode, set temp, hours, windows_open
10. **Heads-ups** — up to 3 priority alerts: cardiac (≥10°C segment drop, overnight <10°C, daily swing ≥15°C), Ménière's (PRES <1013, drop >4 hPa from history, RH >85%), rain (PoP ≥61%), AQI >100, visibility <2 km, commute hazards

**Top-level `processed` dict keys:**
`current`, `forecast_segments`, `transitions`, `heads_ups`, `commute`, `meal_mood`, `recent_meals`, `location_rec`, `recent_locations`, `climate_control`, `cardiac_alert`, `menieres_alert`, `aqi_realtime`, `aqi_forecast`

---

## 3. Narration / Broadcast Pipeline

### Provider selection (`config.NARRATION_PROVIDER`, default `CLAUDE`)

| Provider | Primary model | Fallback |
|---|---|---|
| Claude | `claude-sonnet-4-6` | `claude-haiku-4-5` |
| Gemini | `gemini-2.0-pro-exp` | `gemini-1.5-flash` |
| Template | deterministic | (no fallback needed) |

### Prompt construction (`prompt_builder.build_prompt()`)

Sends to the LLM:
- Date + 3-day history (prior forecast, actual AT/RH/wind/AQI, meal/garden/outdoor meta)
- Full `processed` JSON
- Optional 14-day regen instruction

### System prompt v6 (~1,200 words)

Instructs 500–700 word plain English radio broadcast with 6 paragraphs:
- **P1** (always): conditions + heads-up alerts + cardiac/Ménière's + wardrobe
- **P2** (always): gardening tip + commute (both legs)
- **P3** (conditional): outdoor activity for Dad (skip if rain/AQI/heat/wind unsafe)
- **P4** (conditional): meal suggestion + climate control (each independently skippable)
- **P5** (always): 24-hour forecast narrative
- **P6** (always): yesterday forecast accuracy grade

Followed by `---METADATA---` JSON block with 12 structured keys: wardrobe, rain_gear, commute_am/pm, meal, outdoor, garden, climate, cardiac_alert, menieres_alert, forecast_oneliner, accuracy_grade.

### Summarizer (`narration/summarizer.py`)

Second Claude Haiku call converts narration paragraphs into 7 card-sized text fields (wardrobe, rain_gear, commute, meals, hvac — 2 sentences each; garden, outdoor — 4 sentences each).

### TTS (`narration/tts_client.py`)

Google Cloud TTS (Edge TTS fallback). Produces:
- `broadcast.mp3` — full broadcast, voice `en-US-Neural2-D`, 0.95x speed
- `broadcast_kids.mp3` — first ~60 words, voice `en-US-Neural2-F` / `en-US-AnaNeural`, 1.1x speed

Files uploaded to GCS or saved locally. Both URLs returned in `audio_urls`.

---

## 4. Web API (`web/slices.py`)

### Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Serves dashboard HTML |
| `/api/health` | GET | Health check |
| `/api/broadcast` | GET | Returns today's cached broadcast (or generates it); accepts `?date=YYYY-MM-DD` |
| `/api/refresh` | POST | Re-runs full pipeline; streams NDJSON logs + result |
| `/debug/log` | POST | Receives browser error reports |
| `/local_assets/<path>` | GET | Serves local audio files (LOCAL env only) |

### `build_slices()` output — 5 slices

**`current`**: `temp`, `weather_code/text`, `ground_state/level`, `hum/wind/aqi/vis/uv/pres` (each with `val/text/level`)

**`overview`**: `timeline[]` (segments sorted by `start_time` with `display_name`), `alerts` `{cardiac, menieres, heads_up}`

**`lifestyle`**: `wardrobe {text, feels_like}`, `rain_gear {text}`, `commute {text, hazards[]}`, `hvac {text, mode}`, `meals {text}`, `garden {text}`, `outdoor {text}` — each preferring Haiku summary, then narration paragraph, then hardcoded fallback

**`narration`**: `paragraphs[]` with legacy v5 titles (Current & Outlook, Commute, Outdoor Health, Meals, Climate & Cardiac, Forecast), `meta {model, source}`

**`context`**: `location` (station name), `rain_forecast_text`

---

## 5. Gaps: Data Processed But Not Surfaced

| # | Gap | Where Data Lives | Frontend Impact |
|---|-----|-----------------|----------------|
| 1 | **PM2.5 and PM10** | `processed.aqi_realtime.{pm25, pm10}` | Not in any slice; invisible to user |
| 2 | **AQI forecast `content` field** | `processed.aqi_forecast.content` | Sent to LLM but not in any slice |
| 3 | **AQI forecast as displayable unit** | `processed.aqi_forecast` | Not in any slice; no tomorrow AQI shown |
| 4 | **Transitions array** | `processed.transitions[]` | Not in overview slice; frontend cannot render change indicators |
| 5 | **Observation timestamp** | `processed.current.obs_time` | Not in current slice; only pipeline `generated_at` shown |
| 6 | **v5→v6 paragraph key mismatch** | `slices.py` uses v5 keys; LLM produces v6 keys | Narration view cards silently empty when Haiku summarizer fails |
| 7 | **Commute hazards in overview** | `processed.commute.{morning,evening}.hazards` | Only in lifestyle slice; not visible on dashboard view |
| 8 | **Outdoor location structured data** | `processed.location_rec.top_locations[0]` | Only text summary surfaced; lat/lng/parkinsons/map data lost |
| 9 | **Ménière's pressure delta** | `menieres_alert.{pressure, humidity}` | In slice object but no guaranteed frontend rendering |
| 10 | **Per-segment humidity trend** | `forecast_segments[seg].RH` | In timeline data but may not be rendered |
| 11 | **Regen meal/location data** | `result.regen` (14-day cycle) | Parsed and returned but never persisted — silently discarded |

---

## 6. Recommended Data to Surface

### High priority (zero new backend computation required)

1. Add `pm25` and `pm10` to `slices.current.aqi`
2. Add `aqi_forecast` as a dedicated field in `slices.overview` or `slices.context`
3. Add `transitions[]` to `slices.overview` for frontend change-indicator rendering
4. Add `obs_time` to `slices.current`
5. Fix paragraph key mismatch: update `slices.py` to use v6 keys (`p1_conditions`, `p2_garden_commute`, `p3_outdoor`, `p4_meal_climate`, `p5_forecast`, `p6_accuracy`)

### Medium priority

6. Add commute hazard strings to `slices.overview.alerts` alongside cardiac/Ménière's
7. Expose location structured object `{name, lat, lng, activity, parkinsons, notes}` in `slices.lifestyle.outdoor`
8. Add `menieres_alert.pressure` and computed pressure delta to the Ménière's alert object

### Lower priority

9. Surface per-segment `RH` in timeline cards
10. Persist the 14-day LLM regen output (meals + locations) to a JSON file
11. Surface `aqi_forecast.content` as a tooltip or expandable detail
