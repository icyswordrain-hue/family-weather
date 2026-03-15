# Unified Settings via Player Sheet

## Goal
Remove the language toggle and refresh button from the desktop sidebar and route all settings through the player sheet's Settings tab — matching the mobile experience.

## Problem
Desktop had language toggle and refresh inline in the sidebar, while mobile routed them through the player sheet Settings tab. Two different interaction patterns for the same actions created inconsistency and redundant controls.

## Solution

### Consolidate controls into the player sheet
Moved the language toggle (`name="language"`) and refresh button (`#refresh-btn`) from the sidebar directly into the player sheet's Settings tab. The sheet radios are now the source of truth — no more `name="language-sheet"` delegation layer.

### Sidebar settings trigger
Added a gear icon nav item (`#sidebar-settings-btn`) at the bottom of the sidebar. Clicking it opens the player sheet switched to the Settings tab. Uses `margin-top: auto` to push it to the bottom of the flex column.

### Simplified JS delegation
Removed all the mirroring code in `initSheetSettings()` that synchronized `language-sheet` → `language` and `sheet-refresh-btn` → `refresh-btn`. Since both platforms now use the same elements, no delegation is needed.

## Files Changed
- `web/templates/dashboard.html` — removed `.sidebar-controls` and `.sidebar-status`, added settings nav item, consolidated controls into `#ps-panel-settings`
- `web/static/style.css` — removed sidebar control/status styles, added `.nav-settings-trigger` and `.ps-tab-panel .rp-last-updated` overrides
- `web/static/app.js` — simplified `initSheetSettings()`, added settings trigger click handler, removed `language-sheet` references
