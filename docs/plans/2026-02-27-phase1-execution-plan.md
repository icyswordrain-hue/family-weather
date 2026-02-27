# Phase 1 — Desktop Structural Cleanup: Execution Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Simplify the desktop layout by removing the narration view, adding a sticky player bar + half-sheet, moving controls to the sidebar, and shrinking the right panel to ~180px.

**Architecture:** Three files change — `dashboard.html` (DOM rewiring), `style.css` (layout + animation tokens), and `app.js` (new init functions, removal of dead wiring). No new dependencies. No new routes. All changes are strictly additive-or-replace within the existing single-page app.

**Tech Stack:** Vanilla HTML/CSS/JS. Flask serves `web/templates/dashboard.html` and `web/static/`.

---

## Context for the implementing agent

The project is a family weather dashboard at `c:\Users\User\.gemini\antigravity\scratch\family-weather`.

- **Entry point served by Flask:** `web/templates/dashboard.html`
- **Styles:** `web/static/style.css`
- **Client logic:** `web/static/app.js`

The existing app has:
- A 3-column layout: `.sidebar` | `#main-content` (tab-gated views) | `.right-panel`
- 3 nav tabs: Lifestyle, Dashboard, Narration — each `.view-container` shown/hidden via `.active` class
- Lang + provider radio buttons in `.rp-controls-section` inside `.right-panel`
- A `#theme-toggle` button wired in an inline `<script>` at bottom of `dashboard.html`
- `applyLanguage()` exists in `app.js` and reads `input[name="language"]:checked`
- `--rp-w` CSS variable controls right-panel width (currently `280px`)

The task list file `docs/plans/2026-02-27-phase1-task-list.md` is the cross-off companion to this plan.

---

## Task 1 — Remove `#view-narration` and its nav button

**Files:**
- Modify: `web/templates/dashboard.html`

**Step 1: Locate the narration nav button**

Search for:
```html
<button class="nav-item"
```
Find the one whose label/text is narration (看天氣播報 or similar). Delete that `<button>` element entirely.

**Step 2: Locate and delete `#view-narration`**

Search for `id="view-narration"`. Delete the entire `<div id="view-narration" ...>…</div>` block including all children.

Also delete `<div id="narration-meta"` if present — it lived inside the narration view header.

**Step 3: Remove any inline audio `<audio>` tag**

If there is a standalone `<audio id="narration-audio"` element outside the player bar (not yet added), remove it. The player bar (Task 3) will own the audio element.

**Step 4: Verify the page loads without JS errors**

Run the dev server:
```powershell
python app.py
```
Open `http://localhost:5000` in browser. Console should show no `Cannot find element #view-narration` or similar errors.

**Step 5: Commit**
```bash
git add web/templates/dashboard.html
git commit -m "feat(phase1): remove narration view and nav button"
```

---

## Task 2 — Shrink right panel; strip `.rp-controls-section` entirely

**Files:**
- Modify: `web/static/style.css`
- Modify: `web/templates/dashboard.html`

**Step 1: Change `--rp-w` in CSS**

Find:
```css
--rp-w: 280px;
```
Replace with:
```css
--rp-w: 180px;
```

**Step 2: Strip `.rp-controls-section` (and `.rp-top`) from right panel HTML**

In `dashboard.html`, find and delete the entire `.rp-top` wrapper including `.rp-controls-section` and all its children (`#rp-last-updated`, the `.rp-label`, `.rp-actions`, and `#refresh-btn`). The right panel will now contain **only** the system log (`.rp-log-container`).

> **Rationale (2026-02-27 amendment):** Last-updated timestamp and refresh button are moved to the left sidebar (see Task 2b below). The "系統控制" section label is dropped entirely.

**Step 3: Verify layout**

Reload the page. Right panel should be visibly narrower and show only the system log. No orphaned controls should appear in the right panel.

**Step 4: Commit**
```bash
git add web/static/style.css web/templates/dashboard.html
git commit -m "feat(phase1): shrink right panel to 180px, strip rp-controls-section"
```

---

## Task 2b — Move last-updated + refresh button to left sidebar *(added 2026-02-27)*

**Files:**
- Modify: `web/templates/dashboard.html`
- Modify: `web/static/style.css`

**Step 1: Add `.sidebar-status` block in sidebar HTML**

Inside `<aside class="sidebar">`, immediately after `.sidebar-controls` (before `</aside>`), add:

```html
<!-- Status + Refresh -->
<div class="sidebar-status" id="sidebar-status">
  <div id="rp-last-updated" class="rp-last-updated"></div>
  <button class="rp-btn" id="refresh-btn" title="Fetch latest data" aria-label="獲取最新天氣資料">
    <span data-i18n="refresh_btn">🔄 重新整理</span>
  </button>
</div>
```

