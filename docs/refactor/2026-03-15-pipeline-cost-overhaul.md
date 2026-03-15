# Pipeline Cost & Complexity Overhaul

**Date:** 2026-03-15

## Summary

Simplified the pipeline from 5 skip/cache layers to 2, switched default providers to free/cheaper alternatives, and enabled TTS for all slots.

## Changes

### Provider Switches

| Component | Before | After |
|-----------|--------|-------|
| Narration (default) | Claude Sonnet 4.6 | Gemini Flash 3 |
| Narration (fallback) | Gemini | Claude (cross-provider) |
| Chat | Claude Haiku 4.5 | Gemini Flash 2.5 (Haiku silent fallback) |
| TTS (primary) | Google Cloud TTS | Edge TTS (free, no API key) |
| TTS (fallback) | Edge TTS | Google Cloud TTS |

Users can still override narration via `NARRATION_PROVIDER=CLAUDE` env var.

### Skip Layer Consolidation: 5 → 2

**Removed:**
1. ~~Midday full-pipeline skip~~ — CWA/MOENV APIs are free; always fetch fresh data
2. ~~Narration condition-change skip~~ — replaced by conditions-aware cache key
3. ~~TTS morning-only restriction~~ — Edge TTS is free; all slots get audio

**Kept:**
1. **Narration TTL cache** (30-min) — now with enhanced key: `{lang}_{city}_{wx}_{temp_bucket}_{rain}_{time_of_day}`. Temperature bucketed to 3°C intervals; rain flag added. Auto-invalidates when conditions actually change.
2. **TTS MD5 cache** — identical text → same audio file → skip synthesis.

### Enhanced Cache Key

Old: `en_shulin_sunny_morning` (excluded temperature entirely)
New: `en_shulin_sunny_24c_dry_morning` (temp bucketed to ±3°C, rain flag)

This makes the cache key itself condition-aware, eliminating the need for a separate `_conditions_changed()` check.

### Dead Code Removed
- `_conditions_changed()` function from `app.py`
- `_calc_dew_point` import (was only used by `_conditions_changed`)
- `_skip_narration` / `_prev_broadcast` reuse block
- `_tts_slot = "manual"` logic

## Files Modified

- `config.py` — provider defaults, new `GEMINI_CHAT_MODEL`/`GEMINI_CHAT_MAX_TOKENS`
- `app.py` — removed 3 skip layers, chat switched to Gemini, TTS always runs
- `backend/pipeline.py` — passes temp/rain to cache key
- `backend/cache.py` — `make_cache_key()` with `temp_bucket` + `rain` params
- `narration/tts_client.py` — Edge first, Google fallback
- `tests/test_narration_cache.py` — updated for new cache key params
- `tests/test_narration_skip.py` — removed `_conditions_changed` tests
- `tests/test_tts_mode_split.py` — all slots now produce audio
- `tests/test_cloud_proxy.py` — chat mocks updated for Gemini

## Cost Impact

| | Before | After |
|---|---|---|
| Narration | ~$2.05/mo (Sonnet) | ~$0.39/mo (Flash 3) |
| Chat | ~$0.10/mo (Haiku) | ~$0 (Flash 2.5 free tier) |
| TTS | ~$0.40/mo (Google Cloud) | ~$0 (Edge TTS) |
| **Total** | **~$2.55/mo** | **~$0.39/mo** |
