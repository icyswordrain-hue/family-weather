# Speed-Adjusted Player Progress & Time Display

**Date:** 2026-03-07
**Status:** Completed

## Problem

The narration player displayed raw audio duration (`currentTime / duration`) regardless of playback speed. At 1.5× a 3:20 audio showed a total of 3:20, even though playback would finish in ~2:13. The time display was misleading about actual listening time.

## Solution

Divide both `currentTime` and `duration` by `speed` before formatting in all three sites inside `initPlayerBar()` in `web/static/app.js`:

1. **`timeupdate` handler** — live progress update for player bar and sheet
2. **`loadedmetadata` handler** — initial total shown on audio load
3. **`applySpeed()`** — immediate refresh when speed is toggled while paused

The progress bar percentage is unchanged (still `currentTime / duration`) since it represents position within the audio file.

## Files Changed

- `web/static/app.js` — 3 edits inside `initPlayerBar()`

## Behaviour

| Speed | Raw duration | Displayed total |
|-------|-------------|-----------------|
| 1.0×  | 3:20        | 3:20            |
| 1.2×  | 3:20        | 2:46            |
| 1.5×  | 3:20        | 2:13            |

Speed preference is persisted in `localStorage.playerSpeed` (default 1.2×).
