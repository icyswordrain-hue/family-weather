# Fix: Force Refresh Bypasses In-Memory Narration Cache

**Date:** 2026-03-15
**Status:** Completed

## Problem

Force refresh still showed stale narration. The `force` flag correctly bypassed the app-level condition-change skip (`app.py:537`), but `generate_narration_with_fallback()` in `pipeline.py` has its own 30-minute in-memory `_narration_cache`. That cache was never told about `force`, so it returned the cached LLM result whenever the weather bucket and time-of-day matched.

### Cache layers and force awareness before fix

| Layer | Cache | Force-aware? |
|-------|-------|--------------|
| `app.py` condition-change skip | Reuses previous broadcast | Yes |
| `pipeline.py` `_narration_cache` (30-min TTL) | In-memory LLM result | **No** |

## Fix

1. **`backend/pipeline.py`** — Added `force: bool = False` parameter to `generate_narration_with_fallback()`. Cache check changed from `if cached and not is_regen` to `if cached and not is_regen and not force`.
2. **`app.py`** — Pass `force=force` through to the `generate_narration_with_fallback()` call.

## Files Modified

- `backend/pipeline.py` (signature + cache guard)
- `app.py` (call site)
