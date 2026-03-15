# Player Sheet Desktop Layout Changes

**Date:** 2026-03-15
**Status:** Implemented

## Context

On desktop, the player sheet wasted horizontal space with single-column layouts for both narration and settings. Additionally, opening the sheet would land on whatever tab was last active (often settings), rather than the primary narration tab.

## Changes

### 1. Default to narration tab on open

The toggle button handler now clicks the narration seal before calling `openSheet()`, ensuring the sheet always opens to the narration tab. The sidebar settings button was reordered to click the toggle first (which resets to narration), then override to the settings seal.

### 2. Narration — 3-column newspaper layout

CSS `column-count: 3` on `#ps-narration-content` for `min-width: 768px`. Each `.ps-prose` and `.ps-prose-divider` uses `break-inside: avoid` to keep paragraphs intact within columns. No JS changes required — the same sequential HTML flows into columns automatically. The ink thread continues to work (percentage-based height).

### 3. Settings — 2×2 card grid

CSS `display: grid; grid-template-columns: 1fr 1fr` on `#ps-panel-settings` for `min-width: 768px`. The flat `border-bottom` dividers are replaced with bordered, rounded cards (`border: 1px solid var(--border); border-radius: 8px`) for visual separation in the grid. The ID selector naturally overrides the `.ps-tab-panel:not([hidden])` flex rule.

## Files Changed

| File | Change |
|------|--------|
| `web/static/app.js` | Toggle handler resets to narration seal on open; `initSheetSettings()` reordered (toggle first, settings seal second) |
| `web/static/style.css` | New `@media (min-width: 768px)` block: 3-column narration, 2-column settings grid with card borders |

## CSS Split Note

When the CSS split refactor (`2026-03-15-css-split.md`) is executed, the new media query rules belong in `player.css`.
