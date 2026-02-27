# Localization Epic Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

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


# Traditional Chinese Localization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a runtime EN / 中文 language toggle to the family weather dashboard. Both the LLM narration and all UI labels switch language on demand. Data query payloads stay English for precision. The `---METADATA---` JSON block always stays English (Python parses it).

**Architecture:** A `lang` field (`"en"` | `"zh-TW"`) is sent in every `/api/refresh` POST body and persisted in `localStorage`. Two system prompt variants (`V6_SYSTEM_PROMPT_EN` + `V6_SYSTEM_PROMPT_ZH`) live in `llm_prompt_builder.py`; summarizers accept a `lang` arg. Cache keys are namespaced by language (`en_shulin_rain_morning` vs `zh_shulin_rain_morning`). The frontend `TRANSLATIONS` const in `app.js` provides both label maps; static labels update instantly on toggle without re-fetching. Cloud TTS voice is selected per-request from `lang`. Local Web Speech API TTS sets `utter.lang` accordingly.

**Tech Stack:** Python / Flask backend, vanilla JS frontend, Anthropic Claude Sonnet (primary), Gemini Pro (secondary), Google Cloud TTS, Web Speech API (local browser TTS), `cachetools.TTLCache`

---

## Batch Breakdown (execute one batch per session)

> **Why batches?** Each batch fits comfortably in one agent context window. Start a fresh session for each batch, passing the plan file as context. Do **not** combine batches.

| Batch | Tasks | Files touched | Rationale |
|---|---|---|---|
| **A** | Task 0 | `llm_prompt_builder.py`, `pipeline.py`, `routes.py`, `dashboard.html`, `app.js`, `tests/test_pipeline.py` | Scaffold-only; sets up all plumbing. All other tasks depend on this. |
| **B** | Tasks 2 + 3 | `llm_prompt_builder.py`, `llm_summarizer.py`, `tests/` | Small prompt-string tasks; no new files, safe to pair. |
| **C** | Tasks 4 + 5 | `backend/cache.py` (new), `pipeline.py`, `config.py`, `requirements.txt`, `tests/` | Cache creation + config tweak; tightly related, combined file count is low. |
| **D** | Task 6 | `dashboard.html` | ~20 string swaps in a single large HTML file; own context avoids bleed. |
| **E** | Task 7 | `app.js` | Largest task (16 steps, big `TRANSLATIONS` block); needs the full context window. |
| **F** | Task 8 + E2E | `app.js`, `dashboard.html` | Small TTS button + manual smoke-test; natural finish-line batch. |

---

## Task 0: Language Toggle Plumbing — Backend & Frontend

**Files:**
- Modify: `narration/llm_prompt_builder.py` — add `V6_SYSTEM_PROMPT_ZH`, gate `build_system_prompt(lang)`
- Modify: `narration/llm_summarizer.py` — add `lang` param to both summarizers
- Modify: `backend/pipeline.py` — add `lang` param to `generate_narration_with_fallback`, thread into prompt builder and cache key
- Modify: `web/routes.py` — read `lang` from POST body, pass to pipeline
- Modify: `web/static/app.js` — read `lang` from `localStorage`, send in refresh POST, call `applyLanguage(lang)` on toggle
- Modify: `web/templates/dashboard.html` — add EN / 中文 radio toggle group in Right Panel

This task is the enabling scaffold. No visible language change yet — it just wires the `lang` signal from the UI toggle button all the way through to `build_system_prompt`. Subsequent tasks fill in the actual translations.

**Step 1: Write the failing integration test**

Add to `tests/test_pipeline.py`:
```python
from narration.llm_prompt_builder import build_system_prompt

def test_build_system_prompt_en_returns_english_prompt():
    prompt = build_system_prompt(lang='en')
    assert 'English' in prompt or 'english' in prompt.lower()

def test_build_system_prompt_zh_returns_chinese_prompt():
    prompt = build_system_prompt(lang='zh-TW')
    assert '繁體中文' in prompt or 'Traditional Chinese' in prompt

def test_build_system_prompt_unknown_lang_falls_back_to_en():
    prompt = build_system_prompt(lang='fr')
    # Unknown lang → safe fallback to English
    assert '---METADATA---' in prompt
```

**Step 2: Run to verify failure**
```
pytest tests/test_pipeline.py::test_build_system_prompt_en_returns_english_prompt tests/test_pipeline.py::test_build_system_prompt_zh_returns_chinese_prompt -v
```
Expected: `AttributeError` or `TypeError` — `build_system_prompt` does not yet accept a `lang` arg.

**Step 3: Implement — gate `build_system_prompt` in `llm_prompt_builder.py`**

Add a second constant and update the function signature:
```python
# SEARCH
def build_system_prompt() -> str:
    """Return the v6 system prompt for use as the model's system instruction."""
    return V6_SYSTEM_PROMPT
# REPLACE
V6_SYSTEM_PROMPT_EN = V6_SYSTEM_PROMPT  # alias — English prompt is unchanged

V6_SYSTEM_PROMPT_ZH = V6_SYSTEM_PROMPT  # placeholder — filled in Task 2

def build_system_prompt(lang: str = 'en') -> str:
    """Return the system prompt for the given language code.
    Supported: 'en' (default), 'zh-TW'. Unknown codes fall back to English.
    """
    if lang == 'zh-TW':
        return V6_SYSTEM_PROMPT_ZH
    return V6_SYSTEM_PROMPT_EN
```

**Step 4: Add `lang` param to `generate_narration_with_fallback` in `backend/pipeline.py`**

```python
# SEARCH
def generate_narration_with_fallback(
    provider: str,
    processed: dict,
    history: list[dict],
    date_str: str,
) -> tuple[str, str]:
# REPLACE
def generate_narration_with_fallback(
    provider: str,
    processed: dict,
    history: list[dict],
    date_str: str,
    lang: str = 'en',
) -> tuple[str, str]:
```

Then update the `build_prompt` call inside the same function to pass `lang` through to `build_system_prompt`:
```python
# SEARCH (inside the function body)
        messages = build_prompt(processed, history, date_str)
# REPLACE
        messages = build_prompt(processed, history, date_str, lang=lang)
```

Also update `build_prompt` signature in `llm_prompt_builder.py` to accept and pass `lang`:
```python
# SEARCH
def build_prompt(
    processed_data: dict,
    history: list[dict],
    today_date: str | None = None,
) -> list[dict]:
# REPLACE
def build_prompt(
    processed_data: dict,
    history: list[dict],
    today_date: str | None = None,
    lang: str = 'en',
) -> list[dict]:
```

**Step 5: Read `lang` from POST body in `web/routes.py`**

Find the `/api/refresh` route handler. Locate where `provider` is read from the request JSON and add `lang` alongside it:
```python
# SEARCH (approximate — find the block that reads provider)
    provider = data.get('provider', 'CLAUDE')
# REPLACE
    provider = data.get('provider', 'CLAUDE')
    lang = data.get('lang', 'en')
```

Then pass `lang` into `generate_narration_with_fallback`:
```python
# SEARCH (approximate)
    text, source = generate_narration_with_fallback(provider, processed, history, date_str)
# REPLACE
    text, source = generate_narration_with_fallback(provider, processed, history, date_str, lang=lang)
```

**Step 6: Add toggle UI to `dashboard.html`**

