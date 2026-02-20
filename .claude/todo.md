# Family Weather — Next Iteration TODO

## Slice layer (backend — no new computation)

- [x] **#1** Fix narration paragraph key mismatch (v5→v6)
  - `web/slices.py` uses old v5 display titles to look up narration paragraphs
  - LLM now produces v6 keys: `p1_conditions`, `p2_garden_commute`, `p3_outdoor`, `p4_meal_climate`, `p5_forecast`, `p6_accuracy`
  - Fallback to narration paragraphs silently fails when Haiku summarizer errors

- [x] **#2** Add `pm25`, `pm10`, and `obs_time` to current slice
  - `pm25` / `pm10` from `processed.aqi_realtime` → add to `slices.current.aqi`
  - `obs_time` (CWA observation timestamp) → add as top-level field on `slices.current`

- [x] **#3** Add `aqi_forecast` and `transitions[]` to overview slice
  - `processed.aqi_forecast` → expose as `slices.overview.aqi_forecast`
  - `processed.transitions[]` → expose as `slices.overview.transitions`

- [x] **#4** Add commute hazards and full `heads_ups[]` to overview alerts
  - Merge `processed.commute.morning.hazards` + `processed.commute.evening.hazards` → `slices.overview.alerts.commute_hazards`
  - Expose full `processed.heads_ups[]` list → `slices.overview.alerts.heads_ups` (keep existing `heads_up` string)

- [x] **#5** Expose outdoor location structured object in lifestyle slice
  - From `processed.location_rec.top_locations[0]` → add `slices.lifestyle.outdoor.location`
  - Fields: `name`, `activity`, `surface`, `parkinsons`, `lat`, `lng`, `notes`

---

## Frontend quick wins (HTML/JS only)

- [x] **#6** Add visibility gauge to dashboard
  - Add `<div id="gauge-vis">` to gauges grid in `dashboard.html`
  - Add `renderGauge('gauge-vis', ...)` call in `app.js::renderCurrentView()`

- [x] **#7** Restore rain forecast text in right panel
  - Add `<div id="rp-dynamic"></div>` back into `.rp-top` in `dashboard.html`
  - JS render logic in `updateRightPanel()` already exists; no JS changes needed

- [x] **#8** HVAC mode badge + meal mood tag on lifestyle cards
  - Show `slices.lifestyle.hvac.mode` as a colored badge on the HVAC card
  - Show meal mood category as a tag on the Meals card

- [x] **#9** Commute hazards list + wardrobe feels-like on lifestyle cards
  - Render `slices.lifestyle.commute.hazards[]` as `<ul>` beneath commute card text
  - Show `slices.lifestyle.wardrobe.feels_like` as "Feels like N°" sub-note

---

## Frontend medium (blocked on slice work)

- [x] **#10** Tomorrow's AQI forecast block on dashboard *(done 2026-02-20)*
  - Added `#ov-aqi-forecast` div in `dashboard.html` after `#ov-alerts`
  - Rendered in `renderOverviewView` from `data.aqi_forecast.{status, content, aqi, forecast_date}`
  - Styled as `.aqi-forecast-block` with accent left-border

- [x] **#11** Transition indicators between timeline cards *(done 2026-02-20)*
  - Built `transitionMap` from `data.transitions[]` keyed by `from_segment`
  - Each timeline card shows a `.tc-transition` badge with `at_delta` and `pop_shift` when `is_transition: true`

- [x] **#12** Kids audio toggle in narration view *(done 2026-02-20)*
  - Added `#audio-kids-toggle` button in `.audio-controls` wrapper in `dashboard.html`
  - `renderNarrationView` wires toggle: swaps audio src, updates label/icon, toggles `.active` class
  - Button hidden when `kids_audio_url` not available

- [x] **#13** Outdoor venue card in lifestyle view *(done 2026-02-20)*
  - Renders `name`, `activity`, `surface`, `notes` from `lifestyle.outdoor.location`
  - Google Maps link from `lat`/`lng` (opens in new tab)
  - Parkinson's friendly badge if `parkinsons: true`

---

## Backend persistence

- [x] **#14** Persist 14-day LLM regen output to `local_data/regen.json` *(done 2026-02-20)*
  - `main.py`: added `import os`; in `if regen_data:` block writes `{...regen_data, "updated_at": ISO}` to `LOCAL_DATA_DIR/regen.json`
  - Uses `os.makedirs(exist_ok=True)` for safety; failures logged as warnings (non-fatal)

---

## PWA / service worker

- [x] **#15** Fix service worker SHELL_ASSETS versioned URL mismatch *(done 2026-02-20)*
  - `sw.js`: added `normalisedRequest()` helper that strips `?v=N` query strings before cache lookup/put
  - `/local_assets/` audio: cache-first handler added so last broadcast survives offline
  - Bumped cache name to `weather-v7` to force old SW eviction

---

## Bugs & Hotfixes

