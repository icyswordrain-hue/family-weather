# Current Conditions UI Polish — Collapsible Panel, Brand Icons, Slab Headings, Hero Density

**Date:** 2026-03-07
**Commits:** `4fd34ff` → `0b5f08e` → `2af570d`

---

## Overview

Three rounds of iterative UI polish to the Current Conditions section of the dashboard. Covers the full design arc from a flat 3-column gauge grid to a focused 2-column hero with collapsible secondary metrics, new brand icons, slab-style headings, and a denser balanced layout.

---

## Round 1 — Collapsible Current Conditions Panel (`4fd34ff`)

### Problem
The original layout showed all seven metrics simultaneously in a 3-column top row (ground | hero | wind) plus a fixed 4-gauge row (humidity, AQI, UV, pressure). Equal visual weight was given to both primary actionable conditions and underlying detail metrics.

### Design
Redesign current conditions as a 2-column layout:

- **Left column** — hero card: weather icon + temperature + description + solar sunrise/sunset
- **Right column** — three stacked cards (ground, wind, outdoor score trigger)
- **Below** — expandable panel (humidity, AQI, UV, pressure), hidden by default

Clicking the outdoor score card expands the panel to reveal the four secondary gauges. The chevron `▾` rotates 180° when expanded.

### Layout

```
┌──────────────────────┬──────────────────────┐
│                      │  GROUND              │
│   ☁   10°            │  Dry                 │
│   Cloudy             ├──────────────────────┤
│   ↑ 06:11  ↓ 17:59   │  WIND                │
│                      │  Moderate breeze     │
│                      │  6.2 m/s ENE         │
│                      ├──────────────────────┤
│                      │  OUTDOOR ACTIVITIES ▾│
│                      │  Go out              │
└──────────────────────┴──────────────────────┘
┌──────────┬──────────┬──────────┬────────────┐
│ HUMIDITY │ AIR QUAL │ UV INDEX │ PRESSURE   │
│ Humid    │   62     │  Safe    │  Stable    │
│  68%     │          │ Index 0  │  1022 hPa  │
└──────────┴──────────┴──────────┴────────────┘
           (collapsed by default; click outdoor ▾)
```

### Files Changed

| File | Change |
|------|--------|
| `web/templates/dashboard.html` | 3-col top-row → 2-col (`.current-hero` + `.current-side-stack`); added `#gauge-outdoor` with `role="button"`, `aria-expanded`; `#gauges-expand` starts with `.gauges-collapsed` |
| `web/static/style.css` | Added `.current-conditions-wrapper` (flex column, `max-height: calc(100dvh - 78px - 60px)`); `.current-top-row: 2fr 1fr`; `.current-side-stack` (flex column); `.gauge-outdoor-trigger` (chevron, cursor pointer); `.gauges-grid` collapse animation (`max-height` + `opacity` transition) |
| `web/static/app.js` | `renderCurrentView()` calls `renderGauge('gauge-outdoor', ...)` with `oi-grade-*` class; toggle handler wired once via `outdoorTrigger._expandWired` guard; keyboard-accessible (Enter/Space) |

### Key Decisions
- `max-height` transition (not `display:none`) enables smooth CSS animation without JS measurement
- `_expandWired` guard prevents duplicate event listener registration across re-renders
- `oi-grade-*` CSS class applied to gauge-value with `background:none` override so it shows color only (no pill)
- Outdoor data was already in `slices.current.outdoor` from `_slice_current()` in `routes.py` — no backend change needed

---

## Round 2 — Brand Icons, Icon-Left Headers, AQI Simplification, Slab Headings (`0b5f08e`)

### Requests
1. Trim hero card to 3/4 size; resize icon and text to fill the reduced card
2. Generate brand icons for ground, wind, and air quality gauges
3. Put icon to the LEFT of the card title (not above it)
4. Air quality card: show only the numeric AQI value (no sub-label)
5. Change h1 icons to slab-style: decorative wide image behind the heading text; generate new slab assets for canopy and lifestyle views

### Layout Insight (Hero Density Bug)
**Initial plan** scaled hero content down proportionally. User corrected: the hero card was only 47% filled because the side-stack `min-height: 80px × 3 + 2 gaps ≈ 272px` was controlling the row height. The hero was not "too large" — it was sparsely filled inside a tall row.

**Fix:** Shrink side-stack cards (`80px → 55px`) to reduce row height, AND keep/increase hero content sizes.

### Brand Icons Generated (via nano-banana-pro / Gemini 3 Pro Image API)

| File | Style | Dimensions |
|------|-------|-----------|
| `web/static/brand-icons/ground.webp` | Botanical pen-and-ink soil cross-section, sage green + earth tones on cream | 512×512 |
| `web/static/brand-icons/wind.webp` | Flowing sweeping arcs, sage green on cream textured paper, botanical sketch | 512×512 |
| `web/static/brand-icons/high-canopy-slab.webp` | Tropical canopy watercolor banner, monstera/palm fronds, pastel greens/pinks, edges fade to white | 512×128 (centre-cropped from 512×512) |
| `web/static/brand-icons/daily-canopy-slab.webp` | Morning green leaves with golden light, sage greens/pale yellows, edges fade to white | 512×128 (centre-cropped from 512×512) |

