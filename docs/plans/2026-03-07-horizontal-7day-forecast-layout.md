# Horizontal 7-Day Forecast Layout

**Date:** 2026-03-07
**Status:** Implemented

## Goal

Replace the 7-column × 2-row card grid (day row / night row) with 7 stacked horizontal rows — one per day — where each row shows:

```
[☀️ MON]  22° ━━━▓▓▓▓━━━━  28°  [🌙]
[⛅ TUE]  20° ━▓▓▓▓━━━━━━  26°  [🌧]
```

- **Left end:** daytime weather icon + abbreviated day name
- **Center:** min temp | proportional gradient range bar | max temp
- **Right end:** nighttime weather icon (smaller, 70% opacity)

## Motivation

The previous 7×2 grid required two visual scans to compare day and night for the same date. The horizontal layout pairs day/night per row, making daily ranges immediately legible. The range bar is now full-width of the center section, giving better resolution for temperature spread.

## Files Changed

| File | Change |
|------|--------|
| `web/static/app.js` | Replaced flat `[...topItems, ...bottomItems].forEach` loop (lines 714–799) with a `for (i < 7)` paired loop; combined day + night `MinAT`/`MaxAT` for true daily range |
| `web/static/style.css` | Replaced `.weekly-grid` grid + all `.wk-card*` rules with `.wk-row*` flex layout; removed dead `.weekly-sparkline-wrap` block |
| `web/templates/dashboard.html` | Hidden `#ov-weekly-header` (day names moved into each row's `.wk-row-label`) |

## Architecture Notes

- **`globalMin`/`globalMax`** computation (app.js ~705–712) is unchanged — still iterates all 14 items with `MinAT`/`MaxAT`.
- **Per-row temperature range** aggregates both `topItems[i]` and `bottomItems[i]`, giving a true daily span rather than per-slot span.
- **`#ov-weekly-timeline.weekly-grid`** CSS selector used instead of plain `.weekly-grid` to override the `timeline-scroll` container's `overflow-x: auto` without touching the 24h timeline above.
- **`.wk-range-container`/`.wk-range-bar`** (style.css lines 913–931) kept unchanged and reused via `.wk-row-temps .wk-range-container { flex: 1; margin: 0 }`.

## CSS New Classes

| Class | Purpose |
|-------|---------|
| `.wk-row` | One horizontal row per day; flex, `var(--surface)` bg, `border-radius: 10px` |
| `.wk-row-day` | Left column — day icon + label, `flex: 0 0 52px` |
| `.wk-row-night` | Right column — night icon, `flex: 0 0 44px`, 70% opacity |
| `.wk-row-label` | Day abbreviation (MON/TUE…) below day icon |
| `.wk-row-center` | Flex-grow center; contains `.wk-row-temps` |
| `.wk-row-temps` | Flex row: min-temp | range-container | max-temp |
| `.wk-min-temp` / `.wk-max-temp` | Fira Code monospace, 0.90rem, fixed min-width `2.8ch` |

## Removed Classes

`.weekly-grid` (grid), `.wk-header-row`, `.wk-col-header`, `.wk-day-name`, `.wk-cond`, `.wk-card`, `.wk-card.wk-day`, `.wk-card.wk-night`, `.wk-placeholder`, `.wk-label`, `.wk-temp`, `.wk-rain`, `.wk-period`, `.weekly-sparkline-wrap`
