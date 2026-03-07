# Hero Facelift — 2-Column Current Conditions + Expandable Outdoor Score

**Date:** 2026-03-07

## Problem

The original "Current" tab showed a 3-column top row (ground gauge | icon+temp | wind gauge) plus a fixed 4-column gauge grid (humidity | AQI | UV | pressure). All seven metrics were always visible, making the hero feel dense and exposing equal visual weight to both primary actionable conditions and underlying factors.

## Solution

Redesign the current-conditions area as a 2-column card:

- **Left column** — weather icon anchored large on the left, temperature + description + solar times to its right.
- **Right column** — three stacked rows:
  1. Ground state (Dry / Wet + level colour)
  2. Wind description + speed + direction
  3. Outdoor score button (grade badge + label + chevron) that expands inline to reveal the four scoring factors: Humidity (+dew point), AQI (+PM2.5), UV Index, Pressure.

The gauge grid is removed entirely; the factor details live inside the expandable panel, reducing visual noise on first load.

## Files Changed

| File | Change |
|------|--------|
| `web/routes.py` | `_slice_current()` — added `outdoor` param; returns `outdoor.{score,grade,label}`, `dew_point`, `dew_gap`; `build_slices()` passes `outdoor_index` |
| `web/templates/dashboard.html` | Replaced `.current-top-row` + `.gauges-grid` with `.current-hero-row` → `.hero-left` + `.hero-right-stack` |
| `web/static/app.js` | `renderCurrentView()` drives `_renderHeroStat()` (ground/wind rows) + outdoor button + `_renderOutdoorFactor()` (expand panel); `initOutdoorExpand()` wires click handler |
| `web/static/style.css` | Old hero/gauge CSS replaced with `.current-hero-row`, `.hero-left`, `.hero-text-block`, `.hero-right-stack`, `.hero-stat`/`.hs-*`, `.outdoor-toggle`/`.outdoor-details`/`.of-*`; mobile: single column |

## Layout

```
┌──────────────────────────────────────────────────────────┐
│  [icon]  25°          Ground     Dry                      │
│  Partly Cloudy        Wind       Moderate Breeze 3.2 m/s  │
│  ↑ 06:12  ↓ 18:43   ┌─────────────────────────────────┐  │
│                      │  B  Good to go              ▾   │  │
│                      │── expand ───────────────────────│  │
│                      │  Humidity  72%    Moderate      │  │
│                      │  AQI       85     Moderate      │  │
│                      │  UV Index  3      Low           │  │
│                      │  Pressure  1013   Normal        │  │
│                      └─────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Data Flow

- `outdoor_index` (already computed by `weather_processor.py`) is passed to `_slice_current()` from `build_slices()`.
- `dew_point_c` / `dew_gap_c` come from the station-history derived fields appended by `fetch_current_conditions()`.
- The expand panel renders live from `data.outdoor`, `data.hum`, `data.aqi`, `data.uv`, `data.pres` and `data.dew_point`.

## Interaction

- Clicking the outdoor score button toggles `aria-expanded` and `hidden` on `#outdoor-details`.
- The chevron rotates 180° via CSS `transform` when `aria-expanded="true"`.
- Panel state is not persisted across renders (re-render from a refresh resets to collapsed).