Conversion: Gemini API outputs PNG → Pillow 12.1.1 converts to WebP; slabs centre-cropped to 4:1 (512×128) before saving.

### CSS / JS Changes

**`renderGauge()` restructured — icon left of label:**
```javascript
// New gauge-header flex row wraps icon + label
const hdr = document.createElement('div');
hdr.className = 'gauge-header';  // display:flex; align-items:center; gap:0.3rem
if (icon) { hdr.appendChild(iconEl); }
hdr.appendChild(labelEl);
el.appendChild(hdr);
```

**Slab headings behind h1:**
```css
.heading-slab {
  position: absolute; left: 0; top: 50%; transform: translateY(-50%);
  height: 2.8rem; width: auto; max-width: 100%;
  opacity: 0.18; z-index: 0; pointer-events: none;
}
.view-header h1 { position: relative; z-index: 1; }
```

Both `#view-heading-dashboard` and `#view-heading-lifestyle` headers now contain a `<img class="heading-slab">` sibling to `<h1>`.

**AQI simplified:**
```javascript
renderGauge('gauge-aqi', String(data.aqi.val ?? '—'), T.air_quality, '', `lvl-${data.aqi.level}`, IMG('air-quality', 'Air Quality'));
// No sub-line; previously showed "AQI 67 · PM2.5 9"
```

**Hero density (side-stack shrink):**
- Side-stack `.gauge-card min-height: 80px → 55px` desktop; `70px → 45px` mobile
- Hero min-height: `240px → 160px`; padding: `1.25rem → 0.75rem`
- Icon: `width 5rem → 5.5rem`

---

## Round 3 — Equal Columns, Denser Hero, Longer Slab, Wind-First Order (`2af570d`)

### Requests (from annotated screenshot)
1. **H1 slab**: longer image, higher transparency — apply to both dashboard and lifestyle
2. **Hero**: increase density (bigger icon/temp/text), reduce column width to equal with side-stack
3. **Side stack**: same width as hero (equal columns), larger gauge icons, reorder wind above ground

### Changes

**Equal column layout:**
```css
/* was 2fr 1fr (hero 66% / side 33%) */
.current-top-row { grid-template-columns: 1fr 1fr; }
```
Hero column narrows from 66% → 50% of total width (≈ "4/5" of prior).

**Hero content sizes:**
| Property | Before | After |
|----------|--------|-------|
| hero min-height | 160px | 200px |
| `#cur-icon` width | 5.5rem | 8rem |
| `#cur-temp` font-size | 2.8rem | 3.6rem |
| `#cur-weather-text` font-size | 1.1rem | 1.3rem |
| `.solar-row` font-size | 0.8rem | 0.95rem |
| `.solar-row .brand-icon` | 20px | 28px |

**Heading slab:**
| Property | Before | After |
|----------|--------|-------|
| height | 2.8rem | 4.5rem |
| opacity | 0.18 | 0.30 |

At 4.5rem height, the 4:1 aspect-ratio slab image is ~72px tall × ~288px wide — noticeably spans the heading area on both desktop and mobile.

**Gauge header icons:** `18px → 26px`

**Side-stack card order (HTML):**
```html
<!-- before: ground, wind, outdoor -->
<!-- after:  wind, ground, outdoor -->
<div class="gauge-card" id="gauge-wind"></div>
<div class="gauge-card" id="gauge-ground"></div>
<div class="gauge-card gauge-outdoor-trigger" id="gauge-outdoor" ...></div>
```

---

## Final State — Current Values

### CSS (style.css)
```css
.current-top-row        { grid-template-columns: 1fr 1fr; }
.current-side-stack .gauge-card { min-height: 55px; }   /* desktop */
.current-top-row .current-hero  { min-height: 200px; }
.current-hero           { padding: 0.75rem; }
#cur-icon               { font-size: 3rem; width: 8rem; }
#cur-temp               { font-size: 3.6rem; font-weight: 800; }
#cur-weather-text       { font-size: 1.3rem; font-weight: 600; }
.solar-row              { font-size: 0.95rem; }
.solar-row .brand-icon  { width: 28px; height: 28px; }
.gauge-header .gauge-icon .brand-icon { width: 26px; height: 26px; }
.heading-slab           { height: 4.5rem; opacity: 0.30; }
```

### Mobile overrides (≤767px — unchanged in Round 3)
```css
.current-side-stack .gauge-card { min-height: 45px; }
.current-top-row .current-hero  { min-height: 90px; }
.current-hero           { padding: 0.4rem 0.3rem; }
#cur-icon               { font-size: 2rem; width: 3.5rem; }
#cur-temp               { font-size: 2.2rem; }
```

### Side-stack card order
`#gauge-wind` → `#gauge-ground` → `#gauge-outdoor` (trigger/expand)

---

## Round 4 — Card Height Scale, Denser Text, Slab Polish

**Commit:** `32f5fc6`

