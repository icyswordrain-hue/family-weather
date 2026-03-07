# Canopy Frontend Design Suggestions

Reference: Apple Weather (iOS 18) · Google Pixel Weather (2025)
Reviewed against: `web/templates/dashboard.html`, `web/static/app.js`, `web/static/style.css`

---

## 1. AI Summary as Hero Anchor

Google Pixel's AI Weather Report appears above the fold on first launch — it is the first text users read, not a secondary tab. Apple's weather narrative is similarly the entry point, not buried in a sub-view.

**Current state:** The Lifestyle AI narration lives inside `#view-lifestyle` as one of many equal-weight lifestyle cards. The `current-hero` (large temperature + icon) still dominates visually even when the Lifestyle tab is active.

**Recommendation:** Elevate the AI summary paragraph to a distinct banner just below the hero temperature block — visible without any tab switch or scroll. Use a subtle left-accent border and slightly larger type to distinguish it as "the interpretation of the numbers above." This is the single highest-impact UX change available.

---

## 2. "Feels Like" Smart Contextual Prominence

iOS 18 made "Feels Like" its headline UX change — but critically, it **only appears when the gap from actual temperature is meaningful** (≥2–3 °C). When feels-like equals actual, showing both is redundant noise.

**Current state:** The hero shows actual temperature only. `apparent_temp_c` is computed in `data/helpers.py` and stored in `station_history.jsonl`, but not surfaced in the hero.

**Recommendation:** Show `Feels like N°` directly under the main temperature — only when `|apparent_temp_c − temp_c| ≥ 2`. When the gap is small, suppress it. Pair with a short "Rain likely at HH:MM" line when the next-hour forecast shows PoP > 40%, using existing `forecast_segments` data. These two conditional lines replace the current static sub-label.

---

## 3. Horizontal 24-Hour Forecast Scroll

The 24h timeline uses a CSS grid with 4 equal columns. On mobile this collapses but still requires vertical scrolling through the grid.

**Current state:** `#ov-timeline` is a 4-column CSS grid of `.time-card` elements rendered in `renderOverviewView()`.

**Recommendation:** Replace the 4-column grid with a single horizontal `overflow-x: auto` flex row of fixed-width cards (~120px each), showing 3.5 cards on mobile so overflow is visually implied. Add `scroll-snap-type: x mandatory` for momentum and `-webkit-overflow-scrolling: touch`. This is the universal pattern used by Apple, Google, Carrot, and every modern weather app.

---

## 4. Smart Gauge Visibility by Default

Google Pixel Weather introduced a customizable detail-card grid where users reorder metrics by personal priority. Apple uses visual weight (size, colour) to guide attention without hiding data.

**Current state:** All 4 gauges (Humidity, AQI, UV, Pressure) render equally in a 2×2 grid via `renderGauge()`.

**Recommendation:** Promote the two decision-driving gauges (AQI, UV) to full-size primary slots with value + sub-label. Demote Humidity and Pressure to a compact secondary row (half-height, smaller value text) below. Preserves all data while creating a clear hierarchy: "act on these two, refer to these two." No accordion needed — just size differentiation via a new `.gauge-secondary` modifier class.

---

## 5. Inline Temperature Range Bars in 7-Day Forecast

Apple Weather replaces a separate sparkline chart with inline min-max range bars rendered *within* each daily row — a horizontal pill showing the temperature continuum from day-low to day-high, coloured by relative warmth.

**Current state:** The app renders `wk-card` day/night pairs plus a separate Chart.js canvas sparkline below, requiring a `<canvas>` element and chart instantiation in `renderOverviewView()`.

**Recommendation:** Remove the Chart.js sparkline canvas. Inside each `wk-card`, render a thin horizontal range bar using a CSS `linear-gradient` from cool-blue to warm-amber, with each day's segment positioned proportionally across the week's absolute temperature bounds. Reduces DOM complexity, eliminates a JS dependency, and keeps temperature trends visible inline.

---

## 6. Unified Entry with Lifestyle-First Scroll

The two-tab model (Lifestyle | Dashboard) forces a navigation decision before the user sees anything. Google Pixel and Apple both use a single scrolling canvas — the smart summary at top, raw detail below.