> The existing `.rp-last-updated` and `.rp-btn` CSS rules already style these elements — no new rules for those selectors are needed.

**Step 2: Add `.sidebar-status` CSS rule**

Append to `style.css`:

```css
/* Sidebar Status / Refresh */
.sidebar-status {
  padding: 10px 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-top: 1px solid var(--border-color, rgba(255,255,255,0.08));
}
```

**Step 3: Verify**

- Last-updated text and refresh button appear at the bottom of the sidebar.
- Right panel shows only the system log.
- Clicking refresh still triggers a data fetch.
- Language switch updates the refresh button label (`data-i18n="refresh_btn"`).

**Step 4: Commit**
```bash
git add web/templates/dashboard.html web/static/style.css
git commit -m "feat(phase1): move last-updated and refresh btn to sidebar"
```

---

## Task 3 — Add player bar + player sheet HTML

**Files:**
- Modify: `web/templates/dashboard.html`

**Step 1: Add player bar HTML**

Inside `#main-content` (or as a direct child of the `.app-shell` / body wrapper that spans the main column), add immediately before the closing tag:

```html
<!-- Player Bar -->
<div class="player-bar" id="player-bar">
  <button class="player-play-btn" id="player-play-btn" aria-label="Play/Pause">
    <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
      <polygon id="player-play-icon" points="5,3 17,10 5,17"/>
    </svg>
  </button>
  <span class="player-label" id="player-label">
    <span class="player-cloud-icon" id="player-cloud-icon">☁</span>
    <span id="player-title">Fetching briefing…</span>
  </span>
  <div class="player-progress-wrap">
    <div class="player-progress-bar" id="player-progress-bar"></div>
  </div>
  <span class="player-duration" id="player-duration">--:--</span>
  <button class="player-sheet-toggle" id="player-sheet-toggle" aria-label="Show transcript">⌄</button>
  <audio id="player-audio" preload="none"></audio>
</div>

<!-- Player Sheet (half-sheet overlay for narration text) -->
<div class="player-sheet" id="player-sheet" aria-hidden="true">
  <div class="player-sheet-header">
    <span class="player-sheet-title">Narration</span>
    <button class="player-sheet-close" id="player-sheet-close" aria-label="Close">✕</button>
  </div>
  <div class="player-sheet-body" id="player-sheet-body">
    <!-- narration text rendered here by JS -->
  </div>
</div>
<div class="player-sheet-backdrop" id="player-sheet-backdrop"></div>
```

**Step 2: Verify HTML is valid**

Open page in browser. Player bar should appear at the bottom of the main panel (unstyled at this point is fine — CSS comes in Task 4).

**Step 3: Commit**
```bash
git add web/templates/dashboard.html
git commit -m "feat(phase1): add player bar and player sheet HTML"
```

---

## Task 4 — Style player bar + player sheet in CSS

**Files:**
- Modify: `web/static/style.css`

**Step 1: Add player bar CSS**

Append to `style.css`:

```css
/* ── Player Bar ──────────────────────────────── */
.player-bar {
  position: fixed;
  bottom: 0;
  /* desktop: constrain to main panel width */
  left: var(--sidebar-w, 200px);
  right: var(--rp-w, 180px);
  height: 52px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  background: var(--panel-bg, #1e1e2e);
  border-top: 1px solid var(--border-color, rgba(255,255,255,0.08));
  z-index: 150;
}

.player-play-btn {
  background: none;
  border: none;
  color: var(--text-primary, #e0e0e0);
  cursor: pointer;
  padding: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  transition: background 150ms;
}
.player-play-btn:hover { background: var(--hover-bg, rgba(255,255,255,0.08)); }

.player-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.82rem;
  color: var(--text-secondary, #aaa);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 0;
  max-width: 180px;
}

.player-progress-wrap {
  flex: 1;
  height: 4px;
  background: var(--border-color, rgba(255,255,255,0.12));
  border-radius: 2px;
  overflow: hidden;
}
.player-progress-bar {
  height: 100%;
  width: 0%;
  background: var(--accent, #7c6af7);
  border-radius: 2px;
  transition: width 0.25s linear;
}

.player-duration {
  font-size: 0.75rem;
  color: var(--text-secondary, #aaa);
  flex-shrink: 0;
  min-width: 36px;
  text-align: right;
}

.player-sheet-toggle {
  background: none;
  border: none;
  color: var(--text-secondary, #aaa);
  cursor: pointer;
  font-size: 1.1rem;
  padding: 4px 6px;
  flex-shrink: 0;
  transition: transform 200ms;
}
.player-sheet-toggle.open { transform: rotate(180deg); }

/* Ambient pulse when no audio */
@keyframes player-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.35; }
}
.player-cloud-icon { display: inline-block; }
.player-bar.loading .player-cloud-icon {
  animation: player-pulse 1.6s ease-in-out infinite;
}

/* ── Player Sheet ────────────────────────────── */
.player-sheet {
  position: fixed;
  bottom: 52px;
  left: var(--sidebar-w, 200px);
  right: var(--rp-w, 180px);
  height: 60vh;
  background: var(--panel-bg, #1e1e2e);
  border-top: 1px solid var(--border-color, rgba(255,255,255,0.08));
  overflow-y: auto;
  z-index: 200;
  transform: translateY(100%);
  transition: transform 280ms cubic-bezier(0.32, 0.72, 0, 1);
}
.player-sheet.open { transform: translateY(0); }

.player-sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color, rgba(255,255,255,0.08));
  font-weight: 600;
  font-size: 0.9rem;
}

.player-sheet-close {
  background: none;
  border: none;
  color: var(--text-secondary, #aaa);
  cursor: pointer;
  font-size: 1rem;
  padding: 4px 8px;
}

.player-sheet-body {
  padding: 16px;
  font-size: 0.88rem;
  line-height: 1.65;
  color: var(--text-primary, #e0e0e0);
  white-space: pre-wrap;
}

.player-sheet-backdrop {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  z-index: 199;
}
.player-sheet-backdrop.open { display: block; }

/* Scroll clearance so last content isn't behind player bar */
#main-content { padding-bottom: 60px; }
```

