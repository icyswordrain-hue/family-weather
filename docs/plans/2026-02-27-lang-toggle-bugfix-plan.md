# EN / 中文 Toggle Bugfix Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix three regressions where EN/中文 toggle has no effect on static UI text, cloud-cover labels, and view headings.

**Architecture:**
The `TRANSLATIONS` constant and `applyLanguage(lang)` in `app.js` already exist and correctly swap the `T` map on toggle. However, three categories of strings were never wired to `T` or remain hardcoded in `dashboard.html` HTML that `applyLanguage()` does not touch. Fix strategy: (1) drive static HTML strings through JS at toggle time using `data-i18n` attribute lookups; (2) add missing translation keys; (3) normalize cloud-cover labels from the API to locale-neutral icon keys so EN mode shows English.

**Tech Stack:** Vanilla JS, Jinja2 HTML templates — no library additions needed.

---

## Bug Inventory

| # | Symptom | Root Cause |
|---|---|---|
| 1 | Left panel nav labels (功能, 生活建議, 廣播稿, 天氣總覽) and right panel labels (系統控制, 系統記錄) stay Chinese in EN mode | Hard-coded Chinese text in `dashboard.html`; `applyLanguage()` does not update them |
| 2 | Cloud coverage value in Dashboard / current-conditions hero (`cur-weather-text`) shows Chinese in EN mode | `data.weather_text` from the API is always Chinese (e.g., `"多雲"`) regardless of `lang`; no translation mapping exists in `app.js` |
| 3 | View `<h1>` headings (生活指南, 每日天氣廣播, 天氣儀表板) and `<h2>` section titles (24 小時預報, 七日預報) stay Chinese in EN mode | Hardcoded Chinese HTML; `applyLanguage()` does not touch them |

---

## Task G: Fix Static Panel Labels — `dashboard.html` + `app.js`

**Files:**
- Modify: `web/templates/dashboard.html`
- Modify: `web/static/app.js`

### Step 1: Add `data-i18n` attributes to static HTML strings

In `web/templates/dashboard.html`, annotate every string that must switch language with a `data-i18n` key. Apply the following changes:

```html
<!-- SEARCH -->
<p class="nav-section-label">功能</p>
<!-- REPLACE -->
<p class="nav-section-label" data-i18n="nav_section">功能</p>

<!-- SEARCH -->
<span>生活建議</span>
<!-- REPLACE -->
<span data-i18n="nav_lifestyle">生活建議</span>

<!-- SEARCH -->
<span>廣播稿</span>
<!-- REPLACE -->
<span data-i18n="nav_narration">廣播稿</span>

<!-- SEARCH -->
<span>天氣總覽</span>
<!-- REPLACE -->
<span data-i18n="nav_dashboard">天氣總覽</span>

<!-- SEARCH -->
<p class="rp-label">系統控制</p>
<!-- REPLACE -->
<p class="rp-label" data-i18n="system_controls">系統控制</p>

<!-- SEARCH -->
<span>系統記錄</span>   <!-- inside .rp-log-header -->
<!-- REPLACE -->
<span data-i18n="system_log">系統記錄</span>
```

### Step 2: Add missing translation keys to `TRANSLATIONS` in `app.js`

In the `en` block (after `step7`):

```javascript
// SEARCH
    step7: 'Finalizing…',
  },
  'zh-TW': {
// REPLACE
    step7: 'Finalizing…',
    // Static panel labels
    nav_section: 'Views',
    nav_lifestyle: 'Lifestyle',
    nav_narration: 'Narration',
    nav_dashboard: 'Dashboard',
    system_controls: 'System Controls',
    system_log: 'System Log',
    // View headings
    h1_lifestyle: 'Lifestyle Guide',
    h1_narration: 'Weather Briefing',
    h1_dashboard: 'Weather Dashboard',
    h2_24h: '24-Hour Forecast',
    h2_7day: '7-Day Forecast',
  },
  'zh-TW': {
```

In the `zh-TW` block (after `step7`):

