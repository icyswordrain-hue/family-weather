# Frontend Research: Family Weather Dashboard

**Date of analysis:** 2026-02-20
**Codebase root:** `C:\Users\User\.gemini\antigravity\scratch\family-weather`

---

## 1. Current UI Layout and Components

The UI is a three-column **app shell** (sidebar / main panel / right panel) served by Flask from `web/templates/dashboard.html`. It uses vanilla JavaScript in `web/static/app.js` (no framework). Chart.js is imported via CDN but is not actually used anywhere in the current code.

### Column 1 — Left Sidebar (240 px, dark navy `#1a2235`)

| Component | Description |
|---|---|
| Analog clock | CSS clock with hour and minute hands; second hand element exists in HTML but is `display:none` in CSS |
| Digital time subtitle | 24-hour HH:MM in Asia/Taipei timezone, updates every second |
| Location label `#rp-location` | Populated from `slices.context.location` (CWA station name) |
| Navigation | Three buttons: Dashboard, Lifestyle, Narration |

### Column 2 — Main Panel (flex-grow)

Three mutually exclusive view containers, toggled by `switchView()`.

#### View 1: Dashboard (`#view-dashboard`)

**Current Conditions (upper section):** A 3-column hero row plus a 4-column gauge grid.

| Element | DOM ID | Data source |
|---|---|---|
| Weather icon | `#cur-icon` | `ICONS[slices.current.weather_code]` or `ICONS[slices.current.weather_text]` |
| Temperature | `#cur-temp` | `slices.current.temp` (feels-like AT, rounded) |
| Weather text | `#cur-weather-text` | `slices.current.weather_text` |
| Ground state gauge | `#gauge-ground` | `ground_state` + `ground_level` |
| Wind gauge | `#gauge-wind` | `wind.text`, `wind.val m/s wind.dir`, `wind.level` |
| Humidity gauge | `#gauge-hum` | `hum.text`, `hum.val%`, `hum.level` |
| AQI gauge | `#gauge-aqi` | `aqi.text`, `AQI aqi.val`, `aqi.level` |
| UV Index gauge | `#gauge-uv` | `uv.text`, `Index uv.val`, `uv.level` |
| Pressure gauge | `#gauge-pres` | `pres.text`, `pres.val hPa`, `pres.level` |

All gauges use a 5-level CSS color scale (`lvl-1` green to `lvl-5` red).

**24-Hour Forecast (lower section, below an `<hr>`):**

- `#ov-timeline` — up to 4 time-period cards (Morning/Afternoon/Evening/Overnight). Each shows: period name, weather icon, AT temperature, rain text+level, wind text+level.
- `#ov-alerts` — unified alert box. Renders cardiac alert, Meniere's alert, and heads_up text if triggered.

#### View 2: Lifestyle (`#view-lifestyle`)

Seven icon cards in a 2-column CSS grid. Wide cards span both columns.

| Card | Icon | Data source |
|---|---|---|
| Wardrobe | 🧥 | `slices.lifestyle.wardrobe.text` |
| Rain Gear | ☂️ | `slices.lifestyle.rain_gear.text` |
| Commute | 🚗 | `slices.lifestyle.commute.text` |
| HVAC Advice | 🌡️ | `slices.lifestyle.hvac.text` |
| Meals | 🍱 | `slices.lifestyle.meals.text` |
| Garden Health (wide) | 🌱 | `slices.lifestyle.garden.text` |
| Outdoor Activities (wide) | 🌳 | `slices.lifestyle.outdoor.text` |

#### View 3: Narration (`#view-narration`)

- Native `<audio controls>` element wired to `data.audio_urls.full_audio_url`
- Source badge from `slices.narration.meta.source` and `.model` (CSS class changes color per provider)
- Six paragraph blocks from `slices.narration.paragraphs[]`: Current & Outlook, Commute, Outdoor Health, Meals, Climate & Cardiac, Forecast

### Column 3 — Right Panel (280 px, dark navy)

| Component | Description |
|---|---|
| Last updated | `data.generated_at` formatted to zh-TW locale |
| Provider toggle | Radio: Claude Sonnet / Gemini Pro |
| Refresh button | Posts to `/api/refresh`, streams NDJSON |
| Dark mode toggle | Toggles `html.dark` CSS class, persisted in `localStorage` |
| System Log | Timestamped FIFO log of pipeline steps |