In the Right Panel, after the existing provider toggle group (line ~172), add:
```html
<!-- Language toggle -->
<div class="provider-toggle-group">
  <label class="provider-option">
    <input type="radio" name="lang" value="en">
    <span class="prov-label">EN</span>
  </label>
  <label class="provider-option">
    <input type="radio" name="lang" value="zh-TW" checked>
    <span class="prov-label">中文</span>
  </label>
</div>
```

**Step 7: Wire toggle in `app.js`**

Add after `initRefreshButton()` call in the boot block:
```javascript
  initLangToggle();
```

Add the function:
```javascript
// ── Language Toggle ────────────────────────────────────────────────────────
function initLangToggle() {
  const saved = localStorage.getItem('lang') || 'zh-TW';
  const radio = document.querySelector(`input[name="lang"][value="${saved}"]`);
  if (radio) radio.checked = true;
  applyLanguage(saved);

  document.querySelectorAll('input[name="lang"]').forEach(r => {
    r.addEventListener('change', () => {
      localStorage.setItem('lang', r.value);
      applyLanguage(r.value);
    });
  });
}

function getLang() {
  return localStorage.getItem('lang') || 'zh-TW';
}

function applyLanguage(lang) {
  // Swaps all T.* references — implemented fully in Task 7
  // Placeholder: log the switch
  addLog(`語言切換：${lang}`);
}
```

Update `triggerRefresh` to send `lang` in POST body:
```javascript
// SEARCH
      body: JSON.stringify({
        provider
      })
// REPLACE
      body: JSON.stringify({
        provider,
        lang: getLang()
      })
```

**Step 8: Run tests**
```
pytest tests/test_pipeline.py -v
```
Expected: all existing tests PASS plus new `test_build_system_prompt_*` tests PASS.

**Step 9: Commit**
```
git add narration/llm_prompt_builder.py backend/pipeline.py web/routes.py web/templates/dashboard.html web/static/app.js tests/test_pipeline.py
git commit -m "feat(i18n): wire lang toggle signal from UI through to prompt builder scaffold"
```

---

## Task 2: Update the LLM System Prompt — `narration/llm_prompt_builder.py`

**Files:**
- Modify: `narration/llm_prompt_builder.py` — fill in `V6_SYSTEM_PROMPT_ZH` (the Chinese variant constant added as a placeholder in Task 0)

The spoken script paragraphs (P1–P6) must be in colloquial Traditional Chinese (台灣中文, 繁體). The `---METADATA---` JSON block MUST remain in English (Python parses it). Dish names and location names should now use Chinese characters. The paragraph structure and all hard rules (no markdown, word count) remain identical, just expressed in Chinese.

**Step 1: Write the failing assertion test**

Add to `tests/test_pipeline.py`:
```python
def test_zh_system_prompt_requires_chinese_output():
    """ZH prompt must instruct Chinese output and not say 'English only'."""
    prompt = build_system_prompt(lang='zh-TW')
    assert "繁體中文" in prompt
    assert "English only" not in prompt

def test_zh_metadata_block_stays_english():
    """ZH prompt must still instruct METADATA JSON keys in English."""
    prompt = build_system_prompt(lang='zh-TW')
    assert "---METADATA---" in prompt
    assert '"wardrobe"' in prompt
    assert '"accuracy_grade"' in prompt

def test_en_prompt_unchanged():
    """EN prompt must still contain 'English only' rule."""
    prompt = build_system_prompt(lang='en')
    assert "English only" in prompt
```

**Step 2: Run to verify failure**
```
pytest tests/test_pipeline.py::test_zh_system_prompt_requires_chinese_output tests/test_pipeline.py::test_zh_metadata_block_stays_english -v
```
Expected: `test_zh_system_prompt_requires_chinese_output` FAILS — `V6_SYSTEM_PROMPT_ZH` is still the English placeholder from Task 0.

**Step 3: Implement — write `V6_SYSTEM_PROMPT_ZH` in full**

In `narration/llm_prompt_builder.py`, replace the placeholder `V6_SYSTEM_PROMPT_ZH = V6_SYSTEM_PROMPT` line:

```python
# SEARCH
V6_SYSTEM_PROMPT = """\
You are a warm, concise personal radio broadcaster for a family living near the Shulin/Banqiao border in Taiwan. You receive pre-processed weather data as a JSON object — use ONLY that data, never invent numbers. Your output is a plain spoken English script for a TTS engine.

HARD RULES:
- English only. For Chinese dish names, place names, or terms, use pinyin romanization (e.g. "niu rou mian" not "牛肉麵"). Absolutely zero Chinese characters in the output.
- No markdown formatting whatsoever — no headers, bold, italics, bullets, numbered lists, or code blocks. Output only plain text paragraphs separated by blank lines.
- Total broadcast length: 500–700 words. Be conversational but concise. No verbal filler, no over-explaining.

# REPLACE with:
V6_SYSTEM_PROMPT = """\
你是一個親切、簡潔的家庭廣播員，服務住在台灣樹林/板橋交界處附近的一家人。你收到預處理的天氣數據（JSON 格式）——只使用這些數據，絕對不要自行填補數字。你的輸出是給 TTS 引擎的純口語廣播稿。

硬性規則：
- 使用繁體中文。菜餚名稱、地名等直接用中文（例如「牛肉麵」而非拼音）。
- 絕對不使用 Markdown 格式——不使用標題、粗體、斜體、項目符號、編號列表或程式碼區塊。輸出純文字段落，段落之間用空行分隔。
- 廣播總長度：500–700 個字（中文字數）。口語化但簡潔。不使用語氣詞或過度解釋。
- 廣播稿（P1–P6）全部使用繁體中文。但 ---METADATA--- 分隔符之後的 JSON 物件的「鍵名和英文值」必須保持英文（如 "wardrobe", "rain_gear", true/false），讓後端程式可以正確解析。
```

**Step 4: Run to verify pass**
```
pytest tests/test_pipeline.py::test_zh_system_prompt_requires_chinese_output tests/test_pipeline.py::test_zh_metadata_block_stays_english tests/test_pipeline.py::test_en_prompt_unchanged -v
```
Expected: all PASS.

**Step 5: Commit**
```
git add narration/llm_prompt_builder.py tests/test_pipeline.py
git commit -m "feat(i18n): fill in V6_SYSTEM_PROMPT_ZH — colloquial Traditional Chinese, metadata stays English"
```

---

## Task 3: Update Lifestyle Summarizer — `narration/llm_summarizer.py`

**Files:**
- Modify: `narration/llm_summarizer.py` — implement `lang` param logic in `summarize_for_lifestyle` and `summarize_aqi_forecast` (param scaffold added in Task 0; this task fills in the switch logic)

The two summarizer prompts must gate output language on `lang`. Sentence-count constraints remain identical.

**Step 1: Write the failing assertion test**

Create `tests/test_summarizer_prompts.py`:
```python
import inspect
from narration import llm_summarizer

def test_lifestyle_prompt_requests_chinese():
    """The lifestyle summarizer source must mention Traditional Chinese."""
    src = inspect.getsource(llm_summarizer.summarize_for_lifestyle)
    assert "Traditional Chinese" in src or "繁體中文" in src

def test_aqi_prompt_outputs_chinese():
    """The AQI summarizer source must mention Traditional Chinese output."""
    src = inspect.getsource(llm_summarizer.summarize_aqi_forecast)
    assert "Traditional Chinese" in src or "繁體中文" in src
```

**Step 2: Run to verify failure**
```
pytest tests/test_summarizer_prompts.py -v
```
Expected: FAIL — prompts currently say English.

**Step 3: Implement — update both prompt strings**

