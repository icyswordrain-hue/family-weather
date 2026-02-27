# Mobile-Responsive Overhaul — Architecture Design (Final)

> **Date:** 2026-02-27
> **Status:** All architecture decisions resolved. Ready for implementation planning.

---

## Summary

Overhaul the 3-column desktop-only weather dashboard across three phases:
- **Phase 1**: Desktop structural cleanup — simplified panels, narration removal, controls reorganised
- **Phase 2**: Mobile-first responsive layout — single-column continuous scroll, player bar, FAB
- **Phase 3**: New features and deep refactors — short narration, tablet breakpoint, nav strategy pattern

Narration dissolves from a dedicated view into a persistent sticky player bar with expandable half-sheet on both desktop and mobile.

---

## Decisions

| Topic | Decision |
|---|---|
| Views | **2 views** (Lifestyle + Dashboard). Narration dissolved into sticky player bar |
| Mobile navigation | Continuous scroll, no tab bar — single unbroken page |
| Narration text | Half-sheet (60vh overlay) slides up from player bar — **same on desktop and mobile** |
| Nav system | Option (b): boot-time `matchMedia` → `initMobileNav()` or `initSidebarNav()` |
| Player bar density | Minimal: ▶/⏸ + progress bar + duration |
| Player bar no-audio | Ambient pulse: `☁ Fetching briefing…` with soft icon pulse animation |
| Clock | Desktop: analog in sidebar. Mobile: digital `#mobile-clock` in compact header (time + location side-by-side) |
| Desktop controls | Lang + provider toggles at **sidebar bottom**. No manual theme toggle — `prefers-color-scheme` auto |
| Mobile controls | **FAB only** (mobile) → slide-up sheet: lang, provider, refresh |
| Desktop right panel | Shrunk to ~180px. Contents: refresh + system log only |
| Section separator | Section header card (styled card separating Lifestyle / Dashboard on mobile) |
| Bar dark mode | Follow existing `html.dark` CSS variables |
| Tablet | Deferred to Phase 3 |
| Short narration | Deferred to Phase 3 |

---

## Target Architecture

### Desktop (Phase 1 result)

```
┌──────────┬──────────────────────────┬──────────┐
│ Sidebar  │  Main (2 tabs)           │  Right   │
│ Analog   │  [Lifestyle][Dashboard]  │  ~180px  │
│ clock    │                          │ Refresh  │
│ Nav (2)  │                          │ Log      │
│ ──────── │                          │          │
│ Lang     │                          │          │
│ Provider │                          │          │
└──────────┴──────────────────────────┴──────────┘
       🔊 Player bar (fixed bottom of main panel)
```

### Mobile (Phase 2 result)

```
┌──────────────────────────────────┐
│ [Compact Header]                 │
│  🕐 10:42  📍 台北市              │
├──────────────────────────────────┤
│                                  │
│ ┌── Section Header Card ───────┐ │
│ │  🚲  Lifestyle Guide         │ │
│ └──────────────────────────────┘ │
│   [Lifestyle cards...]           │
│                                  │
│ ┌── Section Header Card ───────┐ │
│ │  📊  Weather Dashboard       │ │
│ └──────────────────────────────┘ │
│   [Hero, gauges 2×2, 24h, 7d]   │
│                                  │
│  (padding-bottom: 68px)          │
├──────────────────────────────────┤
│ 🔊 ▶  Morning Briefing  3:42  ⌄ │  ← Player bar (52px fixed)
└──────────────────────────────────┘
                          ⚙️ FAB (bottom-right, above player bar)
```

---

## Phase 1 — Desktop Structural Cleanup

### Goal
Simplify desktop layout. Remove narration view. Reorganise controls to sidebar. Shrink right panel.

### HTML (`dashboard.html`)

