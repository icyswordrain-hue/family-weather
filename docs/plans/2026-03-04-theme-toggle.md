# Theme Toggle — Changelog

**Date:** 2026-03-04  
**Scope:** `web/templates/dashboard.html`, `web/static/app.js`

---

## What changed

### Replaced provider selection with Dark / Light / Auto theme toggle

The Claude/Gemini provider radio group (sidebar + sheet settings panel) has been removed. It served no function visible to users since the provider was never exposed as a runtime option. In its place is a three-way **Theme** segmented control:

| Value | Behaviour |
|---|---|
| `Auto` | Follows `prefers-color-scheme` system setting (default) |
| `Dark` | Forces `html.dark` class regardless of system |
| `Light` | Removes `html.dark` class regardless of system |

Selection is persisted in `localStorage` under the key `theme`. Removing the key (via **Auto**) returns to system-follow behaviour.

---

### dashboard.html

- Sidebar `sidebar-controls` group: `name="provider"` radios → `name="theme"` radios (Auto / Dark / Light)
- Sheet settings panel: `name="provider-sheet"` radios → `name="theme-sheet"` radios (Auto / Dark / Light)
- Both labels updated: `data-i18n="provider_label"` → `data-i18n="theme_label"`

### app.js

**`initSystemTheme()`** — rewritten:
- Reads `localStorage.getItem('theme')` on every apply call
- `'dark'` → force dark; `'light'` → force light; anything else → follow `mq`
- Syncs the sidebar and sheet radio to the current value on boot
- Exposes `window.setTheme(val)` for radio `change` handlers

**`initSidebarControls()`** — provider `change` listener replaced with theme `change` listener calling `window.setTheme(input.value)`

**`initSheetSettings()`**:
- `provider-sheet` mirror block → `theme-sheet` mirror block
- Init-sync array updated: `['language', 'provider']` → `['language', 'theme']`

**`triggerRefresh()`** — removed dynamic provider lookup; hardcoded to `'CLAUDE'` (provider is a backend config concern, not a UI setting)

**Translations** — `provider_label` key replaced with `theme_label` in both `en` and `zh-TW` locales:
- `en`: `'Theme'`
- `zh-TW`: `'外觀主題'`