**Current state:** `switchView()` in `app.js` toggles `.active` between `#view-lifestyle` and `#view-dashboard`. The sidebar nav items are hard view-toggle triggers.

**Recommendation:** Merge the two views into one vertically scrolling page: AI summary → lifestyle cards → 24h forecast → 4 gauges → 7-day forecast. The sidebar nav items become `scrollIntoView()` anchors rather than view toggles. Keep the tab labels as visible section headers. This eliminates the cognitive cost of choosing a view and matches the scroll-to-explore behaviour of both reference apps.

---

## 7. Solar-Driven Ambient Colour Theming

Apple Weather's background subtly shifts with time of day (blue-black at night, vivid blue midday, amber at sunset). The app already **computes solar phase** — `solar.is_daytime`, `solar.next_event`, `sunrise`, `sunset` are all in `slices.current.solar`.

**Current state:** CSS custom properties (`--main-bg: #F3F0E8`, `--sidebar-bg: #3B2F1E`) are static. Dark mode exists but no time-of-day phase theming.

**Recommendation:** At broadcast render time in `app.js`, read solar phase from the data and apply a `data-phase="dawn|day|dusk|night"` attribute to `<body>`. Define 4 sets of CSS custom property overrides in `style.css` scoped to `[data-phase]`. The earthy palette translates naturally: dawn (warm rose tints), day (current cream/sage), dusk (amber/terracotta), night (deeper walnut, lower contrast). Transitions via `transition: background-color 2s ease`. No new API data needed.

---

## 8. Commute Card Hazard Icon Badges

The Commute lifestyle card renders hazards as unstructured prose (e.g., "Heavy rain expected. Strong winds. Low visibility."), requiring reading rather than scanning.

**Current state:** `renderLifestyleView()` builds the commute card using the `add()` helper with a flat hazard text string.

**Recommendation:** Represent each hazard as a compact `ls-badge`-style pill with a leading icon: `🌧 Rain · Heavy`, `💨 Wind · 45 km/h`, `🌫 Visibility · Low`. Hazard data already arrives structured from the backend; this is purely a frontend rendering change. Matches the established badge system used in the Outdoor, HVAC, and Air Quality cards — brings Commute into visual consistency with the rest of the lifestyle grid.

---

## 9. Outdoor "Best Window" Mini Timeline Bar

The Outdoor Activities card shows a text string like "Best window: 09:00–15:00." This is informative but requires parsing. A visual representation conveys the same at a glance.

**Current state:** `renderLifestyleView()` renders `best_window` as a sub-line via `mkSub()`. The backend already emits `forecast_segments` with per-hour `outdoor_grade` and `is_daylight` flags.

**Recommendation:** Replace the text sub-line with a 24-cell mini timeline bar (one `<span>` per hour, rendered inline via JS). Each cell is colour-coded: `oi-grade-A/B` → green fill, `C` → amber, `D/F` → red, nighttime → dark/empty. The best-window range is highlighted with a subtle raised border. The bar is ~200px wide and non-interactive. Reuses existing `oi-grade-*` colour tokens — zero new CSS needed.

---

## 10. Cross-View Critical Alert Persistence

The current alert card (`ls-alert-card.ls-alert-critical`) only renders inside `#view-lifestyle`. If the user is viewing the Dashboard tab, they have no awareness of an active severe weather or AQI warning.

**Current state:** Alert cards are built inside `renderLifestyleView()` and are invisible when the dashboard view is active.