```javascript
// SEARCH
    step7: '最終處理中…',
  },
};
// REPLACE
    step7: '最終處理中…',
    // Static panel labels
    nav_section: '功能',
    nav_lifestyle: '生活建議',
    nav_narration: '廣播稿',
    nav_dashboard: '天氣總覽',
    system_controls: '系統控制',
    system_log: '系統記錄',
    // View headings
    h1_lifestyle: '生活指南',
    h1_narration: '每日天氣廣播',
    h1_dashboard: '天氣儀表板',
    h2_24h: '24 小時預報',
    h2_7day: '七日預報',
  },
};
```

### Step 3: Wire `applyLanguage()` to update `data-i18n` elements and view headings

In `app.js`, extend `applyLanguage()` to sweep all `data-i18n` elements and the view headings:

```javascript
// SEARCH
function applyLanguage(lang) {
  T = TRANSLATIONS[lang] || TRANSLATIONS['zh-TW'];
  // Update LOADING_MSGS in-place for next animation run
  LOADING_MSGS.splice(0, LOADING_MSGS.length,
    T.step1, T.step2, T.step3, T.step4, T.step5, T.step6, T.step7);

  // Re-render labels if data is already loaded
  if (broadcastData) render(broadcastData);
}
// REPLACE
function applyLanguage(lang) {
  T = TRANSLATIONS[lang] || TRANSLATIONS['zh-TW'];

  // Update LOADING_MSGS in-place for next animation run
  LOADING_MSGS.splice(0, LOADING_MSGS.length,
    T.step1, T.step2, T.step3, T.step4, T.step5, T.step6, T.step7);

  // Swap all data-i18n elements
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    if (T[key] !== undefined) el.textContent = T[key];
  });

  // Swap view headings (hardcoded in HTML, no data-i18n — update by element ID)
  setText('view-heading-lifestyle', T.h1_lifestyle);
  setText('view-heading-narration', T.h1_narration);
  setText('view-heading-dashboard', T.h1_dashboard);
  setText('section-heading-24h', T.h2_24h);
  setText('section-heading-7day', T.h2_7day);

  // Re-render data labels if data is already loaded
  if (broadcastData) render(broadcastData);
}
```

### Step 4: Add IDs to view headings in `dashboard.html`

```html
<!-- SEARCH -->
<div id="view-lifestyle" class="view-container active">
  <header class="view-header">
    <h1>生活指南</h1>
<!-- REPLACE -->
<div id="view-lifestyle" class="view-container active">
  <header class="view-header">
    <h1 id="view-heading-lifestyle">生活指南</h1>

<!-- SEARCH -->
<div id="view-narration" class="view-container">
  <header class="view-header">
    <h1>每日天氣廣播</h1>
<!-- REPLACE -->
<div id="view-narration" class="view-container">
  <header class="view-header">
    <h1 id="view-heading-narration">每日天氣廣播</h1>

<!-- SEARCH -->
<div id="view-dashboard" class="view-container">
  <header class="view-header">
    <h1>天氣儀表板</h1>
<!-- REPLACE -->
<div id="view-dashboard" class="view-container">
  <header class="view-header">
    <h1 id="view-heading-dashboard">天氣儀表板</h1>

<!-- SEARCH -->
<h2 class="section-title">24 小時預報</h2>
<!-- REPLACE -->
<h2 class="section-title" id="section-heading-24h">24 小時預報</h2>

<!-- SEARCH -->
<h2 class="section-title">七日預報</h2>
<!-- REPLACE -->
<h2 class="section-title" id="section-heading-7day">七日預報</h2>
```

### Step 5: Run tests

```
pytest tests/ -v
```

Expected: all tests PASS (no Python logic changed).

### Step 6: Manual verification (static labels)

1. Start server: `.\run_local.ps1`
2. Open `http://localhost:8080`
3. Default lang is `zh-TW` (from `localStorage` or radio default) — all labels show Chinese ✓
4. In Right Panel, click **EN** radio
5. Verify instantly (no page reload needed):
   - Left sidebar: section label → `Views`; buttons → `Lifestyle`, `Narration`, `Dashboard`
   - Right panel: `System Controls`, `System Log`
   - View h1 (whichever is active): switches to English heading
   - Switch to each view and confirm heading switches
6. Click **中文** radio → all revert to Chinese ✓

### Step 7: Commit

```bash
git add web/templates/dashboard.html web/static/app.js
git commit -m "fix(i18n): wire data-i18n sweep + view heading IDs so EN toggle updates all static labels"
```

---

