# Mobile Responsive Overhaul — Implementation Plan

> **Date:** 2026-02-28
> **Status:** Ready for implementation
> **Spec:** `docs/plans/mobile implementation/2026-02-27-mobile-responsive-design.md`

---

## Context

The family weather dashboard is currently desktop-only (3-column grid). The desktop structural cleanup has been completed: player bar, sidebar controls, 2-view nav, `initPlayerBar()`, `initPlayerSheet()`, `initSidebarControls()`, and `initSystemTheme()` are all in place.

The mobile overhaul converts the app to a single-column continuous-scroll layout on screens ≤767px with: a compact header, FAB controls sheet, section header cards separating the two content sections, and full-width player bar. No bottom tab bar — scroll replaces navigation.

---

## Critical Files

- `web/templates/dashboard.html` — HTML additions
- `web/static/style.css` — responsive rules; also must replace old 768px blocks
- `web/static/app.js` — `initNav()`, `initMobileNav()`, `updateClock()`, `initFAB()`

---

## Pre-check: `--rp-w` CSS variable

`style.css` `:root` has `--rp-w: 300px` but the architecture decision sets the right panel to ~180px. The player bar uses `right: var(--rp-w, 180px)`. Before adding mobile CSS:

- If `--rp-w` is still 300px, update `:root { --rp-w: 180px; }` (1-line change)

---

## Task 1 — Remove old 768px mobile CSS blocks

**File:** `web/static/style.css`

Delete both existing `@media (max-width: 768px)` blocks (the bottom tab bar design and the `.dashboard-container` stacking rule). These will be fully replaced by the new `@media (max-width: 767px)` block in Task 3.

Also remove the `.drawer-toggle-btn` rule if it exists.

**Commit:** `refactor(mobile): remove old 768px bottom-nav mobile CSS`

---

## Task 2 — Add HTML: compact header, FAB, section header cards

**File:** `web/templates/dashboard.html`

**Step 1: Compact header** — Add as the first child of `.app-shell`, before `.sidebar`:

```html
<!-- Mobile Compact Header (hidden on desktop) -->
<header class="compact-header" id="mobile-header">
  <span id="mobile-clock">--:--</span>
  <span class="mobile-location" id="mobile-location">—</span>
</header>
```

**Step 2: FAB + sheet** — Add before `</body>`, after the player sheet elements:

```html
<!-- FAB (mobile controls) -->
<button class="fab-btn" id="fab-btn" aria-label="Settings">⚙️</button>
<div class="fab-sheet" id="fab-sheet" aria-hidden="true">
  <div class="fab-sheet-inner">
    <div class="sidebar-control-group">
      <span class="sidebar-control-label" data-i18n="lang_label">Language</span>
      <div class="seg-ctrl fab-seg" role="group">
        <label class="seg-option">
          <input type="radio" name="language-fab" value="en">
          <span>EN</span>
        </label>
        <label class="seg-option">
          <input type="radio" name="language-fab" value="zh-TW" checked>
          <span>中文</span>
        </label>
      </div>
    </div>
    <div class="sidebar-control-group">
      <span class="sidebar-control-label" data-i18n="provider_label">Provider</span>
      <div class="seg-ctrl fab-seg" role="group">
        <label class="seg-option">
          <input type="radio" name="provider-fab" value="CLAUDE" checked>
          <span>Claude</span>
        </label>
        <label class="seg-option">
          <input type="radio" name="provider-fab" value="GEMINI">
          <span>Gemini</span>
        </label>
      </div>
    </div>
    <button class="rp-btn" id="fab-refresh-btn" data-i18n="refresh_btn">重新整理</button>
  </div>
</div>
<div class="fab-backdrop" id="fab-backdrop"></div>
```

> **Note:** Use `name="language-fab"` and `name="provider-fab"` to avoid conflicting with sidebar radio groups. `initFAB()` syncs them via `dispatchEvent` on the sidebar radios.

**Step 3: Section header cards**

Inside `#view-lifestyle`, before `#lifestyle-grid`:

```html
<div class="section-header-card">
  <span>🚲</span>
  <span data-i18n="nav_lifestyle">生活建議</span>
</div>
```

Inside `#view-dashboard`, before `.current-conditions-wrapper`:

```html
<div class="section-header-card">
  <span>📊</span>
  <span data-i18n="nav_dashboard">天氣總覽</span>
</div>
```

**Commit:** `feat(mobile): add compact header, FAB sheet, section header cards to HTML`

---

## Task 3 — Add mobile CSS (`@media max-width: 767px`)

**File:** `web/static/style.css`

**Step 1: Base styles (outside media query — hidden by default)**

