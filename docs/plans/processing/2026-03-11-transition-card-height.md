# Transition Card Height — Desktop & Mobile

**Date:** 2026-03-11

---

## Change

Doubled the height of the 36-hour forecast weather-change card (`.tc-transition`) and aligned its visual style with the adjacent segment rows (`.tc-seg-row`).

---

## Before / After

| Property | Before | After |
|----------|--------|-------|
| `min-height` (desktop) | 48 px | **96 px** |
| `padding` (desktop) | `0.8rem 1.2rem` | `1.4rem 1.4rem` |
| `border-radius` | 10 px | **12 px** (matches `.tc-seg-row`) |
| `border-left` width | 3 px | **4 px** (matches `.tc-seg-row`) |
| `gap` | 0.8 rem | 1.2 rem |
| Icon size | 24 × 24 px | **40 × 40 px** |
| Font size | 0.95 rem | 1.05 rem |
| `min-height` (≤767 px) | — | **72 px** (new override) |
| Icon size (≤767 px) | — | **32 × 32 px** (new override) |

---

## Rationale

The 48 px card was visually thin compared with the 126 px segment rows above and below it, making it easy to miss. Doubling the height gives the "weather change" alert proportional weight in the timeline. Border-radius and border-left thickness were also brought into line with `.tc-seg-row` for visual consistency.

The mobile override (72 px / 32 px icon) scales proportionally to the mobile segment row (96 px) rather than matching desktop exactly.

---

## File Modified

`web/static/style.css` — `.tc-transition`, `.tc-transition-icon .brand-icon`, `.tc-transition-text`, mobile `@media (max-width: 767px)` block.
