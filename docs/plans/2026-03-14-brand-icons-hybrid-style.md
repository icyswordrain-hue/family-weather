# Brand Icons — Hybrid Style Revamp

**Date:** 2026-03-14
**Commits:** `71aa0c2`, `df28346`, `71ffd41`, `7c8c386`

---

## Context

The icon set went through two prior generations:

1. **Fine-line sketch** (2026-03-04) — hand-drawn pencil style, `vase-icon.png` as reference.
   Sophisticated at large sizes but illegible at 16px (insight bar minimum).

2. **Bold flat vector** (2026-03-14) — geometric shapes, high contrast, solid fill.
   Legible at 16px but lacked visual sophistication and resolution at 72px.

This revamp merges the strengths of both into a **hybrid style** that works at every render size.

---

## Hybrid Style Definition

### Prompt suffix (appended to every generation)

```
Bold geometric silhouette with fine-line interior detail strokes, slight stroke weight variation
for organic warmth, flat vector foundation with editorial illustration quality, earthy palette,
solid cream #FAF8F3 background, legible at 16px, centered with 20% padding, no text, no gradients,
no shadows, square 1:1 composition
```

### Style properties

| Dimension | Fine-line sketch | Bold flat vector | **Hybrid** |
|-----------|-----------------|------------------|------------|
| Shape backbone | Organic, loose | Bold geometric | **Geometric** |
| Interior | Hatching, texture | Solid fill | **Fine-line detail strokes** |
| Legibility @16px | Poor | Excellent | **Excellent** |
| Sophistication @72px | High | Low | **High** |
| Stroke weight | Uniform thin | None | **Variable (bold outline, thin interior)** |

### Tool

Nano Banana Pro → Gemini 3 Pro Image API, `--resolution 1K`, `--input-image web/static/brand-icons/vase-icon.webp`

---

## Aspect Ratio Specifications (unchanged)

| Group | Canvas | Notes |
|-------|--------|-------|
| All standard icons | 1:1 square | CSS equal px both axes |
| `sunrise-square.webp`, `sunset-square.webp` | 1:1 square | 1024×1024 source |
| `daily-canopy-slab.webp`, `high-canopy-slab.webp` | 4:1 wide | CSS `height` fixed + `width: auto` |

No CSS changes needed for icon containers — existing sizing rules apply unchanged.

---

## Icon Families (42 active icons)

### Family A — Weather Day
`sunny`, `partly-cloudy`, `cloudy`, `rainy`
Gold `#D99B3F` primary; tan `#C9B89E` cloud; navy `#2B4E72` rain.

### Family B — Weather Night
`clear-night`, `partly-cloudy-night`, `cloudy-night`, `rainy-night`
Mirrors day silhouettes; navy/charcoal palette; crescent replaces sun.

### Family C — Solar
`sunrise-square` (gold), `sunset-square` (terracotta)

### Family D — Lifestyle Activity Cards
`wardrobe` (tan), `commute` (sage), `garden` (sage+brown), `outdoor` (sage+brown), `meals` (gold)

### Family E — Status / Alert
`alert` (terracotta filled), `all-clear` (sage outline), `heads-up` (gold outline), `general` (tan outline)
Semantic color rule: terracotta = critical, gold = caution, sage = safe.

### Family F — Gauge / Detail
`wind`, `air-quality`, `hvac`, `feels-like`, `uv-warning`, `pressure-drop`

### Family G — Canopy
`canopy-log`, `canopy-moisture`, `daily-canopy`, `daily-canopy-slab`, `high-canopy`, `high-canopy-slab`
Shared motif: stylized tree canopy blob (sage green).

### Family H — Shade / Time
`morning-shade`, `cool-shade`, `dusk-cover`
Motif: ground line + sun position indicating time of day.

### Family I — Drip
`drip-warning`, `last-drip`
Shared motif: bold raindrop shape.

### Family J — Alert / Health
`heart-flag` (terracotta, cardiac), `health` (sage, general wellness)

### Family K — Utility
`dashboard`, `ground`, `window-advice`, `rain-gear`

---

## Insight Bar Icon — Aspect Ratio Fix

**File:** `web/static/style.css`

Changed `.ls-insight .brand-icon` from hardcoded `16×16px` to `height: 1em; width: auto`.

```css
/* before */
.ls-insight .brand-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  display: inline-block;
  margin: 0;
}

/* after */
.ls-insight .brand-icon {
  height: 1em;
  width: auto;
  flex-shrink: 0;
  display: inline-block;
  margin: 0;
}
```

**Why:** `width: auto` derives width from height, maintaining 1:1 aspect ratio without clamping. The `1em` unit scales with the text size automatically — including the zh-TW font bump (`0.95rem`) — instead of being pinned at a fixed 16px.

---

## Skipped Files

| File | Reason |
|------|--------|
| `vase-icon.webp` | Style reference anchor — must NOT be overwritten |
| `book-icon.webp` | Unused legacy |
| `sunrise.webp`, `sunset.webp` | Deprecated landscape format (1380×752), no longer referenced |

---

## Verification

1. `RUN_MODE=LOCAL python app.py` → http://localhost:8080
2. **Insight bar (16px)** — icons scale with text; zh-TW toggle should make them proportionally larger
3. **Gauge headers (28px)** — wind, air-quality, pressure-drop, uv-warning
4. **Solar row (33–44px)** — sunrise-square, sunset-square
5. **24h forecast (64–72px)** — weather icons: fine-line detail should be visible at large size
6. **7-day row (42–56px)** — daily-canopy, high-canopy; slab cards
7. **Alert panel (14px badge)** — alert, all-clear, heads-up, general
8. `pytest tests/` — no regressions
