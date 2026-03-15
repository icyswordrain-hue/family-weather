# Pipeline Cost, Complexity & Progressive Rendering Overhaul

**Date:** 2026-03-15

## Summary

Simplified the pipeline from 5 skip/cache layers to 2, switched default providers to free/cheaper alternatives, enabled TTS for all slots, added progressive rendering (3-phase NDJSON streaming), and made force refresh bypass both narration and TTS caches.

## Provider Switches

| Component | Before | After |
|-----------|--------|-------|
| Narration (default) | Claude Sonnet 4.6 | Gemini Flash 3 |
| Narration (fallback) | Gemini | Claude (cross-provider) |
| Chat | Claude Haiku 4.5 | Gemini Flash 2.5 (Haiku silent fallback) |
| TTS (primary) | Google Cloud TTS | Edge TTS (free, no API key) |
| TTS (fallback) | Edge TTS | Google Cloud TTS |

Users can still override narration via `NARRATION_PROVIDER=CLAUDE` env var.

## Skip Layer Consolidation: 5 → 2

**Removed:**
1. ~~Midday full-pipeline skip~~ — CWA/MOENV APIs are free; always fetch fresh data
2. ~~Narration condition-change skip~~ — replaced by conditions-aware cache key
3. ~~TTS morning-only restriction~~ — Edge TTS is free; all slots get audio

**Kept:**
1. **Narration TTL cache** (30-min) — enhanced key: `{lang}_{city}_{wx}_{temp_bucket}_{rain}_{time_of_day}`. Temperature bucketed to 3°C intervals; rain flag added. Auto-invalidates when conditions change.
2. **TTS MD5 cache** — identical text → same audio file → skip synthesis.

### Enhanced Cache Key

Old: `en_shulin_sunny_morning` (excluded temperature entirely)
New: `en_shulin_sunny_24c_dry_morning` (temp bucketed to ±3°C, rain flag)

This makes the cache key itself condition-aware, eliminating the need for a separate `_conditions_changed()` check.

## Force Refresh

Force refresh (`force=true`) bypasses **all** caches:

| Cache Layer | Auto | Force |
|-------------|------|-------|
| Narration TTL (30-min) | Checked | **Bypassed** |
| TTS MD5 | Checked | **Bypassed** |

Previously force only bypassed the narration cache. The standalone "Re-synthesize Audio" button and `/api/tts` endpoint were removed — force refresh now handles both.

The Auto/Force toggle in the settings panel resets to Auto after each refresh completes.

## Progressive Pipeline Rendering

The pipeline now yields partial results at 3 stages via NDJSON streaming, so the frontend can render incrementally instead of waiting 10-25s for everything to complete.

### 3 NDJSON yield points in `_pipeline_steps()`

**Phase 1 — Data ready** (~4s, after fetch + process, before narration):
```json
{"type": "data", "payload": {"date": "...", "processed_data": {...},
  "slices": {"current": {...}, "overview": {...}}}}
```
Dashboard and overview render immediately. Lifestyle view shows a shimmer skeleton.

**Phase 2 — Narration ready** (per-language, after LLM, before TTS):
```json
{"type": "narration", "payload": {"lang": "zh-TW",
  "narration_text": "...", "paragraphs": {...}, "metadata": {...},
  "summaries": {...}, "slices": {"lifestyle": {...}, "narration": {...}}}}
```
Lifestyle and narration views fill in. Player bar shows transcript but no audio.

**Phase 3 — Audio ready** (per-language, after TTS):
```json
{"type": "audio", "payload": {"lang": "zh-TW",
  "audio_urls": {"full_audio_url": "..."}}}
```
Player bar becomes playable.

**Final result** (unchanged, for backward compat + history save):
```json
{"type": "result", "payload": {<full broadcast>}}
```

### Frontend stream processing

`_processNdjsonStream(reader)` — extracted reusable function that handles all event types. Used by both `triggerRefresh()` (manual refresh) and `fetchBroadcast()` (page load when no broadcast exists).

`fetchBroadcast()` detects `application/x-ndjson` content-type from `GET /api/broadcast` (returned when no broadcast exists yet) and switches to streaming mode automatically.

### Skeleton placeholders

When Phase 1 arrives but narration hasn't yet, the lifestyle grid shows a shimmer skeleton (`.narration-skeleton` with CSS `skel-shimmer` animation). The skeleton is injected/removed dynamically by `_showNarrationSkeleton(show)`.

## Dead Code Removed

- `_conditions_changed()` function from `app.py`
- `_calc_dew_point` import (was only used by `_conditions_changed`)
- `_skip_narration` / `_prev_broadcast` reuse block
- `_tts_slot = "manual"` logic
- `/api/tts` endpoint and Modal `tts()` endpoint
- "Re-synthesize Audio" button from settings

## Files Modified

- `config.py` — provider defaults, `GEMINI_CHAT_MODEL`/`GEMINI_CHAT_MAX_TOKENS`
- `app.py` — removed 3 skip layers, added 3 progressive yield points, chat → Gemini, TTS always runs, `/api/broadcast` streams NDJSON when no broadcast exists, passes `force` to TTS
- `backend/pipeline.py` — passes temp/rain to cache key, `force` param on `generate_narration_with_fallback()`
- `backend/cache.py` — `make_cache_key()` with `temp_bucket` + `rain` params
- `narration/tts_client.py` — Edge first / Google fallback, `force` param on `synthesise_with_cache()`
- `web/static/app.js` — `_processNdjsonStream()` handles `data`/`narration`/`audio` events, `fetchBroadcast()` detects NDJSON, skeleton injection
- `web/static/style.css` — skeleton shimmer animation styles
- `tests/test_tts_mode_split.py` — updated `build_slices` mock for progressive yield points

## Cost Impact

| | Before | After |
|---|---|---|
| Narration | ~$2.05/mo (Sonnet) | ~$0.39/mo (Flash 3) |
| Chat | ~$0.10/mo (Haiku) | ~$0 (Flash 2.5 free tier) |
| TTS | ~$0.40/mo (Google Cloud) | ~$0 (Edge TTS) |
| **Total** | **~$2.55/mo** | **~$0.39/mo** |
