# Traditional Chinese Localization — Design Document

## Summary

Deliver the full family weather dashboard in Traditional Chinese — narration, lifestyle cards, AQI summaries, all static UI labels — while preserving English as a runtime toggle. Data query payloads stay in English for precision. The `---METADATA---` JSON block always stays in English (Python parses it).

---

## Proposed Architecture

### 1. Language Toggle (EN / 中文)

A radio toggle in the Right Panel (next to the existing provider selector) lets the user switch language at runtime. The selection is persisted in `localStorage` and sent as a `lang` field (`"en"` or `"zh-TW"`) in every `/api/refresh` POST body.

- Two system prompt variants live side-by-side in `narration/llm_prompt_builder.py`: `V6_SYSTEM_PROMPT_EN` and `V6_SYSTEM_PROMPT_ZH`. `build_system_prompt(lang)` picks the right one.
- Summarizer prompts in `narration/llm_summarizer.py` accept a `lang` arg and inline the correct instruction.
- Cloud TTS voice is selected at runtime based on `lang` (not hardcoded in `config.py`).
- Cache keys are namespaced by language: `en_shulin_rain_morning` vs `zh_shulin_rain_morning`.
- Static UI labels switch instantly via the JS `TRANSLATIONS` object — no re-fetch needed.

### 2. LLM Narration — Direct Generation

The LLM is instructed to output the spoken script directly in the target language. No post-processing translation pipeline. The `---METADATA---` JSON block always uses English keys and values regardless of `lang`.

- **Chinese prompt:** colloquial Traditional Chinese (台灣中文, 繁體). Dish/location names in Chinese characters (e.g., 牛肉麵 not pinyin).
- **English prompt:** existing V6 prompt, unchanged.

### 3. Frontend Static UI Translation

A lightweight `TRANSLATIONS` const object is inlined directly in `web/static/app.js` (not a separate `i18n.js` file — no extra network request). All hardcoded English strings in render functions reference `T.key_name`. `dashboard.html` static elements (nav labels, headings, buttons) are edited directly to Chinese, with the dark mode toggle label driven by JS.

### 4. LLM Summarizers (Lifestyle Cards)

`narration/llm_summarizer.py` prompts accept a `lang` param and gate the output language instruction. JSON keys remain English; values are language-specific strings.

### 5. LLM AQI Forecast Summarizer

The AQI raw data is already in Chinese. The summarizer previously translated it to English. With `lang=zh-TW` it outputs Traditional Chinese directly (no translation step). With `lang=en` the current English translation behaviour is preserved.

### 6. TTS

- **Cloud TTS (server-side):** voice is selected per request based on `lang`. `zh-TW-Wavenet-B` for Chinese; `en-US-Neural2-D` for English. Default constants in `config.py` remain as fallbacks only.
- **Local TTS (browser, Phase 1):** Web Speech API button in the Narration view. Sets `utter.lang = lang` and prefers a matching voice. Silently degrades if no compatible voice is installed.

### 7. Caching

`backend/cache.py` exposes `NarrationCache` (backed by `cachetools.TTLCache`, TTL 30 min) and `make_cache_key`.

- **Key format:** `{lang}_{city}_{wx_bucket}_{time_of_day}` — e.g. `zh_shulin_rain_morning`
- **Fuzzy wx bucket:** weather text is classified into: `Sunny`, `Rain`, `Cloudy`, `Other`. Exact temperature is excluded.
- **Separate namespaces per language** — EN and ZH results never collide.

---

## Affected Files

| Status | File | Change |
|---|---|---|
| MODIFY | `narration/llm_prompt_builder.py` | Add `V6_SYSTEM_PROMPT_EN` + `V6_SYSTEM_PROMPT_ZH`; `build_system_prompt(lang)` gating |
| MODIFY | `narration/llm_summarizer.py` | `lang` param gates output instruction in both summarizer prompts |
| MODIFY | `backend/pipeline.py` | Thread `lang` through `generate_narration_with_fallback`; integrate cache |
| NEW | `backend/cache.py` | `NarrationCache` + `make_cache_key(lang, city, wx, time)` |
| MODIFY | `config.py` | TTS constants become per-lang defaults (env-overridable); add `TTS_VOICE_ZH`, `TTS_VOICE_EN` |
| MODIFY | `web/templates/dashboard.html` | Translate static HTML; add `lang` toggle radio group; add local TTS button |
| MODIFY | `web/static/app.js` | `TRANSLATIONS` const; `applyLanguage(lang)`; thread `lang` into refresh POST; update `translateAQIText` to pass-through |

---

## Verification

1. **Toggle smoke test:** Switch EN ↔ 中文 → all static labels update instantly without a page reload.
2. **LLM generation test (ZH):** Trigger refresh with `lang=zh-TW` → narration text and lifestyle cards are in colloquial Traditional Chinese; backend payload `---METADATA---` JSON keys remain English.
3. **LLM generation test (EN):** Trigger refresh with `lang=en` → narration and cards in English; behaviour identical to pre-localization.
4. **Cache namespace test:** After first ZH generation, switch to EN and refresh → server log must show no cache HIT (different namespace). Second EN refresh → cache HIT.
5. **TTS test:** Narration view → click 🔊 button → browser speaks in Mandarin (ZH) or English (EN) matching the selected language.
6. **Full regression:** `pytest tests/ -v` — all existing tests PASS.
