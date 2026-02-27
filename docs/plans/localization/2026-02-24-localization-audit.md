# Chinese Localization Audit — 2026-02-24

Read-only audit of Batches A–F against the plan in `2026-02-24-chinese-localization-plan.md`.

---

## ✅ Correctly Implemented

| Batch | Item | Status |
|---|---|---|
| A | `build_system_prompt(lang)` gating in `llm_prompt_builder.py` | ✅ |
| A | `V6_SYSTEM_PROMPT_EN` + `V6_SYSTEM_PROMPT_ZH` constants | ✅ |
| A | `build_prompt(lang=...)` signature updated | ✅ |
| A | `generate_narration_with_fallback(lang=...)` signature + cache integration | ✅ |
| A | `/api/refresh` reads `lang` from POST body, passes to pipeline | ✅ |
| A | Language toggle `<div class="provider-toggle-group">` in `dashboard.html` | ✅ |
| A | `initLangToggle()` + `getLang()` + `applyLanguage()` stub in `app.js` | ✅ |
| A | `lang` sent in POST body from `triggerRefresh()` | ✅ |
| A | Test: `test_build_system_prompt_*` in `test_pipeline.py` | ✅ |
| B | `V6_SYSTEM_PROMPT_ZH` fully written (繁體中文, METADATA stays English) | ✅ |
| B | Tests: `test_zh_system_prompt_*`, `test_en_prompt_unchanged` | ✅ |
| B | `summarize_for_lifestyle` has `lang` param + ZH prompt branch | ✅ |
| B | `summarize_aqi_forecast` has `lang` param + ZH prompt branch | ✅ |
| B | `tests/test_summarizer_prompts.py` created | ✅ |
| C | `backend/cache.py` created with `NarrationCache` + `make_cache_key` | ✅ |
| C | Cache wired into `pipeline.py` (check + store) | ✅ |
| C | `tests/test_narration_cache.py` created | ✅ |
| C | `cachetools` in `requirements.txt` | ✅ (assumed — not verified directly) |
| D | `<title>家庭天氣儀表板</title>` | ✅ |
| D | Nav labels: 功能, 生活建議, 廣播稿, 天氣總覽 | ✅ |
| D | Loading text: `正在獲取天氣…` (minor typo: `正在獲獲取`) | ⚠️ TYPO |
| D | Error message: `廣播載入失敗。` | ✅ |
| D | Retry button: `重試` | ✅ |
| D | View h1s: 生活指南, 每日天氣廣播, 天氣儀表板 | ✅ |
| D | 24h/7day h2: `24 小時預報`, `七日預報` | ✅ |
| D | System controls label: `系統控制` | ✅ |
| D | Refresh button: `🔄 重新整理` | ✅ |
| D | Dark mode toggle: `淺色模式` / `深色模式` | ✅ |
| D | System log header: `系統記錄` | ✅ |
| E | `TRANSLATIONS` const (EN + zh-TW) added to `app.js` | ✅ |
| E | `let T = TRANSLATIONS['zh-TW']` initial state | ✅ |
| E | `applyLanguage(lang)` fully implemented (splices LOADING_MSGS, re-renders) | ✅ |
| E | `let LOADING_MSGS = []` (mutable, populated by applyLanguage) | ✅ |
| E | Gauge labels use `T.*` | ✅ |
| E | Alert titles/guidance use `T.*` | ✅ |
| E | Timeline row labels `T.rain`, `T.wind`, `T.outdoor` | ✅ |
| E | 7-day day-of-week uses `T.days`, `T.night`, `T.day` | ✅ |
| E | 7-day rain row uses `T.rain` | ✅ |
| E | AQI forecast title uses `T.aqi_title` | ✅ |
| E | Lifestyle card titles use `T.*` | ✅ |
| E | `T.feels_like`, `T.best_label`, `T.top_label` in lifestyle extras | ✅ |
| E | `T.last_updated` in render footer | ✅ |
| E | `T.render` used for pipeline success log | ✅ |
| E | `T.boot` used in triggerRefresh | ✅ |
| E | `T.data_ok` used | ❌ — see Bug #3 |
| E | `translateAQIText` updated to pass-through | ❌ — see Bug #4 |
| F | `initLocalTTS()` implemented | ✅ |
| F | Local TTS button `#local-tts-btn` in `dashboard.html` | ✅ |
| F | TTS button wired in `renderNarrationView` | ✅ |
| C/D | `config.py` TTS constants: `TTS_VOICE_EN`, `TTS_VOICE_ZH`, legacy aliases | ✅ |

