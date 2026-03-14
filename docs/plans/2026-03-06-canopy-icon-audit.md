# Canopy Icon Audit & Generation Plan

**Goal:** Map every feature in the Canopy / 厝邊天氣 naming system to a brand icon, generating 14 new PNGs for features not covered by existing assets. Ensures the full feature vocabulary has a visual identity before UI wiring begins.

**Architecture:** Audit existing `web/static/brand-icons/` against the Canopy feature taxonomy. Reuse matching icons where semantics align. Generate new icons for gaps using the `nano-banana-pro` skill (Gemini 3 Pro Image). No JS or HTML changes — asset preparation only.

**Tech Stack:** Nano Banana Pro (skill), `gemini-3-pro-image-preview`, `google-genai` SDK, `uv`.

---

## Canopy Feature → Icon Mapping

### Reuse Existing

| Feature | English Name | Icon File |
|---|---|---|
| Air Quality | Clear/Hazy Canopy | `air-quality.png` |
| HVAC suggestion | Inside Canopy | `hvac.png` |
| Meal suggestion | Canopy Kitchen | `meals.png` |
| Commute hazard | Canopy Commute | `commute.png` |
| Wardrobe tip | Layer Up | `wardrobe.png` |
| Health alert system | Canopy Watch | `health.png` |
| Outdoor score | Canopy Score | `outdoor.png` |
| Pipeline status | Canopy Status | `general.png` |
| Alert tiers | Canopy Watch levels | `alert.png` / `heads-up.png` / `all-clear.png` |
| App nav / overview | Canopy (app) | `dashboard.png` |

### Generated New Icons

Style prompt suffix used on all: *"illustrated icon, soft painterly style, warm Taiwanese aesthetic, pastel colors, 1:1 square format, minimal background, clean rounded composition"*

| Icon File | Feature | English Name |
|---|---|---|
| `morning-shade.png` | 早安厝邊 | Morning Shade |
| `high-canopy.png` | 午時天 | High Canopy |
| `dusk-cover.png` | 暗頭仔天 | Dusk Cover |
| `daily-canopy.png` | 今日厝邊天 | The Daily Canopy |
| `feels-like.png` | 體感溫度 | Feels Under |
| `canopy-moisture.png` | 厝邊濕氣 | Canopy Moisture |
| `heart-flag.png` | 心臟旗 | Heart Flag |
| `pressure-drop.png` | 氣壓警示 | Pressure Drop |
| `uv-warning.png` | 遮蔽不足 | Thin Canopy (UV) |
| `drip-warning.png` | 除濕提醒 | Drip Warning |
| `window-advice.png` | 開窗／關窗時機 | Open the Canopy / Seal Up |
| `cool-shade.png` | 冷氣模式 / 乾燥模式 | Cool Shade / Dry Shade |
| `canopy-log.png` | 天氣紀錄 | Canopy Log |
| `last-drip.png` | 最新資料 | Last Drip |

---

### Task 1: Install uv and create nano-banana-pro skill

**Files:**
- Create: `~/.local/bin/uv.exe` (via installer)
- Create: `~/.claude/skills/nano-banana-pro/scripts/generate_image.py`

**Background:** `uv` was not on the system PATH. Installed via the official PowerShell installer. The `nano-banana-pro` skill script was authored to call `gemini-3-pro-image-preview` via `client.models.generate_content` with `response_modalities=["IMAGE", "TEXT"]`.

**Model discovery:** Initial attempt used `imagen-3.0-generate-001` → 404. Listed available models; found `gemini-3-pro-image-preview` (the correct "Nano Banana Pro" model). Updated script accordingly.

**Key implementation details:**
- Uses `uv` inline script metadata (`# /// script`) for zero-setup dependency install
- Reads `GEMINI_API_KEY` from env or `--api-key` flag
- Text-to-image: `generate_content` with prompt string + `IMAGE` modality
- Image-to-image editing: `generate_content` with `Part.from_bytes` input + prompt

---

### Task 2: Generate 14 new brand icons in 3 parallel batches