> **Note on CSS variables:** `--sidebar-w`, `--rp-w`, `--panel-bg`, `--border-color`, `--accent`, `--text-primary`, `--text-secondary`, `--hover-bg` — use whatever variable names already exist in `style.css`. Search the existing file before adding new ones. Align naming with the existing design system.

**Step 2: Verify**

Reload. Player bar appears pinned to the bottom of the main column. Sheet remains hidden. Loading state (add `.loading` to `.player-bar` temporarily via DevTools) shows cloud pulse.

**Step 3: Commit**
```bash
git add web/static/style.css
git commit -m "feat(phase1): style player bar, player sheet, and pulse animation"
```

---

## Task 5 — Add sidebar controls section (lang + provider toggles)

**Files:**
- Modify: `web/templates/dashboard.html`

**Step 1: Add HTML block in `.sidebar`**

Inside `.sidebar`, after the existing `<nav>` nav items block, add:

```html
<!-- Sidebar Controls -->
<div class="sidebar-controls" id="sidebar-controls">
  <div class="sidebar-control-group">
    <label class="sidebar-control-label" data-i18n="lang_label">Language</label>
    <div class="sidebar-toggle-row">
      <label class="sidebar-radio-label">
        <input type="radio" name="language" value="en" checked> EN
      </label>
      <label class="sidebar-radio-label">
        <input type="radio" name="language" value="zh"> 中文
      </label>
    </div>
  </div>
  <div class="sidebar-control-group">
    <label class="sidebar-control-label" data-i18n="provider_label">Provider</label>
    <div class="sidebar-toggle-row">
      <label class="sidebar-radio-label">
        <input type="radio" name="provider" value="openweathermap" checked> OWM
      </label>
      <label class="sidebar-radio-label">
        <input type="radio" name="provider" value="weatherapi"> WApi
      </label>
    </div>
  </div>
</div>
```

> **Note:** The `name` attribute values (`language`, `provider`) must match what `applyLanguage()` and provider-switching logic already read from. Verify in `app.js` before committing.

**Step 2: Verify**

Toggles appear at the bottom of sidebar. Switching language applies language (via existing `applyLanguage()` — no JS change needed for this task).

**Step 3: Commit**
```bash
git add web/templates/dashboard.html
git commit -m "feat(phase1): add lang + provider toggles to sidebar"
```

---

## Task 6 — Style sidebar controls section

**Files:**
- Modify: `web/static/style.css`

**Step 1: Add CSS**

```css
/* ── Sidebar Controls ─────────────────────────── */
.sidebar-controls {
  margin-top: auto;
  padding: 14px 12px;
  border-top: 1px solid var(--border-color, rgba(255,255,255,0.08));
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sidebar-control-group { display: flex; flex-direction: column; gap: 4px; }

.sidebar-control-label {
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-secondary, #aaa);
}

.sidebar-toggle-row { display: flex; gap: 8px; align-items: center; }

.sidebar-radio-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.78rem;
  color: var(--text-primary, #e0e0e0);
  cursor: pointer;
}
.sidebar-radio-label input[type="radio"] { accent-color: var(--accent, #7c6af7); }
```

