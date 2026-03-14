# Remove Modal TTS Endpoint — Always-Eager TTS

**Date:** 2026-03-14
**Status:** Implemented

## Problem

The Modal `tts()` endpoint (`family-weather-engine-tts.modal.run`) failed on every invocation. All calls showed "Failed" status with sub-1s execution times, indicating early crashes during cold-start (likely GCP credential bootstrap or edge_tts network issues in Modal containers).

The on-demand TTS architecture added unnecessary complexity:
```
Browser → Cloud Run /api/tts → Modal tts() → synthesise_with_cache()
  → volume.commit() → return URL
Browser → Cloud Run /api/audio → Modal audio() → serve from volume
```

## Solution

Made TTS **always eager**: audio is synthesized during the refresh pipeline for every time slot (morning, midday, evening), not just morning. This eliminates the need for on-demand TTS entirely.

## Changes

| File | Change |
|------|--------|
| `app.py` | Removed conditional `if RUN_MODE == "LOCAL" or (RUN_MODE == "MODAL" and slot == "morning")`; TTS now runs unconditionally. Deleted `/api/tts` route. |
| `backend/modal_app.py` | Deleted `tts()` Modal function. |
| `web/static/app.js` | Removed on-demand `/api/tts` fetch from player bar; play button uses pre-generated `audioUrl` directly. |
| `.github/workflows/deploy.yml` | Removed `MODAL_TTS_URL` env var from Cloud Run deployment. |
| `README.md` | Removed `MODAL_TTS_URL` from env var table. |
| `tests/test_tts_mode_split.py` | Updated `test_cloud_tts_is_deferred` → `test_cloud_tts_is_eager` to match new behavior. |

## What Remains

- **Modal `audio()` endpoint** — still needed to serve pre-generated audio files from the Modal volume.
- **Cloud Run `/api/audio/<path>`** — still proxies to Modal `audio()` in CLOUD mode.
- **`MODAL_AUDIO_URL`** — still required in Cloud Run env vars.

## After Deploy

- The `tts` function will disappear from the Modal dashboard (no more failed calls).
- Users get instant playback on all time slots with no loading spinner.