**Files created:**
- `web/static/brand-icons/morning-shade.png`
- `web/static/brand-icons/high-canopy.png`
- `web/static/brand-icons/dusk-cover.png`
- `web/static/brand-icons/daily-canopy.png`
- `web/static/brand-icons/feels-like.png`
- `web/static/brand-icons/canopy-moisture.png`
- `web/static/brand-icons/heart-flag.png`
- `web/static/brand-icons/pressure-drop.png`
- `web/static/brand-icons/uv-warning.png`
- `web/static/brand-icons/drip-warning.png`
- `web/static/brand-icons/window-advice.png`
- `web/static/brand-icons/cool-shade.png`
- `web/static/brand-icons/canopy-log.png`
- `web/static/brand-icons/last-drip.png`

**Batches:**
- Batch 1 (5): morning-shade, high-canopy, dusk-cover, daily-canopy, feels-like
- Batch 2 (5): canopy-moisture, heart-flag, pressure-drop, uv-warning, drip-warning
- Batch 3 (4): window-advice, cool-shade, canopy-log, last-drip

All icons verified: HTTP 200 from local Flask server, file sizes 400–635 KB (matching existing icon scale).

**Note:** `GEMINI_API_KEY` sourced from project `.env` via `export $(grep '^GEMINI_API_KEY=' .env)` — background bash tasks don't inherit the parent shell's environment.

---

### Task 3: Generate Canopy PWA app icon and wire to manifest

**Files:**
- Create: `web/static/icon-512.png`
- Create: `web/static/icon-192.png` (copy of 512 — browser resizes as needed)
- Modify: `web/static/manifest.json`
- Modify: `web/templates/dashboard.html`

**Background:** The existing `icon-192.svg` and `icon-512.svg` were generic placeholder SVGs (dark navy square, blue lightning bolt, red arc) with no Canopy brand identity.

**Generated icon prompt:**
```
Square PWA app icon with rounded corners, deep dark navy background, a stylized
painterly canopy of lush tropical leaves arching overhead in warm sage green and
soft gold, a small Taiwanese tile rooftop silhouette at the base in terracotta,
warm amber sky glowing through the canopy leaves, soft illustrated painterly style,
no text, centered composition, app icon format, 1:1 square
```
Resolution: `--resolution 2K`. Output: `web/static/icon-512.png` (~455 KB).

**Manifest changes:**
- Updated `name` to `"Canopy — 厝邊天氣"`, `short_name` to `"厝邊天氣"`
- Replaced SVG icon entries with PNG: `icon-192.png` (192×192) and `icon-512.png` (512×512)
- `type` changed from `image/svg+xml` → `image/png`

**HTML changes (`dashboard.html` lines 12–13):**
- `<link rel="icon">` → `icon-512.png` (`image/png`)
- `<link rel="apple-touch-icon">` → `icon-512.png`

---

### Task 4: Rename app to Canopy / 厝邊天氣 throughout

**Files:**
- Modify: `web/templates/dashboard.html`
- Modify: `web/static/app.js`
- Modify: `web/static/service-worker.js`
- Modify: `web/static/manifest.json`

**Problem:** The app was still named `家庭天氣儀表板` / "Family Weather Dashboard" in the browser tab, i18n strings, and code comments — none of which were updated when the Canopy naming system was established.

**Changes:**

| Location | Before | After |
|---|---|---|
| `dashboard.html` `<title>` | `家庭天氣儀表板` | `厝邊天氣 — Canopy` |
| `dashboard.html` `<meta description>` | `Context-aware…` | `Canopy — 厝邊天氣 · Context-aware…` |
| `app.js` `nav_dashboard` EN | `Dashboard` | `Canopy` |
| `app.js` `nav_dashboard` ZH | `天氣總覽` | `厝邊天氣` |
| `app.js` `h1_dashboard` EN | `Weather Dashboard` | `Canopy` |
| `app.js` `h1_dashboard` ZH | `天氣儀表板` | `厝邊天氣` |
| `app.js` top comment | `Family Weather Dashboard` | `Canopy / 厝邊天氣` |
| `service-worker.js` comment | `Family Weather Dashboard` | `Canopy / 厝邊天氣` |
| `manifest.json` `description` | `Context-aware…` | `Canopy — 厝邊天氣 · Context-aware…` |

