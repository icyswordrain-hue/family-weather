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

Added `.player-speed-btn` before `.player-sheet-toggle`. Blue pill badge treatment:

- `background: var(--blue-lt)` / `color: var(--blue)` — immediately readable as a tappable control
- `border-radius: 20px; padding: 3px 8px; font-size: 0.85rem; font-weight: 700`
- Hover: fills to solid `var(--blue)` with white text
- Dark mode: `rgba(77, 124, 254, 0.18)` translucent blue pill with `#7da4ff` label

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
| `web/static/style.css` | `.player-speed-btn` pill badge + hover/dark-mode rules |

---

## Follow-up — 2026-02-28: Button Visibility Fix

**Commit:** `fix(player): make speed button visible as blue pill badge`

Initial styling used `color: var(--muted); background: none` — identical to the static duration text beside it. The button was present in the DOM but visually indistinguishable from a label.

**Root cause:** No visual affordance (no background, no border, same muted gray as `--:-- / --:--`) made the button invisible as an interactive element on both desktop and mobile.

**Fix (`web/static/style.css` only):**

```css
/* Before — ghost button, invisible as control */
.player-speed-btn {
  background: none;
  color: var(--muted, #7a8ca0);
  font-size: 1.0rem;
  font-weight: 600;
  border-radius: 6px;
}

/* After — blue pill badge */
.player-speed-btn {
  background: var(--blue-lt, #eef2ff);
  color: var(--blue, #4d7cfe);
  font-size: 0.85rem;
  font-weight: 700;
  border-radius: 20px;
  padding: 3px 8px;
}
html.dark .player-speed-btn {
  background: rgba(77, 124, 254, 0.18);
  color: #7da4ff;
}
```

Pattern matches the existing dark-mode badge style used by `.source-gemini` / `.source-claude` pills in the narration sheet.
