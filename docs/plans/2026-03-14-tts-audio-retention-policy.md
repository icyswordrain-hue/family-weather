# TTS Audio Retention Policy — Monthly Snapshots + 30-Day Rolling Window

**Date:** 2026-03-14
**Status:** Implemented (v2 — GCS-based)

## Problem

TTS audio files accumulate indefinitely in GCS (and local disk) at `audio/{date}/{slot}_{lang}_{hash}.mp3`. Each pipeline refresh creates new audio blobs in date-stamped prefixes, but nothing ever cleans them up.

## Solution

`cleanup_old_audio()` in `narration/tts_client.py` runs at the end of each pipeline refresh. It dispatches by `RUN_MODE`:

- **MODAL/CLOUD:** `_cleanup_gcs()` — lists blobs via `bucket.list_blobs(prefix="audio/")`, groups by date, deletes stale blobs
- **LOCAL:** `_cleanup_local()` — walks `local_data/audio/` date subdirectories, deletes stale files

**Retention policy:**

- **Last 30 days:** keep all files (rolling window)
- **1st of each month:** keep 1 file per language (monthly snapshot, forever)
- **Everything else older than 30 days:** delete

### Example (run date: Mar 15)

| Date prefix | Action |
|-------------|--------|
| `2026-03-15/` through `2026-02-13/` | Keep all (within 30 days) |
| `2026-02-01/` | Keep 1 per language (monthly snapshot) |
| `2026-01-15/` | Delete all blobs |
| `2026-01-01/` | Keep 1 per language (monthly snapshot) |

### Language extraction

`_extract_lang_from_filename()` parses `{slot}_{lang}_{hash}.mp3`: `rsplit("_", 1)` isolates the hash, `split("_", 1)` on the remainder extracts lang (e.g. `zh-TW`, `en`).

### v2 changes (GCS migration)

The v1 implementation operated on local filesystem paths, which became dead code after TTS storage moved to GCS (commit `b545d86`). v2 rewrites the cleanup to use the GCS Storage API for MODAL/CLOUD modes, with the local filesystem path preserved for LOCAL mode.

## Files Modified

- `narration/tts_client.py` — `cleanup_old_audio()`, `_cleanup_gcs()`, `_cleanup_local()`, `_extract_lang_from_filename()`
- `app.py` — call site in `_pipeline_steps()` step 7.5 (no longer guarded by RUN_MODE)

## Verification

- `pytest tests/` — 189 tests pass, no regressions
