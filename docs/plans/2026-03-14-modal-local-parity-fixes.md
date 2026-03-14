# Modal ↔ Local Parity Fixes

**Date:** 2026-03-14

## Problem

Three behavioral discrepancies between `RUN_MODE=LOCAL` and `RUN_MODE=MODAL` (Modal serverless):

### 1. TTS local cache miss + flat file path (BUG — fixed)

- **MODAL**: Checked cache → saved to `/data/audio/{date}/{slot}_{lang}_{hash}.mp3` → returned `/api/audio/{date}/...`
- **LOCAL**: Skipped cache → saved to `local_data/audio/{filename_only}` (flat) → returned `/local_assets/audio/{filename_only}`

LOCAL always re-synthesized TTS and lost date organization.

### 2. Midday skip check broken in CLOUD mode (BUG — fixed)

The midday skip check ran in the Flask proxy (`RUN_MODE=CLOUD`) and called `load_broadcast()`, which read from GCS. But `save_day()` inside Modal wrote to Modal volume (`RUN_MODE=MODAL`), not GCS. Morning broadcast was never found → skip optimization never fired.

### 3. Regen cycle triggered every run on Modal (BUG — fixed)

`check_regen_cycle()` scanned history entries for `processed_data.regenerate_meal_lists`. But `save_day()` overwrites same-day entries — when a second run (midday/evening) didn't set the flag, it overwrote the morning entry that had it. Next day, no marker found → regen triggered again.

## Fixes

### Fix 1: TTS cache alignment (narration/tts_client.py)

LOCAL mode now matches MODAL: checks cache before synthesizing, saves with date subdirectory structure, and returns `/api/audio/` URLs (the route already existed for LOCAL at `app.py:303-309`).

### Fix 2: Midday skip moved into pipeline (app.py)

Moved the condition check from the `/api/refresh` route into `_pipeline_steps()`, where it runs in the correct `RUN_MODE` context with access to the right storage backend.

### Fix 3: Regen fallback via regen.json (app.py)

When `check_regen_cycle()` finds no marker in history, the pipeline now checks `regen.json`'s `updated_at` timestamp as a fallback. This file persists independently of history entry overwrites and already existed for the meal/location database.

## Files changed

| File | Change |
|------|--------|
| `narration/tts_client.py` | LOCAL: added cache check + date subdirs + `/api/audio/` URLs |
| `app.py` | Moved midday skip into `_pipeline_steps()`; added regen.json fallback check |
