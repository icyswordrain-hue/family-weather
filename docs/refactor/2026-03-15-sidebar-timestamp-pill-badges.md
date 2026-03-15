# Sidebar Timestamp Pill Badges

**Date:** 2026-03-15
**Status:** Implemented

## Context

The sidebar (240px) displayed timestamps ("updated: 3/15 11:46 · Audio from 11:21") in a single flex row at 0.72rem. The long text with dot separator felt cramped and visually undifferentiated from surrounding elements.

## Changes

### 1. Pill badge styling (style.css)

Three-pill layout stacked vertically:
- Top row: "updated" label pill (`align-self: stretch` to match row width, uppercase, 0.8rem)
- Bottom row: two side-by-side pills for timestamp and audio age (0.8rem)
- `.sidebar-meta` uses `flex-direction: column`; `.sidebar-meta-row` wraps the bottom two pills in a horizontal flex row
- All pills share `background: rgba(255, 255, 255, 0.07)`, `padding: 3px 12px`, `border-radius: 15px`
- Removed the `::before` dot separator (pills provide visual separation)

### 2. Shortened labels (app.js)

Abbreviated timestamp text to fit comfortably in side-by-side pills:
- `last_updated`: removed "updated: " / "更新：" prefix — pill shows just "3/15 11:46"
- `audio_from`: replaced "Audio from " / "語音來自 " with "♪ " — pill shows "♪ 11:21"

Both `en` and `zh-TW` translations updated.

### 3. Mobile pill badges (style.css)

Ported pill styling to the mobile compact header timestamps:

- `#mobile-last-updated` — added `background`, `padding: 2px 8px`, `border-radius: 10px`, bumped opacity to 0.5
- `.mobile-audio-age` — same pill treatment, removed `::before` dot separator
- Stale color classes (`.stale-amber`, `.stale-red`) kept as-is — text color override on pill background

### 4. Mobile location below timestamps (dashboard.html)

Swapped order in `.mobile-meta`: timestamps now appear above the station location name, matching the desktop sidebar's visual hierarchy (clock → timestamps → location).

### 5. Single-pill full-width match (desktop) (style.css)

When audio-age is hidden, the timestamp pill is the only child of `.sidebar-meta-row`. Added `.sidebar-last-updated:only-child { width: 100%; text-align: center; }` so it stretches to match the "updated" pill above. `.sidebar-meta-row` also gets `align-self: stretch` to fill the column width.

### 6. Stale coloring on desktop (style.css + app.js)

Extended stale-data coloring (previously mobile-only) to the desktop sidebar pill:

- Added `#sidebar-last-updated.stale-amber` and `.stale-red` CSS rules
- Hoisted `ageH` computation out of the mobile `if` block so both desktop and mobile share it
- Desktop `#sidebar-last-updated` now toggles `stale-amber` (2–4h) and `stale-red` (4h+)

## Files Changed

- `web/static/style.css` — `.sidebar-meta`, `.sidebar-updated-label`, `.sidebar-meta-row`, `.sidebar-last-updated`, `.sidebar-audio-age`, `#mobile-last-updated`, `.mobile-audio-age` rules
- `web/templates/dashboard.html` — added `sidebar-updated-label` span and `.sidebar-meta-row` wrapper
- `web/static/app.js` — `TRANSLATIONS.en.last_updated`, `TRANSLATIONS.en.audio_from`, `TRANSLATIONS['zh-TW'].last_updated`, `TRANSLATIONS['zh-TW'].audio_from`
