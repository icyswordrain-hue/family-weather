# Lifestyle Card UX Revamp — Whole-Card Click, Mobile Expand All, Airy Open Design

**Date:** 2026-03-14

## Problem

Three issues with the initial glanceable card implementation:

1. Only the small "Details ▾" button was tappable — the click target was too small, especially on mobile.
2. The "Expand All" button lived in `.view-header`, which is `display: none !important` on mobile (`≤767px`), making it invisible on phones.
3. The card design needed a visual refresh: more breathing room, a bolder title, and a proper interactive affordance.

## Changes

### `web/templates/dashboard.html`
Added a second Expand All button (`id="ls-expand-all-btn-mobile"`) inside `.section-header-card` — the mobile-only header row that contains the daily-canopy slab image. Both buttons share the same `class="ls-expand-all-btn"` and `data-i18n="ls_expand_all"`, so `applyLanguage()` keeps them translated automatically.

### `web/static/style.css`

**Whole-card clickable:**
- `.ls-card`: added `cursor: pointer`
- `.ls-card:hover`: soft shadow lift (`0 4px 16px rgba(0,0,0,0.13)`)

**Chevron indicator (replaces standalone button):**
- `.ls-title`: changed to `display: flex; justify-content: space-between; align-items: center` so the chevron sits at the far right of the title row
- `.ls-chevron::before { content: '▾'; }` / `.ls-card.expanded .ls-chevron::before { content: '▴'; }` — state handled entirely in CSS, no JS text manipulation needed

**Removed** `.ls-details-toggle` and `.ls-details-toggle:hover` (no longer rendered)

**Airy Open metrics:**
- Padding: `1.3rem` (was `1.1rem`)
- Title: `1.15rem`, `font-weight: 500` (was `1.1rem`, `400`)
- Insight bars: `0.82rem` (was `0.78rem`)
- zh-TW title bump: `1.3rem` (was `1.25rem`)

**Mobile rule** (inside `@media (max-width: 767px)`):
- `.section-header-card .ls-expand-all-btn`: `position: relative; z-index: 1; margin-left: auto` — floats the button to the right of the slab row, above the absolutely-positioned slab image

### `web/static/app.js`

**`add()` helper:**
- Title `<div class="ls-title">` now contains two children: a `<span>` for text and `<span class="ls-chevron">` for the arrow indicator
- Removed toggle `<button>` entirely
- Click handler moved to the whole card: `card.addEventListener('click', () => { card.classList.toggle('expanded'); updateExpandAllBtn(); })`

**`updateExpandAllBtn()`:**
- Now updates both `ls-expand-all-btn` (desktop) and `ls-expand-all-btn-mobile` in a single loop

**`renderLifestyleView()` wiring:**
- Expand-all `onclick` wired for both button IDs
- `e.stopPropagation()` included (buttons are outside cards, so not strictly needed, but guards against future nesting)

## Architecture Notes

- **CSS-driven chevron state**: `.ls-card.expanded .ls-chevron::before` switches content without any JS. This means the chevron is always correct even if `.expanded` is toggled externally (e.g., by the expand-all handler).
- **Two synced buttons**: `updateExpandAllBtn()` is the single source of truth for button label state. Both buttons' `onclick` re-query live card state rather than tracking a boolean.
- **Alert cards unaffected**: built via a separate code path (`ls-alert-card`), no chevron, no click-to-expand.
- **Language toggle**: `applyLanguage()` → `render()` → `renderLifestyleView()` recreates all cards fresh; expand state resets to collapsed (consistent with default).
