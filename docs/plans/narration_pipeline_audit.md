# Narration Pipeline Audit
_Audited: 2026-03-07 — Bugs fixed: 2026-03-07_

---

## 1. Data Fetch → LLM: Is Anything Lost?

**Short answer: No meaningful data is lost.**

`build_prompt()` in [`narration/llm_prompt_builder.py:237`](../../narration/llm_prompt_builder.py#L237) does:
```python
data_text = json.dumps(processed_data, ensure_ascii=False, indent=2)
```
The entire `processed_data` dict is sent verbatim as the user message. Anything in `processed_data` is automatically available to the LLM.

### Sources fetched and confirmed present in `processed_data`

| Source | Key in processed_data |
|---|---|
| CWA current conditions (Shulin/Xindian fallback) | `current` |
| CWA 36h township forecast (樹林區 + 板橋區) | `forecast_segments` |
| CWA 7-day forecast | `forecast_7day` |
| MOENV realtime AQI (Tucheng) | `aqi_realtime` |
| MOENV AQI forecast (北部空品區) | `aqi_forecast` |
| MOENV hourly AQI history | `aqi_forecast.hourly` |
| Station history (pressure delta, Ménière's) | drives `menieres_alert` |
| Conversation history (last 3 days) | `history` param to `build_prompt()`, formatted in `HISTORY:` block |
| Commute windows | `commute.morning`, `commute.evening` |
| Meal mood + suggestions | `meal_mood` |
| Location recommendations | `location_rec.top_locations` |
| Climate control recommendations | `climate_control` |
| Outdoor activity index (per segment) | `outdoor_index.segments` |
| Per-activity scores | `outdoor_index.activities` |
| Heads-up alerts | `heads_ups` |
| Transition detections | `transitions` |
| Solar times | `solar` |
| Cardiac / Ménière's alerts | `cardiac_alert`, `menieres_alert` |

### Fields fetched but not in `processed_data` (not reaching LLM)

| Field | Status | Why it's fine |
|---|---|---|
| Raw CWA `Wx` integer code | Not in processed_data | Replaced by `Wx_text` and `cloud_cover` descriptors |
| `_stale: True` flag | Pipeline log only | Not useful for narration |
| Cache timestamps | Status NDJSON row only | Not useful for narration |
| Station fallback reason | Log only | Not useful for narration |

### Fields in `processed_data` but underused by LLM prompt

| Field | Location | Prompt guidance |
|---|---|---|
| `current.pm10`, `current.o3` | Set from MOENV realtime | Prompt doesn't mention them; rarely narrated |
| `aqi_forecast.content` | Full MOENV narrative text | Prompt only guides LLM to use `aqi` level + `status`; full content available if LLM chooses |
| `outdoor_index.activities` | Per-activity scores (walking, jogging, etc.) | Prompt doesn't reference; LLM gets it but may not use it |

---

## 2. LLM Output Schema

The v6 system prompt asks for this exact structure:

### Paragraphs (plain text, always 6)
- **P1** — Current Conditions & Alerts
- **P2** — Garden & Commute (merged)
- **P3** — Outdoor with Dad
- **P4** — Meals & Climate Control (merged)
- **P5** — 24-Hour Forecast
- **P6** — Forecast Accuracy vs. yesterday

### `---METADATA---` JSON (12 keys)
```json
{
  "wardrobe": "1-sentence",
  "rain_gear": true | false,
  "commute_am": "1-sentence",
  "commute_pm": "1-sentence",
  "meal": "pinyin dish name or null",
  "outdoor": "1-sentence or null",
  "garden": "3-5 word topic",
  "climate": "1-sentence or null",
  "cardiac_alert": true | false,
  "menieres_alert": true | false,
  "forecast_oneliner": "bottom-line from P5",
  "accuracy_grade": "spot on / close / off / first broadcast"
}
```

### `---CARDS---` JSON (9 keys)
```json
{
  "wardrobe": "1 sentence",
  "rain_gear": "1 sentence",
  "commute": "2 sentences",
  "meals": "1 sentence",
  "hvac": "1 sentence",
  "garden": "2 sentences",
  "outdoor": "2 sentences",
  "air_quality": "1 sentence",
  "alert": { "text": "1-2 sentences", "level": "INFO|WARNING|CRITICAL" }
}
```

### `---REGEN---` JSON (every 14 days)
Meals by mood category + outdoor locations by mood — triggers meal/location database refresh.

### Parsing
`parse_narration_response()` at [`narration/llm_prompt_builder.py:265`](../../narration/llm_prompt_builder.py#L265) correctly splits on `---METADATA---`, `---CARDS---`, `---REGEN---` and JSON-decodes each section.

---

## 3. Bugs Found

### BUG 1 — `outdoor_index` key mismatch — **MEDIUM** ✅ Fixed

**File:** [`web/routes.py`](../../../web/routes.py)

`_slice_lifestyle()` was reading wrong keys from `outdoor_index`. Also, `top_activity` and
`best_window` were read from keys that don't exist at all.

**Fix:** Corrected key names and derived missing values:
```python
# Before → After
outdoor_index.get("score")           → outdoor_index.get("overall_score")
outdoor_index.get("grade")           → outdoor_index.get("overall_grade")
outdoor_index.get("label")           → outdoor_index.get("overall_label")
outdoor_index.get("activity_scores") → outdoor_index.get("activities")
# Derived:
best_window  = max(segments, key=lambda k: segments[k]["score"])  # best segment name
top_activity = max(activities, key=lambda k: activities[k]["score"])  # best activity key
```

Note: Per-segment outdoor grades in the **Overview timeline** were already correct —
`_slice_overview()` uses `outdoor_index.get("segments", {})` which was the right key.

---

### BUG 2 — `beaufort_desc` not set on `current` — **LOW** ✅ Fixed

**File:** [`data/weather_processor.py`](../../data/weather_processor.py)

`_format_history()` and `fallback_narrator` both read `current.get("beaufort_desc")` but
`_process_current()` only set `wind_text`, not `beaufort_desc`.

**Fix:** Added alias at end of the wind block in `_process_current()`:
```python
result["beaufort_desc"] = result["wind_text"]  # alias used by _format_history and fallback_narrator
```
History now shows e.g. `Wind=gentle breeze` instead of `Wind=None`.

---

### BUG 3 — Commute / HVAC / Meals fallback text is the wrong paragraph — **LOW** ✅ Fixed

**File:** [`web/routes.py`](../../../web/routes.py)

When an LLM card was missing, all three fell back to full merged paragraphs (P2/P4 in v6
combine two topics). The `if not ...:` blocks below each line already contained correct
computed fallbacks (hazard-based commute text, climate mode HVAC text, meal suggestion text).

**Fix:** Removed the `or paragraphs.get(...)` short-circuit:
```python
# Before → After
commute_text = summaries.get("commute") or paragraphs.get("p2_garden_commute")  →  summaries.get("commute")
hvac_text    = summaries.get("hvac")    or paragraphs.get("p4_meal_climate")    →  summaries.get("hvac")
meals_text   = summaries.get("meals")   or paragraphs.get("p4_meal_climate")    →  summaries.get("meals")
```

---

## 4. Narration Metadata — Verified Correct

`_slice_narration()` at [`web/routes.py:394`](../../../web/routes.py#L394) returns:
```python
{
  "paragraphs": [
    {"key": "p1", "title": "Current & Outlook",    "text": "..."},
    {"key": "p2", "title": "Garden & Commute",     "text": "..."},
    {"key": "p3", "title": "Outdoor with Dad",     "text": "..."},
    {"key": "p4", "title": "Meals & Climate",      "text": "..."},
    {"key": "p5", "title": "Forecast",             "text": "..."},
    {"key": "p6", "title": "Yesterday's Accuracy", "text": "..."},
  ],
  "meta": {"model": "gemini-2.0-flash-001 / ...", "source": "Gemini/Claude/Template"}
}
```

`narration_source` and `narration_model` are set in [`app.py:444–445`](../../app.py#L444) and persisted to history. The narration source badge in the player sheet renders correctly.

---

## 5. Frontend Rendering Summary

| Component | Status | Root cause if broken |
|---|---|---|
| P1–P6 narration text in player sheet | ✅ Correct | — |
| Model/source badge in player sheet | ✅ Correct | — |
| Wardrobe card | ✅ Correct | — |
| Rain gear card | ✅ Correct | — |
| Garden card | ✅ Correct | Falls back to first sentence of P2 |
| Air quality card | ✅ Correct | Falls back to MOENV summary_en/zh |
| Alert card | ✅ Correct | LLM alert + MOENV injection at AQI ≥ 150 |
| Outdoor card text | ✅ Correct | Falls back to P3 paragraph |
| Commute card | ✅ Fixed | Bug 3: removed bad paragraph fallback |
| HVAC card | ✅ Fixed | Bug 3: removed bad paragraph fallback |
| Meals card | ✅ Fixed | Bug 3: removed bad paragraph fallback |
| **Outdoor card grade badge** | ✅ Fixed | Bug 1: `overall_grade` now used |
| **Outdoor card best_window / top_activity** | ✅ Fixed | Bug 1: derived from segments/activities |
| Timeline outdoor grade/label (Overview) | ✅ Correct | Uses `outdoor_index.segments` — correct key |
| Current conditions gauges (hero) | ✅ Correct | All 5-level metrics correct |
| Solar row (hero) | ✅ Correct | `solar` flows correctly |
| AQI gauge + pm25/pm10 sub-label (hero) | ✅ Correct | `aqi_realtime` passed directly to `_slice_current` |
| P6 wind context in history | ✅ Fixed | Bug 2: `beaufort_desc` alias added to `current` |

---

## 6. Observations (No Bug, Worth Noting)

- **MOENV warning injection** ([`web/routes.py:340–345`](../../../web/routes.py#L340)): threshold is AQI ≥ 150 with Chinese-only keyword gate. MOENV content is always in Chinese in practice so this works, but English-language warning strings would never match.
- **`aqi_forecast.content`** is passed to the LLM but the system prompt doesn't explicitly tell it to use the full narrative. The LLM may draw from it implicitly.
- **History backward-compat** ([`llm_prompt_builder.py:365`](../../narration/llm_prompt_builder.py#L365)): old v5 history used `p6_forecast`; code correctly checks `p5_forecast` first, then falls back to `p6_forecast`.