> **Prerequisite:** For `margin-top: auto` to push controls to the bottom, the parent `.sidebar` must be `display: flex; flex-direction: column`. If it isn't already, add that — but search the existing CSS before changing it.

**Step 2: Verify**

Controls sit at the bottom of the sidebar, visually separated from nav items.

**Step 3: Commit**
```bash
git add web/static/style.css
git commit -m "feat(phase1): style sidebar controls section"
```

---

## Task 7 — Remove theme toggle button + inline theme script

**Files:**
- Modify: `web/templates/dashboard.html`
- Modify: `web/static/style.css`
- Modify: `web/static/app.js`

**Step 1: Delete `#theme-toggle` from HTML**

Find and delete the button:
```html
<button id="theme-toggle" ...>
```
Also delete any `<span>` or icon children inside it.

**Step 2: Delete the inline theme `<script>` block**

Search for the inline `<script>` that reads `localStorage` for `theme` and adds `html.dark`. Delete that entire `<script>` block.

**Step 3: Delete theme toggle wiring from `app.js`**

Search for `theme-toggle` or `theme_toggle` in `app.js`. Delete the `addEventListener` and any related `localStorage.setItem('theme', ...)` calls.

**Step 4: Add `initSystemTheme()` to `app.js`**

Add this function (call it from the main `init()` or `DOMContentLoaded` handler):

```js
function initSystemTheme() {
  const mq = window.matchMedia('(prefers-color-scheme: dark)');
  const apply = (dark) => document.documentElement.classList.toggle('dark', dark);
  apply(mq.matches);
  mq.addEventListener('change', (e) => apply(e.matches));
}
```

**Step 5: Verify**

On a system set to dark mode, page loads dark. Change OS to light → page goes light (requires browser refresh or live listener). No `localStorage` reads/writes for theme.

**Step 6: Commit**
```bash
git add web/templates/dashboard.html web/static/app.js
git commit -m "feat(phase1): replace manual theme toggle with prefers-color-scheme"
```

---

## Task 8 — Implement `initPlayerBar()` in `app.js`

**Files:**
- Modify: `web/static/app.js`

**Step 1: Add `initPlayerBar()`**

```js
function initPlayerBar() {
  const bar      = document.getElementById('player-bar');
  const audio    = document.getElementById('player-audio');
  const playBtn  = document.getElementById('player-play-btn');
  const icon     = document.getElementById('player-play-icon');
  const title    = document.getElementById('player-title');
  const progress = document.getElementById('player-progress-bar');
  const duration = document.getElementById('player-duration');

  if (!bar || !audio) return;

  // Set loading state until audio_url arrives
  bar.classList.add('loading');

  function formatTime(s) {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60).toString().padStart(2, '0');
    return `${m}:${sec}`;
  }

  function setPlaying(playing) {
    // Swap play ↔ pause polygon points
    icon.setAttribute('points', playing
      ? '4,3 8,3 8,17 4,17 M12,3 16,3 16,17 12,17'  // pause bars
      : '5,3 17,10 5,17'                              // play triangle
    );
  }

  audio.addEventListener('play',  () => setPlaying(true));
  audio.addEventListener('pause', () => setPlaying(false));
  audio.addEventListener('ended', () => setPlaying(false));

  audio.addEventListener('timeupdate', () => {
    if (!audio.duration) return;
    progress.style.width = `${(audio.currentTime / audio.duration) * 100}%`;
    duration.textContent = formatTime(audio.currentTime);
  });

  audio.addEventListener('loadedmetadata', () => {
    duration.textContent = formatTime(audio.duration);
  });

  playBtn.addEventListener('click', () => {
    if (audio.paused) audio.play();
    else audio.pause();
  });

  // Called by render() when narration data arrives
  window._playerBarSetAudio = function(audioUrl, narrationTitle, narrationText) {
    bar.classList.remove('loading');
    audio.src = audioUrl;
    if (title) title.textContent = narrationTitle || 'Morning Briefing';
    const body = document.getElementById('player-sheet-body');
    if (body) body.textContent = narrationText || '';
  };
}
```

**Step 2: Wire into `render()` dispatch**

Find where `renderNarrationView()` is called in `render()`. Replace it with:

```js
if (data.narration && data.narration.audio_url) {
  window._playerBarSetAudio(
    data.narration.audio_url,
    data.narration.title,
    data.narration.text
  );
}
```

Remove the `renderNarrationView()` function call entirely.

**Step 3: Call `initPlayerBar()` from `init()` / `DOMContentLoaded`**

Find the main initialisation block. Add:
```js
initPlayerBar();
```

**Step 4: Verify**

