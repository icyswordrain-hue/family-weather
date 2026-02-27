# Phase 1 Task List — Desktop Structural Cleanup

> Cross off each item as you complete it. Full step-by-step instructions are in:
> `docs/plans/2026-02-27-phase1-execution-plan.md`

---

## Task 1 — Remove narration view + nav button
- [x] Delete narration `<button class="nav-item">` from sidebar
- [x] Delete `<div id="view-narration">` and all children
- [x] Delete `<div id="narration-meta">` if present
- [x] Remove standalone `<audio id="narration-audio">` if outside player bar
- [x] Verify no JS errors on page load
- [x] Commit: `feat(phase1): remove narration view and nav button`

## Task 2 — Shrink right panel; strip controls
- [x] Change `--rp-w` from `280px` → `180px` in `style.css`
- [x] Delete `.rp-top` wrapper (`.rp-controls-section`, `#rp-last-updated`, `#refresh-btn`) from `.right-panel`
- [x] Delete language radio group from `.rp-controls-section`
- [x] Delete provider radio group from `.rp-controls-section`
- [x] Verify right panel is narrower and shows only system log
- [x] Commit: `feat(phase1): shrink right panel to 180px, strip rp-controls-section`

### Task 2b — Move last-updated + refresh button to sidebar *(amendment 2026-02-27)*
- [x] Add `<div class="sidebar-status" id="sidebar-status">` with `#rp-last-updated` and `#refresh-btn` inside `<aside class="sidebar">` (after `.sidebar-controls`)
- [x] Add `.sidebar-status` CSS rule (`padding: 10px 12px 14px; flex-direction: column; gap: 8px; border-top`)
- [x] Verify last-updated text + refresh button appear at sidebar bottom; clicking refresh triggers data fetch
- [x] Verify language switch updates refresh button label (`data-i18n="refresh_btn"`)
- [x] Commit: `feat(phase1): move last-updated and refresh btn to sidebar`

## Task 3 — Add player bar + player sheet HTML
- [x] Add `<div class="player-bar" id="player-bar">` with play btn, label, progress, duration, toggle, `<audio>`
- [x] Add `<div class="player-sheet" id="player-sheet">` with header, close btn, body
- [x] Add `<div class="player-sheet-backdrop" id="player-sheet-backdrop">`
- [x] Verify page loads without HTML errors
- [x] Commit: `feat(phase1): add player bar and player sheet HTML`

## Task 4 — Style player bar + player sheet
- [x] Add `.player-bar` CSS (fixed bottom, flex, height 52px, desktop-column-constrained)
- [x] Add `.player-progress-wrap` / `.player-progress-bar` CSS
- [x] Add `@keyframes player-pulse` + `.player-bar.loading .player-cloud-icon` animation
- [x] Add `.player-sheet` CSS (fixed, 60vh, slide up transform, z-index 200)
- [x] Add `.player-sheet-backdrop` CSS
- [x] Add scroll clearance so last content isn't behind player bar (80px on `.main-panel` at style.css:1929)
- [x] Add `@media (prefers-reduced-motion: reduce)` overrides for pulse + sheet transition
- [x] Verify player bar visible, sheet hidden, loading pulse works in DevTools
- [x] Commit: `feat(phase1): style player bar, player sheet, and pulse animation`

## Task 5 — Add sidebar controls HTML
- [x] Add `<div class="sidebar-controls">` after nav items in `.sidebar`
- [x] Add language radio group (`name="language"`, values `en` / `zh-TW`)
- [x] Add provider radio group (`name="provider"`, verify values match `app.js`)
- [x] Verify toggles appear at sidebar bottom
- [x] Commit: `feat(phase1): add lang + provider toggles to sidebar`

## Task 6 — Style sidebar controls
- [x] Confirm `.sidebar` is `display: flex; flex-direction: column` (add if missing)
- [x] Add `.sidebar-controls { margin-top: auto; ... }` CSS
- [x] Add `.sidebar-control-group`, `.sidebar-control-label`, `.sidebar-toggle-row`, `.sidebar-radio-label` CSS
- [x] Verify controls are visually separated and pushed to sidebar bottom
- [x] Commit: `feat(phase1): style sidebar controls section`

