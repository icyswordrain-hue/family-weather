# Brand Icons Revamp — Simplified for Small Render

**Goal:** Redesign 16 existing brand icons (+ 1 slab bonus) using a bold, flat vector style that
remains legible at the smallest render size used in the app (16px insight bar icons). The previous
icons were too photorealistic / detailed to read clearly when scaled down.

**Affected icons:** canopy-log, canopy-moisture, cool-shade, daily-canopy, daily-canopy-slab,
dashboard, drip-warning, dusk-cover, ground, heart-flag, high-canopy, high-canopy-slab (bonus),
last-drip, morning-shade, pressure-drop, uv-warning, window-advice.

---

## Design System

**Style suffix appended to every generation prompt:**
> Flat vector icon style, bold geometric shapes, high contrast, no text, no gradients, isolated on
> solid cream `#FAF8F3` background, clean simple silhouette legible at 24px, centered with 20%
> padding.

**Earthy palette used:**

| Role | Color | Hex |
|------|-------|-----|
| Background | Cream | `#FAF8F3` |
| Primary / canopy | Sage green | `#5B8C85` |
| Alert / warning | Terracotta | `#E26C3B` |
| Structure / soil | Warm brown | `#3B2F1E` |
| Secondary detail | Muted tan | `#C9B89E` |

**Tool:** Nano Banana Pro skill (`~/.claude/skills/nano-banana-pro/`) → Gemini 3 Pro Image API,
resolution `1K` for all icons.

---

## Icon Families & Visual Dependencies

Icons are grouped into families that share a core motif, ensuring visual consistency when multiple
icons from the same family appear together (e.g., daily-canopy and high-canopy in the 7-day
forecast row).

### Family A — Canopy
Shared motif: stylized tree canopy silhouette (sage green blob). Sub-icons vary the secondary
element layered with it.

| Icon | Secondary element | Usage |
|------|-------------------|-------|
| canopy-log | Concentric trunk-ring cross-section (warm brown) | Dashboard gauge |
| canopy-moisture | Water droplet at canopy base (teal) | Dashboard gauge |
| daily-canopy | Small sun circle top-right (yellow) | Lifestyle card, 7-day forecast |
| daily-canopy-slab | Wide horizontal layout of daily-canopy | Slab card (4:1, `height` fixed + `width: auto`) |
| high-canopy | Cloud shape layered above canopy (muted gray) | Lifestyle card, 7-day forecast |
| high-canopy-slab | Wide horizontal layout of high-canopy | Slab card (4:1) |

### Family B — Shade / Time
Shared motif: ground line + sun position indicating time of day.

| Icon | Sun position | Shadow | Usage |
|------|-------------|--------|-------|
| morning-shade | Bottom-left, low | Long diagonal to the right (dark brown) | Lifestyle HVAC card |
| cool-shade | Directly above tree | Cool blue arc beneath canopy | Lifestyle HVAC card |
| dusk-cover | Bottom-right, low (terracotta) | Cloud overlapping from left | Lifestyle HVAC card |

### Family C — Drip
Shared motif: same bold raindrop shape. Secondary element signals the state.

| Icon | Secondary element | Usage |
|------|-------------------|-------|
| drip-warning | Exclamation triangle below droplet (terracotta) | Lifestyle HVAC dehumidify mode |
| last-drip | Clock / hourglass below droplet (tan) | Garden card last-rain detail |

### Family D — Alert
Bold, eye-catching icons. Terracotta dominant.

| Icon | Concept | Usage |
|------|---------|-------|
| heart-flag | Heart + triangular pennant flag on pole (terracotta) | Health alert type icon |
| uv-warning | Sun circle with thick rays + exclamation center (terracotta) | Dashboard UV gauge |
| pressure-drop | Barometer circle outline + bold downward arrow (terracotta) | Dashboard pressure gauge |

### Family E — Utility
Standalone icons with no shared motif.

| Icon | Concept | Usage |
|------|---------|-------|
| dashboard | 2×2 grid of rounded squares (sage) | Sidebar nav, view heading |
| ground | Two-band cross-section: grass on top, soil below (green + brown) | Dashboard ground gauge |
| window-advice | 4-pane window frame + breeze arc lines (sage) | Lifestyle HVAC fan/default mode |

---

## Generation Commands

All icons output to `web/static/brand-icons/`. Replace `$GEMINI_API_KEY` with key from `.env`.

