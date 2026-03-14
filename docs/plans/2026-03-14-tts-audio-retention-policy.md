# TTS Audio Retention Policy — Monthly Snapshots + 30-Day Rolling Window

**Date:** 2026-03-14
**Status:** Implemented

## Problem

TTS audio files accumulate indefinitely on the Modal Volume (and local disk) at `/data/audio/{date}/{slot}_{lang}_{hash}.mp3`. Each pipeline refresh creates new audio files in date-stamped subdirectories, but nothing ever cleans them up. While the storage cost is negligible (~$0.02–0.06/month on Modal Volume), unbounded growth is undesirable.

## Solution

Added a `cleanup_old_audio()` function to `narration/tts_client.py` that runs at the end of each pipeline refresh (MODAL and LOCAL modes only).

**Retention policy:**
- **Last 30 days:** keep all files (rolling window)
- **1st of each month:** keep 1 file per language (monthly snapshot, forever)
- **Everything else older than 30 days:** delete

### Example (run date: Mar 15)

| Directory | Action |
|-----------|--------|
| `2026-03-15/` through `2026-02-13/` | Keep all (within 30 days) |
| `2026-02-01/` | Keep 1 per language (monthly snapshot) |
| `2026-01-15/` | Delete all files + remove dir |
| `2026-01-01/` | Keep 1 per language (monthly snapshot) |

### Language extraction

Filename pattern: `{slot}_{lang}_{hash}.mp3` (e.g. `morning_zh-TW_abc123def456.mp3`). Language is extracted by splitting on `_`: `rsplit("_", 1)` to isolate the hash, then `split("_", 1)` on the remainder to get lang.

## Files Modified

- `narration/tts_client.py` — added `cleanup_old_audio(audio_root, keep_days=30)` (~40 lines)
- `app.py` — call site in `_pipeline_steps()` step 7.5, after history save, before result

## Verification

- `pytest tests/` — 189 tests pass, no regressions
- Manual: create fake date dirs in `local_data/audio/` spanning several months, trigger refresh, verify only 1st-of-month + last-30-days files survive