## Task 7 — Remove theme toggle, add `initSystemTheme()`
- [x] Delete `<button id="theme-toggle">` from HTML
- [x] Delete inline `<script>` that reads `localStorage` for theme
- [x] Delete `theme-toggle` event listener from `app.js`
- [x] Delete `localStorage.setItem('theme', ...)` calls from `app.js`
- [x] Add `initSystemTheme()` function to `app.js`
- [x] Call `initSystemTheme()` from main init
- [x] Verify dark mode follows OS preference; verify `.dark` class toggled on `<html>`
- [x] Commit: `feat(phase1): replace manual theme toggle with prefers-color-scheme`

## Task 8 — Implement `initPlayerBar()`
- [x] Add `initPlayerBar()` function to `app.js`
- [x] Implement play/pause toggle with SVG point swap *(amendment: pause icon uses two rects, not polygon)*
- [x] Implement `timeupdate` progress bar update
- [x] Implement `loadedmetadata` duration display
- [x] Expose `window._playerBarSetAudio(url, title, text)` for `render()` to call
- [x] Replace `renderNarrationView()` call in `render()` with `_playerBarSetAudio` call
- [x] Call `initPlayerBar()` from main init
- [x] Verify audio plays and progress bar scrubs
- [x] Commit: `feat(phase1): implement initPlayerBar() and wire audio to render()`

## Task 9 — Implement `initPlayerSheet()`
- [x] Add `initPlayerSheet()` function to `app.js`
- [x] Wire `⌄` toggle → open/close sheet with CSS class `.open`
- [x] Wire `✕` close button → close sheet
- [x] Wire backdrop click → close sheet
- [x] Lock/restore `document.body.style.overflow` on open/close
- [x] Call `initPlayerSheet()` from main init
- [x] Verify sheet slides up, body scroll locks, both close triggers work
- [x] Commit: `feat(phase1): implement initPlayerSheet() with scroll lock`

## Task 10 — `initSidebarControls()` + remove dead init calls
- [x] Confirm provider handler function name from existing `app.js` code
- [x] Extract provider handler to named function if not already
- [x] Add `initSidebarControls()` — wire lang inputs → `applyLanguage()`, provider inputs → `triggerRefresh`
- [x] *(amendment)* Language radio `value` is `zh-TW` (not `zh`) — matched to `applyLanguage()` check in `app.js`
- [x] *(amendment)* Add `initSidebarStatus()` — wire `#refresh-btn` in sidebar to trigger data refresh
- [x] Delete `initMobileDrawer()` definition and call
- [x] Delete `renderNarrationView()` definition (already unwired in Task 8)
- [x] Delete any other narration-view-specific functions
- [x] Call `initSidebarControls()` and `initSidebarStatus()` from main init
- [x] Verify lang + provider toggles work from sidebar; no console errors
- [x] Commit: `feat(phase1): implement initSidebarControls, remove dead init calls`

## Task 11 — Final integration smoke test
- [x] Page loads without JS console errors
- [x] Narration nav tab is gone
- [x] Right panel is ~180px wide
- [x] Lang + provider visible at sidebar bottom
- [x] Language switch works from sidebar (uses `applyLanguage()`, no page reload)
- [x] Player bar visible at bottom of main content area
- [x] Player sheet opens/closes with `⌄` and `✕`
- [x] Audio plays when narration data is available
- [x] Dark mode follows OS (no manual toggle present)
- [x] No `#view-narration` or `#theme-toggle` elements in DOM
- [x] `prefers-reduced-motion` verified (style.css:1932)
- [ ] Tag: `git tag phase1-complete && git push origin HEAD --tags`

---

