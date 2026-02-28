# Player — Mobile UI Redesign (Slim Bar + Tabbed Sheet)

**Date:** 2026-02-28
**Status:** Implemented

## Problem

The mobile player bar was a single cramped row — five controls in 78px height across a 375px screen. The progress bar got only ~110px of usable space, touch targets were too tight, and a separate FAB (⚙️ gear) opened a competing settings half-sheet (z-index 170), creating two independent overlay layers that could conflict.

| Issue | Detail |
|---|---|
| Cramped progress bar | ~110px available after controls consumed available space |
| Tight touch targets | Speed pill and sheet toggle near screen edge |
| Two overlay layers | FAB sheet (z-170) and player sheet (z-200) both floated independently |
| Emoji icon | `⚙️` renders inconsistently across Android/iOS/Windows |
| No scrubbing | Sheet had no progress bar — no way to seek without closing overlay |

## Design Decision

**Option B (Slim bar + richer sheet)** was chosen over:
- Option A (two-row stack) — taller bar, needs FAB `bottom` adjustment
- Option C (floating card) — most FAB conflict (both elements occupy same vertical zone)

Option B had the least FAB conflict: at `bottom: 68px`, the FAB already clears a 42px bar by 26px. The FAB was then **eliminated entirely** by merging settings into a new Settings tab inside the player sheet.

## Changes

### `web/templates/dashboard.html`

**Sheet toggle — SVG chevron replaces `⌄` character**

```html
<button class="player-sheet-toggle" id="player-sheet-toggle" aria-label="Show transcript">
  <svg width="22" height="22" viewBox="0 0 20 20" fill="none"
       stroke="currentColor" stroke-width="2"
       stroke-linecap="round" stroke-linejoin="round">
    <polyline points="4,7 10,13 16,7"/>
  </svg>
</button>
```

Stroke-based, `22×22`, same `viewBox="0 0 20 20"` as the play/pause button. Lighter weight than the filled polygon play icon. Existing `.player-sheet-toggle.open { transform: rotate(180deg) }` handles the animated flip with no CSS changes needed.

**Player sheet header — tabbed**

Replaced the static `<span class="player-sheet-title">` with a tab bar:

```html
<div class="player-sheet-header">
  <div class="player-sheet-tabs">
    <button class="ps-tab active" data-tab="narration" data-i18n="tab_narration">Narration</button>
    <button class="ps-tab" data-tab="settings" data-i18n="tab_settings">Settings</button>
  </div>
  <button class="player-sheet-close" id="player-sheet-close" aria-label="Close">✕</button>
</div>
```

**Narration tab panel** — adds in-sheet playback controls (full-width scrub bar + speed pills) above the narration paragraphs:

```
[===================progress bar===================]
0:12 / 1:45               [1.0×]  [1.2×]  [1.5×]
───────────────────────────────────────────────────
(narration paragraphs)
```

Narration content now renders into `#ps-narration-content` (child div) instead of directly into `#player-sheet-body`.

**Settings tab panel** — Language + Provider segmented controls + Refresh button, migrated from the removed FAB sheet.

**FAB block removed** — `<button class="fab-btn">`, `.fab-sheet`, `.fab-backdrop` deleted entirely.

---

### `web/static/style.css`

**Mobile player bar — slimmed (42px)**

```css
@media (max-width: 767px) {
  .player-bar {
    height: 42px;          /* was 78px */
    gap: 10px;             /* was 15px */
    padding: 0 14px;       /* was 0 20px */
    cursor: pointer;       /* entire bar tappable on mobile */
  }
  .player-speed-btn,
  .player-sheet-toggle { display: none; }   /* live in sheet on mobile */
  .player-duration { min-width: auto; font-size: 0.95rem; }
  .main-panel { padding-bottom: 62px; }     /* was 98px */
}
```

**Sheet tabs**

```css
.player-sheet-tabs { display: flex; gap: 4px; flex: 1; }
.ps-tab { background: none; border: none; color: var(--muted); padding: 5px 12px; border-radius: 6px; font-weight: 600; }
.ps-tab.active { background: var(--blue-lt); color: var(--blue); }
```

Dark mode: active tab uses `rgba(77, 124, 254, 0.18)` background and `#7da4ff` text — matches the existing dark-mode pill pattern.

**In-sheet controls**

- `.ps-progress-wrap` — 6px track with `padding: 10px 0` for a larger click/tap target (44px effective hit area)
- `.ps-controls-row` — flex row: duration left, speed pills right
- `.ps-speed-pill` — pill buttons matching `.player-speed-btn` style; `.active` uses `var(--blue-lt)` / `var(--blue)`
- `.ps-tab-panel` — `padding: 14px 16px`

**Settings tab — light-surface overrides for dark-sidebar seg-ctrl**

The `.seg-ctrl` component was designed for the dark sidebar. Added scoped overrides under `.ps-tab-panel`:

```css
.ps-tab-panel .seg-ctrl { background: var(--border); }
.ps-tab-panel .seg-option span { color: var(--muted); }
```

