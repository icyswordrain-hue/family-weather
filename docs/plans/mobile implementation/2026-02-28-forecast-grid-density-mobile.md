# Forecast Grid Density on Mobile

> **Date:** 2026-02-28
> **Status:** Implemented
> **Commits:** `405c2b0`, `01ea0b3`, `2b1cda5`

---

## The Problem

Both forecast grids were too sparse on mobile, making them harder to scan:

- **7-day forecast** — rendered 4 columns (set at the 900px breakpoint), so the week was split across two rows of 4. Users couldn't see all 7 days at once without mentally stitching the rows together. PoP text ("Very Unlikely", "Likely", etc.) in each card was the main obstacle to going narrower.

- **24-hour forecast** — rendered 2 columns, so 4–5 time slots stacked into a 2–3 row grid. A single glance couldn't capture the day's arc.

---

## 7-Day Forecast: 7-per-row, PoP hidden

### Feasibility

Mobile content width = device width − 32 px padding. With 7 cards and 6 × 3 px gaps:

| Device | Content | Card width |
|--------|---------|------------|
| 375 px (iPhone SE/14) | 343 px | ~47 px |
| 390 px (iPhone 14 Pro) | 358 px | ~49 px |
| 320 px (small) | 288 px | ~39 px |

At ~47 px per card the three remaining elements fit comfortably:
- Day abbreviation "Mon" at 0.62 rem ≈ 18 px ✓
- Emoji icon at 1.2 rem ≈ 19 px ✓
- Temperature "28°" at 0.9 rem ≈ 21 px ✓

The Day/Night period label ("Mon Day", "Thu Night") was the width bottleneck. Removing it is safe because day vs night is already visually encoded in the card background colour (`.wk-day` / `.wk-night`).

### Changes made

**`web/static/app.js`** — commit `405c2b0`

Split the label from a single text node into two child spans so the period can be hidden by CSS without JS involvement:

```js
// Before
label.textContent = `${dayLabel} ${periodLabel}`;

// After
const daySpan = document.createElement('span');
daySpan.className = 'wk-day-name';
daySpan.textContent = dayLabel;
const periodSpan = document.createElement('span');
periodSpan.className = 'wk-period';
periodSpan.textContent = ` ${periodLabel}`;
label.appendChild(daySpan);
label.appendChild(periodSpan);
```

**`web/static/style.css`** — commit `405c2b0`

New `@media (max-width: 767px)` block appended after the existing 900 px block (which still governs tablets at 768–900 px):

```css
@media (max-width: 767px) {
  .weekly-grid {
    grid-template-columns: repeat(7, 1fr);
    gap: 3px;
  }
  .wk-card   { padding: 4px 3px; gap: 1px; }
  .wk-icon   { font-size: 1.2rem; }
  .wk-temp   { font-size: 0.9rem; }
  .wk-rain   { display: none; }
  .wk-period { display: none; }
}
```

The 900 px rule (4 columns) applies to tablets; the 767 px rule overrides to 7 columns for phones because it appears later in the file.

---

## 24-Hour Forecast: 4-per-row compact cards

### Feasibility

Same content-width math. With 4 cards and 3 × 8 px gaps:

| Device | Content | Card width |
|--------|---------|------------|
| 375 px | 343 px | ~80 px |
| 320 px | 288 px | ~67 px |

With card padding reduced to `0.75 rem 0.4 rem`, the inner draw area is ~54–67 px. The three top elements (header, icon, temp) fit cleanly. The detail rows (Rain, Outdoor) need a stacked layout to fit — side-by-side text like "Rain / Very Unlikely" overflows at any usable font size.

### Changes made

**`web/static/style.css`** — commits `01ea0b3`, `2b1cda5`

The existing mobile `.timeline-grid` rule (previously `repeat(2, 1fr)`) was replaced with the full compact-card block:

```css
/* 24h timeline: 4 per row, compact cards */
.timeline-grid {
  grid-template-columns: repeat(4, 1fr);
  gap: 0.5rem;
}
.time-card {
  padding: 0.75rem 0.4rem;
  min-height: 0;
}
.tc-header {
  font-size: 0.62rem;
  margin-bottom: 0.2rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tc-icon   { font-size: 1.4rem; margin: 0.2rem 0; }
.tc-temp   { font-size: 1rem; margin-bottom: 0.3rem; }
.tc-details { padding-top: 0.4rem; gap: 0.25rem; }
.tc-row    { flex-direction: column; gap: 0.05rem; }
.tc-label  { font-size: 0.55rem; }
.tc-val    { font-size: 0.75rem; }
```

Key decisions:
- `min-height: 0` — the desktop 200 px floor was irrelevant for compact mobile cards.
- `tc-header` ellipsis — "Afternoon" is 9 chars and would overflow the ~54 px inner width on a 320 px phone at 0.62 rem without truncation.
- `tc-row` stacked column — "Very Unlikely" at any practical font size is too wide to sit beside a label. Stacking label above value fits both within the card width.
- `tc-details` padding-top reduced from 0.8 rem to 0.4 rem — the border separator still reads clearly at the tighter spacing.

