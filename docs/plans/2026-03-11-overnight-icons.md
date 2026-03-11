# Overnight Icons

**Goal:** Show condition-appropriate night icons for evening and overnight
slots instead of daytime icons.

**Status:** Fully implemented (commits `b48ea06`, `0a8714c`)

---

## What Was Built

### `web/static/app.js`

`getWeatherIcon(weatherKey, alt, isNight)` after the `ICONS` map (line 156).
Returns a night-specific icon when `isNight=true`; falls back to
`ICONS[key] || IMG('cloudy', 'Cloudy')` for unknown keys.

| Condition keys | Night icon |
|----------------|-----------|
| `sunny`, `Sunny/Clear`, `1`, `Sunny` | `clear-night.webp` |
| `partly-cloudy`, `Mixed Clouds`, `2`, `3` | `partly-cloudy-night.webp` |
| `cloudy`, `Overcast`, `4`–`7` | `cloudy-night.webp` |
| `rainy`, `8`–`20` | `rainy-night.webp` |

Applied in three places:

| Location | `isNight` source |
|----------|-----------------|
| `renderCurrentView` — `#cur-icon` (line 467) | `new Date().getHours() >= 18 \|\| h < 6` |
| `renderOverviewView` — 24h timeline slot icon (line 606) | slot start time |
| `renderOverviewView` — 7-day weekly night column (line 862) | hardcoded `true` |

### `web/static/brand-icons/`

All four generated via Nano Banana Pro using `vase-icon.webp` as style reference
(fine-line sketch, cream background `#F3F7F8`):

| File | Subject | Primary color |
|------|---------|--------------|
| `clear-night.webp` | Crescent moon + stars | Navy Blue `#1C3E75` |
| `partly-cloudy-night.webp` | Crescent moon behind soft cloud | Navy Blue `#1C3E75` |
| `cloudy-night.webp` | Overcast clouds, moonlight glow behind | Dusty Plum `#9B5D77` |
| `rainy-night.webp` | Dark rain cloud with falling drops | Navy Blue `#1C3E75` |

---

## Verification

```bash
./run_local.ps1

# At 6pm–6am: hero icon shows night variant for each condition
# In 24h timeline: evening/overnight slots show night icons
# In 7-day grid: right (night) column shows night icons
```

---

## Post-implementation fixes

### Fix 1 — Icon dimensions (commit `a0d9dd9`)

Nano Banana Pro generated landscape images (e.g. 1408×768) instead of square.
All four night icons center-cropped and resized to 512×512 via Pillow to match
the day icons.

### Fix 2 — `wx_to_cloud_cover` key gaps (commit `a0d9dd9`)

`wx_to_cloud_cover()` (`data/scales.py:202`) returns `"Fair"` for wx codes 2–3
and `"Rain"` for wx codes 11–20. Neither string was in the `getWeatherIcon`
night branches, so those conditions fell back to the daytime cloudy icon.
Added `"Fair"` to the `partly-cloudy-night` branch and `"Rain"` to the
`rainy-night` branch.

### Fix 3 — Integer key type mismatch (commit `927a496`)

`weather_code` in the current-conditions slice (`web/routes.py:130`) is a raw
JSON integer. `Array.includes()` uses strict equality — `['2'].includes(2)` is
`false` — so all night branches were bypassed and integers fell through to the
daytime `ICONS` map. Fixed by coercing `weatherKey` to string at the top of
`getWeatherIcon` (`const key = String(weatherKey)`) and using `key` throughout,
including the `ICONS` fallback.

**Complete key mapping after all fixes:**

| `wx_to_cloud_cover` string | Integer codes | Night icon |
|---------------------------|--------------|-----------|
| `Sunny` | `1` | `clear-night` |
| `Fair` | `2`, `3` | `partly-cloudy-night` |
| `Mixed Clouds` | `4`–`7` | `partly-cloudy-night` |
| `Overcast` | `8`–`10` | `cloudy-night` |
| `Rain` | `11`–`20` | `rainy-night` |
