# 36h Temperature Gauge — Font & Style Alignment with 7-Day Forecast

**Date:** 2026-03-11

---

## Change

Aligned the 36h segment temperature label style (`.tc-seg-temp`) with the 7-day forecast labels (`.wk-min-temp` / `.wk-max-temp`). A prior commit (`152aec5`) had matched bar height and font size but missed font family, font weight, min-width, and bar border-radius.

---

## Before / After

| Property | Before | After |
|----------|--------|-------|
| `font-family` | *inherited (body font)* | **`'Fira Code', monospace`** |
| `font-weight` | *inherited* | **`700`** |
| `min-width` | `3.2ch` | **`2.8ch`** (matches 7-day) |
| Bar `border-radius` | 4 px | **6 px** (matches `.wk-range-bar` base) |

---

## Rationale

The missing `font-family: 'Fira Code', monospace` caused the 36h temperature digits to render in a proportional font while the 7-day digits used monospace, making the two gauges look visually inconsistent even though they share the same bar, color scale, and font size. The `3.2ch` min-width also made 36h labels slightly wider than the 7-day `2.8ch`, shifting the bar leftward.

---

## File Modified

`web/static/style.css` — `.tc-seg-center .wk-range-bar`, `.tc-seg-temp`.