### What stayed the same

- `web/templates/dashboard.html` — no changes.
- JS rendering logic for both forecast grids — untouched (`.tc-details` was never built conditionally; CSS drives visibility).
- Desktop and tablet layouts — unaffected (changes are scoped to `max-width: 767px`).

---

## Follow-up fix — apparent temperature double-calculation

> **Commit:** `652bbae`

After the grid-density work exposed the `.tc-temp` values more prominently, the Afternoon card
showed 38° while the other three segments sat in the low-to-mid 20s. Root cause:

The CWA 36-hour forecast API (`F-D0047-069`) returns `ApparentTemperature` (體感溫度) — already
a pre-computed feels-like value. `fetch_cwa.py` stored this directly as `slot["AT"]`. The segment
enrichment step in `weather_processor.py` then passed `AT` as the actual air temperature (`ta`)
into the BOM formula, double-counting the humidity and wind adjustment.

The 7-day code already had a guard (`# AT is already apparent temperature — do not recalculate`),
but the 36-hour path had no equivalent.

**Fix:** `fetch_cwa.py` now stores the `Temperature` element separately as `slot["T"]`. Segment
enrichment and `_commute_window` use `T` as the BOM formula input, falling back to `AT` only when
`T` is absent. `_average_slots` was updated to include `T` in its numeric averaging keys.

---

## Amendment — 2026-02-28: day-name column headers + condition text

**Commit:** `c6aa60d`

### Problem

With the 7-per-row compact layout the day name ("Mon" / "一") was redundant: it appeared inside **both** the day card and the night card for the same column — twice per column, 14 times across the grid. Additionally the `cloud_cover` field ("Sunny", "Mixed Clouds", etc.) was available in the slot data but only used internally for icon lookup and never shown to the user.

### Changes

**`web/templates/dashboard.html`**

New header container injected directly before `#ov-weekly-timeline`:

```html
<div class="wk-header-row" id="ov-weekly-header"></div>
```

**`web/static/app.js`**

1. `cloudCover` map added to both `TRANSLATIONS.en` and `TRANSLATIONS['zh-TW']`:

   ```js
   // en
   cloudCover: { Sunny: 'Sunny', Fair: 'Fair', 'Mixed Clouds': 'Cloudy', Overcast: 'Overcast', Rain: 'Rain', Unknown: '—' },
   // zh-TW
   cloudCover: { Sunny: '晴', Fair: '晴多雲', 'Mixed Clouds': '多雲', Overcast: '陰', Rain: '雨', Unknown: '—' },
   ```

2. Header row populated from `topItems` before the card loop:

   ```js
   const headerEl = document.getElementById('ov-weekly-header');
   if (headerEl) {
     headerEl.innerHTML = '';
     topItems.forEach(item => {
       const hdr = document.createElement('div');
       hdr.className = 'wk-col-header';
       if (item) {
         let dt;
         try { dt = new Date(item.start_time.replace('+08:00', '')); } catch { dt = new Date(); }
         hdr.textContent = T.days[dt.getDay()];
       } else { hdr.textContent = '—'; }
       headerEl.appendChild(hdr);
     });
   }
   ```

3. `.wk-cond` div added to each card after the icon:

   ```js
   const cond = document.createElement('div');
   cond.className = 'wk-cond';
   cond.textContent = (T.cloudCover && T.cloudCover[item.cloud_cover]) || item.cloud_cover || '—';
   card.appendChild(icon);
   card.appendChild(cond);   // ← new
   card.appendChild(temp);
   ```

   The `.wk-day-name` span remains in the DOM; CSS controls its visibility.

**`web/static/style.css`**

New base rules (outside media queries — apply at desktop ≥901 px):

```css
.wk-header-row { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-bottom: 2px; }
.wk-col-header { text-align: center; font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
                 letter-spacing: 0.04em; color: var(--muted); padding: 2px 0; }
.wk-day-name   { display: none; }   /* header row active — hide day name inside cards */
.wk-cond       { font-size: 0.6rem; color: var(--muted); text-align: center;
                 white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
```

Updated `@media (max-width: 900px)` — tablet 4-column reflow hides header row and restores day names in cards:

```css
.wk-header-row { display: none; }
.wk-day-name   { display: inline; }
```

Updated `@media (max-width: 767px)` — mobile re-shows header row; condition text hidden (cards too narrow):

```css
.wk-header-row { display: grid; grid-template-columns: repeat(7, 1fr); gap: 3px; margin-bottom: 2px; }
.wk-col-header { font-size: 0.6rem; }
.wk-day-name   { display: none; }
.wk-cond       { display: none; }
```

### Responsive summary

| Viewport | Header row | Day name in card | Condition text |
|---|---|---|---|
| ≥ 901 px (desktop) | shown | hidden | shown |
| 768–900 px (tablet) | hidden | restored | shown |
| ≤ 767 px (mobile) | shown | hidden | hidden |
