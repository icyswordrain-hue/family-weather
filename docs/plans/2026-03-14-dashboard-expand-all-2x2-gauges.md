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
