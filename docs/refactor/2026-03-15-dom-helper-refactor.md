# DOM Helper Refactor — `h()` in app.js

**Date:** 2026-03-15
**File:** `web/static/app.js`
**Lines:** 1839 → 1727 (112 lines removed, 6% reduction)

## Problem

`app.js` contained 60 `document.createElement` calls, each followed by `.className =` and often `.textContent =` assignments — a repetitive 3-line pattern used throughout every rendering function.

## Solution

Added a single 6-line helper at the top of the file:

```javascript
function h(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}
```

Named `h` (not `el`) to avoid conflicts with existing local variables named `el` in `renderGauge`, `setText`, `updateClock`, `showStaleIndicator`, `hideStaleIndicator`, and `applyLanguage`.

## Scope

All 60 `createElement` call sites were replaced. The only remaining `createElement` is inside the helper itself. Major areas compressed:

| Function | Before | After | Saved |
|----------|--------|-------|-------|
| `renderGauge` | 33 lines | 17 lines | 16 |
| `add()` (lifestyle cards) | 35 lines | 16 lines | 19 |
| Alert card builder | 41 lines | 27 lines | 14 |
| `addLog` | 30 lines | 15 lines | 15 |
| `_addStatusRow` | 12 lines | 8 lines | 4 |
| Timeline + weekly rendering | scattered | scattered | ~44 |

## What did NOT change

- No CSS changes
- No Python/backend changes
- No HTML template changes
- No behavioral changes — pure mechanical syntax transformation
- All rendering output is identical
