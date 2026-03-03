# Mobile-Responsive Overhaul — Architecture Design (v2, snapshot)

> **Snapshot taken after:** Q1, Q2, Q3 (partial) resolved. Q3 nav strategy still pending discussion.
> **Next version:** v3 — Q3 resolved, remaining questions Q4–Q10.

---

## Decisions Made (at this snapshot)

| Decision | Choice |
|---|---|
| Views | **2 views** (Lifestyle + Dashboard) — narration dissolved |
| Narration | Sticky bottom audio bar — Phase 1: existing full audio only |
| Mobile layout | Single-column, continuous scroll with scroll-spy anchors |
| Navigation (mobile) | Bottom tab bar — icons + labels, scroll-to-anchor |
| Navigation (desktop) | Existing `initSidebarNav()` JS tab-switching unchanged |
| Controls (mobile) | FAB → slide-up sheet |
| Controls (desktop) | Inline right panel (simplified in Phase 2) |
| Desktop layout | Phase 2 revamp |
| System log (mobile) | Not rendered (`display:none` < 768px) |
| System log (desktop) | Collapsible, gated behind `?debug=1` |
| System log (non-dev view) | Moved to dedicated debug/status view — Phase 2 |
| Short narration | Deferred to Phase 2 |

---

## Q1 — Mobile Navigation (✅ Resolved)

**Decision: Continuous scroll with scroll-spy on mobile. JS tab-switching stays desktop-only.**

### Architecture
```
Mobile: IntersectionObserver (scroll-spy)
  ├── Observes #view-lifestyle, #view-dashboard
  ├── Updates bottom tab bar active state on crossing 0.4 threshold
  └── Tab bar taps → scrollIntoView({ behavior: 'smooth' })

Desktop: initSidebarNav() (unchanged)
  ├── Hides/shows .view-container via .active class
  └── Sidebar nav-item.active manages state
```

### Conflict mitigations
- `padding-bottom: 116px` on mobile scroll container (52px player + 60px tab bar + 4px gap)
- Player bar tap target: `▶` left, title center, `⌄` chevron right — **not the full bar**
- `IntersectionObserver threshold: 0.4` prevents jitter at section boundaries
- `body overflow: hidden` + explicit restore on sheet open/close (iOS Safari fix)

---

## Q2 — Narration Text Placement (✅ Resolved)

**Decision: Expandable half-sheet sliding up from the player bar.**

### Architecture
```
[Player Bar]  ← fixed, above tab bar
  └── tap ⌄ → [Half-Sheet]
        ├── position: fixed; bottom: 116px; height: 60vh
        ├── overflow-y: auto (text scrolls inside)
        ├── tap outside / swipe-down → closes
        └── backdrop overlay, body overflow locked
```

### Half-sheet contents
```
┌─────────────────────────────────┐
│  ╌╌╌╌  drag handle             │
│  📻 Morning Briefing            │
│  ─────────────────────────────  │
│  [Narration text, scrollable]   │
│  ───────────── 2:34 / 5:12 ─── │
│  ◀15  ▶  ▐▐  15▶               │
└─────────────────────────────────┘
```
Overlays content (does not push). Tab bar + player bar remain visible beneath.

---

## Q3 — Navigation System (⏳ Pending at this snapshot)

Context: `initSidebarNav()` currently handles all view switching. On mobile this becomes scroll-spy with no view switching. Three options proposed:

- **(a) One unified nav controller** — both modes in one object, CSS decides which controls are visible
- **(b) Two separate systems** — `initSidebarNav()` desktop only; new `initMobileNav()` mobile only; boot-time viewport check
- **(c) NavController + strategy pattern** — clean OO refactor, `DesktopTabStrategy` / `MobileScrollStrategy`

> *Resolution captured in v3.*

---

## Phases (at this snapshot)

### Phase 1 — Mobile Layout
- CSS `@media` collapse to single column (< 768px)
- Sticky bottom audio bar + half-sheet
- Bottom tab bar (scroll-to-anchor)
- Dissolve Narration view → 2-view nav
- Scroll-spy `IntersectionObserver`
- FAB + controls slide-up sheet
- `padding-bottom` compensation
- System log hidden on mobile
- Gauge grid: 4-col → 2-col on mobile

### Phase 2 — Desktop Revamp + Short Narration
- Desktop right panel simplification
- Debug view (`?debug=1`): system log + status
- Non-debug panel: controls-only redesign
- Short narration (< 60s) — new prompt + TTS + player toggle
- Desktop sidebar reconsider (clock size/layout)

---

## Open Questions (Q4–Q10 at this snapshot)

**Q4.** Player bar density: minimal (just ▶ + progress) vs. informational (title, duration, summary text)?

**Q5.** Player bar in "no audio" state: (a) hidden, (b) disabled/loading, (c) only appears after first load?

**Q6.** Desktop sidebar: keep the 140px analog clock? Or shrink/replace with digital-only?

**Q7.** Right panel contents after Phase 2 simplification — which survive: provider toggle, lang toggle, refresh, theme toggle, system log?

**Q8.** Tablet (768–1023px): 2-column (sidebar + main) or single-column mobile layout?

**Q9.** Section separator between Lifestyle / Dashboard on mobile: divider, section header card, gap+shadow, or seamless?

**Q10.** Bottom bars (player + tab) in dark mode: follow existing theme vars, always dark, or frosted glass independent of theme?