With the dev server running, wait for data to load. Player bar should populate with audio. Play button should toggle audio. Progress should scrub.

**Step 5: Commit**
```bash
git add web/static/app.js
git commit -m "feat(phase1): implement initPlayerBar() and wire audio to render()"
```

---

## Task 9 — Implement `initPlayerSheet()` in `app.js`

**Files:**
- Modify: `web/static/app.js`

**Step 1: Add `initPlayerSheet()`**

```js
function initPlayerSheet() {
  const sheet    = document.getElementById('player-sheet');
  const backdrop = document.getElementById('player-sheet-backdrop');
  const toggle   = document.getElementById('player-sheet-toggle');
  const close    = document.getElementById('player-sheet-close');

  if (!sheet || !toggle) return;

  function openSheet() {
    sheet.classList.add('open');
    backdrop.classList.add('open');
    toggle.classList.add('open');
    sheet.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function closeSheet() {
    sheet.classList.remove('open');
    backdrop.classList.remove('open');
    toggle.classList.remove('open');
    sheet.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  toggle.addEventListener('click', () => {
    sheet.classList.contains('open') ? closeSheet() : openSheet();
  });
  if (close)    close.addEventListener('click', closeSheet);
  if (backdrop) backdrop.addEventListener('click', closeSheet);
}
```

**Step 2: Call from init**

Add `initPlayerSheet();` alongside `initPlayerBar()`.

**Step 3: Verify**

Click `⌄` button → sheet slides up from player bar. Body scroll locks. Click `✕` or backdrop → sheet closes.

**Step 4: Commit**
```bash
git add web/static/app.js
git commit -m "feat(phase1): implement initPlayerSheet() with scroll lock"
```

---

## Task 10 — Implement `initSidebarControls()` and remove dead init calls

**Files:**
- Modify: `web/static/app.js`

**Step 1: Add `initSidebarControls()`**

```js
function initSidebarControls() {
  // Language toggles: applyLanguage() already reads input[name="language"]:checked
  // — just ensure change events trigger it
  document.querySelectorAll('input[name="language"]').forEach(input => {
    input.addEventListener('change', () => applyLanguage && applyLanguage());
  });

  // Provider toggles: wire same as existing right-panel provider logic
  document.querySelectorAll('input[name="provider"]').forEach(input => {
    input.addEventListener('change', () => {
      // Re-use whatever handler was wired to the old right-panel provider radios
      // Search app.js for 'provider' event handler and reference that function here
    });
  });
}
```

> **Note:** Before writing the provider handler, search `app.js` for the existing provider radio `change` handler. Extract it into a named function if it isn't already, then call it from both places.

**Step 2: Delete dead init calls**

Search for `initMobileDrawer` in `app.js` — delete the function definition and its call.

Search for any other narration-view-specific functions (`renderNarrationView`, `initNarrationView`, etc.) — delete them.

**Step 3: Call `initSidebarControls()` from init**

**Step 4: Verify**

Language toggle in sidebar switches app language. Provider toggle in sidebar works. No console errors about missing elements.

**Step 5: Commit**
```bash
git add web/static/app.js
git commit -m "feat(phase1): implement initSidebarControls, remove dead init calls"
```

---

## Task 11 — Final integration smoke test

**Goal:** Confirm Phase 1 is complete and stable before branching into Phase 2.

**Step 1: Start the server**
```powershell
python app.py
```

**Step 2: Manual checklist**

- [ ] Page loads without JS console errors
- [ ] Narration view tab is gone from nav
- [ ] Right panel is visibly narrower (~180px)
- [ ] Lang + provider toggles visible at sidebar bottom
- [ ] Language switch works from sidebar
- [ ] Player bar visible at bottom of main column
- [ ] Player sheet opens/closes on `⌄` toggle
- [ ] Audio plays if a narration audio_url is present
- [ ] Dark mode follows OS setting (no manual toggle)
- [ ] No ghost references to `#view-narration` or `#theme-toggle` in DOM

**Step 3: Commit final tag**
```bash
git tag phase1-complete
git push origin HEAD --tags
```

---

## Pre-Delivery Checklist (ui-ux-pro-max)

Before marking Phase 1 done, verify:

- [ ] No emojis used as icons — SVG for play/pause; cloud icon (`☁`) is decorative text, acceptable
- [ ] All interactive elements have focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected — add to pulse animation:
  ```css
  @media (prefers-reduced-motion: reduce) {
    .player-bar.loading .player-cloud-icon { animation: none; }
    .player-sheet { transition: none; }
  }
  ```
- [ ] Player bar has no content hidden behind it (`padding-bottom: 60px` on scroll container)
- [ ] Borders visible in both light and dark modes