**Commit:** `939843b` — `chore: rename app to Canopy / 厝邊天氣 throughout`

---

### Task 5: Rebuild PWA app icon — simpler, mobile-readable

**Problem:** `icon-512.png` (Task 3) was generated at 2K with a complex illustrated scene (arching leaves, rooftop silhouette, amber sky). At 192px or below the detail was unreadable and the icon was unmemorable.

**Design principles applied:** Max 3 colors, single dominant shape/silhouette, flat style, must read at 32px favicon size.

**Three variants generated in parallel at 1K:**

| Variant | File | Concept |
|---|---|---|
| A | `icon-variant-a.png` | Bold arch of 3 sage-green leaves on navy |
| B ✓ | `icon-variant-b.png` | Terracotta tile rooftop + amber arc on navy |
| C (kept) | `icon-variant-c.png` | Single leaf + raindrop on dark teal |

**Selected: Variant B** — Rooftop Sliver. Chosen for its unique silhouette and strong neighbourhood identity.

**Prompt used:**
```
App icon, deep navy square with rounded corners, minimalist Taiwanese tile
rooftop silhouette in terracotta at bottom third, single bold arc of warm amber
light above it like sunrise under an eave, flat vector style, 3 colors only:
navy, terracotta, amber, no text, strong contrast, reads clearly at 32px
```

**Files updated:** `icon-512.png` and `icon-192.png` overwritten with variant B. `icon-variant-c.png` retained. No manifest or HTML changes required (already pointing to `icon-512.png`).

---

### Task 6: Convert PWA icons to WebP (commit `da8de17`)

**Problem:** `icon-512.png` and `icon-192.png` from Task 5 were 1408×768 landscape JPEGs mislabelled as PNG — raw Gemini output. Not square, wrong dimensions, wrong format.

**Fix using Pillow:**
- Center-crop to 768×768 square (x-offset 320 to center the design within the landscape frame)
- Resize to 512×512 → `web/static/icon-512.webp` (6KB, quality 85)
- Resize to 192×192 → `web/static/icon-192.webp` (2.3KB)
- Resize to 32×32 → `web/static/favicon-32.png` (1.9KB — kept PNG for broad browser compat)

**Files updated:**
- `web/static/manifest.json`: icon `src` → `.webp`, `type` → `image/webp`
- `web/templates/dashboard.html`: favicon and apple-touch-icon refs → `.webp`, cache-bust bumped to `v=3`
- Deleted: `web/static/icon-192.png`, `web/static/icon-512.png`

---

### Task 7: Full asset audit + stale file cleanup (commit `5c595d5`)

**Audit scope:** `web/static/` root and `web/static/brand-icons/`

**Findings:**
- All 20 actively-wired brand-icons returned HTTP 200 from local Flask server ✓
- 16 brand-icons were orphans (generated in Task 2 but not yet wired to UI)
- 7 stale files identified in `web/static/` root for deletion

**Deleted:**
- `web/static/icon-192.svg`, `icon-512.svg` — original placeholder SVGs
- `web/static/icon-variant-a.png`, `icon-variant-b.png`, `icon-variant-c.png` — design variants
- `web/static/icon-192.png`, `icon-512.png` — superseded by WebP

**Live PWA icons after cleanup:** `favicon-32.png` (32px PNG) · `icon-192.webp` · `icon-512.webp`

---

### Task 8: Wire 12 orphan Canopy icons to UI (commit `343aa93`)

**Background:** 14 Canopy-feature icons were generated in Task 2. Two (`daily-canopy`, `high-canopy`) were already wired as view header icons in `dashboard.html`. The remaining 12 were unconnected.

**Changes:**

