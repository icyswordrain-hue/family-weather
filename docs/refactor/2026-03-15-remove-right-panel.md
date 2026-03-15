# Remove System Log Right Panel from Desktop UI

**Date:** 2026-03-15

## Reasoning

The 180px right panel displayed a monospace debug log with timestamped pipeline events (CWA fetch, narration provider, TTS synthesis, errors). It served no user-facing purpose:

- **Already hidden** on tablet (≤1024px) and mobile (≤767px) — most users never saw it.
- **Redundant** — the same pipeline progress is shown via the loading screen (`#loading-screen`) and optimistic pill (`#optimistic-loading`), both of which work on all breakpoints.
- **No interactive features** — read-only with a clear button; no user action depended on it.
- **DevTools covers it** — `console.log`, `remoteLog()`, and the Network tab provide richer debugging than the DOM log ever did.

Removing it gives the main content area an extra 180px on desktop without any feature loss.

## What Was Removed

### HTML (`web/templates/dashboard.html`)

- Deleted `<aside class="right-panel">` block containing `rp-log-container`, `rp-log-header`, `rp-log-list`, and the clear button.

### CSS (`web/static/style.css`)

- **Grid simplified**: `grid-template-columns: var(--sidebar-w) 1fr var(--rp-w)` → `var(--sidebar-w) 1fr` (3-column → 2-column).
- **Removed variables**: `--rp-w` (180px), `--rp-bg` (both light and dark themes).
- **Deleted style rules**: `.right-panel`, `.rp-header`, `.rp-controls`, `.rp-time`, `.rp-divider`, `.rp-box`, `.rp-label`, `.rp-big-text`, `.rp-text`, `.rp-top`, `.rp-actions`, `.provider-toggle-group`, `.provider-option`, `.prov-label`, `.rp-log-container`, `.rp-log-header`, `.log-clear-btn`, `.rp-log-list`, `.log-entry`, `.log-ts`, `.log-msg`, `.log-status-row`, `.log-status-chip` (and its state variants).
- **Updated overlays**: `right: var(--rp-w, 180px)` → `right: 0` on player bar, player sheet, and backdrop.
- **Cleaned media queries**: Removed `.right-panel { display: none }` from tablet breakpoint and `--rp-w: 0px` from mobile reset.
- **Cleaned dark mode**: Removed `html.dark .right-panel` rule and `.right-panel` from transition list.

### JavaScript (`web/static/app.js`)

- **Deleted functions**: `addLog()` (timestamped DOM log writer), `_addStatusRow()` (color-coded pipeline status chips).
- **Removed 10 call sites**: boot message, data-received, error prefix, server log lines, pipeline step messages, provider selection, stream truncation warning, refresh error.
- **Simplified global error handler**: Kept `remoteLog()` + `console.error()`, removed DOM log append to `#rp-log-list`.
- **Removed `window._T_runtime_error`** assignment (no longer needed without DOM log).
- **Removed 12 translation keys** from both EN and zh-TW: `error_prefix`, `boot`, `data_ok`, `log_requesting`, `log_title`, `log_step_prefix`, `log_runtime_error`.
- **Updated file header comment**: Removed "Dynamic Right Panel (Context-aware)" from feature list.

## What Was Kept

- `.rp-location` class — used by the sidebar for location display, not the right panel.
- `@keyframes spin` — used by the refresh button spinner.
- `remoteLog()` — still posts errors/info to `/debug/log` server endpoint.
- `LOADING_MSGS` / `startLoadingAnimation()` / `stopLoadingAnimation()` — pipeline progress via loading screen and optimistic pill, unaffected.

## Layout Before/After

```
Before (desktop ≥1025px):
┌──────────┬────────────────────────┬──────────┐
│ Sidebar  │      Main Content      │ System   │
│  240px   │         1fr            │  Log     │
│          │                        │  180px   │
└──────────┴────────────────────────┴──────────┘

After:
┌──────────┬───────────────────────────────────┐
│ Sidebar  │          Main Content             │
│  240px   │              1fr                  │
│          │                                   │
└──────────┴───────────────────────────────────┘
```

Tablet and mobile layouts are unchanged (right panel was already hidden).
