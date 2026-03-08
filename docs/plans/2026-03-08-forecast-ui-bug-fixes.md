# Forecast UI Bug Fixes

**Date:** 2026-03-08
**Status:** Implemented (commits `d24fe6d`, `aa5a157`)

## Goal

Fix four regressions in the 36-hour and 7-day forecast views: gauge range calculation, mobile icon overflow, missing precip-text localisation, and mismatched night icon size.

## Files Changed

| File | Change |
|------|--------|
| `web/static/app.js` | Tasks 1 & 3 — relative gauge range + localised precip text |
| `web/static/style.css` | Tasks 2 & 4 — mobile icon override + night icon sizing |

No HTML or backend changes.

---

## Fix 1 — 36h gauge: relative range (`app.js` ~604)

**Commit:** `d24fe6d`

**Problem:** The temperature range bar inside the 36h segment loop was hardcoded to `left:0%; width:100%`, making every segment appear full-width regardless of temperature. The 7-day bars already computed `leftPct`/`rightPct` from a shared global range; the 36h bars did not.

**Fix:** Mirror the 7-day calculation (lines 812–819) using the already-available `tlGlobalMin`/`tlGlobalMax` (both derived from `weekGlobalMin`/`weekGlobalMax`):

```js
const span = tlGlobalMax - tlGlobalMin;
const leftPct = Math.max(0, ((lo - tlGlobalMin) / span) * 100);
const rightPct = Math.min(100, ((hi - tlGlobalMin) / span) * 100);
rangeBar.style.left  = `${leftPct}%`;
rangeBar.style.width = `${Math.max(5, rightPct - leftPct)}%`;
```

**Effect:** 36h bars are now positioned on the same shared scale as the 7-day bars. A segment at 15° always sits at the same horizontal position in both sections.

---

## Fix 2 — 36h outdoor/PoP icon: half size on mobile (`style.css` ~1203)

**Commit:** `aa5a157`

**Problem:** The desktop icon size for `.tc-seg-stat .tc-stat-icon .brand-icon` is 60px. The `@media (max-width: 767px)` block had no override, so the icon stayed 60px on narrow screens and overflowed its container.

**Fix:** Added inside the existing `@media (max-width: 767px)` block, after `.tc-seg-stat { font-size: 0.78rem; }`:

```css
.tc-seg-stat .tc-stat-icon .brand-icon {
  width: 30px;
  height: 30px;
}
```

**Effect:** The outdoor/PoP icon halves to 30px on mobile, fitting within the 82px right column without clipping.

---

## Fix 3 — 36h night row: localise precip text (`app.js` ~648)

**Commit:** `d24fe6d`

**Problem:** Day rows called `localiseMetric(seg.outdoor_label)` but night rows passed `seg.precip_text` raw. English strings like `"All clear"` or `"~45 min"` appeared in Chinese mode.

`localisePrecipText()` (lines 130–138) already handles all three possible values from `safe_minutes_to_level()`:

| Raw value | `localisePrecipText()` output |
|-----------|-------------------------------|
| `"All clear"` | `'不會降雨'` |
| `"Stay in"` | `'建議待室內'` |
| `"~N min"` | `'約 N 分鐘'` |

**Fix:** One-character change at call site:

```js
// Before
seg.precip_text,
// After
localisePrecipText(seg.precip_text),
```

**Effect:** Night rows now display localised precip text in Chinese mode.

---

## Fix 4 — 7-day night icon: same size as day icon (`style.css` ~3282)

**Commit:** `aa5a157`

**Problem:** Day icons were 54px desktop / 42px mobile. Night icons were 45px desktop / 34px mobile — noticeably smaller, creating visual imbalance.

**Fix:** Updated both rules to match day icon dimensions. Opacity (0.70) is preserved to retain the day/night visual distinction.

```css
/* Desktop */
.wk-row-night .wk-icon .brand-icon { width: 54px; height: 54px; }

/* Mobile (max-width: 767px) */
.wk-row-night .wk-icon .brand-icon { width: 42px; height: 42px; }
```

**Effect:** Day and night icons are the same size. Night icons remain slightly dimmed (opacity 0.70).

---

## Fix 5 — 36h Evening slot translation (`app.js` ~294)

**Commit:** `27db699`

**Problem:** In the 36-hour forecast timeline, the 'Evening' slot was incorrectly translated as '傍晚'.

**Fix:** Updated the translation map for `'Evening'` in `app.js`.

```js
// Before
'Evening': '傍晚',
// After
'Evening': '晚上',
```

**Effect:** The 36-hour view now displays '晚上' during evening segments.