```css
/* ── Compact Header (mobile only) ─────────────── */
.compact-header {
  display: none;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: var(--sidebar-bg);
  color: var(--sidebar-text);
  font-size: 0.9rem;
  font-weight: 500;
  position: sticky;
  top: 0;
  z-index: 50;
}
#mobile-clock {
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.05em;
}

/* ── Section Header Card (mobile only) ────────── */
.section-header-card {
  display: none;
  align-items: center;
  gap: 8px;
  padding: 10px 0 6px;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text);
  border-bottom: 2px solid var(--border);
  margin-bottom: 16px;
}

/* ── FAB (mobile only) ────────────────────────── */
.fab-btn {
  display: none;
  position: fixed;
  bottom: 68px;
  right: 16px;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--blue);
  color: #fff;
  font-size: 1.2rem;
  border: none;
  box-shadow: var(--shadow-md);
  z-index: 160;
  cursor: pointer;
  align-items: center;
  justify-content: center;
}
.fab-sheet {
  position: fixed;
  bottom: 68px;
  right: 0;
  left: 0;
  background: var(--surface);
  border-top: 1px solid var(--border);
  border-radius: 16px 16px 0 0;
  padding: 20px 20px 32px;
  z-index: 170;
  transform: translateY(100%);
  transition: transform 280ms cubic-bezier(0.32, 0.72, 0, 1);
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.fab-sheet.open { transform: translateY(0); }

.fab-backdrop {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  z-index: 169;
}
.fab-backdrop.open { display: block; }

@media (prefers-reduced-motion: reduce) {
  .fab-sheet { transition: none; }
}
```

**Step 2: Mobile breakpoint block**

```css
@media (max-width: 767px) {
  /* Shell: single column */
  .app-shell {
    display: block;
  }

  /* Hide desktop-only elements */
  .sidebar,
  .right-panel {
    display: none !important;
  }

  /* Show mobile-only elements */
  .compact-header,
  .fab-btn,
  .section-header-card {
    display: flex;
  }

  /* All views visible — no tab gating on mobile */
  .view-container {
    display: block !important;
  }

  /* Main panel: full width, clear bottom for player bar */
  .main-panel {
    padding: 20px 16px;
    padding-bottom: 68px;
    height: auto;
    overflow-y: visible;
  }

  /* Player bar + sheet: full width */
  .player-bar {
    left: 0;
    right: 0;
  }
  .player-sheet {
    left: 0;
    right: 0;
  }

  /* Gauges: 2×2 grid */
  .gauges-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  /* Lifestyle: 1 column */
  .lifestyle-grid {
    grid-template-columns: 1fr;
  }
}
```

**Commit:** `feat(mobile): add compact-header, FAB, section-card CSS + 767px breakpoint`

---

## Task 4 — JS: `updateClock()` → also update `#mobile-clock`

**File:** `web/static/app.js`

Locate `updateClock()` (around line 879). After the `#rp-time` block, add:

```js
// Mobile digital clock
const mobileClockEl = document.getElementById('mobile-clock');
if (mobileClockEl) {
  try {
    mobileClockEl.textContent = now.toLocaleTimeString('en-US', {
      hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Taipei'
    });
  } catch (e) {
    mobileClockEl.textContent =
      `${tNow.getHours().toString().padStart(2, '0')}:${tNow.getMinutes().toString().padStart(2, '0')}`;
  }
}
```

Also find where `#rp-location` is set in `render()` and add a parallel assignment to `#mobile-location`:

```js
const mobileLoc = document.getElementById('mobile-location');
if (mobileLoc) mobileLoc.textContent = locationText; // same source as #rp-location
```

**Commit:** `feat(mobile): extend updateClock() to drive #mobile-clock`

---

## Task 5 — JS: `initNav()` dispatch + `initMobileNav()`

**File:** `web/static/app.js`

Replace the `initSidebarNav()` call in `init()` with `initNav()`:

```js
function initNav() {
  const isMobile = window.matchMedia('(max-width: 767px)').matches;
  if (isMobile) {
    initMobileNav();
  } else {
    initSidebarNav();
  }
}
```

Add `initMobileNav()` (minimal stub — all views are already visible via CSS):

```js
function initMobileNav() {
  // Mobile: all views visible via CSS (display: block).
  // No tab switching needed. Scroll is handled by the browser.
}
```

> Keep `initSidebarNav()` intact — it is still called on desktop.

**Commit:** `feat(mobile): add initNav() dispatch + initMobileNav()`

---

## Task 6 — JS: `initFAB()`

**File:** `web/static/app.js`