In `summarize_for_lifestyle`, replace the `prompt = f"""..."""` block. Change line:
```python
# SEARCH
You are a helpful assistant that summarizes weather narration into short, punchy dashboard card snippets. 
User needs a JSON object with specific sentence counts for each card.
# REPLACE
你是一個助理，將天氣廣播稿濃縮成簡短有力的儀表板卡片說明。
請用繁體中文輸出，語氣口語自然。回傳一個 JSON 物件，各鍵名保持英文（後端解析用），值為繁體中文字串。
```

And update the `OUTPUT FORMAT` instruction to clarify Chinese values are expected:
```python
# SEARCH (near end of prompt)
OUTPUT FORMAT:
{{
  "wardrobe": "...",
# REPLACE
OUTPUT FORMAT (鍵名保持英文，值為繁體中文):
{{
  "wardrobe": "...",
```

In `summarize_aqi_forecast`, replace:
```python
# SEARCH
You are an environmental expert specializing in Taiwan's air quality.
Summarize the following Chinese air quality forecast for Northern Taiwan into a concise English update.
# REPLACE
你是一位專精台灣空氣品質的環境專家。
請將以下北台灣空氣品質預報摘要成繁體中文，簡潔口語，2–3 句話。
```

Remove rule 3-4 ("English", "no Chinese characters") from the AQI prompt. Replace rule 3 with:
```python
# SEARCH
3. Mention the primary pollutant (e.g., PM2.5, Ozone) in English.
4. DO NOT include any Chinese characters or specific terminology titles like "細懸浮微粒" or "臭氧" in the output.
# REPLACE
3. 主要污染物可用中文或英文（例如「細懸浮微粒（PM2.5）」或「臭氧」均可）。
```

Update the output instruction:
```python
# SEARCH
OUTPUT: Concise English summary (text only).
# REPLACE
OUTPUT: 繁體中文摘要（純文字，2–3 句）。
```

**Step 4: Run to verify pass**
```
pytest tests/test_summarizer_prompts.py -v
```
Expected: PASS.

**Step 5: Commit**
```
git add narration/llm_summarizer.py tests/test_summarizer_prompts.py
git commit -m "feat(i18n): summarizer prompts gate output language on lang param"
```

---

## Task 4: Add Narration Cache — `backend/cache.py` + `backend/pipeline.py`

**Files:**
- Create: `backend/cache.py`
- Modify: `backend/pipeline.py:58-102`
- Modify: `requirements.txt`

**Step 1: Add dependency**

In `requirements.txt`, append:
```
cachetools>=5.3
```

Install:
```
pip install cachetools
```

**Step 2: Write the failing tests**

Create `tests/test_narration_cache.py`:
```python
from backend.cache import NarrationCache, make_cache_key

def test_cache_key_includes_lang():
    key_en = make_cache_key('en', 'Shulin', 'Rain', 'morning')
    key_zh = make_cache_key('zh-TW', 'Shulin', 'Rain', 'morning')
    assert key_en != key_zh
    assert key_en.startswith('en_')
    assert key_zh.startswith('zh-tw_')

def test_cache_key_ignores_exact_temp():
    """Keys for similar weather states should match regardless of exact temperature."""
    key1 = make_cache_key("Shulin", "Rain", "morning", temp_c=24)
    key2 = make_cache_key("Shulin", "Rain", "morning", temp_c=26)
    assert key1 == key2

def test_cache_key_differs_by_wx_class():
    key_rain = make_cache_key("Shulin", "Rain", "morning", temp_c=24)
    key_sunny = make_cache_key("Shulin", "Sunny", "morning", temp_c=24)
    assert key_rain != key_sunny

def test_cache_key_differs_by_time_of_day():
    key_am = make_cache_key("Shulin", "Rain", "morning", temp_c=24)
    key_pm = make_cache_key("Shulin", "Rain", "evening", temp_c=24)
    assert key_am != key_pm

def test_cache_hit_returns_cached_value():
    cache = NarrationCache(ttl_seconds=60)
    cache.set("zh-tw_shulin_rain_morning", ("narration text", "claude"))
    result = cache.get("zh-tw_shulin_rain_morning")
    assert result == ("narration text", "claude")

def test_cache_miss_returns_none():
    cache = NarrationCache(ttl_seconds=60)
    assert cache.get("missing_key") is None
```

**Step 3: Run to verify failure**
```
pytest tests/test_narration_cache.py -v
```
Expected: ImportError — `backend/cache.py` does not exist.

**Step 4: Implement `backend/cache.py`**

```python
"""backend/cache.py — Simple TTL-based narration cache."""
from __future__ import annotations
from cachetools import TTLCache

_WX_BUCKETS = {
    "sunny": "Sunny", "clear": "Sunny",
    "rain": "Rain", "shower": "Rain", "drizzle": "Rain", "storm": "Rain",
    "cloudy": "Cloudy", "overcast": "Cloudy", "fog": "Cloudy", "mist": "Cloudy",
}

def _classify_wx(weather_text: str) -> str:
    low = weather_text.lower()
    for kw, bucket in _WX_BUCKETS.items():
        if kw in low:
            return bucket
    return "Other"

def _classify_time(hour: int) -> str:
    if 6 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"

def make_cache_key(lang: str, city: str, weather_text: str, time_of_day: str, temp_c: float = 0) -> str:
    """
    Fuzzy cache key: lang + city + wx_bucket + time_of_day.
    temp_c is intentionally excluded to maximise hit rate.
    lang is included to prevent EN and ZH entries colliding.
    """
    wx = _classify_wx(weather_text)
    return f"{lang}_{city}_{wx}_{time_of_day}".lower()

class NarrationCache:
    def __init__(self, ttl_seconds: int = 1800):
        self._store: TTLCache = TTLCache(maxsize=128, ttl=ttl_seconds)

    def get(self, key: str) -> tuple[str, str] | None:
        return self._store.get(key)

    def set(self, key: str, value: tuple[str, str]) -> None:
        self._store[key] = value
```

**Step 5: Wire into `backend/pipeline.py`**

At top of file, add import:
```python
from backend.cache import NarrationCache, make_cache_key, _classify_time
# lang-aware cache — separate namespaces for EN and ZH results

_narration_cache = NarrationCache(ttl_seconds=1800)
```

Wrap `generate_narration_with_fallback` to check cache first. Replace the function signature and add cache check/store at top and bottom:
```python
def generate_narration_with_fallback(
    provider: str,
    processed: dict,
    history: list[dict],
    date_str: str,
    lang: str = 'en',
) -> tuple[str, str]:
    # ── Cache check ────────────────────────────────────────────────────
    from datetime import datetime
    current = processed.get("current", {})
    city = "shulin"
    wx_text = current.get("beaufort_desc", current.get("weather_text", ""))
    hour = datetime.now().hour
    cache_key = make_cache_key(lang, city, wx_text, _classify_time(hour))

    cached = _narration_cache.get(cache_key)
    if cached:
        logger.info("Narration cache HIT: %s", cache_key)
        return cached
    # ── (existing LLM call logic unchanged) ────────────────────────────
    # ... existing code ...
    # ── Cache store ────────────────────────────────────────────────────
    # After obtaining (text, source), before returning:
    _narration_cache.set(cache_key, (text, source))
    return text, source
```

**Step 6: Run all cache tests**
```
pytest tests/test_narration_cache.py -v
```
Expected: all PASS.

**Step 7: Run existing pipeline tests to confirm no regression**
```
pytest tests/test_pipeline.py -v
```
Expected: all PASS.

