# Dashboard Expand All + 2×2 Gauge Grid

**Date:** 2026-03-14

## Problem

The dashboard view's gauge panel (humidity, AQI, UV, pressure) was only expandable via a small chevron on the outdoor activity card — easy to miss. On mobile, the 4 gauge cards in a single row caused text truncation ("PRESSURE" → "PRE").

## Changes

### `web/templates/dashboard.html`

- Added `db-expand-all-btn` to desktop `.view-header` (matches lifestyle pattern)
- Added `db-expand-all-btn-mobile` to mobile `.section-header-card`

### `web/static/app.js`

- Renamed `toggle` → `toggleGauges`, added `updateDbExpandBtn()` call
- Wired `db-expand-all-btn` and `db-expand-all-btn-mobile` click handlers
- Added `updateDbExpandBtn()` function to sync button text (Expand All ↔ Collapse All)

### `web/static/style.css`

- Removed `.gauge-outdoor-trigger::after` chevron pseudo-element
- Mobile: changed `.gauges-grid` from `repeat(4, 1fr)` → `repeat(2, 1fr)` (2×2 layout)
- Mobile: increased `max-height` from `175px` → `350px` to fit two rows

### Wind text overflow fix (follow-up)

The wind gauge card in `.current-side-stack` displays descriptive text like
"Moderate breeze" as the main value. On mobile the side-stack cards are narrow,
and the default `Fira Code` monospace font made these strings ~20% wider than
a proportional font — causing overflow or awkward line breaks.

- `.current-side-stack .gauge-value`: switched `font-family` to `inherit`
  (proportional), added `word-break: break-word` + `overflow-wrap: break-word`
- `.current-side-stack .gauge-sub`: reduced from `0.9rem` → `0.85rem`, same
  word-break safety nets

### Restore gauge icons on mobile (follow-up)

The 4×1 layout had hidden `.gauges-grid .gauge-header .gauge-icon` with
`display: none` to save horizontal space. With the 2×2 grid each card has
ample room, so the rule was removed to restore the brand icons.

### Match side-stack cards to gauge-grid sizing (follow-up)

The 3 side-stack cards (wind, ground, outdoor) had smaller padding, height,
and fonts than the 4 expanded gauge cards, making the dashboard look
inconsistent. Aligned all mobile overrides:

- `.gauge-card` padding `0.5rem 0.4rem` → `0.63rem 0.44rem`, min-height `56px` → `88px`
- `.gauge-label` font-size `0.9rem` → `0.88rem`
- `.gauge-value` font-size `1.35rem` → `1.28rem`
- Removed `flex-start` header override and custom icon size (now inherits centered default + base 28px)
