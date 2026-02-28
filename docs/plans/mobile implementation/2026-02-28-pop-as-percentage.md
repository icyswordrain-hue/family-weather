# PoP Display: Percentage Instead of Scale Text

> **Date:** 2026-02-28
> **Status:** Implemented
> **Commits:** `dd61c74`, `fc8b96d`

---

## The Problem

Both forecast grids were showing precipitation probability as qualitative scale text — "Unlikely", "Possible", "Likely", etc. — rather than the raw percentage the CWA API provides. The scale text was derived from `precip_text`, which is computed by bucketing the PoP value into five levels. Information is lost in that bucketing: "30%" and "39%" both render as "Unlikely", even though they may mean very different things for planning.

Additionally, the 7-day forecast was always showing a precipitation label even when no real PoP data was available — in that case the value was silently inferred from the Wx weather code via `wx_to_pop()`, with no indication to the viewer that it was estimated rather than forecast.

---

## Data Model

### 24-hour forecast (`timeline`)

Each segment is a `PoP6h`-based slot from the CWA 36-hour forecast API:

- `seg.PoP6h` — the actual percentage (e.g. `40.0`), always present when CWA provides it
- `seg.precip_text` — bucketed text ("Unlikely", "Possible", …), derived by `_val_to_scale(PoP6h, PRECIP_SCALE_5)`
- `seg.precip_level` — integer 1–5, used for colour coding

Because `PoP6h` comes directly from the API, it is always a real forecast value — never inferred.

### 7-day forecast (`weekly_timeline`)

Each slot is a `PoP12h`-based slot from the CWA 7-day forecast API:

- `slot.PoP12h` — the actual percentage, or `null` when the API did not supply one
- When `PoP12h` is `null`, `weather_processor.py` falls back to `wx_to_pop(slot.Wx)` to estimate a PoP from the weather code before computing `precip_text` and `precip_level`
- `slot.PoP12h` is passed through to the frontend unchanged; `null` means inferred

The distinction matters: `PoP12h` present → real forecast; `PoP12h` null → estimate from Wx code.

---

## Changes Made

### `web/static/app.js` — commit `dd61c74`

**24-hour timeline (desktop + mobile):**

```js
// Before
addRow(T.rain, localiseMetric(seg.precip_text) || '—', seg.precip_level || 1);

// After
addRow(T.rain, seg.PoP6h != null ? Math.round(seg.PoP6h) + '%' : localiseMetric(seg.precip_text) || '—', seg.precip_level || 1);
```

Falls back to `precip_text` only if `PoP6h` is absent — defensive, but in practice `PoP6h` is always present for timeline segments.

**7-day weekly timeline (desktop only):**

```js
// Before
const rain = document.createElement('div');
rain.className = `wk-rain lvl-${item.precip_level || 1}`;
rain.textContent = localiseMetric(item.precip_text) || '—';
card.appendChild(rain);

// After
if (item.PoP12h != null) {
  const rain = document.createElement('div');
  rain.className = `wk-rain lvl-${item.precip_level || 1}`;
  rain.textContent = Math.round(item.PoP12h) + '%';
  card.appendChild(rain);
}
```

The `wk-rain` element is only appended when `PoP12h` is a real value. When PoP is Wx-inferred, the card shows no precipitation row — absence of data is expressed as absence of element, not as a potentially misleading estimate.

---

## Deployment Bug: Service Worker Cache

After `dd61c74` was committed the desktop still showed scale text. Root cause: the service worker's `normalisedRequest()` helper strips query strings before building cache keys:

```js
// service-worker.js
function normalisedRequest(request) {
    const url = new URL(request.url);
    if (!url.search) return request;
    return new Request(url.origin + url.pathname, { mode: 'no-cors' });
}
```

This means `app.js?v=17` and `app.js?v=16` both resolve to the same cache key `/static/app.js`. The `?v=N` versioning in `dashboard.html` is **silently ignored** by the service worker. Combined with the stale-while-revalidate fetch handler (`return cached || fetching`), the cached old `app.js` was served immediately on every load while the update sat in the background.

Fix (`fc8b96d`): bump `CACHE_NAME` from `'weather-v7'` to `'weather-v8'`. The activate handler deletes all caches not matching the current name, which purges the stale `app.js`. After the next page load the new SW installs and the following reload gets the updated file.

**Lesson:** `?v=N` cache-busting on static asset URLs has no effect as long as the service worker strips query strings. The only reliable way to force a cache refresh is to increment `CACHE_NAME`.

---

## What Stayed the Same

- **Colour coding** — `precip_level` still drives the `lvl-N` class, so the colour band reflects the same bucketed risk as before.
- **Mobile 7-day** — `.wk-rain { display: none }` at `max-width: 767px` (from `405c2b0`) means the PoP row has never been visible on mobile phones for the weekly grid. That CSS rule is unchanged; the JS now simply won't create the element at all when PoP is inferred.
- **`web/static/style.css`** — no changes.
- **`web/routes.py`** — `weekly_timeline` already passes through the full slot dict including `PoP12h`; no backend changes needed.