## Task 12 — Live Data Freshness Indicator *(UX #2)*
- [ ] Add a `<span class="freshness-dot" id="freshness-dot">` next to `#rp-last-updated` in sidebar HTML
- [ ] Add CSS: `.freshness-dot` as a `6px` inline-block circle; three modifier classes `.fresh` (green), `.stale` (amber), `.old` (red)
- [ ] Add `updateFreshnessDot(fetchedAt)` to `app.js` — computes age in minutes, applies correct class
- [ ] Call `updateFreshnessDot()` from `render()` whenever new data arrives
- [ ] Verify: dot is green <30 min, amber 30–90 min, red >90 min
- [ ] Commit: `feat(ux): add freshness dot to last-updated timestamp`

## Task 13 — Semantic Color Consistency *(UX #3)*
- [x] Audit `style.css` — confirm `lvl-1` through `lvl-5` CSS vars/classes exist and are consistently defined
- [x] Audit all gauge card renders in `app.js` — ensure each applies the correct `lvl-N` class to its value element
- [x] Add a sidebar nav alert dot: `<span class="nav-alert-dot" id="nav-alert-dot">` on the Dashboard nav item
- [x] Add `updateNavAlertDot(maxLevel)` in `app.js` — sets `lvl-1…5` class on dot based on highest active alert level
- [x] Call `updateNavAlertDot()` from `render()`
- [x] Verify: gauge card colors consistent; nav dot reflects severity
- [x] Commit: `feat(ux): enforce semantic color scale on gauges and nav alert dot`

## Task 14 — Reduce Animation for Reduced Motion *(UX #7)*
- [x] Search `style.css` for all `animation` and `transition` declarations
- [x] Wrap each in `@media (prefers-reduced-motion: no-preference) { … }` (or move existing bare rules inside the guard)
- [x] Confirm `@media (prefers-reduced-motion: reduce)` overrides are removed (replaced by the no-preference guard pattern)
- [x] Verify in DevTools: with "Emulate prefers-reduced-motion: reduce" on, all animations freeze
- [x] Commit: `feat(ux): guard all animations with prefers-reduced-motion: no-preference`

## Task 15 — Typography Hierarchy Refinement *(UX #8)*
- [x] Define type-scale CSS vars: `--text-hero` (2rem bold), `--text-section` (1.2rem 600 uppercase + tracking), `--text-label` (0.78rem muted)
- [x] Apply `font-family: 'Fira Code', monospace` to all numeric gauge value elements
- [x] Apply `--text-section` sizing to all `h2` / section title elements
- [x] Apply `--text-label` to gauge label/unit text
- [x] Verify visual hierarchy: hero > section > label clearly distinct
- [x] Commit: `feat(ux): apply type-scale vars and Fira Code to gauge numerics`

## Task 16 — Optimistic Refresh UI *(UX #9)*
- [x] Add a `<span class="refreshing-badge" id="refreshing-badge">Refreshing…</span>` adjacent to `#rp-last-updated` in sidebar HTML (hidden by default)
- [x] Add CSS: `.refreshing-badge` — subtle pill, muted color, `display: none` / `display: inline-flex` toggle
- [x] In `app.js` refresh trigger: show badge immediately, do NOT clear existing rendered data
- [x] In `render()`: hide badge when new data replaces stale content
- [x] Remove full-screen loading-spinner show/hide during refresh (keep it only on cold start)
- [x] Verify: clicking Refresh shows badge, stale data stays visible, content swaps in-place on response
- [x] Commit: `feat(ux): optimistic refresh – keep stale data visible while fetching`

## Task 17 — Micro-interaction on Nav Switching *(UX #10)*
- [x] Add CSS: `.view-container` gets `transition: opacity 150ms, transform 150ms` inside a `@media (prefers-reduced-motion: no-preference)` guard
- [x] On hide: add `translateX(20px) + opacity 0`; on show: start from `translateX(-20px)`, animate to `translateX(0) opacity 1`; direction determined by tab order (left tab → slide right, right tab → slide left)
- [x] Update `switchView()` (or equivalent) in `app.js` to apply directional classes
- [x] Verify: Lifestyle ↔ Dashboard transitions feel spatial; no flicker; reduced-motion users see instant switch
- [x] Commit: `feat(ux): directional slide transition on view switching`
