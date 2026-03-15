# Dashboard UI Facelift

Minor visual polish across dashboard, 24h forecast, 7-day forecast, and lifestyle cards.

## Changes

### 1. Default view → Dashboard
Default landing view switched from lifestyle to dashboard (canopy).

### 2. Merged "updated" pill
The "updated" label and timestamp were two separate pills; now merged into a single stacked pill (label on top, timestamp below). Stale colors (amber ≥2h, red ≥4h) tint the entire pill background. Applied to both sidebar and mobile header.

### 3. Wider 24h segment labels
`.tc-seg-left` widened from 72→86px desktop, 72→80px mobile so labels like "OVERNIGHT" are no longer truncated.

### 4. Per-segment weekday location fix
Previously `is_weekday` was checked once using `datetime.now()`. On Sunday evening, Monday morning/afternoon segments incorrectly showed Shulin. Now each segment's `start_time` determines its own weekday — Monday segments correctly show Banqiao.

### 5. Location below weather icon
Both 24h and 7-day forecasts now show the location label (Shulin/Banqiao) below the weather icon instead of above it. In the 7-day view, day and night icons each show their own location independently (was a combined "Shulin / Banqiao" line). Row height increased slightly to accommodate.

### 6. Heads-up card upgrade
Refactored from a custom inline layout to the standard `ls-card` pattern used by other lifestyle cards — icon, title with chevron, tagline (most severe alert message), and click-to-expand body with per-alert rows showing type icon, level, and message.

## Files Modified
- `web/static/app.js` — default view, stale pill targeting, location rendering, heads-up card
- `web/static/style.css` — merged pill, segment width, row heights, location labels, alert card styles
- `web/templates/dashboard.html` — active view classes, pill DOM restructure
- `data/weather_processor.py` — per-segment weekday location logic
