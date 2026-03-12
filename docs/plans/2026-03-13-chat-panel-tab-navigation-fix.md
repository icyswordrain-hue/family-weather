# Chat Panel Tab Navigation Fix

**Date:** 2026-03-13

## Problem

Once the chat panel was opened, the Narration and Settings tabs became permanently inaccessible:

- **Desktop (≥768px):** The "Ask" button on the player bar calls `switchToChat()`, which programmatically clicks `.ps-tab[data-tab="chat"]`. This hides `#ps-panel-narration` and `#ps-panel-settings` (via `setAttribute('hidden', '')`). Because `.player-sheet-tabs` was hidden on desktop via a media query, there was no way to switch back — the sheet was stuck on chat for the rest of the session, even after closing and reopening it.
- **Mobile (≤767px):** The outer `padding: 14px 16px` inherited from `.ps-tab-panel` combined with `height: 100%` on `#ps-panel-chat` double-padded the chat layout. The `.chat-messages` and `.chat-input-row` elements also carry their own padding, so the effective outer whitespace was 14px + 12–10px on each side — visually cramped and inconsistent with the other panels.

## Root Cause

```css
/* style.css — was hiding tabs on desktop */
@media (min-width: 768px) {
  .player-sheet-tabs {
    display: none;
    /* tabs are mobile-only; desktop shows narration directly */
  }
}
```

This rule predates the chat feature. When chat was added to the player bar (Ask button, desktop-only), the tab bar was still hidden on desktop, leaving no UI to switch back from chat.

## Fix

### `web/static/style.css`

1. **Remove** the `@media (min-width: 768px)` block that hid `.player-sheet-tabs`. Tabs are now visible on both desktop and mobile.

2. **Add** `padding: 0` to `#ps-panel-chat` to override the inherited `.ps-tab-panel { padding: 14px 16px }`:

```css
#ps-panel-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 0; /* override .ps-tab-panel — messages/input-row carry their own padding */
}
```

## Gotchas

**Do not re-add `display: none` to `.player-sheet-tabs` at `≥768px`.** The Ask button on desktop relies on the tab bar being visible so users can navigate back to Narration or Settings after opening chat.

**Do not add outer padding back to `#ps-panel-chat`.** `.chat-messages { padding: 12px 16px }` and `.chat-input-row { padding: 10px 14px }` already provide spacing. Adding `.ps-tab-panel`-level padding on top creates double-padding.
