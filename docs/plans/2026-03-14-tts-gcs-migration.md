# TTS Architecture: Modal Volume → GCS + Always-Eager

**Date:** 2026-03-14
**Status:** Implemented

## Problem

1. The Modal `tts()` endpoint failed on every call (cold-start crashes)
2. The on-demand TTS architecture (Cloud Run → Modal TTS → volume → Modal Audio → Cloud Run proxy) was complex and fragile
3. Modal volume `commit()`/`reload()` was unreliable — audio files written during `refresh()` were never visible to the `audio()` endpoint

## Solution

Three changes made in sequence:

### 1. Always-Eager TTS
Removed the conditional that only synthesized audio for LOCAL/morning slots. TTS now runs during the refresh pipeline for **every** slot and mode.

### 2. Google Cloud TTS with GCS Storage
- Enabled Google Cloud Text-to-Speech API on the GCP project
- Added `GCP_SA_JSON` (base64-encoded service account key) to Modal secrets
- Both MODAL and CLOUD modes now upload audio to GCS and return a public URL
- Browser plays audio directly from `https://storage.googleapis.com/family-weather-dashboard/audio/...`

### 3. Removed On-Demand Infrastructure
| Removed | File |
|---------|------|
| Modal `tts()` endpoint | `backend/modal_app.py` |
| Modal `audio()` endpoint | `backend/modal_app.py` |
| Cloud Run `/api/tts` route | `app.py` |
| Cloud Run `/api/audio` proxy (CLOUD mode) | `app.py` |
| `MODAL_TTS_URL` env var | `.github/workflows/deploy.yml` |
| `MODAL_AUDIO_URL` env var | `.github/workflows/deploy.yml` |
| On-demand JS fetch (`/api/tts`) | `web/static/app.js` |

**Kept:** `/api/audio/<path>` route for LOCAL mode only (serves from disk).

## Current Architecture

```
Refresh pipeline
  → synthesise_with_cache(text, lang, date, slot)
    → _render_tts(text, lang)
      → Google Cloud TTS (en-GB-Standard-C / cmn-TW-Standard-A)
      → fallback: Edge TTS (blocked from datacenter IPs — effectively Google-only)
    → _upload_to_gcs(audio_bytes, gcs_path)
    → returns https://storage.googleapis.com/family-weather-dashboard/audio/{date}/{slot}_{lang}_{hash}.mp3
  → saved in broadcast as full_audio_url
  → browser plays GCS URL directly
```

## Voice Configuration

| Language | Voice | Lang Code | Type | Cost |
|----------|-------|-----------|------|------|
| English | `en-GB-Standard-C` | `en-GB` | Standard (female) | $4/1M chars |
| Chinese | `cmn-TW-Standard-A` | `cmn-TW` | Standard (female) | $4/1M chars |

Override via env vars: `TTS_VOICE_NAME` (English), `TTS_VOICE_ZH` (Chinese).

The `lang_code` for English is derived from the voice name prefix (e.g. `en-GB-Standard-C` → `en-GB`), so changing the voice env var automatically adjusts the language code. Chinese always uses `cmn-TW`.

## Cost Estimate

- ~1,500 chars per narration × 1 language per broadcast
- 3 slots/day × 30 days = 90 broadcasts/month
- 90 × 1,500 = 135,000 chars/month × $4/1M = **~$0.54/month per language**
- With caching (same text = same hash = GCS cache hit): likely under $0.50/month

## Key Gotchas

- **`RUN_MODE` import timing:** Modal secrets inject `RUN_MODE=CLOUD` before `config.py` imports. `modal_app.py` overrides to `"MODAL"` after import. `tts_client.py` checks `os.environ.get("RUN_MODE")` at call time to get the correct value.
- **`GCP_SA_JSON` must be in Modal secrets:** Base64-encoded service account JSON. `_bootstrap_gcp_credentials()` decodes it and sets `GOOGLE_APPLICATION_CREDENTIALS`.
- **`TTS_PROVIDER` import timing:** Same issue — resolved at call time in `_render_tts()` by checking `GOOGLE_APPLICATION_CREDENTIALS` in env.
- **GCS bucket permissions:** `family-weather-dashboard` bucket needs Storage Object Admin for the service account and public read (`allUsers:objectViewer`) for browser playback.
- **Edge TTS fallback is non-functional in Modal:** Microsoft blocks datacenter IPs (403). Google Cloud TTS is the only viable provider.

## GCP Setup Checklist

1. Enable Cloud Text-to-Speech API on the project
2. Grant service account `Storage Object Admin` on the GCS bucket
3. Enable public read on the GCS bucket (`allUsers:objectViewer`)
4. Add `GCP_SA_JSON` to Modal secrets (base64-encoded SA key JSON)
