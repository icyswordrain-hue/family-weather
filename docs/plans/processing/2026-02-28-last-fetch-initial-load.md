# Last-Fetch Render as Initial Load (Stale-While-Revalidate)

**Goal:** Eliminate the loading screen for returning users by rendering the last successful broadcast immediately on page load, then refreshing data silently in the background.

**Architecture:** Frontend-only `localStorage` cache. On boot, check for a cached broadcast (≤24h old) and render it instantly while `/api/broadcast` fetches fresh data. The existing `#optimistic-loading` pill serves as the "refreshing…" indicator. No backend changes required.

**Tech Stack:** JavaScript (`app.js`), `localStorage` Web API

---

## Context

Currently every page load triggers `showLoading()` → full-screen spinner → wait for `/api/broadcast` → render. For returning users the API response is typically fast (today's data already in history), but there is still a perceptible blank screen. This change makes the dashboard feel instant on reload by showing the last known render while silently re-validating.

---

## Critical Files

- **Modify:** `web/static/app.js` — 5 targeted edits (constants, helpers, boot handler, `fetchBroadcast`, `triggerRefresh`)
- **Reference:** `web/templates/dashboard.html:120` — `#optimistic-loading` element already exists and is styled
- **Reference:** `web/static/style.css:190` — `.optimistic-loading` pill already styled, no CSS changes needed

---

## Boot Sequence (new)

```
DOMContentLoaded
  → loadCachedBroadcast()
      ├─ No cache → fetchBroadcast(false)   [loading screen, unchanged]
      └─ Cache found
            → render(cached.data)            [fill DOM while main-content hidden]
            → showContent()                  [make main-content visible]
            → showStaleIndicator()           [show #optimistic-loading pill]
            → fetchBroadcast(true)           [background, no loading screen]
                  ├─ success → render(fresh), saveBroadcastCache(), showContent()
                  └─ error   → hideStaleIndicator()    [stale content stays]
```

---

## Edit 1 — Cache constants (~line 46, after state vars)

```js
const CACHE_KEY = 'weather_broadcast_cache';
const CACHE_MAX_AGE_MS = 24 * 60 * 60 * 1000; // 24 hours
```

## Edit 2 — Four helper functions (before DOMContentLoaded handler, ~line 271)

```js
function saveBroadcastCache(data) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ ts: new Date().toISOString(), data }));
  } catch (e) { /* private browsing — fail silently */ }
}

function loadCachedBroadcast() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const cached = JSON.parse(raw);
    if (!cached?.data || !cached?.ts) return null;
    if (Date.now() - new Date(cached.ts).getTime() > CACHE_MAX_AGE_MS) {
      localStorage.removeItem(CACHE_KEY);
      return null;
    }
    return cached; // { ts, data }
  } catch (e) { return null; }
}

function showStaleIndicator() {
  const el = document.getElementById('optimistic-loading');
  if (el) el.classList.remove('hidden');
}

function hideStaleIndicator() {
  const el = document.getElementById('optimistic-loading');
  if (el) el.classList.add('hidden');
}
```

## Edit 3 — DOMContentLoaded boot (line 292): replace bare `fetchBroadcast()`

```js
  const cached = loadCachedBroadcast();
  if (cached) {
    broadcastData = cached.data;
    render(broadcastData);
    showContent();
    showStaleIndicator();
    fetchBroadcast(true);
  } else {
    fetchBroadcast(false);
  }
```

## Edit 4 — `fetchBroadcast()` (lines 296–319): add `silent` parameter

```js
async function fetchBroadcast(silent = false) {
  if (!silent) showLoading();
  const btn = document.getElementById('refresh-btn');
  if (btn) btn.classList.add('loading');

  try {
    const url = new URL('/api/broadcast', window.location.origin);
    if (typeof getLang === 'function') url.searchParams.set('lang', getLang());
    const res = await fetch(url.toString());
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    broadcastData = await res.json();
    if (broadcastData.error) throw new Error(broadcastData.error);
    addLog(T.data_ok);
    render(broadcastData);
    saveBroadcastCache(broadcastData);
    showContent(); // also hides #optimistic-loading (line 1051–1052)
  } catch (err) {
    addLog(`${T.error_prefix}${err.message || 'Unknown error'}`);
    if (!silent) {
      showError(err.message || 'Unknown error');
    } else {
      hideStaleIndicator();
    }
  } finally {
    if (btn) btn.classList.remove('loading');
  }
}
```

## Edit 5 — `triggerRefresh()` result path (line 1135): add cache save

```js
broadcastData = msg.payload;
render(broadcastData);
saveBroadcastCache(broadcastData);  // add this line
showContent();
```

---

## Edge Cases

| Scenario | Behaviour |
|---|---|
| First-ever load | `loadCachedBroadcast()` → null → loading screen as before |
| Cached, same day | Instant render + stale pill + background refresh |
| Cached, previous day (post-midnight) | Same — yesterday briefly shown, replaced in seconds |
| Cache > 24h old | Deleted, treated as first load |
| Background refresh fails | Pill hidden, stale content stays, no error screen |
| Refresh button | `triggerRefresh()` unchanged — full overlay mode |
| Language changed | `applyLanguage()` re-calls `render(broadcastData)` — works with cached data |
| localStorage unavailable | `loadCachedBroadcast()` catches → null → graceful fallback |
| Retry button click | `window.app.fetchBroadcast()` → `silent=false` → loading screen ✓ |

---

## Verification

1. **First load:** clear localStorage → loading screen shows, data renders, `weather_broadcast_cache` written to localStorage
2. **Cached load:** reload → content appears instantly, `#optimistic-loading` pill visible, pill disappears when fresh data arrives
3. **Background failure:** block `/api/broadcast` in DevTools Network → pill disappears, stale content remains, no error screen
4. **Expired cache:** manually set `ts` to >24h ago in DevTools → treated as first load
5. **Refresh button:** still triggers full streaming pipeline overlay
6. **Language switch:** re-render uses correct translations

---

## Implementation Status — 2026-02-28 (commit `65a25bc`)

All 5 edits implemented. Code analysis confirms the pipeline is correct for **both desktop and mobile**.

**Single JS bundle, no separate mobile path.** There is no mobile JS file, no mobile service worker branch, and no user-agent branching. Mobile vs desktop differences are CSS-only plus a DOM reorder by `initMobileNav()` (lines 958–971), which runs before the cache check and only calls `insertBefore()` — it does not touch fetch or render logic.

**Boot sequence race condition: none.** `initMobileNav()` completes before `loadCachedBroadcast()` at line 326, so the DOM is fully reordered when `render()` is called with cached data.

**`render()` has no mobile-specific branches.** Slice rendering is identical on both viewports; the only mobile-aware line sets `#mobile-location` text if that element exists.

**Server-side history always consulted.** `/api/broadcast` calls `get_today_broadcast()` → reads `local_data/history.json` (or GCS). If today's broadcast exists, it returns immediately (pipeline is not re-run). This is independent of the localStorage layer.

**`saveBroadcastCache` called in both write paths:** `fetchBroadcast()` success path and `triggerRefresh()` result path.

**Known edge case (acceptable).** `slices` stored in the localStorage cache are language-specific. If the user switches language between sessions, the instant render briefly shows old-language slices until the background refresh returns fresh slices for the current language. Negligible UX impact.
