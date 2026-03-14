# Solar Row Scale + Square Brand Icons

**Date:** 2026-03-13

## Changes

### 1. Square Sunrise/Sunset Brand Icons

The original `sunrise.webp` and `sunset.webp` are 1380×752 (landscape). The CSS solar row forces equal `width`/`height` on `.brand-icon`, distorting them. New square variants were created and wired in.

- Added `web/static/brand-icons/sunrise-square.webp` (1024×1024) and `sunset-square.webp` (1024×1024), converted from provided PNGs.
- Updated `app.js` solar row render to use `IMG('sunrise-square', …)` and `IMG('sunset-square', …)`.
- The original landscape `sunrise.webp` / `sunset.webp` remain in the directory but are no longer referenced.

**Rule:** All brand icons must be 1:1 square (512×512 recommended). The `*-slab.webp` files (512×128) are intentional exceptions — their CSS uses `height` fixed + `width: auto`.

### 2. Solar Row ×1.5

The solar row (sunrise/sunset times in the dashboard canopy hero) was scaled up by ×1.5 from the 80%-of-original baseline:

| Property | Before | After |
| --- | --- | --- |
| Font size | `0.76rem` | `1.14rem` |
| Icon — desktop | `22px` | `33px` |
| Icon — mobile | `29px` | `44px` |

### 3. 24h Forecast Right Column — Narrowed (Pre-existing)

The `.tc-seg-right` column and `.tc-seg-row` gap were tightened as part of the stacked-stat layout (see `2026-03-13-canopy-view-ui-tweaks.md`). These changes were staged here as they were uncommitted.

| Property | Before | After |
| --- | --- | --- |
| `.tc-seg-row` gap | `14px` | `8px` |
| `.tc-seg-right` flex (desktop) | `160px` | `80px` |
| `.tc-seg-right` flex (mobile) | `100px` | `56px` |

## Files Modified

- `web/static/style.css`
- `web/static/app.js`
- `web/static/brand-icons/sunrise-square.webp` *(new)*
- `web/static/brand-icons/sunset-square.webp` *(new)*
- `CLAUDE.md` *(icon aspect-ratio rule)*
