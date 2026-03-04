# Earthy Color System — Changelog

**Date:** 2026-03-04  
**Scope:** Light mode only (`style.css :root`). Dark mode untouched.

---

## What Changed

### `web/static/style.css`

Replaced the previous cool-blue corporate palette with an **earthy sophistication** system inspired by a curated literary aesthetic.

#### Backgrounds & Surfaces

| Token | Before | After |
|---|---|---|
| `--main-bg` | `#f4f6fb` (blue-white) | `#F3F0E8` (warm cream) |
| `--surface` | `#ffffff` | `#FAF8F3` (off-white) |
| `--border` | `#e8ecf3` | `#E0D9CC` (warm greige) |
| `--text` | `#1e2a3a` (cool navy) | `#2C2318` (espresso) |
| `--muted` | `#64748b` (slate) | `#7A6E64` (warm grey-brown) |

#### Sidebar / Right Panel

| Token | Before | After |
|---|---|---|
| `--sidebar-bg` / `--rp-bg` | `#2c3e6b` (navy) | `#3B2F1E` (dark walnut) |
| `--sidebar-hover` | `#374d7f` | `#4F3E28` |
| `--sidebar-active` | `#4a5f9a` | `#6B5237` |
| `--sidebar-text` | `#b0c4de` | `#C9B89E` |

#### Primary Accent (blue → sage)

| Token | Before | After |
|---|---|---|
| `--blue` | `#4d7cfe` | `#5B8C85` (deep sage) |
| `--blue-lt` | `#eef2ff` | `#E9F0EF` (sage tint) |
| `--teal` | `#00c9a7` | `#5B8C85` (unified with sage) |

#### Alert / Danger (coral → terracotta)

| Token | Before | After |
|---|---|---|
| `--coral` / `--warn` | `#ff6b6b` / `#ff7675` | `#E26C3B` (terracotta) |
| `--warn-lt` | `#fff0f0` | `#FDF0E9` |

#### Success

| Token | Before | After |
|---|---|---|
| `--ok` | `#55efc4` (neon mint) | `#7DB89A` (muted sage green) |
| `--ok-lt` | `#e8fdf5` | `#EBF6F1` |

#### Semantic Levels (mid-contrast earthy)

| Level | Before | After |
|---|---|---|
| `--lvl-1` | `#00b894` | `#4FA882` |
| `--lvl-2` | `#55efc4` | `#7DB89A` |
| `--lvl-3` | `#f9ca24` (sharp yellow) | `#D99B3F` (mustard) |
| `--lvl-4` | `#f0932b` (orange) | `#E26C3B` (terracotta) |
| `--lvl-5` | `#eb4d4b` | `#C0392B` (red, intentionally kept vivid) |

#### New Tokens (bug fixes)

- `--accent: #5B8C85` — previously used in `.aqi-forecast-block` but never defined (silent failure)
- `--hover: #EDE7DD` — previously used as hover background but never defined (silent failure)
- `--font-serif: 'ZCOOL XiaoWei', 'Noto Serif TC', serif` — new token for literary accent

#### Typography

- `.view-header h1` now uses `var(--font-serif)` with `letter-spacing: 0.02em`
- All other UI elements retain `Inter` (legibility over aesthetics for data-dense components)

---

### `web/templates/dashboard.html`

- Removed **Auto** option from theme segmented control (sidebar + mobile sheet settings)
- Two options remain: **Dark** / **Light**

### `web/static/app.js`

- `initSystemTheme()` rewritten: on first load with no saved preference, defaults to system `prefers-color-scheme` and **persists that choice** to `localStorage` as either `'dark'` or `'light'`
- Removed the `mq.addEventListener('change', apply)` listener — preference is now explicit, not auto-reactive
- `window.setTheme(val)` always calls `localStorage.setItem` (no more `removeItem` path for 'auto')
