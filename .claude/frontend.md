# Frontend Code Review: Family Weather Dashboard

**Last reviewed:** 2026-02-20 (round 2 — post tasks 1–9)
**Codebase root:** `C:\Users\User\.gemini\antigravity\scratch\family-weather`

---

## Executive Summary

1. **Dark mode IIFE crashes on page load** — HTML references `dark-mode-btn/icon/label` (null); actual IDs are `theme-toggle/theme-icon/theme-text`. `btn.addEventListener` throws immediately.
2. **Wind direction renders as "null m/s null"** — `data.wind.dir` has no optional chaining fallback when null.
3. **Timeline segment fields render "undefined"** — `seg.precip_text`, `seg.wind_text`, `seg.AT` have no null guards in the card template.
4. **Timeline grid not responsive** — `.timeline-grid` is always `repeat(4,1fr)` with no mobile breakpoint; unreadable at ≤768px.
5. **Service worker cache misses versioned assets** — SW caches `/static/style.css` but HTML requests `/static/style.css?v=14`; stale CSS/JS served offline.

---

## 1. UI Layout and Components

Three-column **app shell** (sidebar / main panel / right panel). Vanilla JS, no framework. Chart.js loaded via CDN but **never used anywhere**.

### Left Sidebar (240 px)

| Component | DOM ID | Source |
|---|---|---|
| Analog clock | `#clock-hour/minute/second` | Local JS |
| Digital time | `#rp-time` | Asia/Taipei, updates every second |
| Location label | `#rp-location` | `slices.current.location` |
| Navigation buttons | `data-view` attrs | `switchView()` |

### Main Panel — View: Dashboard (`#view-dashboard`)

**Current conditions:** 3-column hero row + 4-column gauge grid.

| Element | DOM ID | Slice field |
|---|---|---|
| Weather icon | `#cur-icon` | `current.weather_code` / `weather_text` |
| Temperature | `#cur-temp` | `current.temp` (feels-like AT) |
| Weather text | `#cur-weather-text` | `current.weather_text` |
| Ground state | `#gauge-ground` | `current.ground_state/level` |
| Wind | `#gauge-wind` | `current.wind.*` |
| Humidity | `#gauge-hum` | `current.hum.*` |
| AQI | `#gauge-aqi` | `current.aqi.*` |
| UV | `#gauge-uv` | `current.uv.*` |
| Pressure | `#gauge-pres` | `current.pres.*` |

**24-Hour Forecast:** `#ov-timeline` (4 cards) + `#ov-alerts` (unified alert box).

### Main Panel — View: Lifestyle (`#view-lifestyle`)

Seven `makeIconCard()` tiles in 2-column CSS grid:

| Card | Icon | Slice field |
|---|---|---|
| Wardrobe | 🧥 | `lifestyle.wardrobe.text` + `feels_like` sub-note |
| Rain Gear | ☂️ | `lifestyle.rain_gear.text` |
| Commute | 🚗 | `lifestyle.commute.text` + `hazards[]` list |
| HVAC | 🌡️ | `lifestyle.hvac.text` + `mode` badge |
| Meals | 🍱 | `lifestyle.meals.text` + `mood` badge |
| Garden (wide) | 🌱 | `lifestyle.garden.text` |
| Outdoor (wide) | 🌳 | `lifestyle.outdoor.text` (+ `location` object — not yet rendered) |

### Main Panel — View: Narration (`#view-narration`)

- Native `<audio controls>` wired to `audio_urls.full_audio_url`
- Source badge from `narration.meta.source` / `.model`
- 6 paragraph blocks from `narration.paragraphs[]`

### Right Panel (280 px)

Provider radio, Refresh button, Dark Mode toggle, System Log.

---

## 2. Critical Bugs

### BUG-F1: Dark mode IIFE crashes (CRITICAL)

`dashboard.html:205–223` queries elements that don't exist:

```javascript
// These IDs do not exist in the HTML:
document.getElementById('dark-mode-btn')    // NULL → crash on .addEventListener
document.getElementById('dark-mode-icon')   // NULL
document.getElementById('dark-mode-label')  // NULL

// Actual element IDs in HTML:
// id="theme-toggle"  id="theme-icon"  id="theme-text"
```

**Fix:** Change the three `getElementById` calls to use `theme-toggle`, `theme-icon`, `theme-text`.

### BUG-F2: Wind direction renders "null m/s null" (HIGH)

`app.js` line ~137:
```javascript
`${data.wind.val} m/s ${data.wind.dir}`
// If wind.dir is null → "3.2 m/s null"
```

**Fix:** `${data.wind.dir || '—'}`

