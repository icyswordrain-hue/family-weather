# Brand Icons Full Sweep — Remaining 25 Icons

**Goal:** Complete the across-the-board icon redesign started in `2026-03-14-brand-icons-revamp.md`.
The previous session covered 17 icons (canopy/shade/drip/alert/utility families). This session
redesigns the remaining 25 icons so the entire icon set is visually consistent.

**Follows the same design system:** flat vector style, bold geometric shapes, high contrast, solid
cream `#FAF8F3` background, earthy palette.

---

## Icons Redesigned

### Group 1 — Weather Day
Used at 54–72px in forecast tiles. Day variants use warm gold `#D99B3F` as the primary color.

| Icon | Concept |
|------|---------|
| sunny | Solid circle + 8 thick radiating rays, all gold `#D99B3F` |
| partly-cloudy | Bold cloud lower-left, gold sun peeking upper-right |
| cloudy | Two overlapping cloud puffs, muted tan `#C9B89E`, no sun |
| rainy | Same cloud puff + 4 vertical raindrop lines, dark navy `#2B4E72` |

### Group 2 — Weather Night
Night variants share the same cloud/rain shape as the day counterparts but use dark navy/charcoal
palette. Crescent moon replaces sun.

| Icon | Concept |
|------|---------|
| clear-night | Bold crescent moon + 3 star dots, dark navy `#2B4E72` |
| partly-cloudy-night | Crescent moon upper-right, muted gray cloud lower-left |
| cloudy-night | Two cloud puffs in dark charcoal `#3B2F1E`, tiny crescent at edge |
| rainy-night | Dark charcoal cloud + 4 navy raindrop lines |

**Dependency rule:** Each night icon mirrors the silhouette of its day counterpart — same cloud
shape, swapped palette. This makes the variants read as one family at a glance.

### Group 3 — Solar
Used at 33–44px in the hero solar row.

| Icon | Concept |
|------|---------|
| sunrise-square | Semicircle sun rising above horizon line, gold `#D99B3F` |
| sunset-square | Semicircle sun below horizon line, terracotta `#E26C3B` |

Color intentionally differs: gold for rising dawn, terracotta for setting dusk.

### Group 4 — Lifestyle Activity Cards
Used at 16px (insight bar) and 28px (gauge header). Sage green `#5B8C85` dominant.

| Icon | Concept |
|------|---------|
| wardrobe | Bold t-shirt silhouette, muted tan `#C9B89E` |
| commute | Bicycle silhouette (two circles + frame), sage green |
| garden | Seedling sprout (two leaves on stem above soil line), sage green + warm brown |
| outdoor | Tree silhouette (round canopy + trunk), sage green + warm brown |
| meals | Round bowl + single steam line, warm gold `#D99B3F` |

### Group 5 — Status / Alert
Used at 14px (alert type badge) and as full alert header icons. Ultra-simple shapes.

| Icon | Concept | Color |
|------|---------|-------|
| alert | Exclamation mark in filled circle | Terracotta `#E26C3B` |
| all-clear | Checkmark tick in circle outline | Sage green `#5B8C85` |
| heads-up | Exclamation mark in triangle outline | Gold `#D99B3F` |
| general | Letter "i" in circle outline | Muted tan `#C9B89E` |

**Semantic color rule:** terracotta = critical, gold = caution, sage = safe — matches the app's
5-level alert severity scale.

### Group 6 — Gauge / Detail
Used at 16px (insight bar) and 28px (gauge header).

| Icon | Concept |
|------|---------|
| wind | Three horizontal curved swoosh lines, staggered right, sage green |
| air-quality | Circular swirl/loop arrow suggesting air circulation, sage green |
| hvac | Thermometer (bulb + column), terracotta (heating context) |
| feels-like | Thermometer + small human figure silhouette, muted tan |

### Group 7 — Unused (redesigned for future use)

| Icon | Concept |
|------|---------|
| health | Bold heart + small leaf or pulse arc, sage green (general wellness) |
| rain-gear | Umbrella silhouette (dome + curved handle), dark navy `#2B4E72` |

**Note:** `health` (sage green, wellness) is intentionally distinct from `heart-flag` (terracotta,
cardiac alert) — they serve different semantic roles.

---

## Skipped Files (no redesign)

| File | Reason |
|------|--------|
| `book-icon.webp` | Unused, no planned use |
| `vase-icon.webp` | Unused legacy style-reference |
| `sunrise.webp` | Deprecated landscape format (1380×752) |
| `sunset.webp` | Deprecated landscape format (1380×752) |

---

## Complete Icon Inventory (post-revamp)

All 42 active icons now follow the bold flat vector style:

**Weather (8):** sunny, partly-cloudy, cloudy, rainy, clear-night, partly-cloudy-night,
cloudy-night, rainy-night

**Solar (2):** sunrise-square, sunset-square

**Lifestyle (5):** wardrobe, commute, garden, outdoor, meals

**Status/Alert (4):** alert, all-clear, heads-up, general

**Gauge/Detail (6):** wind, air-quality, hvac, feels-like, uv-warning *, pressure-drop *

**Canopy family (6):** canopy-log, canopy-moisture, daily-canopy, daily-canopy-slab, high-canopy,
high-canopy-slab

**Shade/Time (3):** morning-shade, cool-shade, dusk-cover

**Drip (2):** drip-warning, last-drip

**Alert/Health (2):** heart-flag, uv-warning*

**Utility (3):** dashboard, ground, window-advice

**Unused/kept (2):** health, rain-gear

*uv-warning listed in both gauge and alert — it straddles both contexts.

---

## Verification

1. `RUN_MODE=LOCAL python app.py` → http://localhost:8080
2. **Dashboard view** — gauge icons (wind, air-quality, ground, uv-warning) at 28px; solar row
   (sunrise-square, sunset-square) at 33px
3. **24h forecast row** — weather icons (sunny, cloudy, rainy, etc.) at 64–72px
4. **7-day row** — icons at 56px; slab cards (daily-canopy-slab, high-canopy-slab)
5. **Lifestyle view** — HVAC variants (cool-shade, drip-warning, hvac, window-advice); insight
   bar icons at 16px
6. **Alert panel** — all-clear / heads-up / alert at 14px badge size; heart-flag / general / heads-up
7. `pytest tests/` — no regressions