---

## Task 12 — Live Data Freshness Indicator *(UX #2)*

**Files:**
- Modify: `web/templates/dashboard.html`
- Modify: `web/static/style.css`
- Modify: `web/static/app.js`

**Step 1: Add freshness dot HTML**

Inside `.sidebar-status`, immediately before `#rp-last-updated`, add:
```html
<span class="freshness-dot" id="freshness-dot" title="Data age"></span>
```

**Step 2: Add freshness dot CSS**

```css
/* ── Freshness Dot ─────────────────────────── */
.freshness-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--border-color, #555);
  margin-right: 5px;
  vertical-align: middle;
}
.freshness-dot.fresh { background: #4caf81; }
.freshness-dot.stale { background: #f0a840; }
.freshness-dot.old   { background: #e05c5c; }
```

**Step 3: Add `updateFreshnessDot()` in `app.js`**

```js
function updateFreshnessDot(fetchedAtISO) {
  const dot = document.getElementById('freshness-dot');
  if (!dot || !fetchedAtISO) return;
  const ageMin = (Date.now() - new Date(fetchedAtISO).getTime()) / 60000;
  dot.classList.remove('fresh', 'stale', 'old');
  if (ageMin < 30)       dot.classList.add('fresh');
  else if (ageMin < 90)  dot.classList.add('stale');
  else                   dot.classList.add('old');
}
```

**Step 4: Call from `render()`**

Find where `render()` updates `#rp-last-updated`. Immediately after, add:
```js
updateFreshnessDot(data.fetched_at); // use whatever the timestamp field is named in your API response
```

**Step 5: Verify**

With fresh data: dot is green. In DevTools, manually set the timestamp to >90 min ago and call `updateFreshnessDot()` — dot turns red.

**Step 6: Commit**
```bash
git add web/templates/dashboard.html web/static/style.css web/static/app.js
git commit -m "feat(ux): add freshness dot to last-updated timestamp"
```

---

## Task 13 — Semantic Color Consistency *(UX #3)*

**Files:**
- Modify: `web/static/style.css`
- Modify: `web/templates/dashboard.html`
- Modify: `web/static/app.js`

**Step 1: Audit and normalise `lvl-N` classes in CSS**

Search `style.css` for `.lvl-1` through `.lvl-5`. If any are missing, add:
```css
.lvl-1 { color: #4caf81; }   /* good / low risk */
.lvl-2 { color: #a8d080; }   /* mild */
.lvl-3 { color: #f0a840; }   /* moderate */
.lvl-4 { color: #e07840; }   /* high */
.lvl-5 { color: #e05c5c; }   /* severe */
```
Adjust hex values to match your existing palette — do not introduce new hues.

**Step 2: Audit gauge renders in `app.js`**

Search `app.js` for every place a gauge card value is rendered. Ensure every numeric value element receives a `lvl-N` class. Example pattern:
```js
el.className = `gauge-value lvl-${getLevelForValue(metric, value)}`;
```

**Step 3: Add sidebar nav alert dot HTML**

On the Dashboard nav `<button>`, add:
```html
<span class="nav-alert-dot" id="nav-alert-dot"></span>
```

**Step 4: Add nav alert dot CSS**

```css
.nav-alert-dot {
  display: inline-block;
  width: 7px; height: 7px;
  border-radius: 50%;
  margin-left: 5px;
  background: transparent;
  vertical-align: middle;
}
.nav-alert-dot.lvl-3 { background: #f0a840; }
.nav-alert-dot.lvl-4 { background: #e07840; }
.nav-alert-dot.lvl-5 { background: #e05c5c; }
```

**Step 5: Add `updateNavAlertDot(maxLevel)` in `app.js`**

```js
function updateNavAlertDot(maxLevel) {
  const dot = document.getElementById('nav-alert-dot');
  if (!dot) return;
  dot.classList.remove('lvl-1','lvl-2','lvl-3','lvl-4','lvl-5');
  if (maxLevel >= 3) dot.classList.add(`lvl-${maxLevel}`);
}
```

Call from `render()` with the highest severity level across active alerts.

**Step 6: Verify**

Gauge cards show graduated color. Nav dot appears only when severity ≥ 3.

**Step 7: Commit**
```bash
git add web/templates/dashboard.html web/static/style.css web/static/app.js
git commit -m "feat(ux): enforce semantic color scale on gauges and nav alert dot"
```

---

## Task 14 — Reduce Animation for Reduced Motion *(UX #7)*

**Files:**
- Modify: `web/static/style.css`

**Step 1: Inventory all animations and transitions**

Run:
```powershell
Select-String -Path web/static/style.css -Pattern "animation|transition" | Select-Object LineNumber, Line
```

