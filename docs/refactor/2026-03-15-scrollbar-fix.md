# Fix: Dashboard Scrollbar + Cross-Day Location Test Coverage

**Date:** 2026-03-15

## Scrollbar Fix

### Problem

Dashboard content extending below the viewport was clipped with no scrollbar. The 24-hour forecast and sections below the hero gauge were invisible on smaller screens or when content exceeded one viewport height.

### Root Cause

Classic flexbox `min-height` issue:

- `.app-shell` has `display: flex; height: 100vh; overflow: hidden`
- `.main-panel` has `flex: 1; overflow-y: auto`
- Flexbox default `min-height: auto` prevents `.main-panel` from shrinking below its content size
- Result: `.main-panel` expands beyond 100vh, parent's `overflow: hidden` clips it, and `overflow-y: auto` never activates

### Fix

Added `min-height: 0` to `.main-panel` in the Dashboard Layout section of `web/static/style.css`. This overrides the flexbox default, allowing the flex child to be constrained to the parent's height. Once constrained, `overflow-y: auto` kicks in and produces a scrollbar.

Mobile styles (`@media max-width: 767px`) already override to `height: auto; overflow-y: visible`, so mobile is unaffected.

## Cross-Day Location Test Coverage

### Context

On Sunday evening, the next Morning/Afternoon segments (Monday = weekday) should show "Banqiao" (work location), not "Shulin" (home). The per-segment weekday check was refactored in commit 64cd162 to use each slot's own `start_time` weekday instead of a single `datetime.now().weekday()` check. The logic is correct, but had no test coverage for the cross-day boundary case.

### Tests Added (`tests/test_processor_segmentation.py`)

| Test | Scenario | Expectation |
|------|----------|-------------|
| `test_sunday_evening_monday_segments_get_banqiao` | Sunday 20:00, slots spanning into Monday | Morning/Afternoon = Banqiao, Evening = Shulin, Overnight = Shulin |
| `test_friday_evening_saturday_segments_all_shulin` | Friday 21:00, slots spanning into Saturday | All segments = Shulin |

### Documentation Update

Updated `docs/refactor/2026-03-15-location-aware-forecast.md` to reflect the per-segment `start_time` weekday check (previously documented as `datetime.now().weekday()`).

## Files Changed

| File | Changes |
|------|---------|
| `web/static/style.css` | Added `min-height: 0` to `.main-panel` |
| `tests/test_processor_segmentation.py` | Added 2 cross-day location assignment tests + helper utilities |
| `docs/refactor/2026-03-15-location-aware-forecast.md` | Corrected weekday check documentation |