---

## ❌ Bugs & Gaps

### Bug 1 — Duplicate `getLang()` definition in `app.js` (HIGH)

**File:** `web/static/app.js`, lines ~910–912 and ~954–956

Two functions named `getLang` are defined. The second one (at line 954) overrides the first:

```javascript
// Line 910 — correct implementation
function getLang() {
  return localStorage.getItem('lang') || 'zh-TW';
}

// Line 954 — OVERRIDE: reads from DOM radio, not localStorage
function getLang() {
  return document.querySelector('input[name="lang"]:checked')?.value || 'zh-TW';
}
```

The plan only requires one `getLang()`. The second definition silently overwrites the first, and the DOM-based version can return the wrong value before the toggle is rendered. The `localStorage` version is more reliable.

**Fix:** Remove the second definition (lines 953–956). Keep only the first `getLang()`.

---

### Bug 2 — `run_parallel_summarization` does not pass `lang` to summarizers (HIGH)

**File:** `backend/pipeline.py`, line ~145 and `app.py`, line ~267

`pipeline.py` exposes:
```python
def run_parallel_summarization(paragraphs, aqi_forecast_raw) -> tuple[dict, str | None]:
    ...
    future_lifestyle = executor.submit(summarize_for_lifestyle, paragraphs)  # no lang!
    future_aqi = executor.submit(summarize_aqi_forecast, aqi_forecast_raw)  # no lang!
```

Both `summarize_for_lifestyle` and `summarize_aqi_forecast` support a `lang` param, but `run_parallel_summarization` never forwards it. The summarizers will always use the default English prompt regardless of the `lang` toggle.

`app.py` calls `run_parallel_summarization(paragraphs, aqi_forecast_raw)` without passing `lang` either.

**Fix:**
1. Add `lang: str = 'en'` param to `run_parallel_summarization`.
2. Forward it to both `summarize_for_lifestyle` and `summarize_aqi_forecast`.
3. In `app.py` `_pipeline_steps`, pass `lang=lang` to `run_parallel_summarization`.

---

### Bug 3 — Boot log still uses hardcoded English string (LOW)

**File:** `web/static/app.js`, line ~157 and ~172

```javascript
// line 157 — hardcoded, not T.boot
addLog("System Boot: Initiating connection...");

// line 172 — hardcoded, not removed per plan Step 14
addLog("System Boot: Fetching latest broadcast...");
```

The plan (Task 7, Step 14) says:
- Replace the `addLog("System Boot: Initiating connection...")` with `addLog(T.boot)`.
- Delete the `addLog("System Boot: Fetching latest broadcast...")` line.

The `triggerRefresh()` function correctly calls `addLog(T.boot)` at line ~750. But the `DOMContentLoaded` boot block at lines 157 and 172 still uses hardcoded English strings.

Additionally, `fetchBroadcast()` at line ~178 uses `addLog("Data received successfully.")` instead of `addLog(T.data_ok)`.

**Fix:** Replace those three hardcoded strings with `T.boot`, remove the second redundant boot log, and replace `"Data received successfully."` with `T.data_ok`.

---

### Bug 4 — `translateAQIText` is NOT updated to a pass-through (MEDIUM)

**File:** `web/static/app.js`, lines ~471–482