**Dead code note:** `updateRightPanel()` in `app.js` builds a rain forecast context bubble targeting `#rp-dynamic`, but that element does not exist in the HTML. The rain forecast text and context bubble are entirely silently discarded.

---

## 2. API Calls Made

### `GET /api/broadcast`
- Called on page load by `fetchBroadcast()`
- No query params sent (frontend never passes `?date=`)
- Returns today's cached broadcast or triggers the pipeline if not cached
- On success: calls `render(data)` with full broadcast JSON

### `POST /api/refresh`
- Called by `triggerRefresh()` on Refresh button click
- Body: `{ "provider": "CLAUDE" | "GEMINI" }` from radio selection
- Returns NDJSON stream; processed line-by-line:
  - `{ "type": "log", "message": "..." }` → System Log + loading text
  - `{ "type": "result", "payload": {...} }` → `render()` + `showContent()`
  - `{ "type": "error", "message": "..." }` → `showError()`

### `POST /debug/log`
- Called by `remoteLog()` on load and on `window.onerror`
- Forwards browser-side errors to server stdout log
- Body: `{ "type": "info|error", "msg": "...", "ts": "ISO" }`

---

## 3. Data Currently Rendered

**From `slices.current`:** `temp`, `weather_code`, `weather_text`, `ground_state`, `ground_level`, `wind.*`, `hum.*`, `aqi.*`, `uv.*`, `pres.*`

**From `slices.overview.timeline[]`:** `display_name`, `AT`, `cloud_cover`, `Wx`, `precip_text`, `precip_level`, `wind_text`, `wind_level`

**From `slices.overview.alerts`:** `cardiac.triggered`, `cardiac.reason`, `menieres.triggered`, `menieres.reason`, `heads_up`

**From `slices.lifestyle`:** `wardrobe.text`, `rain_gear.text`, `commute.text`, `hvac.text`, `meals.text`, `garden.text`, `outdoor.text`

**From `slices.narration`:** All six `paragraphs[].title/text`, `meta.source`, `meta.model`

**From root object:** `generated_at`, `audio_urls.full_audio_url`, `slices.context.location`

---

## 4. Data Fetched from API but NOT Rendered

### `slices.current.vis` — Visibility
The visibility metric (`vis.val`, `vis.text`, `vis.level`) is fully sliced and leveled in `slices.py` but has no corresponding `gauge-*` DOM element. It is the only metric in `_slice_current()` with no rendered output.

### `slices.context.rain_forecast_text`
Generated by `_slice_context()` with period-specific rain probability text (e.g., "Rain likely (70%) this afternoon."). `updateRightPanel()` tries to write this to `#rp-dynamic` which does not exist in the HTML. Silently discarded.

### `slices.lifestyle.wardrobe.feels_like`
The raw AT value is in the slice but only the `.text` field is rendered on the card.

### `slices.lifestyle.commute.hazards[]`
Structured driving hazard strings are in the slice. Only `commute.text` (the paragraph summary) is shown.

### `slices.lifestyle.hvac.mode`
The mode string (`"heating"`, `"cooling"`, `"dehumidify"`, `"fan"`) is in the slice but only `.text` is rendered.

### `slices.overview.timeline[]` — per-segment fields not rendered
`PoP6h` (raw percentage), `RH`, `WS`, `WD`, `start_time`, `end_time`, `beaufort_desc`

### `processed_data.transitions[]`
Low Deviation Detection results between adjacent time segments (temperature delta, precipitation category shift, wind change, direction change, cloud cover change). Fully computed, never passed to any slice, never displayed.

### `processed_data.heads_ups[]`
Full prioritized alert list (up to 3 items). Only the `heads_up` paragraph key reaches the alert box; the ordered list from the processor is not used.

### `processed_data.meal_mood`
`mood` category string, `avg_at`, `avg_rh`, `is_rainy` — all computed, none shown on screen.

### `processed_data.location_rec.top_locations[]`
Curated named outdoor venues with `name`, `activity`, `surface`, `parkinsons` suitability, `lat`/`lng`, `notes`. Resolved per-day using a 3-day rotation filter. Never surfaced; only the paragraph text from the LLM is shown in the Outdoor card.

### `processed_data.aqi_forecast`
Next-day AQI forecast from MOENV: `area`, `aqi`, `status`, `forecast_date`, `content` (human-readable). Never shown anywhere in the UI.