- [x] **TTS reads metadata block** *(2026-02-20)*
  - `synthesize_and_upload()` received the raw LLM response including `---METADATA---` and `---REGEN---` blocks
  - Fix: strip on `---METADATA---` at entry of `narration/tts_client.py::synthesize_and_upload()` before any TTS path runs
  - Safe for template narration (no separator present → no-op)

- [x] **Visibility gauge shows "Unknown"** *(2026-02-20)*
  - **Root cause: backend data** — CWA Banqiao station (466881) does not return a `Visibility` or `VisibilityDescription` field in the API response
  - `fetch_cwa.py` tries both fields; both return `None`; `processor.py::_val_to_scale(None, ...)` correctly returns `("Unknown", 0)`
  - Resolution: removed visibility gauge from frontend entirely (data will never be available from this station)
  - `#gauge-vis` removed from `dashboard.html`; `renderGauge('gauge-vis', ...)` removed from `app.js`; gauges grid reverted to 4 columns

- [x] **Remove context slice** *(2026-02-20)*
  - Removed `_slice_context()` from `web/slices.py` and dropped `context` key from `build_slices()`
  - Removed `#rp-dynamic` div from `dashboard.html`
  - Removed `updateRightPanel()` function and all call sites from `app.js`
  - `location` (station name) moved from context slice into `slices.current.location`; sidebar `#rp-location` now set from `renderCurrentView()`

- [x] **BUG-F1: Dark mode IIFE crashes on page load** *(fixed 2026-02-20)*
  - `dashboard.html:205–223` queries `dark-mode-btn`, `dark-mode-icon`, `dark-mode-label` which don't exist
  - Actual IDs: `theme-toggle`, `theme-icon`, `theme-text`
  - Fix: update the three `getElementById` calls in the inline script block

- [x] **BUG-F2: Wind direction renders "null m/s null"** *(fixed 2026-02-20)*
  - `app.js` renders `${data.wind.val} m/s ${data.wind.dir}` with no null guard on `wind.dir`
  - Fix: `${data.wind.dir || '—'}`

- [x] **BUG-F3: Timeline cards show "undefined" text** *(fixed 2026-02-20)*
  - `seg.precip_text`, `seg.wind_text`, `seg.AT` rendered without null guards in card template
  - Fix: add `|| '—'` fallbacks; use `seg.AT ?? seg.T ?? 0` for temperature

- [x] **BUG-B1: `meal_mood.get("suggestions")` KeyError** *(fixed 2026-02-20)*
  - `slices.py:190` accesses `meal_mood.get("suggestions", [])` but processor returns `top_suggestions` / `all_suggestions`
  - Fix: change to `meal_mood.get("top_suggestions", []) or meal_mood.get("all_suggestions", [])`

- [x] **BUG-B2: `int(rh)` / `int(aqi)` TypeError when None** *(fixed 2026-02-20)*
  - `slices.py:181,183` calls `int(rh)` and `int(aqi)` without null guard
  - Fix: `int(rh or 0)`, `int(aqi or 0)`

- [x] **BUG-B3: `activity_suggested` never computed** *(fixed 2026-02-20)*
  - `slices.py:209` accesses `location_rec.get("activity_suggested")` but processor never sets this key
  - Fix: remove reference or derive from `top_locations[0].get("activity")` instead

- [x] **BUG-B4: `top_locations[0]` IndexError when list empty** *(fixed 2026-02-20)*
  - `slices.py:214` accesses index 0 with no length check
  - Fix: `top_locations[0] if top_locations else None`

---

## Code Quality / Debt

- [x] **Dead code removal** *(done 2026-02-20)*
  - Removed dangling `from narration.utils import …` from `gemini_client.py`, `claude_client.py`, `main.py`
  - Removed `_extract_heads_up()` from `slices.py`
  - Removed `_generate_dummy_audio()` from `tts_client.py`
  - Fixed duplicate `RUN_MODE` import in `tts_client.py`

- [x] **Responsive timeline CSS** *(done 2026-02-20)*
  - Added `@media (max-width: 1024px)` → `repeat(2,1fr)` and `@media (max-width: 640px)` → `1fr`

- [x] **Duplicate CSS rule** *(done 2026-02-20)*
  - Removed second `html.dark audio { filter: invert(1) hue-rotate(180deg); }` rule

- [x] **Dark mode level colors incomplete** *(done 2026-02-20)*
  - Added `html.dark .lvl-1` through `html.dark .lvl-5` overrides; replaced stale `[data-theme="dark"]` selectors

- [x] **Move hardcoded thresholds to config.py** *(done 2026-02-20)*
  - Added: `MEAL_FALLBACK_DISH`, `AQI_ALERT_THRESHOLD`, `CLIMATE_TEMP_*`, `CLIMATE_RH_*`, `HISTORY_DAYS`, `REGEN_CYCLE_DAYS`
  - Hoisted `import random` to module level in `processor.py`
  - Updated all references in `processor.py` and `main.py`

- [ ] **Ménière's `pressure_change_24h` sign convention**
  - Currently stored as negative when pressure fell; document clearly or flip to positive (drop = positive number)