**Step 8: Commit**
```
git add backend/cache.py backend/pipeline.py requirements.txt tests/test_narration_cache.py
git commit -m "feat(cache): 30-min fuzzy narration cache keyed on lang+city+wx+time_of_day"
```

---

## Task 5: Update Cloud TTS Config — `config.py`

**Files:**
- Modify: `config.py:98-104`

**Step 1: No dedicated test needed** — config values are trivially correct. Run the existing full test suite to catch imports.

**Step 2: Implement**

Replace the TTS block to support per-request language selection. The default constants remain as env-overridable fallbacks:

```python
# SEARCH
TTS_LANGUAGE_CODE = "en-US"
TTS_VOICE_NAME = os.environ.get("TTS_VOICE_NAME", "en-US-Neural2-D")
# REPLACE
# Per-language TTS voice defaults (overridable via env)
TTS_VOICE_EN = os.environ.get("TTS_VOICE_NAME", "en-US-Neural2-D")
TTS_VOICE_ZH = os.environ.get("TTS_VOICE_ZH", "zh-TW-Wavenet-B")
# Legacy alias — used by any TTS call that hasn't been updated to pass lang yet
TTS_LANGUAGE_CODE = "zh-TW"
TTS_VOICE_NAME = TTS_VOICE_ZH
```

> **Note:** `zh-TW-Wavenet-B` is a Taiwan Mandarin male Wavenet voice. Available voices: https://cloud.google.com/text-to-speech/docs/voices — filter by `zh-TW`. Any TTS call site that uses `lang` should select `TTS_VOICE_ZH` or `TTS_VOICE_EN` directly rather than the legacy `TTS_VOICE_NAME`.

