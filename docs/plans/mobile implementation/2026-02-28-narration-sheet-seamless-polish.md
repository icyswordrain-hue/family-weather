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

---

## Follow-up — 2026-02-28: Dark/Light Mode Contrast Fixes

**Commits:** `fix(narration): handle pill and source badge dark/light contrast`

Post-implementation audit found two visual gaps:

### 1 · Handle pill invisible in both modes

`.player-sheet-handle` used `background: var(--border)`:
- Light mode: `#e8ecf3` on `#ffffff` → 1.5:1 contrast (invisible)
- Dark mode: `#2a3a5e` on `#1a2235` → similarly invisible

Fixed inside `@media (max-width: 767px)`:

```css
.player-sheet-handle { background: rgba(0, 0, 0, 0.15); }       /* light */
html.dark .player-sheet-handle { background: rgba(255, 255, 255, 0.2); } /* dark */
```

Both values are intentionally subtle but contrast rises to ≥3:1 in each mode.

### 2 · Source badges missing dark-mode overrides

`.source-gemini`, `.source-template`, `.source-claude` had light pastel backgrounds (`#eef2ff`, `#f3f4f6`, `#fff0f0`) with no `html.dark` variants — they appeared as bright blotches in dark mode.

Added near the existing `.source-*` rules:

```css
html.dark .source-gemini  { background: rgba(77, 124, 254, 0.18); color: #7da4ff; }
html.dark .source-template { background: rgba(107, 114, 128, 0.18); color: #cbd5e1; }
html.dark .source-claude  { background: rgba(192, 57, 43, 0.18);  color: #ff7675; }
```

Muted translucent backgrounds with lightened text — consistent with the dark surface palette.