| Change | Detail |
|---|---|
| Remove `#view-narration` | Full DOM removal. Audio moves to player bar, text to half-sheet |
| Remove nav button | Delete narration `button.nav-item` from sidebar |
| Add player bar | `<div class="player-bar">` in main panel — fixed bottom |
| Add player sheet | `<div class="player-sheet">` — half-sheet overlay for narration text |
| Add sidebar controls section | Lang toggle + provider toggle below nav items in `.sidebar` |
| Remove right panel toggles | Remove lang + provider radios from `.rp-controls-section` |
| Remove theme toggle button | Delete `#theme-toggle` + inline `<script>` theme logic |
| Remove `#narration-meta` | Was inside narration view header — no longer needed |

### CSS (`style.css`)

| Change | Detail |
|---|---|
| `--rp-w` | Shrink from `280px` to `180px` |
| Player bar | `position: fixed; bottom: 0; height: 52px; width: 100%` (within main panel on desktop) |
| Player bar pulse | `@keyframes pulse` on `☁` icon for loading state |
| Half-sheet | `position: fixed; bottom: 52px; height: 60vh; overflow-y: auto; z-index: 200` |
| Sidebar controls section | Styles for lang + provider toggle group at sidebar bottom |
| System theme | `@media (prefers-color-scheme: dark)` listener replaces manual toggle class |

### JS (`app.js`)

| Change | Detail |
|---|---|
| `initPlayerBar()` | New: wire `audio_url`; play/pause; duration display; pulse loading state |
| `initPlayerSheet()` | New: expand/collapse half-sheet; `body overflow: hidden` lock/restore |
| `initSystemTheme()` | New: `matchMedia('prefers-color-scheme: dark')` → `html.dark`; removes `localStorage` theme |
| `initSidebarControls()` | New: wire lang + provider toggles from sidebar DOM location |
| `applyLanguage()` | Already exists — no change needed if new sidebar inputs share same `name` attribute |
| Remove | `initMobileDrawer()`, manual theme toggle wiring, narration view render calls |
| `render()` dispatch | Remove `renderNarrationView()` call; narration text written to player sheet instead |

---

## Phase 2 — Mobile Responsive Layout

### Goal
Single-column continuous scroll on mobile. No bottom tab bar. FAB for controls. Compact header with digital clock.

### HTML additions

| Change | Detail |
|---|---|
| Compact header | `#mobile-clock` + location element — hidden on desktop |
| FAB + sheet | `<div class="fab-btn">⚙️</div>` + `<div class="fab-sheet">` with lang, provider, refresh |
| Section header cards | Styled cards inside `#view-lifestyle` and `#view-dashboard` |

### CSS additions (`@media max-width: 767px`)

| Change | Detail |
|---|---|
| App shell | Collapse to 1-column. Hide `.sidebar`, `.right-panel` |
| Show mobile elements | `.compact-header`, `.fab-btn` visible |
| All views visible | `.view-container { display: block }` — no `.active` gating |
| Player bar | Full width, `bottom: 0` |
| FAB | `position: fixed; bottom: 68px; right: 16px` |
| Gauge grid | `repeat(4,1fr)` → `repeat(2,1fr)` |
| System log | `display: none` |
| Padding | `padding-bottom: 68px` on scroll container |

### JS additions

| Change | Detail |
|---|---|
| `initNav()` | Boot-time `matchMedia` → `initMobileNav()` or `initSidebarNav()` |
| `initMobileNav()` | `IntersectionObserver` scroll-spy (no tab switching needed — just highlight-free anchoring) |
| `updateClock()` | Extend to also target `#mobile-clock` |
| `initFAB()` | FAB open/close + sheet backdrop dismiss |

---

## Phase 3 — Features & Deep Refactor

- NavController refactor (strategy pattern — option c)
- Tablet responsive breakpoint (768–1023px)
- Short narration: new LLM prompt + TTS + `[Brief|Full]` player toggle
- Debug view: `?debug=1` gates system log + status indicators
- Desktop sidebar deeper reconsider (clock proportion, layout)
