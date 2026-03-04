# Layout Refactor: 2-Column Unified View + Floating Log Drawer

**Date:** 2026-03-04
**Branch:** `master`
**Files modified:** `web/templates/dashboard.html`, `web/static/style.css`, `web/static/app.js`

---

## Problem

The dashboard had three structural pain points:

1. **Mutually exclusive views.** Lifestyle recommendations and weather metrics required a tab switch (`switchView()`), forcing the user to choose one or the other. The two views had no persistent relationship.

2. **180px wasted on a debug tool.** The right panel (`<aside class="right-panel">`) was permanently allocated for the system log — a developer/debug concern — at the cost of main content width on every session.

3. **Missing brand icon CSS.** Nineteen hand-crafted PNG brand icons existed in `/web/static/brand-icons/` with no `.brand-icon` CSS class defined, despite being referenced in HTML and JS.

---

## Design Decision

**Branding philosophy context:** The dashboard targets a "slow media / curated humanism" aesthetic — lifestyle content is the primary editorial surface, weather data is ambient context. This hierarchy informed the column ratio.

### Layout: Option B — Lifestyle 3fr + Weather Rail 2fr

```
┌─ sidebar 240px ─┬──────── lifestyle 3fr ─────────┬─── wx-rail ~280px ───┐
│  clock          │  生活建議 ──────────────────    │  ☀ 24°C              │
│  nav            │  ┌──────┐ ┌──────┐             │  feels 22°           │
│                 │  │ card │ │ card │             │  ──────────          │
│                 │  └──────┘ └──────┘             │  💧 AQI  UV  Press   │
│                 │  ┌──────┐ ┌──────┐             │  ──────────          │
│                 │  │ card │ │ card │             │  next 24h            │
│                 │  └──────┘ └──────┘             │  [▾ 七日預報]        │
├─────────────────┴─────────────────────────────────┴──────────────────────┤
│  ▶ [player bar — full width]                                    [● LOG]  │
└────────────────────────────────────────────────────────────────────────────┘
```

Rejected **Option A** (symmetric 50/50) because the 7-day weekly grid (`repeat(7, 1fr)`) would be severely cramped at half the main panel width.

### Log: Option 2 — Floating Pill Drawer

The `<aside class="right-panel">` is removed entirely. A small `[● LOG]` pill button sits fixed above the player bar. Clicking opens a 320px slide-up drawer using the same `transform: translateY` pattern already used by the player sheet. Error count badges appear on the pill when `window.onerror` fires.

Rejected **Option 1** (sidebar accordion) because the sidebar is already space-constrained with the analog clock, nav, language controls, and refresh button.

---

## Implementation

### `web/templates/dashboard.html`

| Change | Detail |
|--------|--------|
| Removed | `<aside class="right-panel">` and all log container markup |
| Replaced | Two `<div id="view-*" class="view-container">` divs with `.main-two-col` → `#col-lifestyle` + `#wx-rail` |
| Added | `#wx-rail` structure: hero temp row, `#wx-gauges-grid` (4 metrics), `#ov-timeline`, `<details class="wx-rail-weekly">` |
| Added | `#log-pill` floating button (fixed, bottom-right) |
| Added | `#log-drawer` slide-up panel containing `#rp-log-list` (reused existing ID) |
| Changed | Nav `<button data-view>` → `<div>` (non-interactive static labels) |
| Bumped | CSS `?v=19→20`, JS `?v=18→19` |

**Weekly forecast** is wrapped in `<details class="wx-rail-weekly">` — collapsed by default to keep the rail compact, expandable on demand.

### `web/static/style.css`

