# Player — Playback Speed Control (Default 1.2×)

**Date:** 2026-02-28
**Status:** Implemented

## Problem

The audio player had no playback speed control. The `<audio>` element's `playbackRate` was always left at the browser default (1.0×). Users wanting a faster listen had no way to change it, and the setting couldn't persist across sessions or language switches.

## Changes

### `web/templates/dashboard.html` — speed button added

Inserted between the duration `<span>` and the sheet-toggle `<button>`:

```html
<button class="player-speed-btn" id="player-speed-btn" aria-label="Playback speed">1.2×</button>
```

### `web/static/app.js` — speed logic in `initPlayerBar()`

- `SPEEDS = [1.0, 1.2, 1.5]` — cycle order
- On init: reads `localStorage.playerSpeed` (defaults to `1.2` if absent or invalid)
- `applySpeed(s)` — sets `audio.playbackRate`, updates button label, writes to `localStorage`
- `loadedmetadata` listener re-applies speed — browsers reset `playbackRate` when `audio.src` changes
- `_playerBarSetAudio` also sets `audio.playbackRate = speed` immediately after assigning `src` as an early hint
- Speed button click cycles to next value in `SPEEDS`

### `web/static/style.css` — speed button styled

Added `.player-speed-btn` before `.player-sheet-toggle`. Matches the existing muted-button aesthetic:

- `font-size: 1.0rem; font-weight: 600; font-variant-numeric: tabular-nums`
- `color: var(--muted)` default; hover darkens text and adds subtle background tint
- Full dark-mode `html.dark .player-speed-btn:hover` override

## Behaviour

| Scenario | Result |
|---|---|
| First visit | Defaults to 1.2× |
| Tap button | Cycles 1.0× → 1.2× → 1.5× → 1.0× … |
| Refresh page | Speed restored from `localStorage` |
| Switch EN ↔ ZH | Speed preserved (same player component) |
| New audio loaded | `playbackRate` re-applied on `loadedmetadata` |

## Files modified

| File | Change |
|---|---|
| `web/templates/dashboard.html` | Speed button element in player bar |
| `web/static/app.js` | `initPlayerBar()` — speed state, `applySpeed()`, button listener, `loadedmetadata` hook, `_playerBarSetAudio` hook |
| `web/static/style.css` | `.player-speed-btn` and hover/dark-mode rules |
