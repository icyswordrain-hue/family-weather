# Inline Temperature Range Bars Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the separate Chart.js temperature sparkline with inline CSS linear-gradient range bars embedded directly inside each day's forecast card.

**Architecture:** Remove the Chart.js dependency and canvas element from the DOM and JS. Calculate the absolute 7-day minimum and maximum temperatures during the weekly timeline iteration. For each day, calculate the relative left offset and width of its min/max temperature span. Render a thin horizontal `div` inside each `wk-card` using a `linear-gradient` from blue (cool) to amber (warm) sized and positioned proportionally across the 7-day continuum.

**Tech Stack:** Vanilla JavaScript (DOM manipulation), Vanilla CSS (gradients, flexbox, variables)

---

### Task 1: Clean up DOM and Chart.js instantiation

**Files:**
- Modify: `web/static/index.html` (if applicable, though canvas might be hardcoded or injected)
- Modify: `web/static/app.js`

**Step 1: Write the failing test**

*(We are modifying core UI rendering, so our "test" is verifying the canvas creation code is removed).*
Run: `grep -n "tempChart = new Chart" web/static/app.js`
Expected: FAIL (no output after change)

**Step 2: Write minimal implementation**

```javascript
// In web/static/app.js `renderOverviewView`

<<<<
    // 7-Day temperature sparkline (day = amber, night = blue)
    const sparkCanvas = document.getElementById('ov-weekly-sparkline');
    if (sparkCanvas) {
      // Build chart data directly from the rendered columns to guarantee perfect sync
====
    // Calculate global 7-day min and max for inline range bars
    let globalMin = Infinity;
    let globalMax = -Infinity;
    
    [...dayItems, ...nightItems].forEach(item => {
        if(item && item.AT != null) {
            globalMin = Math.min(globalMin, item.AT);
            globalMax = Math.max(globalMax, item.AT);
        }
    });
>>>>
```

Also remove the entire `if (sparkCanvas) { ... }` block surrounding the Chart.js instantiation (lines 750-899).

**Step 3: Run test to verify it passes**

Run: `grep -n "tempChart = new Chart" web/static/app.js`
Expected: PASS (no output)

**Step 4: Commit**

```bash
git add web/static/app.js
git commit -m "refactor(ui): remove Chart.js sparkline instantiation"
```

### Task 2: Inject Inline Range Bars into Weekly Cards

**Files:**
- Modify: `web/static/app.js`

**Step 1: Write the failing test**

Run: `grep -n "wk-range-bar" web/static/app.js`
Expected: FAIL (no output)

**Step 2: Write minimal implementation**

Inside the weekly timeline iteration loop in `web/static/app.js`:

```javascript
<<<<
      const temp = document.createElement('div');
      temp.className = 'wk-temp';
      temp.textContent = `${Math.round(item.AT ?? 0)}°`;

      card.appendChild(label);
      card.appendChild(icon);
      card.appendChild(cond);
      card.appendChild(temp);
      weeklyTimelineEl.appendChild(card);
====
      const temp = document.createElement('div');
      temp.className = 'wk-temp';
      temp.textContent = `${Math.round(item.AT ?? 0)}°`;

      const rangeContainer = document.createElement('div');
      rangeContainer.className = 'wk-range-container';
      
      const rangeBar = document.createElement('div');
      rangeBar.className = 'wk-range-bar';
      
      if (globalMax > globalMin && item.AT != null) {
          // Calculate span - placeholder 15% width for now, centered on the temp
          const tempVal = item.AT;
          const rangeSpan = globalMax - globalMin;
          const relativePos = Math.max(0, Math.min(100, ((tempVal - globalMin) / rangeSpan) * 100));
          
          // Center a 15% wide pill around the relative temperature point
          const leftPos = Math.max(0, relativePos - 7.5);
          rangeBar.style.left = `${leftPos}%`;
          rangeBar.style.width = '15%';
          
          // Colour gradient based on relative warmth
          const isCool = tempVal < 20;
          rangeBar.style.background = isCool ? 'linear-gradient(90deg, #7da4ff, #a4c2f4)' : 'linear-gradient(90deg, #f39c12, #f1c40f)';
      }

      rangeContainer.appendChild(rangeBar);

      card.appendChild(label);
      card.appendChild(icon);
      card.appendChild(cond);
      card.appendChild(rangeContainer);
      card.appendChild(temp);
      weeklyTimelineEl.appendChild(card);
>>>>
```

**Step 3: Run test to verify it passes**

Run: `grep -n "wk-range-bar" web/static/app.js`
Expected: PASS (returns line numbers)

**Step 4: Commit**