The plan (Task 7, Step 15) requires replacing the Chinese-to-English translation map with a simple pass-through:
```javascript
// REQUIRED by plan:
function translateAQIText(status) {
  return status || '';
}
```

Current implementation still contains the full translation map:
```javascript
function translateAQIText(status) {
  if (!status) return '';
  const map = {
    '良好': 'Good',
    '普通': 'Moderate',
    '對敏感族群不健康': 'Unhealthy for Sensitive Groups',
    ...
  };
  return map[status] || status;
}
```

This means AQI status labels will be translated to English even when the user is in `zh-TW` mode. The AQI summarizer now returns Chinese text directly, so the translation step is wrong.

**Fix:** Replace the function body with `return status || '';`.

---

### Bug 5 — Narration view paragraph titles are hardcoded English in `web/routes.py` (MEDIUM)

**File:** `web/routes.py`, lines ~281–288 (`_slice_narration`)

```python
return {
    "paragraphs": [
        {"title": "Current & Outlook",    "text": ...},
        {"title": "Garden & Commute",     "text": ...},
        {"title": "Outdoor with Dad",     "text": ...},
        {"title": "Meals & Climate",      "text": ...},
        {"title": "Forecast",             "text": ...},
        {"title": "Yesterday's Accuracy", "text": ...},
    ],
    ...
}
```

These English titles appear in the Narration view. They are not in the `TRANSLATIONS` map and are not covered by any translation step. When `lang=zh-TW` these section titles will remain in English.

Neither the implementation plan nor `TRANSLATIONS` currently address this. This is an **unplanned gap**.

**Fix options:**
- A) Add ZH paragraph titles to the `TRANSLATIONS` const in `app.js` and use them when rendering the narration blocks.
- B) Have the backend return lang-specific titles (requires passing `lang` to `build_slices`).

---

### Bug 6 — `loading-text` HTML has a doubled character typo (LOW)

**File:** `web/templates/dashboard.html`, line 76

```html
<p id="loading-text">正在獲獲取天氣…</p>
```

`獲獲取` should be `獲取`. This is a character duplication typo.

**Fix:** Change `正在獲獲取天氣…` → `正在獲取天氣…`.

---

### Bug 7 — `TTS_VOICE_EN`/`TTS_VOICE_ZH` from `config.py` are not used per-request in TTS client (LOW)

**File:** `narration/tts_client.py` (not inspected directly, but inferred)

`config.py` correctly defines `TTS_VOICE_EN` and `TTS_VOICE_ZH`. However, the TTS call in `app.py` (`_synth(narration_text, date_str=date_str)`) does not pass `lang`. The TTS client will use the module-level constant `TTS_VOICE_NAME` (which is aliased to `TTS_VOICE_ZH`) rather than selecting the voice based on the current language request.

This means EN refreshes will still use the `zh-TW` Wavenet voice.

**Impact:** Medium — English users will hear narration in a Chinese voice.

**Fix:** Thread `lang` through to `synthesize_and_upload` and have the TTS client select `TTS_VOICE_EN` vs `TTS_VOICE_ZH` accordingly.

---

## Summary

| # | Description | Severity | Batch |
|---|---|---|---|
| 1 | Duplicate `getLang()` — second definition overrides first | HIGH | E/F |
| 2 | `run_parallel_summarization` + `app.py` don't pass `lang` to summarizers | HIGH | B/E |
| 3 | Boot log messages still hardcoded English; `T.data_ok` not used | LOW | E |
| 4 | `translateAQIText` still has old EN translation map, not pass-through | MEDIUM | E |
| 5 | Narration paragraph titles hardcoded English in `web/routes.py` | MEDIUM | E/F |
| 6 | Typo: `正在獲獲取天氣…` in `dashboard.html` | LOW | D |
| 7 | TTS client doesn't receive `lang`; always uses ZH voice | LOW | C/F |
