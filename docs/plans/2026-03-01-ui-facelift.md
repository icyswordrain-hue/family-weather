# UI Facelift Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Resize text in dashboard/lifestyle cards, enlarge narration text, remove the progress bar from inside the player sheet and from the bottom player bar, and surface the speed control in the bottom bar on both breakpoints.

**Architecture:** Changes span `web/static/style.css` (font sizes, `display:none` rules) and `web/templates/dashboard.html` (remove `ps-progress-wrap` block from the sheet; make `player-speed-btn` always visible on mobile).

**Tech Stack:** Vanilla CSS + HTML; mobile breakpoint `@media (max-width: 767px)`; desktop = base styles.

---

## Task 1: Mobile — Slightly Larger Dashboard Card Text

**Files:**
- Modify: `web/static/style.css` (inside `@media (max-width: 767px)`, lines ~1606–1627)

Current mobile gauge sizes:  
`.gauges-grid .gauge-label` `0.65rem` → **`0.75rem`**  
`.gauges-grid .gauge-value` `1rem` → **`1.15rem`**  
`.gauges-grid .gauge-sub` `0.65rem` → **`0.75rem`**  
`.current-top-row .gauge-label` `0.7rem` → **`0.78rem`**  
`.current-top-row .gauge-value` `1rem` → **`1.15rem`**  
`.current-top-row .gauge-sub` `0.7rem` → **`0.78rem`**  

**Step 1: Edit the six size values inside the mobile block**

```css
/* Inside @media (max-width: 767px) */
.current-top-row .gauge-label { font-size: 0.78rem; }
.current-top-row .gauge-value { font-size: 1.15rem; }
.current-top-row .gauge-sub   { font-size: 0.78rem; }

.gauges-grid .gauge-label { font-size: 0.75rem; }
.gauges-grid .gauge-value { font-size: 1.15rem; }
.gauges-grid .gauge-sub   { font-size: 0.75rem; }
```

**Step 2: Commit**
```
git add web/static/style.css
git commit -m "feat(mobile): slightly larger dashboard card text"
```

---

## Task 2: Mobile — 2-size Larger Player Sheet Narration Text at 80% Width

**Files:**
- Modify: `web/static/style.css` (inside `@media (max-width: 767px)`)

The sheet narration body is `.player-sheet-body` (`0.88rem`, lines ~2138–2145) and individual paragraphs are `.ps-para-body` (`0.9rem`, lines ~2164–2170).

**Step 1: Override inside mobile block**

```css
@media (max-width: 767px) {
  .player-sheet {
    height: 80vh;           /* was 78vh */
  }

  .player-sheet-body {
    font-size: 1.2rem;      /* was 0.88rem */
  }

  .ps-para-body {
    font-size: 1.2rem;      /* was 0.9rem */
    line-height: 1.75;
  }

  /* Constrain sheet text to 80% width, centred */
  #ps-narration-content {
    width: 80%;
    margin: 0 auto;
  }
}
```

**Step 2: Commit**
```
git add web/static/style.css
git commit -m "feat(mobile): 2-size larger narration text in player sheet"
```

---

## Task 3: Mobile — Remove Progress Bar from Player Bar; Show Speed Button

**Context:** The bottom player bar on mobile currently hides `.player-speed-btn` (line ~1521). We just remove that hide rule so the speed button appears. The `.player-progress-wrap` is removed globally in Task 5; this task only undoes the mobile speed-btn hide.

**Files:**
- Modify: `web/static/style.css` (inside `@media (max-width: 767px)`, line ~1521)

**Step 1: Remove the `player-speed-btn` hide from the mobile block**

```css
/* BEFORE */
.player-speed-btn,
.player-sheet-toggle {
  display: none;
}

/* AFTER — keep hiding the sheet toggle arrow, but show speed btn */
.player-sheet-toggle {
  display: none;
}
```

**Step 2: Commit**
```
git add web/static/style.css
git commit -m "feat(mobile): show speed button in slim player bar"
```

---

## Task 4: Desktop — Slightly Smaller Lifestyle Card Text

**Files:**
- Modify: `web/static/style.css` (base rules, lines ~894–911)

Current values:  
`.ls-title` `0.9rem` → **`0.82rem`**  
`.ls-text` `0.85rem` → **`0.78rem`**  
`.ls-sub` `0.82rem` → **`0.75rem`**

**Step 1: Edit the three ls-card text rules**

```css
.ls-title {
  font-size: 0.82rem;   /* was 0.9rem */
}

.ls-text {
  font-size: 0.78rem;   /* was 0.85rem */
}

.ls-sub {
  font-size: 0.75rem;   /* was 0.82rem */
}
```

**Step 2: Commit**
```
git add web/static/style.css
git commit -m "feat(desktop): slightly smaller lifestyle card text"
```

---

## Task 5: Desktop — 2-size Larger Player Sheet Narration Text

**Files:**
- Modify: `web/static/style.css` (base rules)

`.player-sheet-body` `0.88rem` → **`1.1rem`** (base, ~line 2140)  
`.ps-para-body` `0.9rem` → **`1.2rem`** (~line 2165)