```bash
git add web/static/app.js
git commit -m "feat(ui): inject wk-range-bar DOM nodes into daily forecast cards"
```

### Task 3: Style the Inline Range Bars

**Files:**
- Modify: `web/static/style.css`

**Step 1: Write the failing test**

Run: `grep -n ".wk-range-container" web/static/style.css`
Expected: FAIL (no output)

**Step 2: Write minimal implementation**

Append to `web/static/style.css` (near other `.wk-` classes or at bottom of section):

```css
<<<<
/* ── AQI Forecast block (#10) ────────────────────────────────────────────── */
====
.wk-range-container {
  width: 100%;
  height: 6px;
  background: rgba(127, 140, 160, 0.15);
  border-radius: 3px;
  margin: 0.5rem 0;
  position: relative;
  overflow: hidden;
}

.wk-range-bar {
  position: absolute;
  height: 100%;
  border-radius: 3px;
  top: 0;
  /* Left and Width set statically via JS */
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

html.dark .wk-range-container {
  background: rgba(255, 255, 255, 0.08);
}

/* ── AQI Forecast block (#10) ────────────────────────────────────────────── */
>>>>
```

**Step 3: Run test to verify it passes**

Run: `grep -n ".wk-range-container" web/static/style.css`
Expected: PASS (returns line numbers)

**Step 4: Commit**

```bash
git add web/static/style.css
git commit -m "style: add CSS for inline temperature range bars"
```

---

## Implementation Notes (2026-03-07)

**Implemented in a single commit.** Key differences from the plan above:

- Canvas was in `web/templates/dashboard.html` (not `index.html`) at line 192–194 inside `.weekly-sparkline-wrap`.
- The global min/max loop uses `topItems`/`bottomItems` (the actual variable names in scope after line 678), not `dayItems`/`nightItems` (which are reassigned and then aliased).
- Sparkline block spanned lines 749–898 (150 lines), including `tempChart` declaration at line 48.
- CSS `margin` used `0.3rem 0` instead of `0.5rem 0` to keep cards compact.
- All three tasks (DOM cleanup, JS injection, CSS) were applied in one pass rather than three separate commits.

**Files changed:**
- `web/templates/dashboard.html` — removed `.weekly-sparkline-wrap` + `<canvas>`
- `web/static/app.js` — removed `tempChart` var + 150-line Chart.js block; added global min/max + range bar injection
- `web/static/style.css` — added `.wk-range-container`, `.wk-range-bar`, dark-mode variant

---

## Extension: Real MaxAT/MinAT Span (2026-03-07)

**Commit 2 — upgrade weekly bars to use actual CWA temperature range.**

The CWA 7-day API (`F-D0047-071`) returns `MaxAT` (最高體感溫度) and `MinAT` (最低體感溫度) per 12-hour slot, but the pipeline was discarding them after deriving the single representative `AT`. Two additive fields are now preserved in each output slot.

**Files changed:**
- `data/fetch_cwa.py` — added `final_slot["MaxAT"]` and `final_slot["MinAT"]` after the `AT` aggregation (uses existing `_max()` helper)
- `web/static/app.js` — `globalMin`/`globalMax` now derived from `MinAT ?? AT` / `MaxAT ?? AT`; bar geometry uses real span (`leftPct` + variable `widthPct`); gradient always cold-blue → warm-amber

---

## Extension: Range Bars on 36-Hour Timeline Cards (2026-03-07)

**Commit 3 — same bar pattern applied to the 24/36h `.time-card` elements.**

The 36-hour API (`F-D0047-069`) has no built-in MaxAT/MinAT — it returns hourly point-in-time slots. The range is derived by collecting *all* raw slots whose timestamps fall within a segment's 6-hour window (0–6, 6–12, 12–18, 18–24) and computing min/max AT across them.

**Architecture change in `data/weather_processor.py` `_segment_forecast()` (lines 494–537):**
- Replaced "find first matching slot and `break`" with "collect all matching slots into `matching` list"
- Representative slot remains `matching[0]` — existing behaviour unchanged
- `MinAT = min(at_vals)`, `MaxAT = max(at_vals)` added to the segment dict
- Single-slot segments (boundary/sparse data) get `MinAT == MaxAT == AT`; bar renders at minimum 5% width

**Frontend (`web/static/app.js`):**
- Pre-pass over `data.timeline` computes `tlGlobalMin`/`tlGlobalMax` from `MinAT ?? AT` / `MaxAT ?? AT`
- Each `.time-card` gets `.wk-range-container` + `.wk-range-bar` injected between the icon and temp (reuses existing CSS — no style changes)

**Tests:** 173/173 pass.