**Recommendation:** For alerts with `level === "critical"` (AQI > 150, Ménière's trigger, or severe CWA warning), inject a persistent slim banner `#global-alert-bar` above the main content area — outside both view containers, rendered by `renderCurrentView()`. The banner shows the highest-severity alert type, a one-line summary, and a "⟶ Details" link that switches to the lifestyle view. It disappears when no critical alerts are present. This mirrors Apple's persistent severe weather strip and Google's above-fold AQI warning bar.

---

## 11. 7-Day Row Typography and Range Bar Weight

Apple Weather's 7-day list uses large, high-contrast day labels and thick temperature range pillars — the type is immediately readable and the bars carry clear visual weight relative to the row height.

**Previous state:** `.wk-row-label` was `0.65rem` (desktop) / `0.58rem` (mobile) — too small relative to the 54px day icon. `.wk-range-container` was `6px` tall, appearing hairline-thin against the enlarged icons. `.wk-min-temp`/`.wk-max-temp` were `0.90rem` / `0.82rem`. `.wk-row-day` used `flex: 0 0 auto`, so variable letter-widths ("WED" vs "FRI") caused the temperature bar to start at inconsistent horizontal positions across rows.

**Implemented:** Enlarged day labels to `1rem` / `0.9rem` mobile. Doubled range bar to `12px` height with `6px` border-radius. Temperature values scaled to `1.35rem` / `1.23rem` mobile. Fixed `.wk-row-day` at `flex: 0 0 106px` (desktop) / `flex: 0 0 88px` (mobile) — a constant flex-basis that locks the day section width regardless of day-name character widths, so the icon column and the range bar column start at the same horizontal position on every row.

---

## 12. 36-Hour Segment Row Visual Parity with 7-Day View

The 36h timeline rows showed several visual regressions relative to the 7-day rows they sit above: the temperature range bar was invisible, the left column was cluttered with a redundant time label, text sizes were mismatched, and the right column showed a raw letter grade rather than meaningful icon+text.

**Previous state:** The range bar was gated on `seg.AT != null` — if only `MinAT`/`MaxAT` were populated (which the CWA 36h API can produce) the bar silently disappeared. The center column container (`tc-seg-center`) used `display:flex` but the inner `wk-row-temps` row had no `width:100%`, causing it to collapse to content width so the bar had no room to render. Segment labels were `0.65rem` vs the 7-day's `1rem`. Temperature values were `1.1rem` vs the 7-day's `1.35rem`. The left column showed a `18:00` / `0:00` timestamp beneath every icon — information already communicated by the segment name ("Day 1", "Tonight"). The right column showed `"A Good to go"` (grade letter + label) with no icon, and plain text for precipitation with no icon.

**Implemented:** Fixed bar condition to `(seg.MinAT != null || seg.AT != null)`. Added `.tc-seg-center .wk-row-temps { width: 100% }` so the range bar fills the column. Removed the `.tc-seg-time` element from the left column. Set `.tc-seg-label` to `1rem` and `.tc-seg-temp` to `1.35rem` (matching `.wk-row-label` and `.wk-min-temp`/`.wk-max-temp` respectively; mobile `1.23rem`). Right column now renders `outdoor.webp` brand icon + outdoor label text (grade letter removed); precipitation renders `rain-gear.webp` icon + precip text. `.tc-seg-stat` is now `display:flex` with `gap:4px` and `.brand-icon` sized at `20px`.

---

## 13. 36-Hour Range Bar: Server-Side Temperature Span Derivation

The CWA 36h API delivers hourly point-in-time AT values. `weather_processor.py` `_segment_forecast()` aggregates each 6-hour window's hourly AT values into `MinAT = min(at_vals)` and `MaxAT = max(at_vals)` per segment, giving each segment a genuine temperature span. However the global 36h range (needed to position each bar proportionally) was being recomputed in the frontend on every render — which duplicates logic and was also broken (previously hardcoded to `left:0%, width:100%`).

**Previous state:** The frontend `renderOverviewView()` re-derived `tlGlobalMin`/`tlGlobalMax` by iterating over timeline segments each render. When the bar position code was later changed to `left:0%, width:100%`, this loop became dead code and the bars lost all proportional meaning. Range bar positioning also showed `min 15° max 15°` for segments where all 6 hourly AT values were flat (e.g., overnight), which is correct data but looked broken alongside the full-width bar.

**Implemented:** `_slice_overview()` in `web/routes.py` now computes `timeline_temp_range = {min, max}` server-side from all segments' `MinAT` (falling back to `AT`) and `MaxAT` (falling back to `AT`), and includes it in the overview slice. The frontend reads `data.timeline_temp_range.min/.max` directly; the local loop is retained as a fallback for old cached broadcasts that pre-date this field. Bar positioning restored to proportional `leftPct`/`rightPct` using this global span. When `lo === hi` (flat overnight segments), the min label is suppressed and a single positioned point is shown.