```bash
# Family A
uv run ~/.claude/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Tree trunk cross-section icon, concentric rings pattern, warm brown tones #3B2F1E and #C9B89E, bold circular shape with clear ring lines, flat vector icon style, bold geometric shapes, high contrast, no text, no gradients, isolated on solid cream #FAF8F3 background, clean simple silhouette legible at 24px, centered with 20% padding" \
  --filename "web/static/brand-icons/canopy-log.webp" --resolution 1K

uv run ~/.claude/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Tree canopy silhouette with a bold water droplet at base, sage green #5B8C85 canopy, blue-teal droplet, flat vector icon style, bold geometric shapes, high contrast, no text, no gradients, isolated on solid cream #FAF8F3 background, clean simple silhouette legible at 24px, centered with 20% padding" \
  --filename "web/static/brand-icons/canopy-moisture.webp" --resolution 1K

uv run ~/.claude/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Simple bold tree canopy silhouette with small sun circle above right, sage green #5B8C85 canopy, warm yellow sun, flat vector icon style, bold geometric shapes, high contrast, no text, no gradients, isolated on solid cream #FAF8F3 background, clean simple silhouette legible at 24px, centered with 20% padding" \
  --filename "web/static/brand-icons/daily-canopy.webp" --resolution 1K

uv run ~/.claude/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Wide horizontal banner icon, bold tree canopy silhouette with sun on right side, sage green #5B8C85 canopy, warm yellow sun, panoramic landscape layout wide aspect ratio, flat vector icon style, bold geometric shapes, high contrast, no text, no gradients, isolated on solid cream #FAF8F3 background, clean simple silhouette, horizontally centered composition" \
  --filename "web/static/brand-icons/daily-canopy-slab.webp" --resolution 1K

uv run ~/.claude/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Bold tree canopy silhouette at bottom, fluffy cloud shape above at top, sage green #5B8C85 canopy, light muted cloud, vertical stacking showing sky layers, flat vector icon style, bold geometric shapes, high contrast, no text, no gradients, isolated on solid cream #FAF8F3 background, clean simple silhouette legible at 24px, centered with 20% padding" \
  --filename "web/static/brand-icons/high-canopy.webp" --resolution 1K

uv run ~/.claude/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Wide horizontal banner icon, bold tree canopy silhouette at bottom with fluffy cloud above it, sage green #5B8C85 canopy, light muted cloud shape at top, panoramic wide aspect ratio landscape layout, flat vector icon style, bold geometric shapes, high contrast, no text, no gradients, isolated on solid cream #FAF8F3 background, clean simple silhouette, horizontally centered composition" \
  --filename "web/static/brand-icons/high-canopy-slab.webp" --resolution 1K

# Family B
uv run ~/.claude/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Low morning sun at bottom-left with long bold shadow stretching diagonally to the right, warm golden yellow circle sun, dark warm brown #3B2F1E long shadow on ground, morning atmosphere, flat vector icon style, bold geometric shapes, high contrast, no text, no gradients, isolated on solid cream #FAF8F3 background, clean simple silhouette legible at 24px, centered with 20% padding" \
  --filename "web/static/brand-icons/morning-shade.webp" --resolution 1K

uv run ~/.claude/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Tree casting a bold cool blue shadow on the ground, sage blue tones #5B8C85, shadow arc beneath tree canopy, midday sun directly above, flat vector icon style, bold geometric shapes, high contrast, no text, no gradients, isolated on solid cream #FAF8F3 background, clean simple silhouette legible at 24px, centered with 20% padding" \
  --filename "web/static/brand-icons/cool-shade.webp" --resolution 1K

uv run ~/.claude/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Low setting sun at bottom-right edge with bold cloud covering it from the left, warm terracotta orange #E26C3B sun semicircle, muted gray-brown cloud shape, dusk atmosphere, flat vector icon style, bold geometric shapes, high contrast, no text, no gradients, isolated on solid cream #FAF8F3 background, clean simple silhouette legible at 24px, centered with 20% padding" \
  --filename "web/static/brand-icons/dusk-cover.webp" --resolution 1K

# Family C
uv run ~/.claude/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Bold raindrop shape with exclamation mark warning triangle overlapping below it, terracotta orange #E26C3B color scheme, high humidity dehumidify alert icon, flat vector icon style, bold geometric shapes, high contrast, no text, no gradients, isolated on solid cream #FAF8F3 background, clean simple silhouette legible at 24px, centered with 20% padding" \
  --filename "web/static/brand-icons/drip-warning.webp" --resolution 1K

uv run ~/.claude/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Single bold raindrop with small clock face or hourglass below indicating elapsed time, sage green #5B8C85 droplet, muted tan clock, last rainfall time indicator, flat vector icon style, bold geometric shapes, high contrast, no text, no gradients, isolated on solid cream #FAF8F3 background, clean simple silhouette legible at 24px, centered with 20% padding" \
  --filename "web/static/brand-icons/last-drip.webp" --resolution 1K

# Family D
uv run ~/.claude/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Bold heart shape with small triangular pennant flag on a pole attached to top right, terracotta red #E26C3B heart, health cardiac alert warning icon, flat vector icon style, bold geometric shapes, high contrast, no text, no gradients, isolated on solid cream #FAF8F3 background, clean simple silhouette legible at 24px, centered with 20% padding" \
  --filename "web/static/brand-icons/heart-flag.webp" --resolution 1K

uv run ~/.claude/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Bold sun circle with thick radiating rays and large exclamation mark in center, terracotta orange #E26C3B sun with rays, UV index high warning, flat vector icon style, bold geometric shapes, high contrast, no text, no gradients, isolated on solid cream #FAF8F3 background, clean simple silhouette legible at 24px, centered with 20% padding" \
  --filename "web/static/brand-icons/uv-warning.webp" --resolution 1K

uv run ~/.claude/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Circular barometer gauge outline with bold downward arrow inside pointing down, dark warm brown #3B2F1E circle outline, terracotta orange #E26C3B bold downward arrow, atmospheric pressure falling, flat vector icon style, bold geometric shapes, high contrast, no text, no gradients, isolated on solid cream #FAF8F3 background, clean simple silhouette legible at 24px, centered with 20% padding" \
  --filename "web/static/brand-icons/pressure-drop.webp" --resolution 1K

# Family E
uv run ~/.claude/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Four rounded squares arranged in a 2x2 grid, dashboard navigation icon, sage green #5B8C85 squares, equal spacing on cream background, bold simple grid shape, flat vector icon style, bold geometric shapes, high contrast, no text, no gradients, isolated on solid cream #FAF8F3 background, clean simple silhouette legible at 24px, centered with 20% padding" \
  --filename "web/static/brand-icons/dashboard.webp" --resolution 1K

uv run ~/.claude/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Ground cross-section icon, top layer bold green grass strip, bottom layer warm brown soil #3B2F1E, two distinct bold horizontal bands with slight texture, earthy colors, flat vector icon style, bold geometric shapes, high contrast, no text, no gradients, isolated on solid cream #FAF8F3 background, clean simple silhouette legible at 24px, centered with 20% padding" \
  --filename "web/static/brand-icons/ground.webp" --resolution 1K

uv run ~/.claude/skills/nano-banana-pro/scripts/generate_image.py \
  --prompt "Simple window frame with 4 panes in 2x2 grid and curved wind lines flowing through it, sage green #5B8C85 window frame, breeze lines suggesting ventilation airflow, open window advice icon, flat vector icon style, bold geometric shapes, high contrast, no text, no gradients, isolated on solid cream #FAF8F3 background, clean simple silhouette legible at 24px, centered with 20% padding" \
  --filename "web/static/brand-icons/window-advice.webp" --resolution 1K
```