### Requests
1. **Mobile:** all card heights ×1.25
2. **Desktop:** all card heights ×1.1
3. Scale text and icons proportionally to maintain density (75–90% small cards, 70–85% large cards)
4. H1 slab fills full width on mobile
5. Slab opacity ×2

### Changes

**Global slab (style.css):**
| Property | Before | After |
|----------|--------|-------|
| `.heading-slab` opacity | 0.30 | 0.60 |
| `.section-slab` opacity | 0.15 | 0.30 |
| `.heading-slab` width (mobile) | auto | 100% |

**Desktop card heights (×1.1):**
| Selector | Before | After |
|----------|--------|-------|
| `.current-top-row .current-hero` min-height | 200px | 220px |
| `.current-side-stack .gauge-card` min-height | 55px | 61px |
| `.gauge-card` (full-size) min-height | 120px | 132px |
| `.gauges-grid` max-height | 200px | 220px |
| `.timeline-scroll .time-card` min-height | 180px | 198px |
| `.time-card` min-height | 200px | 220px |
| `.wk-card` padding | 14px 8px | 15px 9px |
| `.ls-card` padding | 1rem | 1.1rem |

**Desktop text + icons (×1.05–1.08):**
| Selector | Property | Before | After |
|----------|----------|--------|-------|
| `.gauge-label` | font-size | 0.85rem | 0.9rem |
| `.gauge-value` | font-size | 1.4rem | 1.5rem |
| `.gauge-sub` | font-size | 0.9rem | 0.95rem |
| `.gauge-header .gauge-label` | font-size | 0.75rem | 0.8rem |
| `.gauge-header .gauge-icon .brand-icon` | w/h | 26px | 28px |
| `#cur-icon` | font-size / width | 3rem / 8rem | 3.3rem / 8.8rem |
| `#cur-temp` | font-size | 3.6rem | 3.96rem |
| `#cur-weather-text` | font-size | 1.3rem | 1.4rem |
| `.tc-header` | font-size | 0.85rem | 0.9rem |
| `.tc-icon .brand-icon` | w/h | 60px | 64px |
| `.tc-temp` | font-size | 1.8rem | 1.98rem |
| `.tc-label` | font-size | 0.75rem | 0.8rem |
| `.tc-val` | font-size | 1.1rem | 1.18rem |
| `.wk-icon .brand-icon` | w/h | 52px | 56px |
| `.ls-icon` | w/h | 40px | 44px |
| `.ls-title` | font-size | 1.05rem | 1.1rem |
| `.ls-text` | font-size | 0.78rem | 0.82rem |

**Mobile card heights (×1.25, inside `@media (max-width: 767px)`):**
| Selector | Before | After |
|----------|--------|-------|
| `.current-top-row .current-hero` min-height | 90px | 113px |
| `.current-hero` padding | 0.4rem 0.3rem | 0.5rem 0.4rem |
| `.current-side-stack .gauge-card` min-height | 45px | 56px |
| `.current-side-stack .gauge-card` padding | 0.4rem 0.3rem | 0.5rem 0.4rem |
| `.gauges-grid .gauge-card` min-height | 70px | 88px |
| `.gauges-grid .gauge-card` padding | 0.5rem 0.35rem | 0.63rem 0.44rem |
| `.gauges-grid` max-height | 140px | 175px |
| `.time-card` padding | 0.75rem 0.4rem | 0.94rem 0.5rem |
| `.wk-card` padding | 4px 3px | 5px 4px |
| `.ls-card` padding (new mobile rule) | 1rem | 1.25rem |

**Mobile text + icons (×1.15–1.2):**
| Selector | Property | Before | After |
|----------|----------|--------|-------|
| `.current-side-stack .gauge-label` | font-size | 0.78rem | 0.9rem |
| `.current-side-stack .gauge-value` | font-size | 1.15rem | 1.35rem |
| `.current-side-stack .gauge-sub` | font-size | 0.78rem | 0.9rem |
| `.current-side-stack .gauge-header .brand-icon` | w/h | 26px | 30px |
| `.gauges-grid .gauge-label` | font-size | 0.75rem | 0.88rem |
| `.gauges-grid .gauge-value` | font-size | 1.1rem | 1.28rem |
| `.gauges-grid .gauge-sub` | font-size | 0.72rem | 0.85rem |
| `#cur-icon` | font-size / width | 2rem / 3.5rem | 2.5rem / 4.4rem |
| `#cur-temp` | font-size | 2.2rem | 2.75rem |
| `#cur-weather-text` | font-size | 0.85rem | 1.05rem |
| `.tc-header` | font-size | 0.62rem | 0.72rem |
| `.tc-icon .brand-icon` | w/h | 44px | 54px |
| `.tc-temp` | font-size | 1rem | 1.25rem |
| `.tc-label` | font-size | 0.55rem | 0.65rem |
| `.tc-val` | font-size | 0.75rem | 0.88rem |
| `.wk-icon` | font-size | 1.2rem | 1.5rem |
| `.wk-icon .brand-icon` | w/h | 34px | 42px |
| `.wk-temp` | font-size | 0.9rem | 1.1rem |
| `.ls-icon` | w/h | 40px | 50px |
