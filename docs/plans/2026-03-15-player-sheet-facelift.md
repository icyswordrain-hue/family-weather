# Player Sheet Facelift — Elevated Card-Drawer

**Date:** 2026-03-15

## Problem

The player sheet (narration / settings / chat panel that slides up from the bottom) was assembled from components originally built for the dark sidebar context. On the warm cream surface this produced several visual mismatches:

- **Flat top edge** — the sheet slid up with a hard square top, inconsistent with the 16px radius used on every card in the main panel.
- **Cold blue accents** — active tab highlight, speed pills, and the progress bar all used `--blue-lt` / `--blue` tints whose CSS fallback values (`#4d7cfe`) bled through as cold blue on first paint, clashing with the earthy palette.
- **`rp-btn` context mismatch** — buttons in the Settings tab reused `.rp-btn`, a class designed for the dark sidebar (white-on-dark semitransparent fills), requiring brittle `.ps-tab-panel .rp-btn` overrides to look passable on a cream surface.
- **All-caps muted paragraph headers** — `.ps-para-title` used `text-transform: uppercase` + `letter-spacing` in `var(--muted)` gray. Every other section header in the app uses the serif accent font (`ZCOOL XiaoWei`) with earthy color.
- **Handle bar mobile-only** — the drawer handle was hidden on desktop, losing the visual cue that the sheet is a draggable surface.
- **Plain header background** — the tab header blended into the scrollable body with no visual separation.

## Solution

Redesign the sheet as a first-class card-drawer surface that follows the same visual language as the lifestyle panel:

- **Rounded top corners** (20px) and a warm shadow (`rgba(44,35,24,0.15)`) replacing the flat border + cold drop shadow.
- **Handle bar** always visible — centered 40px × 4px pill in `var(--border)` tan, present on both desktop and mobile.
- **Header background** `var(--main-bg)` (#F3F0E8, the slightly darker cream) creates a distinct zone separating the chrome from the scrollable body.
- **Tab bar as segmented pill** — `.player-sheet-tabs` gains a warm tint pill container (`rgba(44,35,24,0.07)`). Active tab = lifted white card with soft shadow; no blue highlight anywhere.
- **Narration paragraphs as card tiles** — each `.ps-para` becomes a bordered card (`var(--surface)` + `var(--border)` + `var(--shadow)` + 12px radius). Paragraph titles use `ZCOOL XiaoWei` serif in `var(--teal)`, replacing all-caps muted gray. The narration source badge (Claude / Gemini / template) floats to the top-right of the final card's title row.
- **Settings section cards** — controls grouped in `.ps-section-card` tiles (`var(--main-bg)` background + border + 12px radius): one for the language segmented control, one for the action buttons.
- **New `.ps-btn` / `.ps-btn-secondary`** — native sheet-surface buttons replace all `rp-btn` overrides. Primary: teal fill (`var(--teal)`), hover lightens to `var(--ok)`. Secondary: warm tan fill (`var(--hover)`) with border. All `loading` / `spinning` animation classes transferred.
- **Segmented control** in sheet context uses a warm dark tint background (`rgba(44,35,24,0.08)`) and teal active state with a teal box-shadow instead of the cold blue glow.

## Files Changed

| File | Change |
|------|--------|
| `web/static/style.css` | `.player-sheet` — radius + warm shadow; `.player-sheet-handle` — always-visible desktop default; `.player-sheet-header` — `--main-bg` background; `.player-sheet-tabs` — pill container; `.ps-tab.active` — card-lift style; `.ps-para` / `.ps-para-title` — card tile + serif teal; `#ps-narration-content` — remove width constraint; added `.ps-para-title-row`, `.ps-section-card`, `.ps-section-label`, `.ps-last-updated`, `.ps-btn`, `.ps-btn-secondary` and dark-mode variants; removed old `.ps-tab-panel .rp-btn*` overrides |
| `web/templates/dashboard.html` | Settings panel: `sidebar-control-group` → `ps-section-card` wrapping; buttons `rp-btn` → `ps-btn`; `rp-last-updated` class → `ps-last-updated` (id unchanged) |
| `web/static/app.js` | Narration render: source badge moved inline to the last paragraph card's title row (`.ps-para-title-row` flex) instead of a trailing `.ps-meta` div |

## Before / After

```
Before                          After
──────────────────────          ──────────────────────────────
[flat top edge, no radius]      [╭──────────────────────────╮]
[tab bar: blue active]          [  ──── handle bar ────      ]
                                [╰──────────────────────────╯]
                                [main-bg header zone        ]
                                [  ╔══╗ Narration Settings  ]
                                [  ╚══╝ (card-lift active)  ]

Narration tab                   Narration tab
  MORNING FORECAST              ┌─────────────────────────┐
  Partly cloudy...              │ Morning Forecast  badge │
                                │ Partly cloudy...        │
                                └─────────────────────────┘

Settings tab                    Settings tab
  Language (dark-sidebar btn)   ┌─ Language ──────────────┐
  [rp-btn override]             │  [EN] [中文]             │
                                └─────────────────────────┘
                                ┌─ Actions ───────────────┐
                                │  [teal] 重新整理         │
                                │  [tan]  重新合成語音     │
                                └─────────────────────────┘
```

## Amendment — source badge repositioned + settings warmer tones (2026-03-15)

**Badge:** The Claude / Gemini / template source badge was initially placed in the last paragraph card's title row, then removed. Final position: a small right-aligned `.ps-meta` row beneath all paragraph cards. All source-specific colour classes dropped — badge uses a single neutral style (`var(--hover)` background, `var(--muted)` text) so it reads as a quiet footnote rather than a branded chip. Dead CSS (`.source-claude`, `.source-gemini`, `.source-template`, `.ps-para-title-row`) deleted.

**Settings buttons:** `.ps-btn` primary colour changed from `var(--teal)` (#5B8C85, sage) to `var(--coral)` (#E26C3B, terracotta), hover darkens to `var(--warn)`. Matches the warm earthy tone of the settings section cards rather than the cooler green used in data-driven UI elements.

## Amendment — CJK stroke weight boost (2026-03-15)

Chinese characters throughout the UI appeared too light relative to the earthy, warm visual language of the design. Bumping `font-weight` globally was not an option because it would also thicken English text (Inter).

**Technique:** CSS `@font-face` `unicode-range` override. By declaring new `@font-face` blocks for `Noto Sans TC` that cover only CJK codepoints and point to a heavier woff2 binary, the browser uses the heavier file for Chinese glyphs while Latin glyphs (rendered by Inter, which lies outside the unicode-range) are untouched.

Two remappings were added:

- CSS `font-weight: 400` → loads Noto Sans TC **weight-500** woff2 (medium strokes)
- CSS `font-weight: 500` → loads Noto Sans TC **weight-700** woff2 (bold strokes)

202 `@font-face` blocks were generated from the Google Fonts CSS2 API (`Noto+Sans+TC:wght@500;700`) and inserted before `:root {` in `style.css`. The 101 blocks per weight correspond to Google Fonts' CJK unicode-range slices; the non-CJK tail subsets (cyrillic, vietnamese, latin-ext, latin) were excluded.

**What changes:** Chinese body text, card titles, narration paragraphs — all Noto Sans TC rendering.
**Unchanged:** English text (Inter), serif display titles (ZCOOL XiaoWei — different font-family), monospace numbers (Fira Code).

| File | Change |
| --- | --- |
| `web/static/style.css` | 202 `@font-face` CJK weight-remap blocks inserted before `:root {` |
| `web/templates/dashboard.html` | `style.css` cache-bust version v19 → v20 |