**Step 2: Wrap bare animation/transition rules**

For every `animation` or `transition` property that is NOT already inside a `prefers-reduced-motion` query, move it inside:
```css
@media (prefers-reduced-motion: no-preference) {
  /* selector { animation / transition goes here } */
}
```

Remove any existing `@media (prefers-reduced-motion: reduce)` override blocks — they become unnecessary once the guard pattern is used.

**Step 3: Verify**

In Chrome DevTools → Rendering → "Emulate CSS media feature prefers-reduced-motion: reduce". All transitions and animations should freeze. Interactions (hover states that use `background` changes without `transition`) may remain.

**Step 4: Commit**
```bash
git add web/static/style.css
git commit -m "feat(ux): guard all animations with prefers-reduced-motion: no-preference"
```

---

## Task 15 — Typography Hierarchy Refinement *(UX #8)*

**Files:**
- Modify: `web/static/style.css`
- Modify: `web/templates/dashboard.html` (add Google Fonts link if not present)

**Step 1: Add Fira Code to Google Fonts import**

If not already imported, add to the top of `style.css` (or in `<head>`):
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
```

**Step 2: Add type-scale CSS vars**

In `:root`:
```css
--text-hero:    2rem;
--text-section: 1.2rem;
--text-label:   0.78rem;
--font-mono:    'Fira Code', 'Courier New', monospace;
```

**Step 3: Apply scale**

```css
/* Section headings */
h2, .section-title {
  font-size: var(--text-section);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-secondary, #aaa);
}

/* Gauge numeric values */
.gauge-value, .metric-value {
  font-family: var(--font-mono);
  font-size: 1.6rem;
  font-weight: 500;
}