## Task H: Fix Cloud-Cover Text in EN Mode — `app.js`

**Files:**
- Modify: `web/static/app.js`

The `cur-weather-text` element displays `data.weather_text` from the API. That field is always in Chinese (e.g., `"多雲"`, `"陰天"`) because the CWA API returns Chinese strings. In EN mode this must be translated to English.

### Step 1: Add a cloud-cover translation map to `app.js`

Insert after the `ICONS` constant (around line 59):

```javascript
// ── Weather text localisation map (CWA API → English) ──────────────────────
const WEATHER_TEXT_EN = {
  '晴': 'Sunny',
  '晴時多雲': 'Partly Cloudy',
  '多雲時晴': 'Mostly Sunny',
  '多雲': 'Cloudy',
  '陰': 'Overcast',
  '陰時多雲': 'Mostly Cloudy',
  '多雲時陰': 'Mostly Cloudy',
  '短暫雨': 'Brief Rain',
  '短暫陣雨': 'Brief Showers',
  '陣雨': 'Showers',
  '雨': 'Rain',
  '大雨': 'Heavy Rain',
  '豪雨': 'Torrential Rain',
  '短暫雷陣雨': 'Brief Thunderstorms',
  '雷陣雨': 'Thunderstorms',
  '有霧': 'Foggy',
  '霧': 'Fog',
  '有靄': 'Hazy',
};

function localiseWeatherText(text) {
  if (getLang() === 'en') return WEATHER_TEXT_EN[text] || text;
  return text;
}
```

### Step 2: Apply `localiseWeatherText` in `renderCurrentView`

```javascript
// SEARCH
  setText('cur-weather-text', data.weather_text || '—');
// REPLACE
  setText('cur-weather-text', localiseWeatherText(data.weather_text || '—'));
```

### Step 3: Run tests

```
pytest tests/ -v
```

Expected: all PASS.

### Step 4: Manual verification (cloud cover text)

1. Switch to **EN** radio in right panel
2. Click **Refresh** (or wait for cached data to re-render via `applyLanguage`)
3. In **Weather Dashboard** view, the weather label under the temperature hero should display English (e.g., `Cloudy`, `Partly Cloudy`) instead of Chinese characters
4. Switch back to **中文** → reverts to Chinese `"多雲"` etc. ✓

> **Note:** `applyLanguage()` calls `render(broadcastData)` when data is loaded, so toggling EN without refreshing will also re-render the weather text correctly.

### Step 5: Commit

```bash
git add web/static/app.js
git commit -m "fix(i18n): translate CWA weather_text to English when lang=en using WEATHER_TEXT_EN map"
```

---

## End-to-End Smoke Test

After both tasks are committed, run the full manual checklist:

1. Open `http://localhost:8080` (default: 中文)
2. **Left panel** shows: 功能 / 生活建議 / 廣播稿 / 天氣總覽 ✓
3. **Right panel** shows: 系統控制 / 系統記錄 ✓
4. **View h1** (each tab) shows Chinese heading ✓
5. **Section h2** (24 小時預報, 七日預報) in Chinese ✓
6. **Weather text** shows Chinese cloud label ✓
7. Toggle to **EN**:
   - Left panel labels → English ✓
   - Right panel labels → English ✓
   - View headings → English ✓
   - Section headings → English ✓
   - Weather text → English (after re-render) ✓
8. Toggle back to **中文** → all revert ✓

---

## Execution Options

Plan saved to `docs/plans/2026-02-27-lang-toggle-bugfix-plan.md`.

**1. Subagent-Driven (this session)** — Dispatch Task G subagent, review, then Task H subagent.

**2. Parallel Session (separate)** — Open new session with `executing-plans` and pass this file as context.

Which approach?

---

## Task I: Fix Dark / Light Mode on Left & Right Panels — `style.css`

**Files:**
- Modify: `web/static/style.css`

### Root Cause

In `:root`, the sidebar and right-panel background variables are declared as static dark-navy values:

```css
--sidebar-bg: #1a2235;
--rp-bg:      #1a2235;
```

The `html.dark` block **never overrides these variables**, so toggling dark mode has zero visual effect on `.sidebar` (which uses `var(--sidebar-bg)`) and `.right-panel` (which uses `var(--rp-bg)`). Both panels show the same dark navy in both light and dark mode.

