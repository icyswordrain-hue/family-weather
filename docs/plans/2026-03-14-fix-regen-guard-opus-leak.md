# Fix: Regen Guard Opus API Leak

**Date:** 2026-03-14

## Problem

Every Cloud Run refresh triggered a `claude-opus-4-6` call (~$0.45, 16K input / 1800 output tokens) instead of once per 30-day regen cycle. API logs showed 5 Opus calls in a 2-hour window on a single evening.

## Root Causes

Three compounding bugs in the regen cycle detection:

### 1. History overwrites erase the regen marker

`save_day()` in `history/conversation.py` is keyed by date. The second refresh of the day overwrites the entry with a fresh `processed_data` dict that lacks `regenerate_meal_lists`. `check_regen_cycle()` scans history for `meta.get("regen")` or `proc.get("regenerate_meal_lists")` — neither survives the overwrite. Neither `metadata` nor `processed_data` retained proof that regen happened.

### 2. CLOUD-mode fallback guard reads local disk

The `regen.json` fallback guard (`app.py:479-492`) read `Path(LOCAL_DATA_DIR) / "regen.json"` regardless of `RUN_MODE`. In CLOUD mode, `_persist_regen()` writes to GCS (`GCS_REGEN_PATH`), but Cloud Run containers are ephemeral — there is never a local `regen.json` to read.

### 3. Narration cache is not regen-aware

The narration cache key is built from `lang + city + weather + time_of_day` but does not include the `regenerate_meal_lists` flag. A cached regen response (containing `---REGEN---` blocks + 1800 tokens) could be returned on non-regen runs, and conversely a cache hit could mask a needed regen call.

## Changes

| File | Change |
|------|--------|
| `app.py` ~line 530 | Stamp `metadata["regen"] = True` when `processed["regenerate_meal_lists"]` is set, before `save_day()`. Ensures `check_regen_cycle()` finds the marker even after same-day overwrites. |
| `app.py` ~lines 479-502 | Mode-aware regen.json guard: reads from GCS in CLOUD mode, local filesystem otherwise. |
| `backend/pipeline.py` ~line 88 | Move `is_regen` check before cache lookup; skip cache hit when `is_regen=True`. |
| `backend/pipeline.py` ~line 139 | Skip `_narration_cache.set()` for regen responses to avoid polluting the cache. |

## Expected Impact

- Opus calls drop from N-per-day to **1 per 30-day cycle**
- Normal Sonnet narration caching unaffected
- Regen detection works correctly across all three `RUN_MODE` values (LOCAL, CLOUD, MODAL)
