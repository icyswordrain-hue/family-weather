# Mobile-Responsive Overhaul — Architecture Design (v3, snapshot)

> **Snapshot taken after:** Q1–Q10 all resolved (Q8 deferred to Phase 2).
> **Next version:** Implementation plan (writing-plans).

---

## All Decisions (Complete)

| Q | Topic | Decision |
|---|---|---|
| Q1 | Mobile navigation | Continuous scroll + scroll-spy. Tab bar = anchors, not view-switcher |
| Q2 | Narration text | Expandable half-sheet sliding up from player bar (overlays, doesn't push) |
| Q3 | Nav system | Option (b) — two separate systems, boot-time viewport check |
| Q4 | Player bar density | Minimal: ▶/⏸ + progress bar + **duration** only |
| Q5 | Player bar no-audio state | (i) Ambient pulse: `☁ Fetching briefing…` with soft pulse animation on icon |
| Q6 | Clock | Analog in desktop sidebar (existing). Digital in mobile compact header via new `#mobile-clock` + `updateClock()` dual-target. Time + location side-by-side |
| Q7 | Controls location | Lang + provider toggles: **FAB sheet only** (removed from right panel). Theme: `prefers-color-scheme` auto (no manual toggle). Right panel: refresh + system log only |
| Q8 | Tablet (768–1023px) | Deferred to Phase 2 — no optimization in Phase 1 |
| Q9 | Section separator | Section header card (visual card separating Lifestyle / Dashboard) |
| Q10 | Bar dark mode | Follow existing `html.dark` theme CSS variables |

---

## Target Architecture

### Mobile
```
┌──────────────────────────────────┐
│ [Compact Header]                 │
│  🕐 10:42  📍 台北市              │  ← #mobile-clock + location
├──────────────────────────────────┤
│                                  │
│ ┌── Section Header Card ───────┐ │
│ │  🚲  Lifestyle Guide         │ │  ← id="view-lifestyle"
│ └──────────────────────────────┘ │
│   [Lifestyle cards...]           │
│                                  │
│ ┌── Section Header Card ───────┐ │
│ │  📊  Weather Dashboard       │ │  ← id="view-dashboard"
│ └──────────────────────────────┘ │
│   [Hero, gauges 2×2, 24h, 7d]    │
│                                  │
│  (padding-bottom: 116px)         │
├──────────────────────────────────┤
│ 🔊 ☁ Fetching briefing… [pulse] │  ← Player bar (52px, fixed)
│    OR: ▶  Morning Briefing  0:00/3:42  ⌄ │
├──────────────────────────────────┤
│  🚲 Lifestyle   │  📊 Dashboard  │  ← Bottom tab bar (60px, fixed)
└──────────────────────────────────┘
              ⚙️ FAB (bottom-right, above bars)
```

**FAB Sheet contents (mobile + desktop):**
- Lang toggle (中文 / EN)
- Provider toggle (Claude / Gemini)
- Refresh button

### Desktop
```
┌──────────┬────────────────────────┬──────────┐
│ Sidebar  │  Main (2 tabs)         │  Right   │
│ ─────── │  [Lifestyle][Dashboard]│  Panel   │
│ Analog  │                        │ Refresh  │
│ clock   │                        │ Log      │
│ ─────── │  ─────────────────── │          │
│ Nav (2) │  🔊 Player Bar (fixed) │          │
└──────────┴────────────────────────┴──────────┘
                                    ⚙️ FAB (controls)
```

---

## Phase 1 — Scope (Mobile Layout, No Backend)

### HTML changes (`dashboard.html`)
- [ ] Add `#mobile-clock` + mobile location element in new compact header
- [ ] Add `<nav class="bottom-tab-bar">` (icons + labels, 2 items)
- [ ] Add `<div class="fab-btn">` + `<div class="fab-sheet">` (lang, provider, refresh)
- [ ] Add `<div class="player-bar">` (fixed, above tab bar)
- [ ] Add `<div class="player-sheet">` (half-sheet for narration text)
- [ ] Add section header cards inside `#view-lifestyle` and `#view-dashboard`
- [ ] Remove narration view (`#view-narration`) from nav; keep in DOM for now (Phase 2 cleanup)
- [ ] Remove manual theme toggle button
- [ ] Remove lang + provider radios from right panel

### CSS changes (`style.css`)
- [ ] `@media (max-width: 767px)`: collapse `.app-shell` to 1-column
- [ ] Hide `.sidebar`, `.right-panel` on mobile
- [ ] Show `.compact-header`, `.bottom-tab-bar`, `.fab-btn` on mobile
- [ ] `.view-container { display: block }` on mobile (all visible, scroll-driven)
- [ ] Player bar: fixed, `bottom: 60px`, `height: 52px`, full width
- [ ] Player bar pulse animation for loading state
- [ ] Half-sheet: `position: fixed; bottom: 116px; height: 60vh`
- [ ] FAB: `position: fixed; bottom: 116px; right: 16px`
- [ ] FAB sheet: slide-up, `position: fixed; bottom: 116px`
- [ ] Section header card styles
- [ ] Gauge grid: `repeat(4,1fr)` → `repeat(2,1fr)` on mobile
- [ ] System log: `display: none` on mobile
- [ ] `padding-bottom: 116px` on mobile scroll container
- [ ] `prefers-color-scheme: dark` → apply `html.dark` class (replaces manual toggle logic)

### JS changes (`app.js`)
- [ ] `initNav()` — boot-time viewport check → `initMobileNav()` or `initSidebarNav()`
- [ ] `initMobileNav()` — `IntersectionObserver` scroll-spy + bottom tab bar anchor nav
- [ ] `updateClock()` — extend to also target `#mobile-clock`
- [ ] `initFAB()` — FAB open/close + sheet backdrop dismiss
- [ ] `initPlayerBar()` — wire `audio_url` from broadcast data; play/pause; duration display; pulse state
- [ ] `initPlayerSheet()` — expand/collapse half-sheet; body scroll lock
- [ ] `initSystemTheme()` — `matchMedia('prefers-color-scheme')` listener → `html.dark` class; remove `localStorage` theme logic
- [ ] Remove `initMobileDrawer()` (replaced by FAB)
- [ ] Remove `handleLangChange()` right-panel wiring (moved to FAB sheet)

---

## Phase 2 — Scope (Desktop Revamp)

- Desktop right panel: refresh + log only (controls moved to FAB)
- Debug view: `?debug=1` gates system log + status indicators
- NavController refactor (option c) if warranted
- Tablet (768–1023px) responsive breakpoint
- Short narration: new LLM prompt + TTS + `[Brief|Full]` player toggle
- Desktop sidebar reconsider (clock size, layout)

---

## Open: Narration View in Phase 1

`#view-narration` stays in DOM during Phase 1 but is removed from tab navigation. The audio player bar + half-sheet replace its function entirely. Full DOM removal deferred to Phase 2 cleanup to reduce Phase 1 risk.
