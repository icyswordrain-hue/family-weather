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

## Re-enabling

1. Remove `hidden` from the chat tab button (line ~237)
2. Remove `hidden` from `#player-chat-btn` (line ~215)
3. Uncomment `initChat();` in `app.js` (line ~415)

The `/api/chat` backend endpoint remains intact and requires no changes.