/* Gauge labels and units */
.gauge-label, .metric-unit {
  font-size: var(--text-label);
  color: var(--text-secondary, #aaa);
}
```

> **Note:** Search `style.css` for existing selectors before adding. Prefer adding `font-family` / `font-size` to existing rules rather than duplicating selectors.

**Step 4: Verify**

Section headings have uppercase tracking. Gauge numbers render in Fira Code monospace. Labels are visually subordinate.

**Step 5: Commit**
```bash
git add web/templates/dashboard.html web/static/style.css
git commit -m "feat(ux): apply type-scale vars and Fira Code to gauge numerics"
```

---

## Task 16 — Optimistic Refresh UI *(UX #9)*

**Files:**
- Modify: `web/templates/dashboard.html`
- Modify: `web/static/style.css`
- Modify: `web/static/app.js`

**Step 1: Add refreshing badge HTML**

Inside `.sidebar-status`, after `#rp-last-updated`:
```html
<span class="refreshing-badge" id="refreshing-badge">Refreshing…</span>
```

**Step 2: Add refreshing badge CSS**

```css
.refreshing-badge {
  display: none;
  align-items: center;
  font-size: 0.72rem;
  color: var(--text-secondary, #aaa);
  background: var(--border-color, rgba(255,255,255,0.08));
  padding: 2px 8px;
  border-radius: 99px;
}
.refreshing-badge.visible { display: inline-flex; }
```

**Step 3: Modify refresh trigger in `app.js`**

Find the function that fires when `#refresh-btn` is clicked (or the data fetch is triggered). At the top of that function:
```js
document.getElementById('refreshing-badge')?.classList.add('visible');
// Do NOT call showLoading() here if data is already rendered — only on cold start
```

**Step 4: Hide badge in `render()`**

At the top of `render()` (before data is applied to DOM):
```js
document.getElementById('refreshing-badge')?.classList.remove('visible');
```

**Step 5: Guard `showLoading()` calls**

Find `showLoading()` (or equivalent). Ensure it is called only when no data has been rendered yet (e.g., `if (!window._hasRenderedOnce) showLoading()`). Set `window._hasRenderedOnce = true` at the end of the first `render()` call.

**Step 6: Verify**

Cold start: loading screen shows normally. Clicking Refresh: badge appears on timestamp, existing content stays visible, content swaps in-place on response.

**Step 7: Commit**
```bash
git add web/templates/dashboard.html web/static/style.css web/static/app.js
git commit -m "feat(ux): optimistic refresh – keep stale data visible while fetching"
```

---

## Task 17 — Micro-interaction on Nav Switching *(UX #10)*

**Files:**
- Modify: `web/static/style.css`
- Modify: `web/static/app.js`

**Step 1: Add transition CSS**

```css
@media (prefers-reduced-motion: no-preference) {
  .view-container {
    transition: opacity 150ms ease, transform 150ms ease;
  }
  .view-container.slide-out-left  { opacity: 0; transform: translateX(-20px); }
  .view-container.slide-out-right { opacity: 0; transform: translateX(20px); }
  .view-container.slide-in-left   { opacity: 0; transform: translateX(-20px); }
  .view-container.slide-in-right  { opacity: 0; transform: translateX(20px); }
}
```

**Step 2: Update `switchView()` in `app.js`**

Find the nav-switching function (likely wired to `.nav-item` click). Define tab order:
```js
const TAB_ORDER = ['lifestyle', 'dashboard']; // left to right
```

On switch, determine direction (going right = new tab index > current), then:
```js
function switchView(newId) {
  const currentEl = document.querySelector('.view-container.active');
  const newEl     = document.getElementById(`view-${newId}`);
  if (!currentEl || !newEl || currentEl === newEl) return;

  const oldIdx = TAB_ORDER.indexOf(currentEl.id.replace('view-',''));
  const newIdx = TAB_ORDER.indexOf(newId);
  const goingRight = newIdx > oldIdx;

  currentEl.classList.add(goingRight ? 'slide-out-left' : 'slide-out-right');

  setTimeout(() => {
    currentEl.classList.remove('active', 'slide-out-left', 'slide-out-right');
    newEl.classList.add('active', goingRight ? 'slide-in-right' : 'slide-in-left');
    // trigger reflow
    newEl.getBoundingClientRect();
    newEl.classList.remove('slide-in-left', 'slide-in-right');
  }, 150);
}
```

> **Note:** If `switchView` already exists with different logic, adapt directional classes into it rather than rewriting. Do not break existing tab state management.

**Step 3: Verify**

Click Lifestyle → Dashboard: content slides left. Click Dashboard → Lifestyle: content slides right. With reduced-motion emulated: instant switch, no animation.

**Step 4: Commit**
```bash
git add web/static/style.css web/static/app.js
git commit -m "feat(ux): directional slide transition on view switching"
```

---

## Task 18 — Fix 7-Day Forecast Dataset ID

**Files:**
- Modify: `config.py`
- Modify: `docs/API_QUIRKS.md`
- Modify: `data/fetch_cwa.py`

**Step 1: Update config.py**

Find:
```python
CWA_FORECAST_7DAY_DATASET = "F-D0047-069" # New Taipei City Township Forecast (7-day)
```

Replace with:
```python
CWA_FORECAST_7DAY_DATASET = "F-D0047-075"  # the correct 7-day one for New Taipei
```

**Step 2: Update fetch_cwa.py fallback**

Find:
```python
CWA_FORECAST_7DAY_DATASET = getattr(config, "CWA_FORECAST_7DAY_DATASET", "F-D0047-069")
```

Replace with:
```python
CWA_FORECAST_7DAY_DATASET = getattr(config, "CWA_FORECAST_7DAY_DATASET", "F-D0047-075")
```

**Step 3: Update API_QUIRKS.md**

Update the documentation to clarify that `069` is for 72-hour hourly forecasts, `073` is weekly string descriptions, and `075` is the correct 7-day timeline forecast.

**Step 4: Verify**

Run the backend and check the payload for `/api/broadcast`. The `weekly_timeline` array in the `overview` slice should now contain 14-15 items (7 days of Day/Night slots) instead of just 5-8.

**Step 5: Commit**
```bash
git add config.py data/fetch_cwa.py docs/API_QUIRKS.md
git commit -m "fix: correct 7-day forecast dataset ID from 069 to 075"
```

---

## Task 19 — Investigate and Fix Missing 7-Day Forecast Data

**Goal:** Identify why `forecast_7day` is missing from the processed API payload, which causes the frontend to display an empty 7-day forecast.

**Files:**
- Modify: `data/weather_processor.py`
- Modify: `data/fetch_cwa.py`

**Step 1: Audit `data/weather_processor.py`**
Inspect the `process()` function to verify how `forecasts_7day` is handled. Ensure that the 7-day forecast data is correctly mapped and appended to `processed["forecast_7day"]` so that it reaches `web/routes.py`.

**Step 2: Audit `data/fetch_cwa.py`**
Inspect `fetch_all_forecasts_7day()` to ensure that the API fetch is successfully returning data and that the structure matches the expectations of `weather_processor.py`.

**Step 3: Implement Fix**
Correct any mismatches, key errors, or omission logic in the data processing flow. 

**Step 4: Verify**
Restart the backend server. Trigger a `/api/broadcast` fetch or force a refresh and verify that `processed.get("forecast_7day")` is a populated list and the UI renders the 7-day weekly grid cards.

**Step 5: Commit**
```bash
git add data/weather_processor.py data/fetch_cwa.py
git commit -m "fix: resolve missing 7-day forecast data in API payload"
```
