# Lifestyle Card Styling Tweaks

**Date:** 2026-03-14

## Problem

Lifestyle cards had overly prominent collapsed tagline text (bold, 1.05rem), tiny chevron arrows that were hard to spot, and a nearly invisible "Expand All" button that blended into the slab background. The dashboard outdoor-trigger arrow was also much smaller than the lifestyle chevrons.

## Changes

### `web/static/style.css`

**Collapsed tagline — lighter, smaller:**
- `.ls-tagline`: `font-weight: 600` → `400`, `font-size: 1.05rem` → `0.9rem`
- `html[lang="zh-TW"] .ls-tagline`: `1.2rem` → `1.08rem`

**Chevron arrows — 2x size across both views:**
- `.ls-chevron`: `0.75rem` → `1.5rem`
- `.gauge-outdoor-trigger::after`: `0.7rem` → `1.5rem` (dashboard outdoor card)

**Expand All button — visually prominent:**
- Added blue tint background (`var(--blue-lt)`), blue border/text, larger padding (`5px 14px`), bumped font size (`0.85rem`)
- Added `position: relative; z-index: 1` so it sits above the heading slab image
- `html[lang="zh-TW"]`: `0.9rem` → `1rem`

**Chevron alignment — consistent position:**
- Added `.ls-content { flex: 1; min-width: 0; }` so all content areas stretch equally, ensuring every chevron sits at the same right-edge position regardless of title length
