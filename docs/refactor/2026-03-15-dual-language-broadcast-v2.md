# Dual-Language Broadcast (v2 Schema)

## Goal
Generate narration in both EN and ZH in every pipeline run, run TTS only once per day (morning), and store both languages side-by-side in a single broadcast entry. Reduces LLM costs via condition-change skip (both languages skipped together) and TTS costs via morning-only synthesis.

## Schema Change (v1 → v2)

**v1 (flat):** Single `narration_text`, `paragraphs`, `metadata`, `audio_urls`, `summaries` at top level.

**v2 (langs):** Language-specific fields nested under `langs`:
```json
{
  "schema_version": 2,
  "generated_at": "...",
  "tts_generated_at": "...",
  "raw_data": {},
  "processed_data": {},
  "langs": {
    "en":    { "narration_text", "paragraphs", "metadata", "summaries", "audio_urls" },
    "zh-TW": { "..." }
  }
}
```

`_normalize_broadcast()` in `history/conversation.py` migrates v1 entries transparently — all consumers always see v2 format.

## Pipeline Changes (`app.py:_pipeline_steps`)

1. **Dual narration loop:** After weather processing, generates narration for both `zh-TW` and `en` (unless condition-change skip fires — skips both).
2. **Morning-only TTS:** `synthesise_with_cache()` only called when `slot == "morning"`. Sets `tts_generated_at` timestamp.
3. **Regen data:** Captured from first language parse only (structured data, language-independent).
4. **Result flattening:** The NDJSON result uses the request's `lang` to pick which language sub-dict to return. Frontend sees the same response shape as v1.

## New Endpoints

- **`POST /api/tts`** — Re-synthesizes audio for both languages from existing narration text. Updates `audio_urls` and `tts_generated_at` in the broadcast. Available in both Flask and Modal.

## Frontend Changes

- **TTS button** in player sheet settings tab — calls `POST /api/tts`, reloads audio element on success.
- **Audio age badge** (`player-audio-age`) — shows "Audio from HH:MM" when TTS timestamp is >10 minutes older than narration timestamp. Hidden when they match (morning run).

## Files Modified

| File | Change |
|------|--------|
| `history/conversation.py` | v2 schema, `_normalize_broadcast()`, `get_lang_data()`, new `save_day()` signature |
| `app.py` | Dual-language narration loop, morning-only TTS, `/api/tts` endpoint, `/api/broadcast` flattening |
| `backend/modal_app.py` | `broadcast()` flattening, new `tts()` endpoint |
| `narration/chat_context.py` | v2 schema handling |
| `narration/llm_prompt_builder.py` | v2 history reading in `_format_history()` |
| `web/templates/dashboard.html` | TTS button, audio age badge element |
| `web/static/app.js` | TTS handler, `_updateAudioAgeBadge()`, i18n strings |
| `web/static/style.css` | `.player-audio-age`, `.rp-btn-secondary` styles |

## Backwards Compatibility

Old v1 broadcasts load correctly — `_normalize_broadcast()` wraps flat fields under `langs["zh-TW"]` and sets `tts_generated_at` to `generated_at`. No data migration script needed.