### BUG-F3: Timeline cards show "undefined" text (HIGH)

Segment card template renders `seg.precip_text`, `seg.wind_text`, `seg.AT` without guards.

**Fix:** `${seg.precip_text || '—'}`, `${seg.wind_text || '—'}`, `${Math.round(seg.AT ?? seg.T ?? 0)}`

---

## 3. Data Gaps — Fetched but Not Rendered

| Field | Source | Status |
|---|---|---|
| `current.vis.*` | visibility metric | ⚠️ Sliced but no gauge rendered |
| `current.obs_time` | CWA observation timestamp | ⚠️ In slice, never displayed |
| `current.aqi.pm25` / `.pm10` | particulate matter | ⚠️ In slice, never displayed |
| `overview.alerts.heads_ups[]` | full heads-up list | ⚠️ Array in slice, not rendered |
| `lifestyle.outdoor.location` | structured venue object | ⚠️ In slice (task #5), not yet rendered |
| `audio_urls.kids_audio_url` | kids broadcast | ⚠️ Generated, not wired to player |

---

## 4. CSS Issues

### Missing responsive breakpoint for timeline (HIGH)

```css
/* Only rule — always 4 columns */
.timeline-grid { grid-template-columns: repeat(4, 1fr); }
```

Add:
```css
@media (max-width: 1024px) { .timeline-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 768px)  { .timeline-grid { grid-template-columns: 1fr; } }
```

### Incomplete dark mode level colors (MEDIUM)

Only `lvl-1` and `lvl-5` have dark mode overrides. `lvl-2`, `lvl-3`, `lvl-4` use light-theme colors on dark backgrounds.

### Duplicate CSS rule (LOW)

```css
/* Lines 1280 and 1286 — identical rule duplicated */
html.dark audio { filter: invert(1) hue-rotate(180deg); }
```

### Chart.js loaded but unused (LOW)

`<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/...">` — remove if not needed, saves ~50 KB.

---

## 5. Service Worker Issues

### Cache version / query param mismatch (HIGH)

`sw.js` caches bare URLs; HTML uses versioned URLs:

| Cached in SW | Requested by HTML |
|---|---|
| `/static/style.css` | `/static/style.css?v=14` |
| `/static/app.js` | `/static/app.js?v=16` |

Cache miss on every load → falls back to network. Offline stale-while-revalidate broken.

**Fix:** Strip query strings in SW fetch handler, OR increment `CACHE_NAME` on every deploy, OR serve assets at versioned paths without query params.

### Missing assets (MEDIUM)

- Google Fonts CDN not cached → offline renders unstyled text
- Chart.js CDN not cached → offline breaks if charts added
- `/local_assets/*.mp3` not cached → offline playback unavailable

### API offline fallback (MEDIUM)

Network-first for `/api/*` falls back to cache, but API responses are never explicitly cached (`cache.put()` missing). Effective result: offline shows error screen.

---

## 6. PWA (manifest.json)

| Check | Status |
|---|---|
| `name`, `short_name`, `display: standalone` | ✓ |
| `start_url`, `theme_color`, `background_color` | ✓ |
| `orientation: any` | ✓ |
| SVG icons (192, 512) | ✓ |
| PNG icon fallbacks | ⚠️ Missing — older Android may not render SVG |
| `categories` | ⚠️ Missing |
| `screenshots`, `shortcuts` | ⚠️ Missing (optional) |

---

## 7. Element / Class Reference Map

### Element IDs in HTML with no JS consumer

*(None currently — all IDs are referenced)*

### CSS classes applied in JS but verified in CSS

| Class | Generated by | CSS defined |
|---|---|---|
| `.lvl-0` through `.lvl-5` | `renderGauge()` | ✓ |
| `.hvac-heating/cooling/dehumidify/fan` | lifestyle render | ✓ |
| `.mood-badge` | meals render | ✓ |
| `.ls-sub`, `.ls-badge`, `.ls-hazards` | lifestyle render | ✓ |
| `.has-health` | alert render | ✓ |
| `.source-gemini/claude/template` | narration render | ✓ |

---

## 8. Priority Fixes

1. **Fix dark mode IIFE element IDs** in `dashboard.html:205–223` — CRITICAL, crashes page load
2. **Add `|| '—'` fallback to `wind.dir`** in `app.js` — HIGH, renders "null" in production
3. **Add null guards to timeline segment fields** in `app.js` — HIGH, renders "undefined" in production
4. **Add responsive CSS breakpoints to `.timeline-grid`** — HIGH, unusable on mobile
5. **Fix SW cache to strip query params or bump `CACHE_NAME`** — MEDIUM, offline/stale mode broken
