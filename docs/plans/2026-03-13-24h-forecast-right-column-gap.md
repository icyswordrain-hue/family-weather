# 24h Forecast Right-Column Gap Alignment

**Date:** 2026-03-13

## Problem

The 24-hour forecast right column (`.tc-seg-right`) was 160px wide, but the outdoor/PoP stat inside it (60px icon + short text) is centred, leaving ~80px of dead space between the temperature gauge and the actual content. In contrast, the 7-day view right column (`.wk-row-night`) is 54px with an 8px row gap, so the night icon sits immediately adjacent to the gauge. This made the two views look visually inconsistent.

## Change

Three CSS-only edits in `web/static/style.css`:

| Selector | Property | Before | After |
|---|---|---|---|
| `.tc-seg-row` | `gap` | `14px` | `8px` |
| `.tc-seg-right` | `flex` | `0 0 160px` | `0 0 80px` |
| `.tc-seg-right` (mobile ≤767px) | `flex` | `0 0 100px` | `0 0 56px` |

The row gap now matches `.wk-row` (8px). The right column shrinks to fit its content snugly, extending the temperature gauge by ~80px on desktop and ~44px on mobile.

No JS changes. Icon sizes, text labels, and level colour classes are untouched.
