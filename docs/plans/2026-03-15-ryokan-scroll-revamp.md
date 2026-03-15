# Player Sheet Revamp — Ryokan Scroll

**Date:** 2026-03-15

## Problem

Following the card-drawer facelift (see `2026-03-15-player-sheet-facelift.md`), the player sheet still read as a generic mobile UI component. The paragraph cards, segmented tab bar, and section boxes borrowed patterns from common design systems. The goal was a complete aesthetic overhaul — something clearly belonging to this app's earthy Taiwanese identity — without removing any features.

## Solution

Redesign the sheet as a **washi-paper scroll**: warm parchment surface with ink-on-paper typography, a woven reed-mat handle strip, circular calligraphy seal-stamp navigation, and a vertical ink thread that traces audio playback progress along the left edge.

### Visual Language

```
┌─────────────────────────────────────────────────────────────┐
│ ║║║║║║║║║║║║║║║║║║ washi handle ║║║║║║║║║║║║║║║║║║║║║║║║│
│                                                             │
│   ╭──────╮    ╭──────╮                              ✕     │
│   │  活  │    │  ⚙   │   (活 = active, coral fill)        │
│   │▓▓▓▓▓▓│    │      │                                    │
│   ╰──────╯    ╰──────╯                                    │
│ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │
│                                                             │
│ ║  天氣概況   今天早上台北地區，北部沿海有零星降雨...        │
│ ║             氣溫攝氏24度，濕度79%，體感涼爽。             │
│ ║                                                           │
│ ║  - - - ∿ - - - - - - - - - - - - - - - - - - - - - -   │
│ ║                                                           │
│ ║  健康建議   注意心臟健康，氣壓明顯變化...                 │
│ ║             建議補充水分，避免過度勞累。                   │
│                                                  Claude ·  │
└─────────────────────────────────────────────────────────────┘
║ = coral ink thread filling with audio progress
```

### Key Design Decisions

- **Handle**: Full-width 12px strip using `repeating-linear-gradient` to simulate woven textile texture, replacing the centered pill dot.
- **Navigation**: Two seal-stamp buttons (活 = narration, ⚙ = settings) — 46px circles, `ZCOOL XiaoWei` serif. Active = `var(--coral)` fill + coral glow shadow. Inactive = `var(--border)` ring only. Chat tab remains in DOM but is not surfaced.
- **No tab bar container**: The segmented pill container removed entirely. Seals float directly in the header with a 1px fade-in/out gradient rule beneath.
- **Prose layout**: `.ps-para` card boxes removed. Each paragraph renders as `.ps-prose` — plain text with `.ps-prose-label` (coral serif, 0.88rem) above `.ps-prose-body`. Paragraphs separated by `.ps-prose-divider` (gradient left-to-transparent brush rule).
- **Ink thread**: `6px` vertical bar (`div.ps-ink-track`) left of the prose column. `var(--hover)` background, fills with `var(--coral)` via `ps-ink-fill` height `0%→100%` on `audio.timeupdate`.
- **Parchment**: Sheet gains two warm `radial-gradient` overlays using `--tint-heat` (top-right corner) and `--tint-caution` (bottom-left), giving an aged-paper warmth against the cream surface.
- **Settings**: `.ps-section-card` card boxes replaced with flat border-bottom rows — paper-form aesthetic. Segmented control checked state changed from teal to coral throughout.
- **Speed pills**: Active/hover states changed from `--blue` to `--coral` / `--warn-lt`.

## Layout Structure

```
.player-sheet (flex column)
  .player-sheet-handle          ← woven strip
  .player-sheet-header          ← transparent, seal nav + close
  .ps-scroll-rule               ← gradient divider
  .player-sheet-body (flex col, overflow hidden)
    #ps-panel-narration (flex col)
      .ps-controls              ← mobile-only: duration + speed pills
      .ps-scroll-row (flex row)
        .ps-ink-track           ← 6px vertical progress track
        .ps-scroll-content      ← overflow-y: auto
          #ps-narration-content ← .ps-prose + .ps-prose-divider cards
    #ps-panel-settings (flex col, overflow-y: auto)
      .ps-section-card ×3       ← flat border-bottom rows
    #ps-panel-chat (hidden)     ← unchanged, not surfaced
```

## Files Changed

| File | Change |
|------|--------|
| `web/static/style.css` | Handle → woven strip; header → transparent; body → flex column overflow hidden; `.ps-para*` → `.ps-prose*`; new `.ps-ink-track / .ps-ink-fill / .ps-ink-track-bg`; new `.ps-scroll-row / .ps-scroll-content`; `.player-sheet-tabs / .ps-tab*` → `.ps-seal-nav / .ps-seal*`; new `.ps-scroll-rule`; `.ps-section-card` → flat rows; seg-ctrl + speed pills → coral; removed two-column layout; updated mobile overrides |
| `web/templates/dashboard.html` | Seal nav replaces tab nav; `ps-scroll-rule` div added; narration panel wrapped in `.ps-scroll-row` with `.ps-ink-track` + `.ps-scroll-content` |
| `web/static/app.js` | `_playerBarSetAudio()` generates `.ps-prose` + `.ps-prose-divider` HTML; `initPlayerSheet()` queries `.ps-seal` instead of `.ps-tab`; new `initInkThread()` attaches `timeupdate` listener; settings/chat triggers updated to `.ps-seal` selectors |

## Warm Color Usage

All accents draw exclusively from the earthy palette:

| Element | Color |
|---------|-------|
| Active seal button | `var(--coral)` #E26C3B |
| Ink thread fill | `var(--coral)` #E26C3B |
| Prose section label | `var(--coral)` #E26C3B |
| Parchment overlay | `var(--tint-heat)` + `var(--tint-caution)` |
| Prose divider | `var(--border)` #E0D9CC |
| Ink track background | `var(--hover)` #EDE7DD |
| Inactive seal ring | `var(--border)` #E0D9CC |
| Settings row dividers | `var(--border)` #E0D9CC |
| Speed pill active | `var(--warn-lt)` + `var(--coral)` |
| Seg-ctrl checked | `var(--coral)` #E26C3B |
