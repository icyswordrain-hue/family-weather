# Cloud Run Proxy Bug Fixes

**Date:** 2026-03-13

## Problem

Three bugs were discovered in the Cloud Run → Modal proxy layer:

### Bug 1: Midday skip never worked (`app.py`)

`refresh()` imported `get_today_broadcast as load_broadcast` and called it with
`load_broadcast(date=date_str, slot="morning")`. `get_today_broadcast` takes
`date_str` as a positional parameter and does not accept a `date` keyword — so
every call raised `TypeError`, which was swallowed by the surrounding
`except Exception`, causing the midday skip check to silently fail every time.
The full pipeline always ran at midday regardless of whether conditions had changed.

**Fix:** Import the actual `load_broadcast` function (which exists in
`conversation.py` specifically for this purpose) and call it positionally:
`load_broadcast(date_str, slot="morning")`.

### Bug 2: No timeout on `/api/broadcast` proxy (`app.py`)

```python
# before
resp = requests.get(modal_url, params={"date": date_str, "lang": lang})
# after
resp = requests.get(modal_url, params={"date": date_str, "lang": lang}, timeout=30)
```

The `/api/broadcast` proxy had no `timeout` argument. If Modal was cold-starting
or unresponsive, Cloud Run would hang the request indefinitely. The `/api/refresh`
proxy already had a 290s timeout; broadcast was the only unguarded call.

**Fix:** Added `timeout=30` (consistent with the `_get_broadcast_for_chat` fallback
fetch which also uses 15s).

### Bug 3: `lang` parameter dropped by Modal `broadcast()` endpoint (`modal_app.py`)

Cloud Run's `get_broadcast()` passed `lang` as a query param to Modal, but Modal's
`broadcast()` function only declared `date` in its signature. FastAPI silently
ignored the unknown `lang` param, and `build_slices(cached)` was always called
without a language, defaulting to `"en"`. The language toggle had no effect in
production.

**Fix:** Added `lang: str = "en"` to Modal's `broadcast()` signature and threaded
it through to `build_slices(cached, lang=lang)`.

## Files Changed

- `app.py` — midday skip import fix + broadcast proxy timeout
- `backend/modal_app.py` — `broadcast()` accepts and forwards `lang`

## Notes

Also identified during this audit (not fixed, low priority):
- GCS history paths in `conversation.py` are dead code — the pipeline always runs
  in MODAL mode and writes to Modal Volume; the CLOUD branches of `save_day()` /
  `_load_history_map()` are never exercised.
- `_broadcast_cache` in Cloud Run has no eviction, but entries are small and the
  service restarts periodically so this is not a practical concern.
- `/api/chat` calls Anthropic directly from Cloud Run — `ANTHROPIC_API_KEY` must
  be present in Cloud Run's Secret Manager (not just Modal secrets).
