# 24-Hour Forecast Card Height Reduction (Desktop)

**Date:** 2026-03-15

## Problem

The 24-hour forecast cards in the dashboard view were taller than necessary on desktop, making the timeline less scannable when multiple segments were visible.

## Solution

Scale all desktop card dimensions to 0.8× of the original values. Mobile (≤767px) is unchanged — it was already at ~0.76× of desktop.

### Changes (desktop only)

| Property | Before | After (×0.8) |
|----------|--------|--------------|
| `.tc-seg-row` min-height | 126px | 101px |
| `.tc-seg-row` padding | 10px 18px | 8px 14px |
| `.tc-seg-left` flex-basis | 90px | 72px |
| `.tc-seg-left .brand-icon` | 72×72px | 58×58px |
| `.tc-seg-stat .brand-icon` | 60×60px | 48×48px |

### File

- `web/static/style.css` — base (non-media-query) rules for `.tc-seg-*` selectors