**`player-sheet-header`** — updated to `flex` with `gap: 8px` to accommodate the tab bar alongside the close button.

**`player-sheet-body`** — changed to `padding: 0; flex: 1` (padding moved to `.ps-tab-panel`) so tabs can have consistent inset without double-padding.

**Player sheet toggle** — removed `font-size: 1.6rem` (was sizing the unicode character), added `display: flex; align-items: center; justify-content: center` for SVG alignment.

**All `.fab-*` CSS removed** — `.fab-btn`, `.fab-sheet`, `.fab-backdrop`, associated overrides and `@media` show rule.

---

### `web/static/app.js`

**`initPlayerBar()` — speed pill sync and seek**

- `applySpeed(s)` now also syncs sheet speed pills: toggles `.active` class on `.ps-speed-pill[data-speed]`
- Sheet speed pills wired: `document.querySelectorAll('.ps-speed-pill').forEach(pill => pill.addEventListener('click', ...))`
- Desktop speed button click uses `e.stopPropagation()` to prevent triggering bar tap
- Play button click uses `e.stopPropagation()` for the same reason
- `timeupdate` listener syncs `#ps-progress-bar` width and `#ps-duration` text in the sheet
- `loadedmetadata` listener also updates `#ps-duration`
- `#ps-progress-wrap` click handler: seeks by ratio `(e.clientX - rect.left) / rect.width`
- Mobile bar tap: `bar.addEventListener('click', ...)` — only fires sheet open when `matchMedia('(max-width: 767px)')` and sheet is not already open
- `_playerBarSetAudio` now writes to `#ps-narration-content` (not `#player-sheet-body`)

**`initPlayerSheet()` — tab switching added**

```js
document.querySelectorAll('.ps-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const target = tab.dataset.tab;
    // toggle .active on tabs, toggle hidden on panels
  });
});
```

Toggle button and close button clicks use `e.stopPropagation()` to prevent triggering the bar's tap listener.

**`initFAB()` → replaced with `initSheetSettings()`**

| Old | New |
|---|---|
| `input[name="language-fab"]` | `input[name="language-sheet"]` |
| `input[name="provider-fab"]` | `input[name="provider-sheet"]` |
| `#fab-refresh-btn` | `#sheet-refresh-btn` |
| Closes FAB sheet before refresh | Closes player sheet (`#player-sheet-close` click) before refresh |
| Sync init: `language-fab` / `provider-fab` | Sync init: `language-sheet` / `provider-sheet` |

Boot call updated: `initFAB()` → `initSheetSettings()`.

**i18n keys added** — in both `en` and `zh-TW` translation objects:

| Key | EN | 中文 |
|---|---|---|
| `tab_narration` | `Narration` | `解說` |
| `tab_settings` | `Settings` | `設定` |

---

## Architecture Notes

**Single overlay layer** — the FAB's sheet (z-170) and backdrop are gone. Only one sheet layer remains (player sheet z-200 + backdrop z-199), reducing overlay complexity.

**Scrub bar in both places** — the bar-level progress bar (`#player-progress-bar`) and the sheet's scrub bar (`#ps-progress-bar`) both update from the same `timeupdate` listener. Seeking via the sheet bar updates `audio.currentTime` directly, which immediately fires `timeupdate` and syncs both bars.

**Speed state ownership** — speed state (`let speed`) lives inside `initPlayerBar()` closure. The desktop button, sheet pills, and localStorage all read/write through `applySpeed()`.

**Sidebar sync pattern** — sheet language/provider radios delegate to sidebar radios via `dispatchEvent(new Event('change', { bubbles: true }))`, so all existing state management in `initSidebarControls` runs unchanged.

---

## Behaviour

| Scenario | Result |
|---|---|
| Mobile, player bar visible | 42px bar: play/pause + progress + elapsed time only |
| Tap player bar (mobile) | Sheet slides up to 78vh |
| Tap ⌄ toggle (desktop) | Sheet slides up to 60vh |
| Sheet Narration tab | Full scrub bar + speed pills + narration text |
| Sheet Settings tab | Language + Provider seg controls + Refresh |
| Change language in sheet | Mirrors to sidebar radio → applies language |
| Change provider in sheet | Mirrors to sidebar radio → triggers refresh |
| Tap Refresh in sheet | Closes sheet, fires sidebar refresh button |
| Speed pills | Active pill highlighted in blue; persists to localStorage |
| Dark mode | Tabs, pills, sheet content all render correctly |

## Files Modified

| File | Change |
|---|---|
| `web/templates/dashboard.html` | SVG chevron, tabbed sheet header, narration/settings panels, FAB removed |
| `web/static/style.css` | 42px mobile bar, tab styles, speed pills, ps-controls, light-surface overrides, FAB CSS removed |
| `web/static/app.js` | Speed pill sync, sheet scrub bar, bar tap-to-open, tab switching, `initSheetSettings`, i18n keys |
