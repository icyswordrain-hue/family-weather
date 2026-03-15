# System Log Cleanup & Mobile Progress Pill

**Date:** 2026-03-15

## Problem

Two issues with the system log during refresh:

1. **Duplicate pipeline appearance:** `startLoadingAnimation()` logged fake client-side step messages (步驟：取得鄉鎮預報, etc.) to the system log every 1.2 seconds via `addLog()`. When real server-streamed messages arrived seconds later, the log showed both sets — making it look like the pipeline ran twice.

2. **Frozen mobile pill:** The `optimistic-loading` pill on mobile showed static "正在獲取天氣…" text during refresh with no progress updates. The cycling step text and real server log messages both targeted `#loading-text` inside `loading-screen`, which is hidden during refresh.

3. **Non-factual log messages:** `T.boot` ("System Boot: Initiating connection…") logged on every refresh click and `T.render` ("Pipeline success. Rendering…") added noise.

## Changes

### `web/static/app.js`

- **`startLoadingAnimation()`:** Removed `addLog()` calls. Now only updates `textContent` on `#loading-text` and `#optimistic-text` (no log pollution).
- **`startLoadingAnimation()`:** Added `#optimistic-text` targeting so the mobile pill cycles through step messages.
- **`triggerRefresh()`:** Removed duplicate `startLoadingAnimation()` call (already called inside `showLoading(true)`). Removed `addLog(T.boot)` and `addLog(T.render)`.
- **Server log handler (`msg.type === 'log'`):** Also updates `#optimistic-text` so real server messages appear in the mobile pill.

### `web/templates/dashboard.html`

- Added `id="optimistic-text"` to the text span inside `#optimistic-loading`.

### `web/static/style.css`

- Added `max-width: calc(100vw - 3rem)` to `.optimistic-loading` to prevent overflow.
- Added `overflow: hidden; text-overflow: ellipsis; white-space: nowrap` to the pill's text span for graceful truncation of long server messages.
