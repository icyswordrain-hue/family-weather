# Dashboard-as-Hero, Lifestyle-Below-Fold

> **Date:** 2026-02-28
> **Status:** Implemented
> **Related:** `2026-02-28-mobile-responsive-plan.md`

---

## The Idea

Keep the two views separate in the codebase but treat the scroll order on mobile as a deliberate narrative:

1. **Hero block** — Current conditions (gauges + weather icon + temperature) fills the top of the page. The user lands here. This is the answer to "what's it like outside right now?"
2. **Below the fold** — Lifestyle recommendations follow naturally. This is the answer to "so what should I do about it?"

The mental model mirrors how people think: *observe → act*. The gauges set context; the lifestyle cards are the payoff.

---

## How It Was Implemented

The DOM swap approach was rejected in favour of JS reordering in `initMobileNav()`. This left the HTML untouched and kept desktop behaviour completely unaffected.

### Scroll order on mobile (after `initMobileNav()` runs)

| # | Content | Source |
|---|---|---|
| 1 | 📊 section-header-card "天氣總覽" | moved from `#view-dashboard` |
| 2 | `.current-conditions-wrapper` (top row + gauges grid) | moved from `#view-dashboard` |
| 3 | 🚲 section-header-card "生活建議" | stays in `#view-lifestyle` |
| 4 | `.lifestyle-grid` (recommendation cards) | stays in `#view-lifestyle` |
| 5 | `#view-dashboard` remainder: 24h · 7-day · AQI forecast | stays in place |

### Changes made

**`web/static/app.js` — `initMobileNav()`** (commits `e321166`, `3be5310`)

```js
function initMobileNav() {
  const conditions = document.querySelector('.current-conditions-wrapper');
  const dashHeader = document.querySelector('#view-dashboard .section-header-card');
  const lifestyle  = document.getElementById('view-lifestyle');
  if (conditions && lifestyle) {
    if (dashHeader) lifestyle.parentNode.insertBefore(dashHeader, lifestyle);
    lifestyle.parentNode.insertBefore(conditions, lifestyle);
  }
}
```

**`web/static/style.css` — mobile block** (multiple commits)

- `.view-header` hidden on mobile — redundant alongside `section-header-card` (commit `4bf7f6d`)
- `.section-header-card` and `.view-header h1` font aligned to `section-title`: `1.4rem / 700` (commit `db293bc`)
- Top row and gauges grid compacted to prevent horizontal overflow, then fonts increased to comfortable reading sizes (commits `ac3d9cc`, `31dce51`, `7eeec02`, `46d60aa`)

### What stayed the same

- `web/templates/dashboard.html` — no changes
- `switchView()` and desktop sidebar nav — untouched
- All data slices and render functions — untouched
- FAB controls sheet — untouched

---

## Trade-offs (resolved)

The original plan considered a straight HTML DOM swap. JS reordering in `initMobileNav()` was chosen instead because:
- Zero HTML changes — no risk of breaking desktop tab behaviour
- `initMobileNav()` only runs when `matchMedia('(max-width: 767px)').matches` — desktop path is fully isolated
- Gauge card IDs remain valid regardless of where the wrapper lives in the DOM
