# Narration Sheet — Seamless Desktop & Mobile Polish

**Date:** 2026-02-28
**Status:** Implemented

## Problem

The narration (player) sheet had several rough edges that broke the seamless feel on both desktop and mobile:

1. **Paragraph structure discarded** — `_playerBarSetAudio` joined all 6 paragraphs into a flat string set via `textContent`. Section titles ("Current & Outlook", "Garden & Commute", etc.) and the LLM source badge (Gemini / Claude / Template) were never shown.
2. **Backdrop bled into sidebars** — `position: fixed; inset: 0` dimmed the entire screen including the 240 px sidebar and 180 px right panel, even though the sheet itself is constrained to the centre column.
3. **No drag-handle affordance on mobile** — the sheet appeared with no visual cue that it was a bottom sheet.
4. **Sheet height fixed at `60vh`** — too short on small phones; left dead space when narration was brief.
5. **No scroll-fade indicator** — no visual cue that content continued below the visible area.

## Changes

### 1 · Structured paragraph rendering
**Files:** `web/static/app.js`, `web/static/style.css`

- `render()` now passes the raw `paragraphs` array + `meta` object to `_playerBarSetAudio` instead of a pre-joined string.
- `_playerBarSetAudio` builds HTML: each paragraph gets a small-caps section label (`ps-para-title`) and a body (`ps-para-body`). A source badge (`narration-badge source-gemini/claude/template`) is appended after the last paragraph.
- Existing `.source-gemini`, `.source-claude`, `.source-template`, `.narration-badge` CSS classes are reused.
- New CSS: `.ps-para`, `.ps-para-title`, `.ps-para-body`, `.ps-meta` (dark-mode variants included).

### 2 · Desktop backdrop constraint
**File:** `web/static/style.css`

- Changed `.player-sheet-backdrop` from `inset: 0` to `left: var(--sidebar-w, 240px); right: var(--rp-w, 180px)` so the dim overlay matches the sheet's footprint exactly.
- `@media (max-width: 767px)` override restores `left: 0; right: 0` for full-width mobile backdrop.

### 3 · Mobile drag-handle pill + taller sheet
**Files:** `web/templates/dashboard.html`, `web/static/style.css`

- Added `<div class="player-sheet-handle" aria-hidden="true">` as the first child of `.player-sheet`.
- Desktop: `display: none` (handle invisible).
- Mobile (`≤767px`): 36 × 4 px rounded pill using `var(--border)` colour; sheet height increased from `60vh` → `78vh`.

### 4 · Scroll-fade indicator
**File:** `web/static/style.css`

- `.player-sheet` changed from `overflow-y: auto` to `overflow: hidden; display: flex; flex-direction: column`.
- `.player-sheet-body` gains `overflow-y: auto; height: calc(100% - 45px)` so it scrolls independently.
- `::after` pseudo-element: `position: absolute; bottom: 0; height: 40px` gradient from transparent to `var(--surface)` (dark-mode variant to `#1a2235`). `pointer-events: none` prevents click-through interference.

## Files modified

| File | Change |
|---|---|
| `web/static/app.js` | `render()` call site (~line 386); `_playerBarSetAudio` setter (~line 1015) |
| `web/static/style.css` | Backdrop constraint; `.ps-para*` CSS; handle pill in `@media (max-width: 767px)`; scroll fade `::after` |
| `web/templates/dashboard.html` | `.player-sheet-handle` div added before `.player-sheet-header` |
