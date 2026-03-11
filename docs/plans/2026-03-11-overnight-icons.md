# Overnight Icons

**Goal:** Show clear-night / partly-cloudy-night icons for evening and overnight
slots instead of the daytime sunny/partly-cloudy icons.

**Status:** Implemented (commit `b48ea06`)

---

## What Was Built

### `web/static/app.js`

Added `getWeatherIcon(weatherKey, alt, isNight)` after the `ICONS` map (line 156).
Returns `clear-night.webp` or `partly-cloudy-night.webp` when `isNight=true` and
the condition key maps to clear or partly cloudy; otherwise falls back to
`ICONS[key] || IMG('cloudy', 'Cloudy')`.

Applied in three places:

| Location | `isNight` source |
|----------|-----------------|
| `renderCurrentView` — `#cur-icon` (line 467) | `new Date().getHours() >= 18 \|\| h < 6` |
| `renderOverviewView` — 24h timeline slot icon (line 606) | existing `isNight` variable from slot start time |
| `renderOverviewView` — 7-day weekly night column (line 862) | hardcoded `true` (column is always night) |

### `web/static/brand-icons/`

- `clear-night.webp` — crescent moon + stars on dark blue background (placeholder)
- `partly-cloudy-night.webp` — crescent moon + soft cloud (placeholder)

Both are 200×200 RGBA WebP generated via Pillow. Replace with final brand-style
art when available.

> **Note:** The original plan referenced `.png` and Nano Banana Pro for asset
> generation. Assets were generated programmatically as placeholders instead;
> `.png` references were corrected to use `IMG()` (→ `.webp`).

---

## Verification

```bash
# Start local server
./run_local.ps1

# At 6pm–6am: hero icon should show crescent moon (clear conditions)
# In 24h timeline: evening/overnight rows should show night icons
# In 7-day grid: right (night) column should show night icons

# Confirm no .png references remain in the helper
grep "clear-night\|partly-cloudy-night" web/static/app.js
# Expected: both lines use IMG() with no .png suffix
```
