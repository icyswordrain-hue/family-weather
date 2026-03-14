# Hide Chatbot Feature

**Date**: 2026-03-14
**Status**: Done

## What

Temporarily hide the chat (Ask) feature from the UI. All chat code is preserved
and can be re-enabled by reverting three small changes.

## Changes

| File | Change |
|------|--------|
| `web/templates/dashboard.html` | Added `hidden` to chat tab button (`data-tab="chat"`) |
| `web/templates/dashboard.html` | Added `hidden` to player bar chat button (`#player-chat-btn`) |
| `web/static/app.js` | Commented out `initChat()` call |
| `web/static/style.css` | Fixed `#ps-panel-chat` so `display: flex` only applies via `:not([hidden])` — prevents chat panel leaking below narration on mobile |
| `web/static/style.css` | Fixed `.player-chat-btn` so `display: flex` only applies via `:not([hidden])` — prevents chat icon showing on desktop |

## Re-enabling

1. Remove `hidden` from the chat tab button (line ~237)
2. Remove `hidden` from `#player-chat-btn` (line ~215)
3. Uncomment `initChat();` in `app.js` (line ~415)

The `/api/chat` backend endpoint remains intact and requires no changes.

## Bug fix: chat panel visible on mobile (2026-03-14)

`#ps-panel-chat { display: flex }` overrode the HTML `hidden` attribute (UA
stylesheet has lowest priority), so the chat panel rendered below the narration
text. Clicking Send triggered a default form submission (no `initChat()` →
no `preventDefault`), reloading the page and wiping the narration. Fixed by
moving `display: flex` into `#ps-panel-chat:not([hidden])`.

## Bug fix: chat button visible on desktop (2026-03-14)

Same root cause: `.player-chat-btn { display: flex }` overrode the `hidden`
attribute. On mobile it was coincidentally hidden by a media query
`display: none`, but on desktop the button remained visible. Fixed by moving
`display: flex` into `.player-chat-btn:not([hidden])`.
