# Family Weather — TODO

**Last updated:** 2026-02-21
**Commit:** `e4e473e` — all tasks 1–15 + bug fixes + code quality pass complete

---

## Open

- [x] **Ménière's `pressure_change_24h` sign convention**
  - Currently stored as `drop` so a 7 hPa fall is `7.0` (positive)

---

## Recently completed

### Outdoor Index (2026-02-21)
- [x] **`data/processor.py`** — added `GRADE_THRESHOLDS`, `OUTDOOR_WEIGHTS_GENERAL`, `OUTDOOR_WEIGHTS_BY_ACTIVITY` constants; new helpers `_grade_score()`, `_score_conditions()`, `_compute_outdoor_index()`; Step 11 in `process()` computes index after menieres/cardiac alerts; `_classify_outdoor_mood()` refactored to accept `outdoor_index`, use score thresholds (35/50) for mood buckets, rank locations by top activity match; `"outdoor_index"` added to return dict
- [x] **`web/slices.py`** — `build_slices()` extracts `outdoor_index`; `_slice_overview()` merges `outdoor_score`/`outdoor_grade` into each timeline segment; `_slice_lifestyle()` returns full index data (score, grade, label, top_activity, activity_scores, parkinsons_safe, best_window) in the `"outdoor"` dict
- [x] **`web/static/app.js`** — timeline cards: new "Outdoor" row with `oi-grade-*` coloured pill (e.g. `A · 90`); Lifestyle Outdoor Activities card: grade badge (`Grade A · Excellent`) + sub-line (`Best: Morning · Top activity: cycling`)
- [x] **`web/static/style.css`** — five `.oi-grade-A/B/C/D/F` pill classes added after `.ls-badge` section

---

## Next iteration candidates

### Backend
- [ ] **pm25 / pm10 pipeline gap** — `fetch_moenv` returns both values but they are lost before reaching `processor.py`; wire through so they can be used in AQI risk logic and sliced to the UI
- [ ] **Load `regen.json` into processor** — 14-day regen cycle writes fresh meal/location lists to `local_data/regen.json` but processor still uses hardcoded lists; load from file if present
- [ ] **Date navigation API** — frontend never passes `?date=YYYY-MM-DD` to `/api/broadcast`; add prev/next day buttons and wire the query param
- [ ] **`save_day()` error handling** — pipeline silently reports success even if history save fails; wrap in try/except and surface in the NDJSON log stream
- [ ] **Thread safety for `_refresh_counter`** — global counter mutated across concurrent requests without a lock; use `threading.Lock` or `itertools.count`

### Frontend
- [ ] **Display `obs_time`** — CWA observation timestamp is in `slices.current.obs_time` but never shown; render as "As of HH:MM" beneath the temperature hero
- [ ] **Display pm25 / pm10** — available in `slices.current.aqi.pm25` / `.pm10`; add as sub-rows on the AQI gauge card
- [ ] **`heads_ups[]` list in overview** — full ranked list is in `slices.overview.alerts.heads_ups[]` but only the first paragraph `heads_up` string is rendered; expand the alert box to show all items
- [ ] **Date navigation UI** — prev/next buttons calling `/api/broadcast?date=YYYY-MM-DD`
- [ ] **Offline fallback page** — SW serves browser error page if both network and cache miss for `/`; add a minimal offline.html to SHELL_ASSETS

### PWA
- [ ] **PNG icon fallbacks** — `manifest.json` only has SVG icons; older Android may not render them; generate 192×192 and 512×512 PNGs



---

## Completed (this session)

### Slice layer
- [x] #1 Fix narration paragraph key mismatch (v5 → v6)
- [x] #2 Add pm25, pm10, obs_time to current slice
- [x] #3 Add aqi_forecast and transitions[] to overview slice
- [x] #4 Add commute_hazards and heads_ups[] to overview alerts
- [x] #5 Expose outdoor location structured object in lifestyle slice

### Frontend quick wins
- [x] #6 Visibility gauge (later removed — station 466881 has no data)
- [x] #7 Rain forecast text in right panel (later removed with context slice)
- [x] #8 HVAC mode badge + meal mood tag on lifestyle cards
- [x] #9 Commute hazards list + wardrobe feels-like

### Frontend medium
- [x] #10 Tomorrow's AQI forecast block (below 24h timeline)
- [x] #11 Transition badges on timeline cards (at_delta, pop_shift)
- [x] #12 Kids audio toggle in narration view
- [x] #13 Outdoor venue card with Maps link + Parkinson's badge

### Backend
- [x] #14 Persist 14-day regen output to local_data/regen.json
- [x] Ménière's alert rewrite — 4 triggers, severity levels, new schema
- [x] Claude model IDs corrected (claude-sonnet-4-6, claude-haiku-4-5-20251001)
- [x] TTS strips ---METADATA--- block before synthesis

### PWA
- [x] #15 SW normalisedRequest() strips ?v=N; /local_assets/ cached; weather-v7

### Bugs fixed
- [x] BUG-F1 Dark mode IIFE crash (wrong element IDs)
- [x] BUG-F2 Wind direction "null m/s null"
- [x] BUG-F3 Timeline cards "undefined" text
- [x] BUG-B1 meal_mood KeyError ("suggestions" → top_suggestions)
- [x] BUG-B2 int(rh) / int(aqi) TypeError when None
- [x] BUG-B3 activity_suggested dead reference
- [x] BUG-B4 top_locations[0] IndexError
- [x] Remove context slice (backend + frontend)

### Code quality
- [x] Dead code removed (dangling utils imports, _extract_heads_up, _generate_dummy_audio, duplicate RUN_MODE import)
- [x] Threshold constants moved to config.py (HISTORY_DAYS, REGEN_CYCLE_DAYS, MEAL_FALLBACK_DISH, AQI_ALERT_THRESHOLD, CLIMATE_TEMP_*, CLIMATE_RH_*)
- [x] import random hoisted to module level in processor.py
- [x] Responsive CSS for .timeline-grid (1024px → 2-col, 640px → 1-col)
- [x] Duplicate html.dark audio CSS rule removed
- [x] Dark mode level colors completed (lvl-1 through lvl-5)
- [x] `template_narrator.py:47` — `float(rain or 0)` added
- [x] `fetch_moenv.py:113` — parse to `datetime` before sorting
- [x] `narration/summarizer.py:72` — try/except for `json.loads()`
- [x] Config validation on startup added to `main.py`
