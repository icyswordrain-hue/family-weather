# Location-Aware Forecast Segments & Commute

**Date:** 2026-03-15

## Summary

Forecast segments and commute windows now reflect **where Dad actually is** at each time of day. On weekdays, Morning/Afternoon use Banqiao (work) forecast data; Evening/Overnight use Shulin (home). Weekends use Shulin for everything. The same logic extends to the 7-day forecast timeline.

## Before

- All 4 forecast segments (Morning/Afternoon/Evening/Overnight) used Shulin data only
- Commute windows used home forecast for both legs
- `banqiao_slots` was assigned but never referenced (dead code)
- `fetch_work_conditions()` existed but was never called (still unused — fetches observations, not forecasts)
- 7-day forecast used only Shulin (`primary_7day_slots`)

## After

### 36-Hour Segments (weather_processor.py Step 3)

| Segment | Weekday Source | Weekend Source |
|---------|---------------|----------------|
| Morning (06–12) | Banqiao | Shulin |
| Afternoon (12–18) | Banqiao | Shulin |
| Evening (18–24) | Shulin | Shulin |
| Overnight (00–06) | Shulin | Shulin |

Implementation: calls `_segment_forecast()` twice (once per location) and merges by segment name. Each segment dict tagged with `location` field ("Banqiao" or "Shulin"). Falls back to Shulin if Banqiao data is missing.

### Commute Windows (Step 6)

| Leg | Weekday | Weekend |
|-----|---------|---------|
| Morning (07:00–08:30) | Banqiao slots (destination) | Shulin slots |
| Evening (17:00–18:30) | Shulin slots (home) | Shulin slots |

### 7-Day Forecast (Step 2b)

- Day slots (hour < 18) on weekdays use Banqiao; Night slots and weekends use Shulin
- Both location slot arrays are enriched independently via `_enrich_7day()` helper
- Slots matched by `start_time` key for accurate pairing

### Transitions

`_detect_transitions()` now includes `location_change: true/false` on each transition dict. This lets the frontend/LLM distinguish "weather shifted" from "you moved locations."

### Narration

- LLM prompt updated: "Shulin → Banqiao morning, Banqiao → Shulin evening"
- Commute hints include direction labels and apparent temperature at each destination
- Downstream consumers (outdoor index, cardiac alerts, fallback narrator) automatically use location-aware segment data

### Frontend

- 36h timeline: small location badge ("Banqiao" / "Shulin") under each segment label
- 7-day timeline: location badge per row ("Banqiao / Shulin" on weekdays, "Shulin" on weekends)
- New CSS class `.tc-seg-location` — 0.65rem, 55% opacity

## Files Changed

| File | Changes |
|------|---------|
| `data/weather_processor.py` | Segment merge, 7-day merge, commute weekday guard, transition location_change flag |
| `narration/llm_prompt_builder.py` | Directional commute prompt + enriched commute hints |
| `web/routes.py` | Pass `location` to timeline segments |
| `web/static/app.js` | Location badges on 36h + 7-day timelines |
| `web/static/style.css` | `.tc-seg-location` styling |

## Notes

- `fetch_work_conditions()` in `fetch_cwa.py` remains unused — it fetches live observations (not forecasts). Will become useful when adding real-time destination conditions to the dashboard.
- The `is_weekday` check uses `datetime.now().weekday()` — same naive-Taipei-time contract as the rest of the codebase.
- Banqiao forecast data was already being fetched by `fetch_all_forecasts()` / `fetch_all_forecasts_7day()` via `CWA_FORECAST_LOCATIONS = ["樹林區", "板橋區"]` — no additional API calls needed.