| Change | Detail |
|--------|--------|
| Removed | `--rp-w: 180px` variable |
| Updated | `.app-shell` grid: `var(--sidebar-w) 1fr` (was `… var(--rp-w)`) |
| Replaced | `.view-container` tab styles with `.main-two-col { grid-template-columns: 3fr 2fr; height: 100% }` |
| Added | `#col-lifestyle` — `padding: 40px 32px 100px 48px; overflow-y: auto; border-right` |
| Added | `#wx-rail` — `padding: 28px 20px 100px; overflow-y: auto; background: var(--surface)` |
| Added | `#wx-rail` condensed overrides: `#wx-gauges-grid { repeat(2,1fr) }`, `.timeline-grid { repeat(2,1fr) }` |
| Added | `.wx-rail-hero`, `.wx-rail-gauges-top`, `.wx-rail-weekly`, `.wx-rail-weekly-toggle` |
| Added | `.log-pill`, `.log-badge`, `.log-drawer`, `.log-drawer-header`, `.log-drawer-actions`, `.log-drawer-close` |
| Added | `.brand-icon { 40px × 40px; object-fit: contain; border-radius: 10px }` |
| Added | `.nav-icon .brand-icon { 24px × 24px }` |
| Added | `--plum: #9B5D77` (dusty rose — missing from brand spec) |
| Added | `.loading-screen`, `.error-screen`, `.spinner`, `.retry-btn` base styles (were completely missing) |
| Updated | Player bar `right: var(--rp-w, 180px)` → `right: 0` (×3: bar, sheet, backdrop) |
| Updated | Mobile `≤767px`: `main-two-col → 1fr`, log pill/drawer bottom offsets for 40px bar |
| Updated | Tablet `≤1024px`: `main-two-col → 1fr 1fr` |
| Updated | `#col-lifestyle .section-header-card` always visible on desktop (was mobile-only) |
| Added | `#col-lifestyle, #wx-rail { padding-bottom: 100px }` (replaces old `.main-panel` scroll clearance) |

### `web/static/app.js`

| Change | Detail |
|--------|--------|
| Removed | `switchView()` function |
| Replaced | `initSidebarNav()` with no-op (nav items are decorative `<div>`, not `<button data-view>`) |
| Simplified | `initMobileNav()` — DOM reordering removed (CSS stacking handles mobile order) |
| Added | `initLogPill()` — toggles `#log-drawer.open`, wires close button, manages `aria-hidden` / `aria-expanded` |
| Added | `let _logErrorCount = 0` at top-level (before `window.onerror`) |
| Added | `_incrementLogBadge()` — increments counter, adds `.visible` class to `#log-badge` |
| Updated | `window.onerror` — calls `_incrementLogBadge()` after appending error entry |
| Wired | `initLogPill()` called in `DOMContentLoaded` sequence |

---

## Color Palette Alignment

The earthy color system maps cleanly to the design spec:

| Design Spec | Hex | CSS Variable | Status |
|---|---|---|---|
| Paper cream | `#F3F7F8` | `--main-bg: #F3F0E8` | ✓ warm variant |
| Terracotta | `#E26C3B` | `--coral / --warn` | ✓ exact |
| Deep sage | `#5B8C85` | `--blue / --teal` | ✓ exact |
| Mustard | `#D99B3F` | `--lvl-3`, `--tint-caution` | ✓ exact |
| Dusty rose/plum | `#9B5D77` | `--plum` ← **added** | ✓ now present |
| Royal/navy blue | `#615EBB`, `#2B5291` | — | skipped — sage reads as primary brand color |

---

## Brand Icons

19 hand-crafted PNGs live in `/web/static/brand-icons/`. The `IMG(name, alt)` JS helper (top of `app.js`) generates `<img class="brand-icon">` tags. The `.brand-icon` CSS class was previously missing; now defined:

```css
.brand-icon {
  width: 40px;
  height: 40px;
  object-fit: contain;
  border-radius: 10px;
  flex-shrink: 0;
  display: block;
}
```

Category map used in lifestyle card icons: `wardrobe`, `commute`, `outdoor`, `meals`, `hvac`, `health`, `rain-gear`, `garden`, `air-quality`. Alert icons: `alert`, `heads-up`, `all-clear`, `general`.

---

## Verification

```bash
# Start local server
RUN_MODE=LOCAL flask run

# Tests to perform
# 1. Desktop (≥1280px) — 3fr/2fr columns render with live data
# 2. Lifestyle cards populate in left column; gauges/timeline in right rail
# 3. Click [▾ 七日預報] in wx-rail — weekly section expands
# 4. Click [● LOG] pill — drawer slides up from bottom-right
# 5. Click ✕ in drawer — drawer slides back down
# 6. Trigger a JS error in console — badge appears on pill
# 7. Tablet (≤1024px) — both columns at 1fr 1fr, sidebar slims to 80px
# 8. Mobile (≤767px) — wx-rail stacks below lifestyle, full-width
# 9. Player bar spans full width (no right gap)
# 10. Player sheet opens full width on click
```
