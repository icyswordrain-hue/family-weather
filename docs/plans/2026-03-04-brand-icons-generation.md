# Brand Icons Generation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Progressively replace all native emojis in the UI with custom, fine-line SVG/PNG illustrations generated via Nano Banana Pro, ensuring no broken images during the transition.

**Architecture:** The transformation is phased into bite-sized compute tasks. First, CSS is established in `style.css` so graphics align perfectly as fonts and handle missing files gracefully. Then, image assets are generated in three distinct batches (Nav/Alerts, Weather, Lifestyle) to manage API load. Finally, `app.js` and `routes.py` are safely updated to inject HTML `<img>` elements instead of text strings, completing the replacement.

**Tech Stack:** Nano Banana Pro (skill), HTML, CSS, Vanilla JS, Python.

---

## Brand Style Reference

The two existing test icons are the de-facto style standard — reference them in all generations:
- `web/2026-03-04-22-30-00-vase-icon.png` — fine-line terracotta vase with sage leaves
- `web/2026-03-04-22-30-10-book-icon.png` — hand-drawn stacked books in mustard/plum

**Earthy-color doc mapping:** Base palette is "Nature Distilled" (terracotta, sand, sage, soft
cream) extended with academic blues (#1C3E75, #2B5291) and dusty plum (#9B5D77) for a
"literary salon" tone rather than "artisan shop."

---

## Master Prompt Template

Apply this preamble to **every** generation:

```
Fine-line sketch illustration, hand-drawn pencil art, [SUBJECT], [PRIMARY COLOR #HEX] accent tones,
sage green #5B8C85 secondary accents, soft cream background #F3F7F8, subject fills 70% of frame,
clean editorial line weight, sketchbook feel, isolated centered composition, no text, no shadow
```

**Always pass `--input-image web/2026-03-04-22-30-00-vase-icon.png`** and frame the prompt as:
> "Redraw in the same fine-line sketch style as this illustration, but replace the subject with [X]."

This locks stroke weight, line density, and background tone across all icons.

---

## Color-per-Category Mapping

| Category | Primary Color | Hex |
|----------|---------------|-----|
| Weather — sun / partly-cloudy | Mustard Yellow | #D99B3F |
| Weather — rain / cloud | Navy Blue | #1C3E75 |
| Commute / Outdoor / Air Quality | Deep Sage Green | #5B8C85 |
| Health / Wardrobe | Dusty Rose / Plum | #9B5D77 |
| Alert / HVAC / Heads-up | Terracotta Orange | #E26C3B |
| Garden / All-clear | Sage Green | #5B8C85 |
| General / Meals | Mustard Yellow | #D99B3F |

---

### Task 1: Establish Foundational CSS for Brand Icons

**Files:**
- Modify: `web/static/style.css`

**Step 1: Write the minimal implementation**
Append the `.brand-icon` styling to enable smooth transition holding.

```css
/* Brand Icon Integration */
.brand-icon {
  height: 1.25em;
  width: auto;
  vertical-align: text-bottom;
  display: inline-block;
  margin-right: 0.25em;
  /* gracefully handle load failures */
  background-color: transparent;
}
.error-icon .brand-icon {
  height: 3em;
  margin: 0 auto;
}
.nav-icon .brand-icon {
  height: 1.5em;
}
```

**Step 2: Commit**
```bash
git add web/static/style.css
git commit -m "style: add global brand-icon class for custom illustrations"
```

---

### Task 2: Generate Core UI Assets (Phase 1)

**Files:**
- Create: `web/static/brand-icons/commute.png`
- Create: `web/static/brand-icons/health.png`
- Create: `web/static/brand-icons/general.png`
- Create: `web/static/brand-icons/alert.png`
- Create: `web/static/brand-icons/all-clear.png`
- Create: `web/static/brand-icons/heads-up.png`

**Step 1: Generate each icon using the master prompt + vase reference image**

| Icon | Subject | Color |
|------|---------|-------|
| commute | Fine-line bicycle wheel | Sage Green #5B8C85 |
| health | Simple heart with leaf accent | Dusty Rose #9B5D77 |
| general | Open bookmark / folded page corner | Mustard Yellow #D99B3F |
| alert | Wobbly exclamation mark | Terracotta #E26C3B |
| all-clear | Flowing checkmark | Sage Green #5B8C85 |
| heads-up | Hand-drawn megaphone | Terracotta #E26C3B |

Example command for `alert`:
```
python .agent/skills/nano-banana-pro/scripts/generate_image.py \
  --input-image web/2026-03-04-22-30-00-vase-icon.png \
  --prompt "Redraw in the same fine-line sketch style as this illustration, but replace the subject with a wobbly hand-drawn exclamation mark, terracotta orange #E26C3B accent tones, sage green #5B8C85 secondary, soft cream background #F3F7F8, subject fills 70% of frame, sketchbook feel, no text, no shadow" \
  --filename web/static/brand-icons/alert.png
```

**Step 2: Check each icon generated correctly. Verify legibility at 20px (browser zoom).**

**Step 3: Commit**
```bash
git add web/static/brand-icons/
git commit -m "assets: generate core UI and alert illustrations"
```

---

### Task 3: Generate Weather Icons (Phase 2)

**Files:**
- Create: `web/static/brand-icons/sunny.png`
- Create: `web/static/brand-icons/partly-cloudy.png`
- Create: `web/static/brand-icons/cloudy.png`
- Create: `web/static/brand-icons/rainy.png`

**Step 1: Generate each weather icon**

| Icon | Subject | Color |
|------|---------|-------|
| sunny | Radiant sun with rays | Mustard Yellow #D99B3F |
| partly-cloudy | Sun half-hidden behind cloud | Mustard #D99B3F + Sage #5B8C85 |
| cloudy | Soft stacked clouds | Dusty Plum #9B5D77 |
| rainy | Rain cloud with falling drops | Navy Blue #1C3E75 |

**Step 2: Check each generated correctly.**

**Step 3: Commit**
```bash
git add web/static/brand-icons/
git commit -m "assets: generate core weather condition illustrations"
```

---

### Task 4: Generate Lifestyle Icons (Phase 3)

**Files:**
- Create: `web/static/brand-icons/air-quality.png`
- Create: `web/static/brand-icons/rain-gear.png`
- Create: `web/static/brand-icons/wardrobe.png`
- Create: `web/static/brand-icons/garden.png`
- Create: `web/static/brand-icons/outdoor.png`
- Create: `web/static/brand-icons/meals.png`
- Create: `web/static/brand-icons/hvac.png`

**Step 1: Generate each lifestyle icon**

| Icon | Subject | Color |
|------|---------|-------|
| air-quality | Abstract wind swirl | Sage Green #5B8C85 |
| rain-gear | Open umbrella | Navy Blue #1C3E75 |
| wardrobe | Folded sweater | Dusty Rose #9B5D77 |
| garden | Seedling sprout | Sage Green #5B8C85 |
| outdoor | Branched tree silhouette | Sage Green #5B8C85 |
| meals | Simple bowl / lunchbox | Mustard Yellow #D99B3F |
| hvac | Vintage thermometer | Terracotta #E26C3B |

**Step 2: Check each generated correctly.**

**Step 3: Commit**
```bash
git add web/static/brand-icons/
git commit -m "assets: generate lifestyle category illustrations"
```

---

### Task 5: (Optional) Strip Backgrounds to Transparent

The generated icons have a soft cream #F3F7F8 background. For dark-mode compatibility, strip
backgrounds to transparent using Pillow:

```python
from PIL import Image
import numpy as np

def remove_light_background(path, threshold=240):
    img = Image.open(path).convert("RGBA")
    data = np.array(img)
    r, g, b, a = data[:,:,0], data[:,:,1], data[:,:,2], data[:,:,3]
    mask = (r > threshold) & (g > threshold) & (b > threshold)
    data[:,:,3][mask] = 0
    Image.fromarray(data).save(path)
```

Run on all files in `web/static/brand-icons/`. Verify one sample looks clean before batch.

```bash
git add web/static/brand-icons/
git commit -m "assets: strip cream backgrounds for transparent-bg brand icons"
```

---

### Task 6: Refactor JS & HTML to use brand icons

**Files:**
- Modify: `web/static/app.js` (Lines mapping to Unicode dicts)
- Modify: `web/templates/dashboard.html` (Static text Nav icons)

**Step 1: Write the minimal code replacements**
Rewrite `ICONS` and `TYPE_ICONS` dictionaries in `app.js` to return `<img>` template literals instead of bare text emojis.

```javascript
  const TYPE_ICONS = {
    Health: '<img src="/static/brand-icons/health.png" class="brand-icon" alt="Health" />',
    Commute: '<img src="/static/brand-icons/commute.png" class="brand-icon" alt="Commute" />',
    // etc...
  };
```

Change instances of `innerElement.textContent = ...` or `icon.textContent = ...` to `innerElement.innerHTML = ...` when injecting these HTML strings. Do the same for `dashboard.html` nav icons manually (replacing `🚲` with the image tag).

In `routes.py`, update the wardrobe functions to inject raw HTML strings directly into the returned text arrays:
```python
        parts.append(f'舒適/短袖 <img src="/static/brand-icons/tshirt.png" class="brand-icon" alt="T-Shirt" />' if is_zh else f'Comfortable / T-shirt <img src="/static/brand-icons/tshirt.png" class="brand-icon" alt="T-Shirt" />')
```

**Step 2: Verify in browser**
Run the server to verify the native emojis are gone and not throwing broken image box indicators.

**Step 3: Commit**
```bash
git add web/static/app.js web/templates/dashboard.html web/routes.py
git commit -m "feat: replace unicode emojis with generated brand illustrations"
```

---

### Task 7: Fix brand icon sizing (post-integration bugfix)

**Problem:** `.brand-icon` CSS class was never written to `style.css` in Task 1. Images rendered
at native Gemini-generated resolution (~512px+), overflowing the 40×40px `.ls-icon` container
(which has no `overflow: hidden`).

**Fix — `web/static/style.css`** (appended after `.ls-icon` block):

```css
/* Brand Icon Integration */
.brand-icon {
  display: block;
  max-width: 100%;
  height: auto;
  margin: 0 auto;
}
```

`max-width: 100%` clamps the image to its container width (40px inside `.ls-icon`,
24px inside `.nav-icon`). `height: auto` preserves aspect ratio. `margin: 0 auto`
centres it in block containers.

**Commit:** `201625e` — `fix: add .brand-icon CSS to constrain brand illustrations to container size`

---

### Task 8: Fine-tune sizing — dashboard hero icon + alert type icon

**Problems observed after Task 7:**
1. **`#cur-icon` (dashboard hero)** — still too large; `#cur-icon` had no explicit width so
   `max-width: 100%` resolved to the full flex-parent width (~200px+).
2. **`.ls-alert-type-icon`** (Heads Up card per-item icon) — brand icon rendered at native
   resolution (~500px) because the unsized `<span>` gave `max-width: 100%` nothing to clamp to.

**Fix — `web/static/style.css`:**

```css
/* desktop */
#cur-icon {
  font-size: 2.5rem;
  width: 5rem;        /* ← added */
}

/* mobile override */
#cur-icon {
  font-size: 2rem;
  width: 3.5rem;      /* ← added */
}

/* scoped alert icon rule (appended after .brand-icon block) */
.ls-alert-type-icon .brand-icon {
  height: 0.9rem;
  width: auto;
  display: inline-block;
  vertical-align: middle;
  margin: 0;
}
```

**Commit:** `11e86cc` — `fix: constrain brand icon sizes for dashboard hero and alert type icons`

---

### Task 9: Forecast icon sizing hierarchy — current > 24h > 7-day

**Problem:** `.tc-icon` and `.wk-icon` containers had no explicit width on their `.brand-icon`
children. Icons sized implicitly via `max-width: 100%` against card width — correct by accident
but fragile. On mobile, 24h cards (~80px wide) made forecast icons appear disproportionately large
relative to the 7-day grid.

**Design:** Explicit `width` + `height` on `.brand-icon` within each forecast context, plus
responsive overrides at 900px and 767px breakpoints. The `#cur-icon` hero is left untouched — its
parent already has `width: 5rem / 3.5rem` which clamps the PNG via `max-width: 100%`.

**Fix — `web/static/style.css`:**

```css
/* Base (desktop) — after .ls-alert-type-icon .brand-icon block */
.tc-icon .brand-icon { width: 60px; height: 60px; }
.wk-icon .brand-icon { width: 36px; height: 36px; }

/* 900px tablet — inside @media (max-width: 900px) */
/* 7-day switches to 4-col; cards wider, icon can afford 32px */
.wk-icon .brand-icon { width: 32px; height: 32px; }

/* 767px mobile — inside @media (max-width: 767px) timeline section */
.tc-icon .brand-icon { width: 44px; height: 44px; }

/* 767px mobile — inside @media (max-width: 767px) weekly section */
/* 7-col ultra-compact; strip to 28px */
.wk-icon .brand-icon { width: 28px; height: 28px; }
```

**Size table across breakpoints:**

| Section | Desktop | Tablet (900px) | Mobile (767px) |
|---------|---------|----------------|----------------|
| Current (`#cur-icon`) | ~80px (via parent `width: 5rem`) | ~80px | ~56px (via parent `width: 3.5rem`) |
| 24-hour (`.tc-icon`) | 60px | 60px | 44px |
| 7-day (`.wk-icon`) | 36px | 32px | 28px |

**Commit:** `fix: add explicit brand-icon sizing hierarchy for forecast sections`

---

### Task 10: Generate missing Dashboard nav icon

**Problem:** The Dashboard nav button (`data-view="dashboard"`) in `dashboard.html` was never
updated during Task 6. It still displayed the raw `📊` emoji while the Lifestyle nav button had
already been converted to use `commute.png`.

**Root cause:** `dashboard.png` did not exist in `web/static/brand-icons/` — it was omitted from
the original Task 2 generation batch.

**Fix:**

1. **Generated `web/static/brand-icons/dashboard.png`** via Nano Banana Pro using
   `vase-icon.png` as the fine-line sketch style reference.
   - Subject: vintage hand-drawn barometer dial with needle
   - Primary color: Mustard Yellow `#D99B3F` (General / overview category)
   - Resolution: 1K (auto-detected from vase reference)

2. **Updated `web/templates/dashboard.html`** line 62 — replaced emoji span with brand icon:
   ```html
   <!-- before -->
   <span class="nav-icon">📊</span>

   <!-- after -->
   <span class="nav-icon"><img src="/static/brand-icons/dashboard.png" class="brand-icon" alt="Dashboard" /></span>
   ```

No CSS changes required — `.nav-icon .brand-icon` sizing (24px via `max-width: 100%`) already
applied from Task 7.

**Commit:** `35bd02c` — `assets: generate dashboard brand icon and wire to nav button`
