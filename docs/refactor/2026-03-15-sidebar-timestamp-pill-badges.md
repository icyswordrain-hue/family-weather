# Sidebar Timestamp Pill Badges

**Date:** 2026-03-15
**Status:** Implemented

## Context

The sidebar (240px) displayed timestamps ("updated: 3/15 11:46 · Audio from 11:21") in a single flex row at 0.72rem. The long text with dot separator felt cramped and visually undifferentiated from surrounding elements.

## Changes

### 1. Pill badge styling (style.css)

Replaced the plain inline text with subtle pill-shaped badges:
- Added `background: rgba(255, 255, 255, 0.07)`, `padding: 3px 12px`, `border-radius: 15px`
- Font size set to 0.975rem (1.5× scale-up from initial 0.65rem)
- Increased text opacity from 0.4 to 0.5 to compensate for smaller size
- Removed the `::before` dot separator (pills provide visual separation)

### 2. Shortened labels (app.js)

Abbreviated timestamp text to fit comfortably in side-by-side pills:
- `last_updated`: removed "updated: " / "更新：" prefix — pill shows just "3/15 11:46"
- `audio_from`: replaced "Audio from " / "語音來自 " with "♪ " — pill shows "♪ 11:21"

Both `en` and `zh-TW` translations updated.

## Files Changed

- `web/static/style.css` — `.sidebar-meta`, `.sidebar-last-updated`, `.sidebar-audio-age` rules
- `web/static/app.js` — `TRANSLATIONS.en.last_updated`, `TRANSLATIONS.en.audio_from`, `TRANSLATIONS['zh-TW'].last_updated`, `TRANSLATIONS['zh-TW'].audio_from`
