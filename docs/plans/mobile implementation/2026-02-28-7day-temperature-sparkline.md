# 7-Day Temperature Sparkline

> **Date:** 2026-02-28
> **Status:** Implemented
> **Commits:** `093f81d`, `556dac4`, `d11744f`, `4ec06cf`

---

## The Problem

The 7-day forecast grid showed temperature as a number in each card. There was no visual sense of how temperature varied across the week — whether tomorrow was warmer or colder than Sunday, or whether the whole week was flat. The existing `tempChart` variable (line 48, `app.js`) and Chart.js 4.4.0 (already loaded via CDN in `dashboard.html`) were both unused.

---

## Data Available

Each slot in `data.weekly_timeline` already has an `AT` (apparent temperature) value. Because the backend splits the 7-day forecast into day and night slots, grouping by calendar date gives two distinct temperatures per day — effectively a high (day AT) and low (night AT) — without any backend changes. `MaxAT` / `MinAT` from the raw CWA API are aggregated away during processing, but the day/night slot split recovers the same information.

---

## Design

A dual-line sparkline placed directly below the weekly grid, spanning the same width:

- **Day line** — amber (`#f0932b`, matches `--lvl-4`)
- **Night line** — blue (`#7da4ff`, matches the dark-mode night card border)
- **Plot area background** — `--surface`, filled via inline plugin so it follows light/dark theme
- **Outer padding background** — `--blue-lt`, making the padding zone visually distinct from the page background
- **Y-axis** — temperature gridlines at 5° intervals (15°, 20°, 25° …), always at least 3 lines

No new dependencies — Chart.js was already loaded.

---

## Changes Made

### `web/templates/dashboard.html` — commit `093f81d`

A `<canvas>` element added inside the 7-day `dashboard-overview-section`, immediately after `#ov-weekly-timeline`:

```html
<div class="weekly-sparkline-wrap">
  <canvas id="ov-weekly-sparkline"></canvas>
</div>
```

### `web/static/app.js` — commits `093f81d`, `556dac4`, `d11744f`, `4ec06cf`

Sparkline rendering added at the end of the existing `if (weeklyTimelineEl && data.weekly_timeline)` block, reusing the already-computed `isNightSlot` function and `T.days` translation table.

**Data preparation** — group `weekly_timeline` items by calendar date, sort by date, then produce two parallel arrays `sparkDay` and `sparkNight` (nulls for days where a slot is missing):

```js
const dateMap = new Map();
data.weekly_timeline.forEach(item => {
  const dt = new Date(item.start_time.replace('+08:00', ''));
  const key = `${dt.getFullYear()}-${dt.getMonth()}-${dt.getDate()}`;
  if (!dateMap.has(key)) dateMap.set(key, { dt, day: null, night: null });
  if (isNightSlot(item)) dateMap.get(key).night = item;
  else dateMap.get(key).day = item;
});
```

**Axis snapping** — bounds are snapped to the nearest 5° below/above the data, then the range is expanded to at least 10° so there are always ≥ 3 gridlines:

```js
let axisMin = Math.floor(dataMin / 5) * 5;
let axisMax = Math.ceil(dataMax / 5) * 5;
if (axisMax === axisMin) axisMax = axisMin + 10;
if (axisMax - axisMin < 10) axisMin = axisMax - 10;
```

**Dot alignment** — the built-in Chart.js y-axis is disabled (`display: false`). Instead, `layout.padding.left` and `layout.padding.right` are both set to `halfCard = (gridWidth − 24) / 14`. This is provably correct: for a 7-point line chart with no x-offset, Chart.js places dot `i` at `chartArea.left + plotWidth × i/6`. With `chartArea.left = halfCard` and `plotWidth = 6 × (cardWidth + gap)`, dot `i` lands exactly over card `i`'s centre column at any container width.

```js
const gridWidth = weeklyTimelineEl.offsetWidth || sparkCanvas.parentElement.offsetWidth || 700;
const halfCard  = Math.max(16, Math.round((gridWidth - 24) / 14));
// layout: { padding: { left: halfCard, right: halfCard } }
```

**Inline plugin** (`sparklineExtras`) handles three concerns in separate Chart.js hooks:

| Hook | What it draws |
|------|---------------|
| `beforeDraw` | Fills the plot area with `--surface` (theme-aware, read at render time via `getComputedStyle`) |
| `beforeDatasetsDraw` | Horizontal gridlines at each 5° tick, drawn behind the data lines |
| `afterDraw` | Temperature labels (`25°`, `20°` …) in `--muted` / Fira Code 10px, placed 8px outside both the left and right chart edges |

Theme colours are captured once at render time (`getComputedStyle(document.documentElement)`) so they reflect whichever theme is active when data loads. The chart is destroyed and recreated on each data refresh via the existing `tempChart` state variable.

### `web/static/style.css` — commits `093f81d`, `556dac4`

`.weekly-grid` `margin-bottom` moved from the grid to the new wrapper so the sparkline sits flush below the cards:

```css
.weekly-grid           { margin-bottom: 0; }

.weekly-sparkline-wrap {
  position: relative;
  height: 120px;          /* 96px on mobile */
  margin-top: 4px;
  margin-bottom: 1.5rem;
  background: var(--blue-lt);
  border-radius: 10px;
}
```

Mobile override inside the existing `@media (max-width: 767px)` block:

```css
.weekly-sparkline-wrap { height: 96px; }
```

---

## What Stayed the Same

- **Backend** — no changes. Day/night AT split is derived entirely from `start_time` in the frontend.
- **Weekly card rendering** — the existing loop is untouched; the sparkline block follows it.
- **Desktop/tablet card layout** — unaffected.
- **Chart.js CDN** — already present in `dashboard.html`; no version change.
