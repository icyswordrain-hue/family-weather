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
