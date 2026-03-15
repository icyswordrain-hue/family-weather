# Player Sheet Desktop Layout Changes

**Date:** 2026-03-15
**Status:** Implemented

## Context

On desktop, the player sheet wasted horizontal space with single-column layouts for both narration and settings. Additionally, opening the sheet would land on whatever tab was last active (often settings), rather than the primary narration tab. The "updated" timestamp was buried in the settings tab, separate from the "Audio from" badge in the player bar.

## Changes

### 1. Default to narration tab on open

The toggle button handler now clicks the narration seal before calling `openSheet()`, ensuring the sheet always opens to the narration tab. The sidebar settings button was reordered to click the toggle first (which resets to narration), then override to the settings seal.

### 2. Narration — JS-based 3-column grid

Initial attempt used CSS `column-count: 3`, which failed because CSS columns in a fixed-height flex container clip content instead of scrolling vertically.

**Fix:** `_playerBarSetAudio()` now distributes paragraphs into 3 `<div class="ps-column">` containers inside a `<div class="ps-columns">` CSS grid on desktop (`min-width: 768px`). On mobile, the original sequential layout is preserved. The grid scrolls as a single unit inside `.ps-scroll-content`. Paragraphs are distributed round-robin (`i % 3`).

### 3. Settings — 2×2 card grid

CSS `display: grid; grid-template-columns: 1fr 1fr` on `#ps-panel-settings` for `min-width: 768px`. `align-content: start` prevents cards from stretching to fill the sheet height. The flat `border-bottom` dividers are replaced with bordered, rounded cards for visual separation.

### 4. Timestamps grouped in player bar

Added `player-last-updated` span to the player bar, adjacent to `player-audio-age`. Both timestamps ("updated: M/DD HH:MM" and "Audio from HH:MM") are now visible without opening the sheet. Hidden on mobile (≤767px) since `mobile-last-updated` in the compact header already shows this. The settings tab retains its own copy via `rp-last-updated`.

## Files Changed

| File | Change |
|------|--------|
| `web/static/app.js` | Toggle handler resets to narration seal on open; `initSheetSettings()` reordered; `_playerBarSetAudio()` distributes paragraphs into 3 grid columns on desktop; `render()` sets `player-last-updated` |
| `web/static/style.css` | `.ps-columns` / `.ps-column` grid; `align-content: start` on settings grid; `.player-last-updated` styling; hidden on mobile |
| `web/templates/dashboard.html` | Added `player-last-updated` span to player bar |

## CSS Split Note

When the CSS split refactor (`2026-03-15-css-split.md`) is executed, `.ps-columns`/`.ps-column` and the settings media query belong in `player.css`. The `.player-last-updated` rule belongs in `player.css` as well.