The `html.dark .right-panel` rule that exists only adjusts the right panel's background to `#111a2a` via a direct property, but the sidebar has no matching override at all.

### Step 1: Define proper light-mode palette values in `:root`

Change the variable declarations in `:root` from dark-navy to light-mode values:

```css
/* SEARCH */
  --sidebar-bg: #1a2235;
  --sidebar-hover: #232f48;
  --sidebar-active: #2a3a5e;
  --sidebar-text: #8fa3c0;
  --sidebar-active-text: #ffffff;
  --rp-bg: #1a2235;
/* REPLACE */
  /* Light mode sidebar / right panel */
  --sidebar-bg: #2c3e6b;
  --sidebar-hover: #374d7f;
  --sidebar-active: #4a5f9a;
  --sidebar-text: #b0c4de;
  --sidebar-active-text: #ffffff;
  --rp-bg: #2c3e6b;
```

> **Why #2c3e6b?** It is visibly lighter and more blue-toned than the pure dark navy `#0f1520`, so users see a clear difference between light and dark mode on the panels while keeping the professional dark-sidebar aesthetic.

### Step 2: Add `html.dark` overrides to restore the dark values

Append to the `html.dark { … }` block in `style.css` (around line 1539):

```css
/* SEARCH */
html.dark {
  --main-bg: #0f1520;
  --surface: #1a2235;
  --border: #2a3a5e;
  --text: #e0e6f0;
  --muted: #8fa3c0;

  --blue-lt: rgba(77, 124, 254, 0.12);
  --warn-lt: rgba(255, 118, 117, 0.12);
  --ok-lt: rgba(85, 239, 196, 0.12);

  --shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
  --shadow-md: 0 4px 24px rgba(0, 0, 0, 0.35);
}
/* REPLACE */
html.dark {
  --main-bg: #0f1520;
  --surface: #1a2235;
  --border: #2a3a5e;
  --text: #e0e6f0;
  --muted: #8fa3c0;

  /* Restore dark sidebar / right panel */
  --sidebar-bg: #1a2235;
  --sidebar-hover: #232f48;
  --sidebar-active: #2a3a5e;
  --sidebar-text: #8fa3c0;
  --rp-bg: #1a2235;

  --blue-lt: rgba(77, 124, 254, 0.12);
  --warn-lt: rgba(255, 118, 117, 0.12);
  --ok-lt: rgba(85, 239, 196, 0.12);

  --shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
  --shadow-md: 0 4px 24px rgba(0, 0, 0, 0.35);
}
```

### Step 3: Remove the now-redundant `html.dark .right-panel` direct-background override

The existing rule sets a direct `background` value that would conflict with the variable approach:

```css
/* SEARCH — remove this block entirely */
/* Dark mode right panel */
html.dark .right-panel {
  background: #111a2a;
  border-left-color: var(--border);
}
/* REPLACE */
/* Dark mode right panel — border only; background comes from var(--rp-bg) */
html.dark .right-panel {
  border-left-color: var(--border);
}
```

### Step 4: Add the sidebar to the smooth transition list

The sidebar is not in the transition list, so it will flash on toggle instead of animating. Add it:

```css
/* SEARCH */
body,
.main-panel,
.right-panel,
/* REPLACE */
body,
.sidebar,
.main-panel,
.right-panel,
```

### Step 5: Run tests

```
pytest tests/ -v
```

Expected: all PASS (no Python logic changed).

### Step 6: Manual verification

1. Start server: `.\run_local.ps1`
2. Open `http://localhost:8080`
3. Default should be **light mode** (no `dark` class on `<html>`)
   - Left sidebar: medium blue (#2c3e6b) — clearly different from the light main background
   - Right panel: same medium blue
4. Click **深色模式** button in right panel
   - Left sidebar transitions to dark navy (#1a2235)
   - Right panel transitions to dark navy (#1a2235)
   - Main content area darkens as before
5. Click **淺色模式** button
   - Left and right panels lighten back to #2c3e6b
6. Verify transition is smooth (200ms fade, no flash)

### Step 7: Commit

```bash
git add web/static/style.css
git commit -m "fix(theme): define light-mode --sidebar-bg/--rp-bg in :root; restore dark values under html.dark so toggle visibly affects both panels"
```
