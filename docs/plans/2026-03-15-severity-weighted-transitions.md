# Severity-Weighted Transition Alerts

## Context

The transition system compares adjacent 6-hour forecast segments and flags
"breaches" shown as compact badges between timeline slots (e.g., "change +10° ·
Cloudy"). Several accuracy and delivery issues were identified:

- AT/RH deltas used a single CWA slot instead of the segment average
- CloudCover triggered on cosmetic 1-step changes (Fair <-> Mixed Clouds)
- Wind Direction was computed but never rendered (dead code)
- No severity ranking — a 15 C swing and a cloud shift had equal visual weight
- AT showed only the delta (+10) with no absolute temperature context
- RH showed only direction ("Humid") with no magnitude

## Changes

### Backend (`data/weather_processor.py`)

**`_segment_forecast()`** now stores `AvgAT` and `AvgRH` per segment, averaged
across all CWA slots in the 6-hour window.

**`_detect_transitions()`** overhauled with 7 severity-weighted metrics:

| Metric | Threshold | Severity tiers |
|--------|-----------|---------------|
| AT | >5 C delta (uses AvgAT) | >5 mild, >8 notable, >12 significant |
| PoP6h | >1 category jump | >1 mild, >2 notable, >3 significant |
| DewGap (replaces RH) | Comfort category shift | 1-step mild, 2 notable, 3+ significant |
| WS | >2 Beaufort jump | >2 mild, >3 notable, >4 significant |
| CloudCover | >=2 category jump (was: any) | 2 mild, 3 notable, 4 significant |
| SafeMinutes (new) | Outdoor window shrinkage | Boundary-based (120/20 min thresholds) |
| WD | Removed | Was dead code — never rendered in frontend |

Breaches sorted by severity (significant first). Each transition carries an
overall `severity` field matching the highest breach severity.

### Frontend (`web/static/app.js`)

- AT displays absolute temps: `18->28` instead of `+10`
- DewGap shows comfort destination label (Clammy, Comfortable, Dry, etc.)
- SafeMinutes shows actionable labels (Outdoor window closing, etc.)
- Transition badge receives severity CSS class (`tc-transition--{severity}`)
- Chinese translations added for all new labels

### Styling (`web/static/style.css`)

Three severity levels using existing earthy design tokens:

- **mild**: default gold border (unchanged)
- **notable**: mustard tint (`--tint-caution`) + `--lvl-3` border
- **significant**: terracotta tint (`--tint-heat`) + `--warn` border

Dark mode overrides included.

## Metrics Considered but Skipped

| Metric | Reason |
|--------|--------|
| UV Index | Not available per segment (current conditions only) |
| Pressure | Covered by Menieres 24h alert separately |
| Visibility | Not in segment data |
| T (actual temp) | Redundant with AT |