**Step 1: Edit base rules**

```css
.player-sheet-body {
  font-size: 1.1rem;    /* was 0.88rem */
}

.ps-para-body {
  font-size: 1.2rem;    /* was 0.9rem */
  line-height: 1.7;
}
```

**Step 2: Commit**
```
git add web/static/style.css
git commit -m "feat(desktop): 2-size larger narration text in player sheet"
```

---

## Task 6: Both — Remove Progress Bar from Player Sheet & Player Bar

**Context:** The "top player" = the `ps-progress-wrap` block inside the player sheet (dashboard.html lines 230–232). The bottom player bar also has a `player-progress-wrap`. Both should be hidden/removed.

**Files:**
- Modify: `web/templates/dashboard.html` — remove `ps-progress-wrap` HTML block
- Modify: `web/static/style.css` — hide `player-progress-wrap` on both sizes

**Step 1: Delete the `ps-progress-wrap` block from HTML**

In `dashboard.html` lines 230–232, remove:
```html
<div class="ps-progress-wrap" id="ps-progress-wrap">
  <div class="ps-progress-bar" id="ps-progress-bar"></div>
</div>
```

> **Note:** `ps-progress-bar` is referenced in `app.js` via `getElementById`. After removal, those JS lines will silently no-op (they already null-guard). Confirm the `if (sheetBar)` guard exists at lines ~1062–1064 of app.js — it does.

**Step 2: Hide the bottom player bar progress wrap via CSS**

```css
/* Global — applies to both mobile and desktop */
.player-progress-wrap {
  display: none;
}

/* Let duration fill the freed space */
.player-duration {
  flex: 1;
}
```

**Step 3: Commit**
```
git add web/static/style.css web/templates/dashboard.html
git commit -m "feat(both): remove progress bars from player sheet and player bar"
```

---

## Verification Plan

### Manual — Browser DevTools

Run the app:
```powershell
.\run_local.ps1
```
Then open `http://localhost:5000` in a browser.

**Desktop (>767px):**
1. Lifestyle view → lifestyle cards should be visibly more compact text than before
2. Open the player sheet (▲ toggle) → transcript text should be noticeably larger (1.2rem body)
3. Player bar at bottom → NO progress bar; play/pause on left, duration in middle, speed button, sheet toggle
4. Player bar at bottom → NO thin `ps-progress-wrap` above the transcripts in the sheet

**Mobile (≤767px, DevTools device mode at 375px):**
1. Dashboard view → gauge labels/values should be slightly larger than before
2. Open the player sheet (tap anywhere on slim bar) → text should be large (1.2rem), centred, ~80% width
3. Player bar → NO progress bar; play/pause + duration + speed button all visible in the 42px bar
4. Sheet header → the `ps-progress-wrap` block is gone entirely

**Dark mode:** Toggle and spot-check — no contrast regressions expected.

### No automated tests cover CSS/HTML structure. Visual-only.

---

## Part 2 — Further UI Improvements (2026-03-01)

**Goal:** Taller 7-day forecast cards, player sheet at 90% of visible screen, and keep the audio player bar interactive when the sheet is open (both breakpoints).

**Architecture:** All changes in `web/static/style.css` only — no HTML or JS changes.

**Root cause (player bar blocked):** The backdrop (`z-index: 199`) had `bottom: 0`, extending over the player bar (`z-index: 150`). Fix: set `bottom` on the backdrop to the player bar height per breakpoint.

---

### Task 7: Desktop — Taller 7-Day Forecast Cards

**Files:** `web/static/style.css` (base rules)

| Selector | Property | From | To |
|---|---|---|---|
| `.wk-card` | padding | `8px 6px` | `14px 8px` |
| `.wk-card` | gap | `2px` | `4px` |
| `.wk-col-header` | font-size | `0.65rem` | `0.75rem` |
| `.wk-icon` | font-size | `1.4rem` | `1.7rem` |
| `.wk-temp` | font-size | `1.1rem` | `1.35rem` |
| `.wk-cond` | font-size | `0.6rem` | `0.72rem` |
| `.wk-rain` | font-size | `0.7rem` | `0.85rem` |

```
git commit -m "feat(desktop): taller 7-day forecast cards with larger text"
```

---

### Task 8: Desktop — Player Sheet at 90% of Visible Screen

**Files:** `web/static/style.css` (base `.player-sheet`)

`.player-sheet` `height: 60vh` → **`height: calc(90vh - 78px)`**

Sheet bottom stays at 78px (above player bar); top sits at ~10% from viewport top.

```
git commit -m "feat(desktop): expand player sheet to 90% of visible screen"
```

---

### Task 9: Desktop — Keep Player Bar Interactive When Sheet Is Open

**Files:** `web/static/style.css` (base `.player-sheet-backdrop`)

`.player-sheet-backdrop` `bottom: 0` → **`bottom: 78px`**

Backdrop no longer covers the player bar area.

