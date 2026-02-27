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