```js
function initFAB() {
  const btn      = document.getElementById('fab-btn');
  const sheet    = document.getElementById('fab-sheet');
  const backdrop = document.getElementById('fab-backdrop');

  if (!btn || !sheet) return;

  function openFAB() {
    sheet.classList.add('open');
    if (backdrop) backdrop.classList.add('open');
    sheet.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function closeFAB() {
    sheet.classList.remove('open');
    if (backdrop) backdrop.classList.remove('open');
    sheet.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  btn.addEventListener('click', () => {
    sheet.classList.contains('open') ? closeFAB() : openFAB();
  });
  if (backdrop) backdrop.addEventListener('click', closeFAB);

  // FAB language radios → mirror sidebar radios
  document.querySelectorAll('input[name="language-fab"]').forEach(fab => {
    fab.addEventListener('change', () => {
      const sidebar = document.querySelector(`input[name="language"][value="${fab.value}"]`);
      if (sidebar) { sidebar.checked = true; sidebar.dispatchEvent(new Event('change', { bubbles: true })); }
    });
  });

  // FAB provider radios → mirror sidebar radios
  document.querySelectorAll('input[name="provider-fab"]').forEach(fab => {
    fab.addEventListener('change', () => {
      const sidebar = document.querySelector(`input[name="provider"][value="${fab.value}"]`);
      if (sidebar) { sidebar.checked = true; sidebar.dispatchEvent(new Event('change', { bubbles: true })); }
    });
  });

  // FAB refresh → delegate to sidebar refresh button
  const fabRefresh = document.getElementById('fab-refresh-btn');
  if (fabRefresh) {
    fabRefresh.addEventListener('click', () => {
      closeFAB();
      document.getElementById('refresh-btn')?.click();
    });
  }

  // Sync FAB radios to current sidebar state on init
  ['language', 'provider'].forEach(name => {
    const checked = document.querySelector(`input[name="${name}"]:checked`);
    if (checked) {
      const fab = document.querySelector(`input[name="${name}-fab"][value="${checked.value}"]`);
      if (fab) fab.checked = true;
    }
  });
}
```

Call `initFAB()` from `init()` / `DOMContentLoaded` (the `if (!btn || !sheet) return` guard makes it safe on desktop).

**Commit:** `feat(mobile): implement initFAB() with radio sync to sidebar controls`

---

## Task 7 — Smoke test

Run `python app.py` and verify:

**Desktop (>767px):**
- [ ] 3-column layout intact
- [ ] Compact header hidden, FAB hidden, section header cards hidden
- [ ] Player bar aligned between sidebar and right panel
- [ ] Sidebar nav switches views with slide animation

**Mobile (≤767px — DevTools device emulation):**
- [ ] Compact header visible: live clock (HH:MM) + location side-by-side
- [ ] Sidebar hidden, right panel hidden
- [ ] Both lifestyle and dashboard sections visible in one scroll
- [ ] Section header cards visible as separators
- [ ] FAB (⚙️) visible at bottom-right above player bar
- [ ] Tapping FAB opens slide-up sheet; backdrop click closes
- [ ] Lang/provider toggles in FAB sheet work (language switch propagates)
- [ ] FAB refresh button triggers data fetch
- [ ] Player bar spans full screen width (left: 0, right: 0)
- [ ] Player sheet opens full-width
- [ ] Gauge grid is 2×2
- [ ] Last card not obscured behind player bar

**Commit:** `feat(mobile): mobile responsive layout complete`

---

## Reuse Map

| Need | Existing asset to reuse |
|---|---|
| Language change | `applyLanguage()` — trigger via `dispatchEvent` on `input[name="language"]` |
| Provider change | existing `input[name="provider"]` change listener — same mechanism |
| Refresh | `#refresh-btn` click — FAB refresh delegates to it |
| Location text | `#rp-location` render path — copy to `#mobile-location` in same call |
| Sidebar nav | `initSidebarNav()` — still called from `initNav()` on desktop |
| Segmented controls | `.seg-ctrl` + `.seg-option` CSS — already styled, reused in FAB sheet |

---

## Amendment — 2026-02-28: 1.5× compact header font

**Commit:** `style(mobile): 1.5x compact-header font for time & station`

After initial implementation, the compact header clock and station name were too small for a quick-glance mobile display. Both elements are scaled up 1.5×:

**`web/static/style.css` — `.compact-header`**

| Property | Before | After |
|---|---|---|
| `font-size` | `0.9rem` | `1.35rem` (0.9 × 1.5) |
| `padding` | `10px 16px` | `12px 16px` |

`#mobile-clock` and `.mobile-location` inherit `font-size` from `.compact-header`; no additional rules needed. The station name source remains `data.location` (CWA current conditions station name via `/api/broadcast`).

---

## Amendment — 2026-02-28: Mobile Light Mode Visibility Fix

**Commit:** `style(mobile): fix light mode visibility for --muted, header and wk-night cards`

Investigation showed that `--muted` text in light mode failed WCAG contrast, and elements using `var(--sidebar-text)` like the mobile header and forecast night cards were too dim against their dark backgrounds.

**`web/static/style.css` Changes:**
- Updated `--muted` from `#7a8ca0` to `#64748b` for better readability.
- Forced `.compact-header` color to `#ffffff` (previously `var(--sidebar-text)`).
- Forced `.wk-card.wk-night` color to `#ffffff` (previously `var(--sidebar-text)`).
- Added `.fab-sheet` overrides to ensure dashboard settings labels are visible against the light mobile sheet background.
- Bumped `dashboard.html` cache buster to `v=19`.