```
git commit -m "feat(desktop): keep player bar interactive when sheet is open"
```

---

### Task 10: Mobile — Player Sheet at 90% of Visible Screen

**Files:** `web/static/style.css` (inside `@media (max-width: 767px)`)

`.player-sheet` `height: 80vh` → **`height: calc(90vh - 42px)`**

```
git commit -m "feat(mobile): expand player sheet to 90% of visible screen"
```

---

### Task 11: Mobile — Keep Player Bar Interactive When Sheet Is Open

**Files:** `web/static/style.css` (inside `@media (max-width: 767px)`)

Add `bottom: 42px` to the `.player-sheet-backdrop` mobile override.

```
git commit -m "feat(mobile): keep player bar interactive when sheet is open"
```

---

### Verification (Part 2)

**Desktop (>767px):**
1. Weekly forecast section → cards noticeably taller; temp/icon/condition text larger
2. Open player sheet (▲) → sheet fills ~90% of viewport, ~10% of content visible above
3. With sheet open → click play/pause and speed button → both respond (backdrop no longer blocks bar)

**Mobile (≤767px, DevTools 375px):**
1. Open player sheet (tap bar) → sheet fills ~90% of viewport, 10% visible above
2. With sheet open → tap play/pause → responds normally (backdrop stops at 42px bar)

---

## Part 3 — Player Sheet Polish (2026-03-01)

**Goal:** Clean up the player sheet on both breakpoints: hide redundant UI on desktop, add two-column narration layout, reduce text to match card density, widen the content area, enlarge mobile tab targets, and fix a CSS cascade bug that was silently hiding the tab row on mobile.

**Architecture:** All changes in `web/static/style.css` only.

---

### Task 12: Desktop — Hide Redundant Controls Row

`.ps-controls { display: none; }` in base styles. The duration and speed controls are now always accessible in the always-interactive player bar (fixed in Part 2).

```
feat(desktop): hide redundant controls row in player sheet
```

---

### Task 13: Desktop — Two-Column Narration Layout (≥1280px)

Added `@media (min-width: 1280px)` block:

```css
#ps-narration-content { column-count: 2; column-gap: 2.5rem; }
.ps-para { break-inside: avoid; }
```

Columns only activate at ≥1280px to avoid cramped layout at 1024px.

```
feat(desktop): two-column narration layout in player sheet (>=1280px)
```

---

### Task 14: Desktop — Hide Tab Row; Controls Hidden on All Breakpoints

- `.player-sheet-tabs` hidden via `@media (min-width: 768px) { display: none; }` — tabs are mobile-only; desktop shows narration directly
- Removed the earlier mobile `.ps-controls { display: block; }` restore (controls hidden everywhere at this point; later reversed in Task 16)

```
feat(desktop): hide tab row; hide sheet controls on all breakpoints
```

---

### Task 15: Desktop — Reduce Narration Text; 90% Content Width

Narration text reduced to match lifestyle card density:

| Selector | Property | From | To |
|---|---|---|---|
| `.ps-para-title` | font-size | `0.72rem` | `0.88rem` (larger than body) |
| `.ps-para-body` | font-size | `1.2rem` | `0.78rem` (matches `.ls-text`) |
| `#ps-narration-content` | width | (none) | `90%; margin: 0 auto` |

```
feat(desktop): reduce narration text to match lifestyle cards; 90% content width
```

---

### Task 16: Mobile — Wider Content; Larger Tab Targets; Restore Controls

- `#ps-narration-content` mobile width: `80%` → `90%`
- `.ps-tab` mobile: `padding: 10px 18px; font-size: 1rem`
- `.ps-controls { display: block; }` restored in mobile block

```
feat(mobile): wider narration content and larger tab touch targets
feat(mobile): restore controls row in player sheet
```

---

### Task 17: Fix — Restore Tab Row on Mobile (CSS Cascade Bug)

**Bug:** `.player-sheet-tabs { display: none; }` (Task 14) was declared as a base rule at line ~2422, *after* the mobile `display: flex` override at line ~1552. In CSS, equal-specificity rules resolve by file order — the later base rule silently won on mobile, hiding the tabs.

**Fix:** Wrapped the hide in `@media (min-width: 768px)` so it only applies on desktop. Removed the now-redundant mobile `display: flex` override.

**Also enlarged mobile tab row:**
- `.player-sheet-header` mobile: `padding: 14px 16px`
- `.ps-tab` mobile: `padding: 12px 22px; font-size: 1.05rem`

```
fix(mobile): restore tab row and enlarge touch targets in player sheet
```

---

### Verification (Part 3)

**Desktop (>767px):**
1. Open player sheet → no controls row (duration/speed hidden); no tab bar
2. Narration text at ~0.78rem body / 0.88rem headings; content centred at 90% width
3. At ≥1280px → text flows in two columns

**Mobile (≤767px, DevTools 375px):**
1. Open player sheet → tab bar visible (Narration / Settings); tabs are tall and easy to tap
2. Narration panel → controls row (duration + speed pills) visible above text
3. Content centred at 90% width