| Icon | Placement | Mechanism |
|---|---|---|
| `canopy-moisture` | Humidity gauge (dashboard view) | `renderGauge()` extended with optional 6th `icon` param |
| `uv-warning` | UV gauge | Same |
| `pressure-drop` | Pressure gauge | Same |
| `feels-like` | Wardrobe lifestyle card | Replaced `wardrobe.webp` — AT is the primary wardrobe driver |
| `heart-flag` | Alert `TYPE_ICONS.Health` | Replaced `health.webp` for Ménière's/cardiac alerts |
| `cool-shade` | HVAC card — mode `cooling` | Conditional icon per `hvacMode` |
| `drip-warning` | HVAC card — mode `dehumidify` | Conditional icon |
| `window-advice` | HVAC card — mode `fan`/`off` | Conditional icon (natural ventilation context) |
| `canopy-log` | ~~Right panel log header~~ | Reverted (commit `c70210b`) — icon too large for narrow header |
| `last-drip` | ~~Last-updated timestamp prefix~~ | Reverted (commit `c70210b`) — full-size brand-icon overwhelmed sidebar |
| `morning-shade` | Sidebar lifestyle nav button | `.nav-icon` span inside `<button data-view="lifestyle">` |
| `dusk-cover` | Sidebar dashboard nav button | `.nav-icon` span inside `<button data-view="dashboard">` |

**CSS additions (`style.css`):**
- `.gauge-icon .brand-icon { width: 28px; height: 28px; }`
- `.nav-icon .brand-icon { width: 24px; height: 24px; }`

---

## 2026-03-14 — Wx Icon Mapping Fix & Partly-Cloudy Regeneration

**Commit:** `fc98cff` — `fix: wx icon mapping — add missing ICONS keys, regenerate partly-cloudy`

### Problem

The dashboard canopy displayed the cloudy (overcast) icon even when the condition was "Sunny". Two root causes:

1. **ICONS dict key mismatch** — The backend `wx_to_cloud_cover()` (`data/scales.py:202`) returns `"Sunny"`, `"Fair"`, and `"Rain"`, but the frontend `ICONS` dict (`app.js:143`) only had lowercase `'sunny'`, `'Sunny/Clear'`, and `'rainy'`. Unmatched keys fell through to the default `IMG('cloudy', 'Cloudy')`.
2. **Broken partly-cloudy images** — `partly-cloudy.webp` and `partly-cloudy-night.webp` showed a vase with leaves (bad Gemini generation artifact from the style-reference approach), not weather icons.

### 4 Wx Levels (day / night)

| Level | Backend `cloud_cover` | Wx codes | Day icon | Night icon |
|---|---|---|---|---|
| Clear | `"Sunny"` | 0–1 | `sunny.webp` | `clear-night.webp` |
| Partly cloudy | `"Fair"`, `"Mixed Clouds"` | 2–7 | `partly-cloudy.webp` | `partly-cloudy-night.webp` |
| Overcast | `"Overcast"` | 8–10 | `cloudy.webp` | `cloudy-night.webp` |
| Rain | `"Rain"` | 11–20 | `rainy.webp` | `rainy-night.webp` |

### Changes

**`web/static/app.js:143–154`** — Added 3 missing keys to `ICONS` dict:
- `'Sunny': IMG('sunny', 'Sunny')`
- `'Fair': IMG('partly-cloudy', 'Partly Cloudy')`
- `'Rain': IMG('rainy', 'Rainy')`

The night branch in `getWeatherIcon()` (lines 159–170) already had `'Sunny'`, `'Fair'`, and `'Rain'` in the array checks — only the daytime `ICONS` dict lookup was broken.

**`web/static/brand-icons/partly-cloudy.webp`** — Regenerated via Nano Banana Pro. New icon: mustard sun with rays partially hidden behind a tan cloud, flat vector style on cream background.

**`web/static/brand-icons/partly-cloudy-night.webp`** — Regenerated. New icon: navy crescent moon partially hidden behind a gray-brown cloud, flat vector style on cream background.
