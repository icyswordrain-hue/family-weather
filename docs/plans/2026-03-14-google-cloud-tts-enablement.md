# Enable Google Cloud TTS in Production

**Date:** 2026-03-14

## Problem

`tts_client.py` always called `_render_edge_tts()` (Microsoft Edge's free WebSocket-based TTS) regardless of environment. Edge TTS is unreliable from cloud/datacenter IPs — Microsoft's undocumented endpoint rate-limits or blocks non-residential connections. Meanwhile, `config.py` already detected GCP credentials and set `TTS_PROVIDER = "GOOGLE"`, and Modal's `_bootstrap_gcp_credentials()` already decoded `GCP_SA_JSON` into `GOOGLE_APPLICATION_CREDENTIALS` — but none of this was wired into the actual TTS rendering.

## Solution

Added Google Cloud TTS support to `narration/tts_client.py` with automatic fallback to Edge TTS on failure.

## Changes

### `narration/tts_client.py`

1. **New import:** `TTS_PROVIDER`, `TTS_VOICE_EN`, `TTS_VOICE_ZH`, `TTS_SPEAKING_RATE` from `config.py`

2. **`_render_google_tts(text, lang)`** — calls Google Cloud TTS API using `google.cloud.texttospeech`, selecting voice by language (`zh-TW-Wavenet-B` for Chinese, `en-US-Neural2-D` for English)

3. **`_render_tts(text, lang)`** — dispatcher:
   - If `TTS_PROVIDER == "GOOGLE"`: try Google Cloud TTS, fall back to Edge TTS on any exception
   - Otherwise: use Edge TTS directly

4. **All three call sites** in `synthesise_with_cache()` (MODAL, CLOUD, LOCAL paths) now call `_render_tts()` instead of `_render_edge_tts()`

## Provider Selection

| Environment | `GOOGLE_APPLICATION_CREDENTIALS` | `TTS_PROVIDER` | Primary TTS | Fallback |
|---|---|---|---|---|
| Modal | Set by `_bootstrap_gcp_credentials()` | `GOOGLE` | Google Cloud TTS | Edge TTS |
| Cloud Run | Set if `GCP_SA_JSON` available | `GOOGLE` | Google Cloud TTS | Edge TTS |
| Local (with SA key) | Set from `local_data/service-account.json` | `GOOGLE` | Google Cloud TTS | Edge TTS |
| Local (no SA key) | Not set | `EDGE` | Edge TTS | — |

## No Config Changes Required

All credentials and config were already in place:
- `config.py:159-161` — `TTS_PROVIDER` auto-detection already existed
- `config.py:151-152` — Google voice names already defined
- `backend/modal_app.py:23-32` — `_bootstrap_gcp_credentials()` already ran in all endpoints
- Modal secret `family-weather-secrets` — already contains `GCP_SA_JSON`
