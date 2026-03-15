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

## Bug Fix: Settings panel visible behind narration tab

### Problem

On desktop (≥768px), clicking the 活 (narration) seal showed both the narration content and the settings content simultaneously. The settings panel was always visible regardless of tab state.

### Root Cause

The desktop media query for the settings 2×2 grid originally used a bare selector:

```css
@media (min-width: 768px) {
  #ps-panel-settings {
    display: grid;  /* overrides browser [hidden] { display: none } */
  }
}
```

The `display: grid` declaration has higher specificity than the browser's user-agent `[hidden] { display: none }` rule, so the `hidden` attribute set by the tab-switching JS had no effect on desktop.

### Fix

Added `:not([hidden])` qualifier so the grid layout only applies when the panel is the active tab:

```css
@media (min-width: 768px) {
  #ps-panel-settings:not([hidden]) {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px 24px;
    align-content: start;
  }
}
```

### Tab switching mechanism

The player sheet uses `[hidden]` attribute toggling (not CSS classes) to show/hide tab panels. The seal click handler at `app.js:1123–1135` loops through all `.ps-tab-panel` elements, removing `hidden` from the target and setting `hidden` on all others. Any CSS rule that sets `display` on a panel **must** include `:not([hidden])` to avoid overriding the native hidden behavior.

## Reuse badge → timestamp + column count updates

### 1. Reuse badge shows `hh:mm` instead of "Claude_Reuse"

When narration is reused from a previous broadcast cycle, the source badge previously displayed `"Claude_Reuse"` or `"Gemini_Reuse"`. Now it shows the broadcast generation time as `hh:mm` (e.g., `14:30`).

**How it works:**

- `render()` in `app.js` injects `data.generated_at` into the narration `meta` object before passing it to `_playerBarSetAudio()`
- The badge renderer checks if `source` contains `"reuse"` — if so, it parses `meta.generated_at` into `hh:mm` for the badge text
- The CSS class strips the `_reuse` suffix (`source-claude` / `source-gemini`) so badge styling matches the original provider

### 2. Narration columns: 3 → 5

`_playerBarSetAudio()` now distributes paragraphs round-robin across 5 columns (`i % 5`) on desktop. CSS grid updated to `repeat(5, 1fr)`. With 5 narration paragraphs (p1–p5), each gets its own column.

### 3. Settings columns: 2 → 4

CSS grid updated to `repeat(4, 1fr)` inside the `@media (min-width: 768px)` block. All 4 settings cards (provider, language, narration mode, refresh) display in a single row.

### Files changed

| File | Change |
|------|--------|
| `web/static/app.js` | Pass `generated_at` into meta; 5-column distribution; badge shows `hh:mm` for reuse |
| `web/static/style.css` | `.ps-columns` grid → `repeat(5, 1fr)`; settings grid → `repeat(4, 1fr)` |

## Bug Fix: Force refresh blocked by midday skip

### Problem

Clicking "Force refresh" (強制 + 重新整理) during midday hours produced a blank narration tab. The pipeline returned `{"status": "skipped", "broadcast": ...}` with no `slices` key, so `data.slices.narration` was undefined and `_playerBarSetAudio` received an empty paragraphs array.

### Root Cause

Two independent skip checks exist in `_pipeline_steps()`:

1. **Line 383 — Pipeline-level midday skip** (`slot == "midday"`): Compares live CWA conditions against the morning broadcast. If unchanged, returns early from the **entire pipeline** — no data processing, no narration, no slices built.
2. **Line 537 — Narration-level skip** (`_skip_narration`): Only skips narration generation, still builds slices from reused paragraphs.

The `force` flag was checked at skip #2 (line 537) but **not** at skip #1 (line 383). So a force refresh during midday still hit the early return, producing a result without `slices`.

### Fix

Added `and not force` to the midday skip gate:

```python
# Before
if slot == "midday":

# After
if slot == "midday" and not force:
```

Now force refresh bypasses both skip checks and always runs the full pipeline.

### Frontend resilience for auto midday skip

Even in auto mode, the midday skip result `{"status": "skipped", "broadcast": ...}` was fed directly into `render()`, overwriting the existing `broadcastData` with a skeleton object that has no `slices`. This caused blank views until the next full refresh.

**Fix:** The frontend refresh handler (`app.js:triggerRefresh`) now checks `msg.payload?.status === 'skipped'` before calling `render()`. If skipped, it logs a message and keeps the current broadcast data intact.

## CSS Split Note

When the CSS split refactor (`2026-03-15-css-split.md`) is executed, `.ps-columns`/`.ps-column` and the settings media query belong in `player.css`. The `.player-last-updated` rule belongs in `player.css` as well.
