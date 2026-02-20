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

- [ ] **#10** Tomorrow's AQI forecast block on dashboard *(blocked by #3)*
  - Show `aqi_forecast.forecast_date`, `.aqi`, `.status`, `.content`
  - Below current AQI gauge or in a new section under the 24h timeline

- [ ] **#11** Transition indicators between timeline cards *(blocked by #3)*
  - Match `transitions[]` entries to adjacent timeline card pairs
  - Render colored divider / arrow badge when `is_transition: true`
  - Show `at_delta`, `pop_shift` as inline text or tooltip

- [ ] **#12** Kids audio toggle in narration view
  - Add toggle button swapping audio src between `full_audio_url` and `kids_audio_url`

- [ ] **#13** Outdoor venue card in lifestyle view *(blocked by #5)*
  - Render `name`, `activity`, `surface`, `notes` below LLM paragraph text
  - Add Google Maps link from `lat`/`lng`
  - Add "Parkinson's friendly" badge if `parkinsons: true`

---

## Backend persistence

- [ ] **#14** Persist 14-day LLM regen output to `local_data/regen.json`
  - After parsing narration response, if `result.regen` is present write to file
  - Structure: `{ "meals": [...], "locations": [...], "updated_at": "ISO" }`

---

## PWA / service worker

- [ ] **#15** Fix service worker SHELL_ASSETS versioned URL mismatch
  - Strip query strings in SW `fetch` handler before cache lookup
  - Also cache `/local_assets/` audio files for offline playback of last broadcast
