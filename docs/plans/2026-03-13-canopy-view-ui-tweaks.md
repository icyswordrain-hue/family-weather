# Canopy View UI Tweaks

**Date:** 2026-03-13

## Changes

Three targeted CSS-only changes to the Canopy (dashboard) view.

### 1. Sunrise/Sunset Text ×1.5

`.solar-row` font size increased from `0.95rem` → `1.43rem`. Solar brand icons scaled proportionally: `28px → 42px` (desktop), `36px → 54px` (mobile). Makes the solar row visually prominent inside the current-conditions hero.

### 2. 24h Forecast Stat — Stacked Layout

The outdoor-grade label (daytime) and precip text (nighttime) in each forecast row were displayed side-by-side with the icon. Changed to a stacked layout: icon on top, text below.

**Mechanism:** `mkStat()` in `app.js` builds `.tc-seg-stat` with DOM order `[textSpan, iconSpan]`. Using `flex-direction: column-reverse` visually reverses this so the icon appears first. `align-items: center` + `text-align: center` centre the stack; `white-space: nowrap` and `justify-content: space-between` removed.

Both desktop (60px icon) and mobile (30px icon) use the same stacked layout — widths (`160px` / `100px`) are sufficient for all label strings in both languages.

### 3. Language Toggle — Tag Text (Investigation, No Code Change)

Outdoor labels ("Go out", "Manageable", …) go through `localiseMetric()` → `T.metrics[text]` (zh-TW mapping at `app.js:311`). Precip text ("All clear", "Stay in", "~N min") goes through `localisePrecipText()` (`app.js:130`). Both are called inside `renderOverviewView()`, which `applyLanguage()` triggers on every toggle. **Tags update immediately — no regeneration or new mapping needed.**

## Files Modified

- `web/static/style.css`