**Step 3: Run full test suite**
```
pytest tests/ -v
```
Expected: all PASS (config change is non-breaking, it's just a string swap).

**Step 4: Commit**
```
git add config.py
git commit -m "feat(tts): add TTS_VOICE_EN + TTS_VOICE_ZH for per-lang voice selection"
```

---

## Task 6: Translate Static HTML — `web/templates/dashboard.html`

**Files:**
- Modify: `web/templates/dashboard.html`

All hardcoded English strings in HTML are replaced. No new files needed.

**Reference table (English → Traditional Chinese):**

| Element | English | Traditional Chinese |
|---|---|---|
| `<title>` | Family Weather Dashboard | 家庭天氣儀表板 |
| nav section label | Views | 功能 |
| nav button: lifestyle | Lifestyle | 生活建議 |
| nav button: narration | Narration | 廣播稿 |
| nav button: dashboard | Dashboard | 天氣總覽 |
| loading text | Fetching forecast… | 正在獲取天氣…  |
| error msg | Could not load broadcast. | 廣播載入失敗。 |
| retry button | Retry | 重試 |
| view h1: lifestyle | Lifestyle Guide | 生活指南 |
| view h1: narration | Weather Briefing | 每日天氣廣播 |
| view h1: dashboard | Weather Dashboard | 天氣儀表板 |
| 24h forecast h2 | 24-Hour Forecast | 24 小時預報 |
| 7-day forecast h2 | 7-Day Forecast | 七日預報 |
| system controls label | System Controls | 系統控制 |
| refresh button | 🔄 Refresh | 🔄 重新整理 |
| dark mode button default | Dark Mode | 深色模式 |
| system log header | System Log | 系統記錄 |
| provider label: Claude | Claude Sonnet | Claude Sonnet |
| provider label: Gemini | Gemini Pro | Gemini Pro |

**Step 1: No test needed** — visual, verified by browser inspection.

**Step 2: Implement** — make each replacement above directly in `dashboard.html`.

Also update the `<html>` tag's `lang` attribute (already `zh-TW` ✅ — no change needed).

Also update the dark mode toggle JS block in `dashboard.html` (lines 219–223):
```javascript
// SEARCH
label.textContent = isDark ? 'Light Mode' : 'Dark Mode';
// REPLACE
label.textContent = isDark ? '淺色模式' : '深色模式';
```

**Step 3: Commit**
```
git add web/templates/dashboard.html
git commit -m "feat(i18n): translate all static dashboard HTML to Traditional Chinese"
```

---

## Task 7: Translate Dynamic JS Labels & `applyLanguage` — `web/static/app.js`

**Files:**
- Modify: `web/static/app.js`

Add a `TRANSLATIONS` constant containing both EN and ZH label maps. Replace all hardcoded English UI strings throughout the rendering functions to reference `T[key]`. Implement `applyLanguage(lang)` (stubbed in Task 0) to re-render all labels when the toggle changes without re-fetching data.

**Step 1: No automated test** — visual. Verify by opening the dashboard and toggling EN ↔ 中文, checking that all labels switch instantly.

**Step 2: Add `TRANSLATIONS` constant** — insert AFTER the `ICONS` constant (line ~66):

```javascript
// ── Translations ───────────────────────────────────────────────────────────
const TRANSLATIONS = {
  en: {
    loading: 'Fetching forecast…',
    error_prefix: 'Error: ',
    last_updated: 'Last updated: ',
    ground: 'Ground',
    wind: 'Wind',
    humidity: 'Humidity',
    air_quality: 'Air Quality',
    uv: 'UV Index',
    pressure: 'Pressure',
    feels_like: 'Feels like',
    rain: 'Rain',
    outdoor: 'Outdoor',
    days: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
    night: 'Night', day: 'Day',
    cardiac_title: 'Cardiac Alert',
    cardiac_guidance: 'Keep warm and avoid sudden cold exposure.',
    menieres_title: "Ménière's Alert",
    menieres_guidance: 'Watch for vertigo or ear fullness; stay hydrated.',
    heads_up_title: 'Heads Up',
    aqi_title: "Tomorrow's Air Quality",
    wardrobe: 'Wardrobe',
    rain_gear: 'Rain Gear',
    commute: 'Commute',
    garden: 'Garden Health',
    outdoor_act: 'Outdoor Activities',
    meals: 'Meals',
    hvac: 'HVAC Advice',
    best_label: 'Best',
    top_label: 'Top',
    boot: 'System Boot: Initiating connection…',
    data_ok: 'Data received successfully.',
    render: 'Pipeline success. Rendering…',
    step1: 'Connecting to CWA Banqiao Station…',
    step2: 'Retrieving Township Forecasts…',
    step3: 'Checking MOENV Air Quality…',
    step4: 'Processing V5 Logic…',
    step5: 'Generating Narration…',
    step6: 'Synthesizing Audio…',
    step7: 'Finalizing…',
  },
  'zh-TW': {
    loading: '正在獲取天氣…',
    error_prefix: '錯誤：',
    last_updated: '最後更新：',
    ground: '地面狀況',
    wind: '風速',
    humidity: '濕度',
    air_quality: '空氣品質',
    uv: '紫外線',
    pressure: '氣壓',
    feels_like: '體感溫度',
    rain: '降雨',
    outdoor: '戶外',
    days: ['日', '一', '二', '三', '四', '五', '六'],
    night: '晚', day: '早',
    cardiac_title: '心臟警示',
    cardiac_guidance: '請保持溫暖，避免突然暴露於冷空氣中。',
    menieres_title: '梅尼爾氏症警示',
    menieres_guidance: '注意眩暈或耳鳴；多補充水分。',
    heads_up_title: '注意事項',
    aqi_title: '明日空氣品質',
    wardrobe: '穿搭建議',
    rain_gear: '雨具準備',
    commute: '通勤狀況',
    garden: '花園照護',
    outdoor_act: '戶外活動',
    meals: '餐食建議',
    hvac: '空調建議',
    best_label: '最佳時段',
    top_label: '推薦活動',
    boot: '系統啟動：初始化連線…',
    data_ok: '資料接收成功。',
    render: '管道成功，正在渲染…',
    step1: '連線至 CWA 板橋站…',
    step2: '取得鄉鎮預報…',
    step3: '查詢 MOENV 空氣品質…',
    step4: '處理 V5 邏輯…',
    step5: '生成廣播稿…',
    step6: '合成語音…',
    step7: '最終處理中…',
  },
};

// Active translation map — updated by applyLanguage()
let T = TRANSLATIONS['zh-TW'];
```

**Step 3: Implement `applyLanguage(lang)`** — replace the stub from Task 0:

```javascript
function applyLanguage(lang) {
  T = TRANSLATIONS[lang] || TRANSLATIONS['zh-TW'];
  // Update LOADING_MSGS in-place for next animation run
  LOADING_MSGS.splice(0, LOADING_MSGS.length,
    T.step1, T.step2, T.step3, T.step4, T.step5, T.step6, T.step7);
  // Re-render labels if data is already loaded
  if (broadcastData) render(broadcastData);
}
```

**Step 4: Replace LOADING_MSGS** (lines 50–58) with a mutable array (so `applyLanguage` can splice it):
```javascript
// SEARCH
const LOADING_MSGS = [
  "Connecting to CWA Banqiao Station...",
  ...
];
// REPLACE
let LOADING_MSGS = [T.step1, T.step2, T.step3, T.step4, T.step5, T.step6, T.step7];
// Note: `let` not `const` — applyLanguage() splices this array.
```

**Step 5: Replace gauge labels** in `renderCurrentView` (lines ~139–144):
```javascript
// SEARCH
  renderGauge('gauge-ground', data.ground_state, 'Ground', ...
  renderGauge('gauge-wind', data.wind.text, 'Wind', ...
  renderGauge('gauge-hum', data.hum.text, 'Humidity', ...
  renderGauge('gauge-aqi', data.aqi.text, 'Air Quality', ...
  renderGauge('gauge-uv', data.uv.text, 'UV Index', ...
  renderGauge('gauge-pres', data.pres.text, 'Pressure', ...
// REPLACE
  renderGauge('gauge-ground', data.ground_state, T.ground, ...
  renderGauge('gauge-wind', data.wind.text, T.wind, ...
  renderGauge('gauge-hum', data.hum.text, T.humidity, ...
  renderGauge('gauge-aqi', data.aqi.text, T.air_quality, ...
  renderGauge('gauge-uv', data.uv.text, T.uv, ...
  renderGauge('gauge-pres', data.pres.text, T.pressure, ...
```

**Step 6: Replace alert titles/guidance** in `renderOverviewView` (lines ~181–184):
```javascript
// SEARCH
        items.push({ type: 'health', icon: '❤️', title: 'Cardiac Alert', ...guidance: 'Keep warm and avoid sudden cold exposure.' });
        items.push({ type: 'health', icon: '🦻', title: 'Ménière\'s Alert', ...guidance: 'Watch for vertigo or ear fullness; stay hydrated.' });
        items.push({ type: 'narrative', icon: '📢', title: 'Heads Up', ...
// REPLACE
        items.push({ type: 'health', icon: '❤️', title: T.cardiac_title, ...guidance: T.cardiac_guidance });
        items.push({ type: 'health', icon: '🦻', title: T.menieres_title, ...guidance: T.menieres_guidance });
        items.push({ type: 'narrative', icon: '📢', title: T.heads_up_title, ...
```

**Step 7: Replace timeline row labels** in the `addRow` calls (lines ~264–268):
```javascript
// SEARCH
      addRow('Rain', seg.precip_text || '—', seg.precip_level || 1);
      addRow('Wind', seg.wind_text || '—', seg.wind_level || 1);
      if (seg.outdoor_grade) {
        addRow('Outdoor', `${seg.outdoor_grade} · ${seg.outdoor_score}`, ...
// REPLACE
      addRow(T.rain, seg.precip_text || '—', seg.precip_level || 1);
      addRow(T.wind, seg.wind_text || '—', seg.wind_level || 1);
      if (seg.outdoor_grade) {
        addRow(T.outdoor, `${seg.outdoor_grade} · ${seg.outdoor_score}`, ...
```

**Step 8: Replace 7-day day-of-week labels** (lines ~318–319):
```javascript
// SEARCH
      const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      const displayTime = `${days[dt.getDay()]} ${isNight ? 'Night' : 'Day'}`;
// REPLACE
      const displayTime = `${T.days[dt.getDay()]}（${isNight ? T.night : T.day}）`;
```

**Step 9: Replace 7-day rain row label** (line ~338):
```javascript
// SEARCH
      l.textContent = 'Rain';
// REPLACE
      l.textContent = T.rain;
```

**Step 10: Replace AQI forecast title** (line ~367):
```javascript
// SEARCH
    title.textContent = "Tomorrow's Air Quality";
// REPLACE
    title.textContent = T.aqi_title;
```

**Step 11: Replace lifestyle card titles** in `renderLifestyleView` (lines ~449–488):
```javascript
// SEARCH
    add('🧥', 'Wardrobe', ...
    if (data.rain_gear) add('☂️', 'Rain Gear', ...
    add('🚗', 'Commute', ...
    if (data.garden && data.garden.text) add('🌱', 'Garden Health', ...
    if (data.outdoor && data.outdoor.text) { ... add('🌳', 'Outdoor Activities', ...
    if (data.meals && data.meals.text) { ... add('🍱', 'Meals', ...
    if (data.hvac) { ... add('🌡️', 'HVAC Advice', ...
// REPLACE
    add('🧥', T.wardrobe, ...
    if (data.rain_gear) add('☂️', T.rain_gear, ...
    add('🚗', T.commute, ...
    if (data.garden && data.garden.text) add('🌱', T.garden, ...
    if (data.outdoor && data.outdoor.text) { ... add('🌳', T.outdoor_act, ...
    if (data.meals && data.meals.text) { ... add('🍱', T.meals, ...
    if (data.hvac) { ... add('🌡️', T.hvac, ...
```

**Step 12: Replace lifestyle sub-labels** (feels_like, Best/Top):
```javascript
// SEARCH
    if (data.wardrobe.feels_like != null) extras.push(mkSub(`Feels like ${Math.round(data.wardrobe.feels_like)}°`));
    if (data.outdoor.top_activity) extras.push(mkSub(`Best: ${data.outdoor.best_window || ''} · Top: ${data.outdoor.top_activity}`));
// REPLACE
    if (data.wardrobe.feels_like != null) extras.push(mkSub(`${T.feels_like} ${Math.round(data.wardrobe.feels_like)}°`));
    if (data.outdoor.top_activity) extras.push(mkSub(`${T.best_label}：${data.outdoor.best_window || ''} · ${T.top_label}：${data.outdoor.top_activity}`));
```

**Step 13: Replace `Last updated:` string** (line ~125):
```javascript
// SEARCH
    const msg = `Last updated: ${dateStr}`;
// REPLACE
    const msg = `${T.last_updated}${dateStr}`;
```

And update the `dateStr` locale to `zh-TW` in the same block (already done ✅ at line 120 — `toLocaleString('zh-TW', ...)`).

**Step 14: Replace log boot messages** (lines ~76, 90, 96, 709):
```javascript
// SEARCH (line 76)
  addLog("System Boot: Initiating connection...");
// REPLACE
  addLog(T.boot);

// SEARCH (line 90)
  addLog("System Boot: Fetching latest broadcast...");
// (remove this redundant log — the loading animation covers it)
// REPLACE
  // (delete this line)

// SEARCH (line 96)
    addLog("Data received successfully.");
// REPLACE
    addLog(T.data_ok);

// SEARCH (line 709)
            addLog("Pipeline success. Rendering...");
// REPLACE
            addLog(T.render);
```

**Step 15: Update the `translateAQIText` function** — it currently translates Chinese → English. With `lang=zh-TW` data is already Chinese; with `lang=en` the EN summarizer returns English directly. Make it a pass-through:
```javascript
// SEARCH
function translateAQIText(status) {
  if (!status) return '';
  const map = {
    '良好': 'Good',
    '普通': 'Moderate',
    ...
  };
  return map[status] || status;
}
// REPLACE
function translateAQIText(status) {
  // AQI status is now returned in Traditional Chinese directly — pass through.
  return status || '';
}
```

**Step 16: Commit**
```
git add web/static/app.js
git commit -m "feat(i18n): TRANSLATIONS const with EN+ZH maps, applyLanguage() re-renders on toggle"
```

---

## Task 8: Local Browser TTS (Web Speech API) — `app.js`

**Files:**
- Modify: `web/static/app.js` — add TTS helper after the audio player section in `renderNarrationView`

The server-side Cloud TTS still generates `full_audio_url` (used in `<audio>` player). This task adds a **supplementary** local TTS button that uses the browser's Web Speech API with a `zh-TW` voice for instant low-latency playback without waiting for the audio file.

**Step 1: Add TTS helper function** — append to the bottom of `app.js`:

```javascript
// ── Local TTS (Web Speech API) ─────────────────────────────────────────────
function initLocalTTS(text) {
  if (!('speechSynthesis' in window)) return; // Silently degrade

  const synth = window.speechSynthesis;

  function speak() {
    synth.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = getLang();  // reads localStorage — matches the active toggle
    utter.rate = 0.95;

    // Prefer a voice matching the active language
    const lang = getLang();
    const voices = synth.getVoices();
    const matchVoice = voices.find(v => v.lang === lang) ||
                       voices.find(v => v.lang.startsWith(lang.split('-')[0]));
    if (matchVoice) utter.voice = matchVoice;

    synth.speak(utter);
  }

  // voices may not be loaded immediately — wait if needed
  if (synth.getVoices().length > 0) {
    speak();
  } else {
    synth.addEventListener('voiceschanged', speak, { once: true });
  }
}
```

**Step 2: Add local TTS button to `renderNarrationView`**

After the `// Audio Player` block (line ~521), add:
```javascript
  // Local TTS button (Web Speech API)
  const ttsBtn = document.getElementById('local-tts-btn');
  if (ttsBtn && data.full_text) {
    ttsBtn.onclick = () => initLocalTTS(data.full_text);
    ttsBtn.style.display = 'block';
  }
```

**Step 3: Add the button to `dashboard.html`** — inside `#view-narration`, after the `<audio>` player:
```html
<!-- SEARCH -->
          <div class="audio-controls">
            <audio id="audio-player-native" controls class="native-audio"></audio>
          </div>
<!-- REPLACE -->
          <div class="audio-controls">
            <audio id="audio-player-native" controls class="native-audio"></audio>
            <button id="local-tts-btn" class="rp-btn" style="display:none">
              🔊 本機語音播放
            </button>
          </div>
```

**Step 4: Manual verification**
1. Open dashboard at `http://localhost:8080`
2. Navigate to **每日天氣廣播** (Narration) tab
3. Wait for data to load
4. Click **🔊 本機語音播放**
5. Expected: browser speaks the Chinese narration text in Mandarin. If no `zh-TW` voice is installed, button is visible but no audio plays (silent degrade — acceptable for Phase 1)

**Step 5: Commit**
```
git add web/static/app.js web/templates/dashboard.html
git commit -m "feat(tts): add local Web Speech API zh-TW TTS button with graceful degrade"
```

---

## End-to-End Verification

**Run full test suite:**
```
pytest tests/ -v
```
Expected: all existing tests PASS, new tests PASS.

**Manual smoke test (local server):**
```
python app.py
# or
.\run_local.ps1
```
1. Open `http://localhost:8080` — default is 中文
2. All sidebar labels in Chinese: 功能, 生活建議, 廣播稿, 天氣總覽
3. Gauge labels in Chinese: 地面狀況, 風速, 濕度, 空氣品質…
4. Lifestyle cards have Chinese titles and Chinese body text
5. Click **重新整理** → loading steps appear in Chinese
6. After load, narration text is in Traditional Chinese
7. **Toggle to EN** → all static labels switch to English immediately (no reload)
8. Click **Refresh** → narration fetched in English, lifestyle cards in English
9. **Toggle back to 中文** → static labels switch back. Click **重新整理** → narration in Chinese again
10. **Cache namespace test:** After ZH generation, switch to EN and refresh → server log must show no cache HIT (`en_` key). Second EN refresh → `Narration cache HIT: en_shulin_...`

---

## Execution Options

Plan is saved to `docs/plans/2026-02-24-chinese-localization-plan.md`.

**1. Subagent-Driven (this session)** — Dispatch fresh subagent per task, review between tasks, fast iteration.

**2. Parallel Session (separate)** — Open new session with `executing-plans`, batch execution with checkpoints.

Which approach?


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


# EN / 中文 Toggle Bugfix Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix three regressions where EN/中文 toggle has no effect on static UI text, cloud-cover labels, and view headings.

**Architecture:**
The `TRANSLATIONS` constant and `applyLanguage(lang)` in `app.js` already exist and correctly swap the `T` map on toggle. However, three categories of strings were never wired to `T` or remain hardcoded in `dashboard.html` HTML that `applyLanguage()` does not touch. Fix strategy: (1) drive static HTML strings through JS at toggle time using `data-i18n` attribute lookups; (2) add missing translation keys; (3) normalize cloud-cover labels from the API to locale-neutral icon keys so EN mode shows English.

**Tech Stack:** Vanilla JS, Jinja2 HTML templates — no library additions needed.

---

## Bug Inventory

| # | Symptom | Root Cause |
|---|---|---|
| 1 | Left panel nav labels (功能, 生活建議, 廣播稿, 天氣總覽) and right panel labels (系統控制, 系統記錄) stay Chinese in EN mode | Hard-coded Chinese text in `dashboard.html`; `applyLanguage()` does not update them |
| 2 | Cloud coverage value in Dashboard / current-conditions hero (`cur-weather-text`) shows Chinese in EN mode | `data.weather_text` from the API is always Chinese (e.g., `"多雲"`) regardless of `lang`; no translation mapping exists in `app.js` |
| 3 | View `<h1>` headings (生活指南, 每日天氣廣播, 天氣儀表板) and `<h2>` section titles (24 小時預報, 七日預報) stay Chinese in EN mode | Hardcoded Chinese HTML; `applyLanguage()` does not touch them |

---

## Task G: Fix Static Panel Labels — `dashboard.html` + `app.js`

**Files:**
- Modify: `web/templates/dashboard.html`
- Modify: `web/static/app.js`

### Step 1: Add `data-i18n` attributes to static HTML strings

In `web/templates/dashboard.html`, annotate every string that must switch language with a `data-i18n` key. Apply the following changes:

```html
<!-- SEARCH -->
<p class="nav-section-label">功能</p>
<!-- REPLACE -->
<p class="nav-section-label" data-i18n="nav_section">功能</p>

<!-- SEARCH -->
<span>生活建議</span>
<!-- REPLACE -->
<span data-i18n="nav_lifestyle">生活建議</span>

<!-- SEARCH -->
<span>廣播稿</span>
<!-- REPLACE -->
<span data-i18n="nav_narration">廣播稿</span>

<!-- SEARCH -->
<span>天氣總覽</span>
<!-- REPLACE -->
<span data-i18n="nav_dashboard">天氣總覽</span>

<!-- SEARCH -->
<p class="rp-label">系統控制</p>
<!-- REPLACE -->
<p class="rp-label" data-i18n="system_controls">系統控制</p>

<!-- SEARCH -->
<span>系統記錄</span>   <!-- inside .rp-log-header -->
<!-- REPLACE -->
<span data-i18n="system_log">系統記錄</span>
```

### Step 2: Add missing translation keys to `TRANSLATIONS` in `app.js`

In the `en` block (after `step7`):

```javascript
// SEARCH
    step7: 'Finalizing…',
  },
  'zh-TW': {
// REPLACE
    step7: 'Finalizing…',
    // Static panel labels
    nav_section: 'Views',
    nav_lifestyle: 'Lifestyle',
    nav_narration: 'Narration',
    nav_dashboard: 'Dashboard',
    system_controls: 'System Controls',
    system_log: 'System Log',
    // View headings
    h1_lifestyle: 'Lifestyle Guide',
    h1_narration: 'Weather Briefing',
    h1_dashboard: 'Weather Dashboard',
    h2_24h: '24-Hour Forecast',
    h2_7day: '7-Day Forecast',
  },
  'zh-TW': {
```

In the `zh-TW` block (after `step7`):

```javascript
// SEARCH
    step7: '最終處理中…',
  },
};
// REPLACE
    step7: '最終處理中…',
    // Static panel labels
    nav_section: '功能',
    nav_lifestyle: '生活建議',
    nav_narration: '廣播稿',
    nav_dashboard: '天氣總覽',
    system_controls: '系統控制',
    system_log: '系統記錄',
    // View headings
    h1_lifestyle: '生活指南',
    h1_narration: '每日天氣廣播',
    h1_dashboard: '天氣儀表板',
    h2_24h: '24 小時預報',
    h2_7day: '七日預報',
  },
};
```

### Step 3: Wire `applyLanguage()` to update `data-i18n` elements and view headings

In `app.js`, extend `applyLanguage()` to sweep all `data-i18n` elements and the view headings:

```javascript
// SEARCH
function applyLanguage(lang) {
  T = TRANSLATIONS[lang] || TRANSLATIONS['zh-TW'];
  // Update LOADING_MSGS in-place for next animation run
  LOADING_MSGS.splice(0, LOADING_MSGS.length,
    T.step1, T.step2, T.step3, T.step4, T.step5, T.step6, T.step7);

  // Re-render labels if data is already loaded
  if (broadcastData) render(broadcastData);
}
// REPLACE
function applyLanguage(lang) {
  T = TRANSLATIONS[lang] || TRANSLATIONS['zh-TW'];

  // Update LOADING_MSGS in-place for next animation run
  LOADING_MSGS.splice(0, LOADING_MSGS.length,
    T.step1, T.step2, T.step3, T.step4, T.step5, T.step6, T.step7);

  // Swap all data-i18n elements
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    if (T[key] !== undefined) el.textContent = T[key];
  });

  // Swap view headings (hardcoded in HTML, no data-i18n — update by element ID)
  setText('view-heading-lifestyle', T.h1_lifestyle);
  setText('view-heading-narration', T.h1_narration);
  setText('view-heading-dashboard', T.h1_dashboard);
  setText('section-heading-24h', T.h2_24h);
  setText('section-heading-7day', T.h2_7day);

  // Re-render data labels if data is already loaded
  if (broadcastData) render(broadcastData);
}
```

### Step 4: Add IDs to view headings in `dashboard.html`

```html
<!-- SEARCH -->
<div id="view-lifestyle" class="view-container active">
  <header class="view-header">
    <h1>生活指南</h1>
<!-- REPLACE -->
<div id="view-lifestyle" class="view-container active">
  <header class="view-header">
    <h1 id="view-heading-lifestyle">生活指南</h1>

<!-- SEARCH -->
<div id="view-narration" class="view-container">
  <header class="view-header">
    <h1>每日天氣廣播</h1>
<!-- REPLACE -->
<div id="view-narration" class="view-container">
  <header class="view-header">
    <h1 id="view-heading-narration">每日天氣廣播</h1>

<!-- SEARCH -->
<div id="view-dashboard" class="view-container">
  <header class="view-header">
    <h1>天氣儀表板</h1>
<!-- REPLACE -->
<div id="view-dashboard" class="view-container">
  <header class="view-header">
    <h1 id="view-heading-dashboard">天氣儀表板</h1>

<!-- SEARCH -->
<h2 class="section-title">24 小時預報</h2>
<!-- REPLACE -->
<h2 class="section-title" id="section-heading-24h">24 小時預報</h2>

<!-- SEARCH -->
<h2 class="section-title">七日預報</h2>
<!-- REPLACE -->
<h2 class="section-title" id="section-heading-7day">七日預報</h2>
```

### Step 5: Run tests

```
pytest tests/ -v
```

Expected: all tests PASS (no Python logic changed).

### Step 6: Manual verification (static labels)

1. Start server: `.\run_local.ps1`
2. Open `http://localhost:8080`
3. Default lang is `zh-TW` (from `localStorage` or radio default) — all labels show Chinese ✓
4. In Right Panel, click **EN** radio
5. Verify instantly (no page reload needed):
   - Left sidebar: section label → `Views`; buttons → `Lifestyle`, `Narration`, `Dashboard`
   - Right panel: `System Controls`, `System Log`
   - View h1 (whichever is active): switches to English heading
   - Switch to each view and confirm heading switches
6. Click **中文** radio → all revert to Chinese ✓

### Step 7: Commit

```bash
git add web/templates/dashboard.html web/static/app.js
git commit -m "fix(i18n): wire data-i18n sweep + view heading IDs so EN toggle updates all static labels"
```

---

## Task H: Fix Cloud-Cover Text in EN Mode — `app.js`

**Files:**
- Modify: `web/static/app.js`

The `cur-weather-text` element displays `data.weather_text` from the API. That field is always in Chinese (e.g., `"多雲"`, `"陰天"`) because the CWA API returns Chinese strings. In EN mode this must be translated to English.

### Step 1: Add a cloud-cover translation map to `app.js`

Insert after the `ICONS` constant (around line 59):

```javascript
// ── Weather text localisation map (CWA API → English) ──────────────────────
const WEATHER_TEXT_EN = {
  '晴': 'Sunny',
  '晴時多雲': 'Partly Cloudy',
  '多雲時晴': 'Mostly Sunny',
  '多雲': 'Cloudy',
  '陰': 'Overcast',
  '陰時多雲': 'Mostly Cloudy',
  '多雲時陰': 'Mostly Cloudy',
  '短暫雨': 'Brief Rain',
  '短暫陣雨': 'Brief Showers',
  '陣雨': 'Showers',
  '雨': 'Rain',
  '大雨': 'Heavy Rain',
  '豪雨': 'Torrential Rain',
  '短暫雷陣雨': 'Brief Thunderstorms',
  '雷陣雨': 'Thunderstorms',
  '有霧': 'Foggy',
  '霧': 'Fog',
  '有靄': 'Hazy',
};

function localiseWeatherText(text) {
  if (getLang() === 'en') return WEATHER_TEXT_EN[text] || text;
  return text;
}
```

### Step 2: Apply `localiseWeatherText` in `renderCurrentView`

```javascript
// SEARCH
  setText('cur-weather-text', data.weather_text || '—');
// REPLACE
  setText('cur-weather-text', localiseWeatherText(data.weather_text || '—'));
```

### Step 3: Run tests

```
pytest tests/ -v
```

Expected: all PASS.

### Step 4: Manual verification (cloud cover text)

1. Switch to **EN** radio in right panel
2. Click **Refresh** (or wait for cached data to re-render via `applyLanguage`)
3. In **Weather Dashboard** view, the weather label under the temperature hero should display English (e.g., `Cloudy`, `Partly Cloudy`) instead of Chinese characters
4. Switch back to **中文** → reverts to Chinese `"多雲"` etc. ✓

> **Note:** `applyLanguage()` calls `render(broadcastData)` when data is loaded, so toggling EN without refreshing will also re-render the weather text correctly.

### Step 5: Commit

```bash
git add web/static/app.js
git commit -m "fix(i18n): translate CWA weather_text to English when lang=en using WEATHER_TEXT_EN map"
```

---

## End-to-End Smoke Test

After both tasks are committed, run the full manual checklist:

1. Open `http://localhost:8080` (default: 中文)
2. **Left panel** shows: 功能 / 生活建議 / 廣播稿 / 天氣總覽 ✓
3. **Right panel** shows: 系統控制 / 系統記錄 ✓
4. **View h1** (each tab) shows Chinese heading ✓
5. **Section h2** (24 小時預報, 七日預報) in Chinese ✓
6. **Weather text** shows Chinese cloud label ✓
7. Toggle to **EN**:
   - Left panel labels → English ✓
   - Right panel labels → English ✓
   - View headings → English ✓
   - Section headings → English ✓
   - Weather text → English (after re-render) ✓
8. Toggle back to **中文** → all revert ✓

---

## Execution Options

Plan saved to `docs/plans/2026-02-27-lang-toggle-bugfix-plan.md`.

**1. Subagent-Driven (this session)** — Dispatch Task G subagent, review, then Task H subagent.

**2. Parallel Session (separate)** — Open new session with `executing-plans` and pass this file as context.

Which approach?

---

## Task I: Fix Dark / Light Mode on Left & Right Panels — `style.css`

**Files:**
- Modify: `web/static/style.css`

### Root Cause

In `:root`, the sidebar and right-panel background variables are declared as static dark-navy values:

```css
--sidebar-bg: #1a2235;
--rp-bg:      #1a2235;
```

The `html.dark` block **never overrides these variables**, so toggling dark mode has zero visual effect on `.sidebar` (which uses `var(--sidebar-bg)`) and `.right-panel` (which uses `var(--rp-bg)`). Both panels show the same dark navy in both light and dark mode.

The `html.dark .right-panel` rule that exists only adjusts the right panel's background to `#111a2a` via a direct property, but the sidebar has no matching override at all.

### Step 1: Define proper light-mode palette values in `:root`

Change the variable declarations in `:root` from dark-navy to light-mode values:

```css
/* SEARCH */
  --sidebar-bg: #1a2235;
  --sidebar-hover: #232f48;
  --sidebar-active: #2a3a5e;
  --sidebar-text: #8fa3c0;
  --sidebar-active-text: #ffffff;
  --rp-bg: #1a2235;
/* REPLACE */
  /* Light mode sidebar / right panel */
  --sidebar-bg: #2c3e6b;
  --sidebar-hover: #374d7f;
  --sidebar-active: #4a5f9a;
  --sidebar-text: #b0c4de;
  --sidebar-active-text: #ffffff;
  --rp-bg: #2c3e6b;
```

> **Why #2c3e6b?** It is visibly lighter and more blue-toned than the pure dark navy `#0f1520`, so users see a clear difference between light and dark mode on the panels while keeping the professional dark-sidebar aesthetic.

### Step 2: Add `html.dark` overrides to restore the dark values

Append to the `html.dark { … }` block in `style.css` (around line 1539):

```css
/* SEARCH */
html.dark {
  --main-bg: #0f1520;
  --surface: #1a2235;
  --border: #2a3a5e;
  --text: #e0e6f0;
  --muted: #8fa3c0;

  --blue-lt: rgba(77, 124, 254, 0.12);
  --warn-lt: rgba(255, 118, 117, 0.12);
  --ok-lt: rgba(85, 239, 196, 0.12);

  --shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
  --shadow-md: 0 4px 24px rgba(0, 0, 0, 0.35);
}
/* REPLACE */
html.dark {
  --main-bg: #0f1520;
  --surface: #1a2235;
  --border: #2a3a5e;
  --text: #e0e6f0;
  --muted: #8fa3c0;

  /* Restore dark sidebar / right panel */
  --sidebar-bg: #1a2235;
  --sidebar-hover: #232f48;
  --sidebar-active: #2a3a5e;
  --sidebar-text: #8fa3c0;
  --rp-bg: #1a2235;

  --blue-lt: rgba(77, 124, 254, 0.12);
  --warn-lt: rgba(255, 118, 117, 0.12);
  --ok-lt: rgba(85, 239, 196, 0.12);

  --shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
  --shadow-md: 0 4px 24px rgba(0, 0, 0, 0.35);
}
```

### Step 3: Remove the now-redundant `html.dark .right-panel` direct-background override

The existing rule sets a direct `background` value that would conflict with the variable approach:

```css
/* SEARCH — remove this block entirely */
/* Dark mode right panel */
html.dark .right-panel {
  background: #111a2a;
  border-left-color: var(--border);
}
/* REPLACE */
/* Dark mode right panel — border only; background comes from var(--rp-bg) */
html.dark .right-panel {
  border-left-color: var(--border);
}
```

### Step 4: Add the sidebar to the smooth transition list

The sidebar is not in the transition list, so it will flash on toggle instead of animating. Add it:

```css
/* SEARCH */
body,
.main-panel,
.right-panel,
/* REPLACE */
body,
.sidebar,
.main-panel,
.right-panel,
```

### Step 5: Run tests

```
pytest tests/ -v
```

Expected: all PASS (no Python logic changed).

### Step 6: Manual verification

1. Start server: `.\run_local.ps1`
2. Open `http://localhost:8080`
3. Default should be **light mode** (no `dark` class on `<html>`)
   - Left sidebar: medium blue (#2c3e6b) — clearly different from the light main background
   - Right panel: same medium blue
4. Click **深色模式** button in right panel
   - Left sidebar transitions to dark navy (#1a2235)
   - Right panel transitions to dark navy (#1a2235)
   - Main content area darkens as before
5. Click **淺色模式** button
   - Left and right panels lighten back to #2c3e6b
6. Verify transition is smooth (200ms fade, no flash)

### Step 7: Commit

```bash
git add web/static/style.css
git commit -m "fix(theme): define light-mode --sidebar-bg/--rp-bg in :root; restore dark values under html.dark so toggle visibly affects both panels"
```


