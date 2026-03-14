# Mobile Forecast Card Alignment Fix

**Date:** 2026-03-14

## Problem
The 24-hour forecast segment cards had misaligned temperature bars across rows on mobile (≤767px). Longer segment labels like "AFTERNOON" and "OVERNIGHT" (9 uppercase characters) overflowed their 72px fixed-width flex column, pushing the center temperature bar rightward. Shorter labels like "EVENING" and "MORNING" fit within 72px, so their bars started further left — creating a jagged, unaligned layout.

Secondary issue: "Good to go" outdoor grade text wrapped to 2 lines in the 56px right column.

## Root Cause
`.tc-seg-left` used `flex: 0 0 72px` on mobile but lacked `min-width: 0`. Combined with `white-space: nowrap` on `.tc-seg-label`, the flex item's intrinsic minimum width exceeded 72px for long labels, overriding the flex basis.

## Changes

**File:** `web/static/style.css`

1. Added `min-width: 0` and `overflow: hidden` to `.tc-seg-left` — forces the column to respect its declared flex basis regardless of content width.
2. Reduced `.tc-seg-label` font-size from `1rem` to `0.82rem` on mobile — fits "AFTERNOON" within 72px so no content is visually clipped.
3. Widened `.tc-seg-right` from `56px` to `64px` on mobile — prevents "Good to go" from wrapping to 2 lines.
4. Reduced base `.tc-seg-label` font-size from `1rem` to `0.88rem` — fits "AFTERNOON" and "OVERNIGHT" within the 90px desktop column without clipping.
