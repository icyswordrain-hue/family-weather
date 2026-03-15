# CSS Dead Code Removal & Selector Consolidation

**Date:** 2026-03-15
**File:** `web/static/style.css`
**Result:** 3633 → 3431 lines (−202 lines, −5.6%)

## What was removed

### Dead selectors (no matching HTML/JS class names)

- **Legacy dark-mode card classes** — `.card`, `.metric-card`, `.lifestyle-card`,
  `.narration-card`, `.timeline-slot`, `.heads-up-card`, `.metric-value`,
  `.metric-label`, `.card-title`, `.view-title`, `.lifestyle-title`, `.metric-sub`,
  `.lifestyle-text`, `.muted-text` — remnants of a prior design iteration.
  Removed from both the theme-transition selector list and all `html.dark` overrides.

- **`.narration-text`**, **`.narration-para`**, **`.chart-container canvas`** dark-mode
  rules — class names no longer exist in templates or JS.

- **`.rp-btn`** (both definitions) — class not used anywhere in HTML or JS.
  The refresh button uses `.ps-btn` instead. Removed both the original pill-style
  block and the later flat-style redefinition, along with `.rp-btn-secondary`,
  `.rp-btn:hover/:active/:disabled`, `.rp-btn.loading`, `.rp-btn.spinning`.
  Kept `@keyframes spin` (used by `.ps-btn.spinning`).

- **`.rp-btn.loading .refresh-icon`** early rule — orphaned since `.rp-btn` is dead.

- **`.player-progress-wrap`** first definition and its `html.dark` override —
  immediately overwritten by a second `display: none` rule, making the styled
  version dead code.

### Consolidated selectors

- **`prefers-reduced-motion` hover blocks** — three identical `translateY(-3px)`
  hover-lift rules for `.gauge-outdoor-trigger`, `.gauge-card`, `.time-card`
  merged into one `@media` block with a comma-joined selector list.

- **`.wk-row-day`/`.wk-row-night` brand-icon sizing** — identical `width`/`height`
  rules merged in both base (54px) and mobile (42px) contexts.

- **`.log-status-warn`/`.log-status-stale`** — byte-for-byte identical rules
  merged with comma-joined selector.

- **`.gauge-header .gauge-icon .brand-icon`** — redundant more-specific duplicate
  of existing `.gauge-icon .brand-icon` rule (both set `width: 28px; height: 28px`).

- **Duplicate `/* ── Right Panel Log ── */` comment** — one copy removed.

## What was NOT changed

- All live class names, responsive breakpoints, and dark-mode variables untouched
- Shell layout blocks (`.app-shell`, `.sidebar`, `.main-panel`, `.right-panel`) —
  appear duplicated but are additive (grid vs flex contexts), left as-is
- `html.dark audio`, `html.dark .loading-screen`, `html.dark .error-screen` — kept
  (elements confirmed in use)
- `@keyframes spin` — kept (used by `.ps-btn.spinning`)

## Verification

- All 245 tests pass
- Pure deletions and mechanical selector merges — zero behavioral change