---

## Render Size Reference

Icons are used at these sizes — the 16px insight bar is the hardest test:

| Context | Size | CSS selector |
|---------|------|-------------|
| Insight bar | 16×16px | `.ls-insight .brand-icon` |
| Nav / alert type | 24px (inline) | `.nav-icon`, `.ls-alert-type-icon` |
| View heading | 32px | `.view-heading-icon.brand-icon` |
| Solar row | 33px | `.solar-row .brand-icon` |
| 7-day forecast | 56px → 42px mobile | `.wk-icon .brand-icon` |
| Forecast stat | 60px → 30px mobile | `.tc-stat-icon .brand-icon` |
| 24h forecast | 64px → 54px mobile | `.tc-icon .brand-icon` |
| 24h left segment | 72px → 54px mobile | `.tc-seg-left .tc-icon .brand-icon` |

---

## Verification

1. `RUN_MODE=LOCAL python app.py` → open http://localhost:8080
2. Check Dashboard view — gauge icons (pressure-drop, uv-warning, canopy-moisture, ground) at ~28px
3. Check Lifestyle view — HVAC card shows correct shade/drip icon variant; insight bar at 16px
4. Check 24h forecast — canopy icons at 64–72px
5. Check 7-day forecast row — daily-canopy / high-canopy at 56px; slab cards
6. `pytest tests/` — no regressions expected (icons not covered by tests)
