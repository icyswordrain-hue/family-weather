# Glanceable Lifestyle Cards with Expand/Collapse

**Date:** 2026-03-14

## Problem

Lifestyle cards showed the LLM-generated paragraph as the dominant content, requiring reading several sentences per card before getting to the key insight. For a family weather dashboard, users typically want to scan quickly — "do I need an umbrella? what's the commute like?" — not read paragraphs.

## Solution

Collapse the LLM text by default. Each card shows only:
- Icon + title
- Insight-bar data (temperature, grade, mode, hazards, etc.)
- A "Details ▾" toggle button

A global "Expand All" button in the view header expands or collapses all cards at once.

## Changes

### `web/templates/dashboard.html`
Added `<button id="ls-expand-all-btn">` to the lifestyle view header with `data-i18n="ls_expand_all"`. The existing `display: flex` on `.view-header` places it naturally at the right edge.

### `web/static/style.css`
- `.ls-card:not(.expanded) .ls-text { display: none; }` — hides LLM text when card is collapsed
- `.ls-details-toggle` — per-card toggle button (inline-flex, muted colour, no border)
- `.ls-expand-all-btn` — pill button in the header (border, rounded, muted)
- `html[lang="zh-TW"]` font bumps for both new buttons (0.9rem)

### `web/static/app.js`
- `updateExpandAllBtn()` — reads all `.ls-card` expanded states, sets button text to "Expand All" or "Collapse All"
- `add()` helper — appends a `.ls-details-toggle` button after `extraNodes`; click toggles `.expanded` on the card and calls `updateExpandAllBtn()`
- `renderLifestyleView()` — wires `expandAllBtn.onclick` after each render (re-wire needed because `grid.innerHTML = ''` destroys card refs); calls `updateExpandAllBtn()` at the end for initial state
- i18n keys added to both `'en'` and `'zh-TW'` translation objects: `ls_details_show`, `ls_details_hide`, `ls_expand_all`, `ls_collapse_all`

## Architecture Notes

- **Alert cards are unaffected** — built via a separate code path using `ls-alert-card`, not through `add()`. Critical health/commute alerts always show in full.
- **Language toggle compatibility** — `applyLanguage()` calls `render(broadcastData)` which re-creates all cards via `renderLifestyleView()`. Cards are recreated fresh with correct `T.*` strings, so no separate i18n handling is needed for the dynamic toggle buttons.
- **No backend changes** — pure frontend. All data fields remain the same.

## Result

Cards are now glanceable at a glance. Users see the key data points (feels-like temp, commute hazards, outdoor grade, HVAC mode) instantly. The LLM narrative is one tap away when they want more context.
