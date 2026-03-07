# Horizontal 36-Hour Forecast Layout

**Date:** 2026-03-07
**Status:** Implemented (commit `0813c2f`)

## Goal

Replace the 4-column × N-row vertical card grid with stacked horizontal rows — one per time slot (Morning / Afternoon / Evening / Overnight) — matching the visual language of the 7-day layout but at 2× the row height (168px desktop, 128px mobile).

```
MORNING                                    A  Go out
[☀️ 72px]   22°  ━━━━━▓▓▓▓▓━━━━━━━  28°   All clear
06:00        ↑↑↑↑ 9px range bar ↑↑↑↑
```

## Motivation

The previous 4-column card layout required scanning across a wide grid. The horizontal row layout pairs the visual anchor (icon + time slot) with the single most important piece of data per slot (temperature range) and the two decision-relevant outputs (outdoor suitability + rain safety). Eliminated: AT hero, AQI, humidity, wind — information already covered by the hero section and other views.

## Files Changed

| File | Change |
|------|--------|
| `web/static/app.js` | Replaced `(data.timeline || []).forEach` card-building loop (old lines 556–661) with new `.tc-seg-row` row-building loop |
| `web/static/style.css` | Added `.tc-seg-*` CSS block after `.tc-transition` (line ~1011); added `#ov-timeline.timeline-grid` flex-column override |

No HTML or backend changes. The `#ov-timeline` container keeps its `timeline-grid` HTML class; the CSS override `#ov-timeline.timeline-grid { display: flex; ... }` wins via ID+class specificity (same pattern as `#ov-weekly-timeline.weekly-grid`).

## Layout Architecture

**Three fixed sections per row:**

| Section | Class | Width | Contents |
|---------|-------|-------|----------|
| Left | `.tc-seg-left` | `flex: 0 0 90px` | Slot label → 72px icon → start time |
| Center | `.tc-seg-center` | `flex: 1` | Range bar row only (min° \| 9px bar \| max°) |
| Right | `.tc-seg-right` | `flex: 0 0 100px` | Outdoor grade (top) + precip text (bottom) |

**Day/night differentiation:** `border-left: 4px solid var(--blue)` for day; `var(--muted)` for Evening/Overnight slots.

## Data Fields Used

| Field | Source | Example |
|-------|--------|---------|
| `seg.display_name` | `routes.py` | "Morning" |
| `seg.start_time` | CWA | "2026-03-07T06:00:00+08:00" |
| `seg.cloud_cover` / `seg.Wx` | CWA | "Sunny" |
| `seg.MinAT` / `seg.MaxAT` | `weather_processor.py` | 22.1 / 28.3 |
| `seg.outdoor_grade` / `seg.outdoor_label` | outdoor index | "A" / "Go out" |
| `seg.precip_text` | `safe_minutes_to_level()` — `data/scales.py:172` | "All clear" / "~45 min" / "Stay in" |
| `seg.precip_level` | `safe_minutes_to_level()` | 1 / 3 / 5 → `.lvl-*` |

`precip_text` and `precip_level` are derived from the **Poisson distribution** via `pop_to_safe_minutes()` (`scales.py:144`): given a 6-hour PoP and a 15% acceptable-rain-risk threshold, it returns the max safe outing duration in minutes. `safe_minutes_to_level()` maps this to human text ("All clear" ≥120 min, "~N min" for 20–119, "Stay in" <20 min).

## CSS New Classes

| Class | Purpose |
|-------|---------|
| `.tc-seg-row` | One row per slot; flex, `var(--surface)` bg, `border-radius: 12px`, `min-height: 168px` |
| `.tc-seg-row.tc-seg-night` | Muted left border for Evening/Overnight |
| `.tc-seg-left` | Left column — label + icon + time |
| `.tc-seg-label` | Slot name in muted uppercase |
| `.tc-seg-time` | Start hour (e.g. "06:00"), tabular-nums |
| `.tc-seg-center` | Flex-grow center, `align-items: center` |
| `.tc-seg-center .wk-range-container` | Overrides bar height to **9px** (1.5× the 7-day's 6px) |
| `.tc-seg-temp` | 1.1rem min/max labels flanking the bar |
| `.tc-seg-right` | Right column — outdoor grade + precip text |
| `.tc-seg-stat` | Default stat text (0.88rem, muted) |
| `.tc-seg-grade` | Outdoor grade line (0.95rem, bold, inherits `.lvl-*` color) |

## Reused (unchanged)

- `.wk-row-temps` / `.wk-min-temp` / `.wk-max-temp` — range bar row layout (7-day layout)
- `.wk-range-container` / `.wk-range-bar` — shared between 36h and 7-day
- `.lvl-1` – `.lvl-5` — semantic color classes (`style.css:752`)
- `.tc-transition` / `.tc-col` — transition arrows between segments
- `tlGlobalMin` / `tlGlobalMax` — global range computation (`app.js:548–554`)

## Post-Implementation Corrections (2026-03-07)

Several bugs and visual inconsistencies were fixed after initial implementation:

### Temperature Range Bar (commits `fa12137`, `0ab602e`, `e08e0bf`)

**Problems fixed:**
1. `.tc-seg-center` uses `display:flex`, making `wk-row-temps` a flex *item* that collapsed to content width — the range bar had no room to render. Fixed by adding `.tc-seg-center .wk-row-temps { width: 100% }`.
2. Bar condition `seg.AT != null` silently hid the bar when only `MinAT`/`MaxAT` were present. Fixed to `(seg.MinAT != null || seg.AT != null)`.
3. Bar position was hardcoded to `left:0%, width:100%` (all bars full-width, no proportional meaning). Restored to proportional `leftPct`/`rightPct` using the global span.
4. When `lo === hi` (overnight segments where all 6 hourly AT values are flat), both labels showed the same value (e.g., "15° 15°"). Fixed by suppressing the min label when `lo === hi`, showing only `maxTempEl`.
5. **Global range now computed server-side** (`_slice_overview()` in `web/routes.py`): iterates all segments' `MinAT`/`MaxAT` → emits `timeline_temp_range: {min, max}` in the overview slice. Frontend reads `data.timeline_temp_range` directly; retains local fallback scan for old cached broadcasts.

**Current bar behaviour:** Each segment bar is positioned proportionally within the full 36h AT span. Segments with a genuine 6h range (e.g., Morning 15°→19°) show a wide coloured pill; overnight flat segments show a narrow positioned point. Min label suppressed when lo === hi.

### Visual Parity with 7-Day View (commit `fa12137`)

| Change | Before | After |
|--------|--------|-------|
| Segment label size | `0.65rem` | `1rem` (matches `.wk-row-label`) |
| Temperature label size | `1.1rem` | `1.35rem` (matches `.wk-min-temp`/`.wk-max-temp`); mobile `1.23rem` |
| Time label | "18:00" / "00:00" under every icon | Removed — segment name conveys the slot |

### Right Column: Icons + Text (commit `fa12137`)

| Change | Before | After |
|--------|--------|-------|
| Outdoor section | `"A Good to go"` (grade letter + label, no icon) | `outdoor.webp` 20px icon + label text (grade letter removed) |
| Precipitation section | plain `"Unlikely"` text | `rain-gear.webp` 20px icon + precip text |
| `.tc-seg-stat` display | block | `display:flex; align-items:center; gap:4px` |
| `.tc-seg-grade` rule | present (0.95rem bold) | removed (no longer used) |

### Left Column (commit `fa12137`)

| Class | Change |
|-------|--------|
| `.tc-seg-time` | element removed from DOM entirely |
| `.tc-seg-label` | `font-size: 0.65rem` → `1rem` |