### `processed_data.climate_control`
Full HVAC recommendation object: `mode`, `set_temp`, `estimated_hours`, `dehumidify`, `windows_open`, `notes[]`. Only the text summary reaches the HVAC lifestyle card.

### `data.audio_urls` — kids audio
The TTS pipeline generates both `full_audio_url` and `kids_audio_url`. Only `full_audio_url` is wired to the player.

---

## 5. Missing UI Sections That Would Benefit from Backend Data

1. **Visibility gauge** — Add `#gauge-vis` to the gauges grid; one HTML element + one JS call.
2. **Rain forecast text in right panel** — Restore `#rp-dynamic` to the HTML; `updateRightPanel()` already builds it.
3. **Commute hazard bullet list** — Show `commute.hazards[]` beneath the commute card text.
4. **HVAC mode badge** — Display `hvac.mode` as a badge on the HVAC card.
5. **Meal mood tag** — Show `meal_mood.mood` as a badge on the Meals card.
6. **Feels-like sub-note on wardrobe card** — Show `wardrobe.feels_like` as "Feels like N°" below the text.
7. **Transition indicators on timeline** — Highlight adjacent timeline cards where `is_transition: true` in `transitions[]`.
8. **Structured outdoor location tiles** — Show `location_rec.top_locations[0-1]` as concrete venue cards with name, activity, and map link.
9. **Tomorrow's AQI** — Display `aqi_forecast.content` below the AQI gauge or in a forecast section.
10. **Kids audio toggle** — Wire `audio_urls.kids_audio_url` to a second player or a toggle.
11. **Date navigation** — Prev/Next day buttons calling `/api/broadcast?date=YYYY-MM-DD`.
12. **Full heads-up list** — Render all items in `processed_data.heads_ups[]`, not just the first one routed through paragraphs.

---

## 6. PWA / Offline Features

### Manifest (`/static/manifest.json`)
- `display: standalone`, `theme_color: #1a2235`, `start_url: /`
- Two SVG icons (192 and 512 px), both `purpose: any maskable`
- **Gaps:** No `screenshots`, no `shortcuts`, no `categories`; older audits may prefer PNG fallbacks alongside SVG.

### Service Worker (`/static/sw.js`) — Cache name: `weather-v6`

| Route pattern | Strategy |
|---|---|
| `/api/*` | Network-first, cache fallback |
| All other routes (static assets) | Stale-while-revalidate (cache immediately, fetch update in background) |

**Lifecycle:** `skipWaiting()` on install + `clients.claim()` on activate for immediate takeover. Old caches deleted on activation.

**Gaps:**
- Audio files (`/local_assets/...`) are not cached — offline playback of last broadcast is not possible.
- Bare URLs in `SHELL_ASSETS` (e.g., `/static/style.css`) do not match the versioned URLs the HTML references (`?v=11`, `?v=13`), creating a potential cache miss for the versioned URLs.
- No background sync or push notifications for new broadcast availability.
- No explicit offline fallback page — browser shows its own offline screen if both network and cache fail for `/`.

---

## 7. Recommended Frontend Improvements

### Low effort (1–5 lines of code each)
- Add `#gauge-vis` to HTML, call `renderGauge('gauge-vis', ...)` in `renderCurrentView()`
- Add `<div id="rp-dynamic"></div>` back to `dashboard.html` inside `.rp-top`
- Enable the second hand on the analog clock (remove `display: none` from `.hand.second` in CSS)
- Add HVAC mode badge inside the HVAC lifestyle card
- Add meal mood tag inside the Meals lifestyle card

### Medium effort
- Render `commute.hazards[]` as a bullet list beneath the commute card
- Show `wardrobe.feels_like` as a sub-note on the wardrobe card
- Wire `audio_urls.kids_audio_url` to a second audio player or toggle
- Add tomorrow's AQI block using `aqi_forecast.content`
- Add date prev/next navigation buttons

### Higher effort (requires slice changes or new UI components)
- Pass `transitions[]` through the overview slice and render visual transition markers between timeline cards
- Pass `location_rec.top_locations` through the lifestyle slice and render concrete venue cards
- Pass full `heads_ups[]` through the overview slice instead of the single `heads_up` paragraph key
- Add PWA offline fallback page and cache the last audio file for offline playback
- Fix service worker SHELL_ASSETS to use versioned URLs that match what the HTML actually requests
