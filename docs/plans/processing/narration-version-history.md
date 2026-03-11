# Narration System — Version History

Consolidated record of narration pipeline changes across v5, v6, and v7.

---

## v5 (Legacy — no formal plan doc)

Reconstructed from backward-compatibility code in `narration/llm_prompt_builder.py:404–439` and the observation note in `docs/audit/narration_pipeline_audit.md:220`.

### Paragraph Structure (~7–8 paragraphs)

Garden and commute were separate paragraphs. Meals and climate control were separate paragraphs. No fixed key names are preserved — only the forecast key `p6_forecast` survives in the fallback chain.

### Metadata Keys (v5)

| Key | Notes |
|-----|-------|
| `meals_suggested` | Array of dish names (not a single `meal` string) |
| `gardening_tip_topic` | Garden tip topic string |
| `location_suggested` | Outdoor location string |

These keys appear only in the backward-compat block of `_format_history()` — they were replaced in v6.

### Other Characteristics

- Word count: ~500–700 words (EN)
- Regen cycle: ~7 days, 30km radius
- Max tokens: unknown
- No `rain_gear` boolean in metadata
- No `---CARDS---` JSON block (cards added in v6)

---

## v6

**Documented in:** `docs/audit/narration_pipeline_audit.md`

### Paragraph Structure (6 paragraphs, always present)

| Key | Title | Content | Max sentences |
|-----|-------|---------|---------------|
| `p1_conditions` | Current Conditions & Alerts | Current weather, wardrobe, health alerts, **AQI status** | ≤4 |
| `p2_garden_commute` | Garden & Commute | Gardening tip + both commute legs merged | ≤4 |
| `p3_outdoor` | Outdoor with Dad | Activity recommendation; Parkinson's safety phrasing | ≤4 |
| `p4_meal_climate` | Meals & Climate Control | Meal suggestion + HVAC advice (each independently skippable) | ≤4 |
| `p5_forecast` | 24-Hour Forecast | Weather narrative over next 24h | ≤5 |
| `p6_accuracy` | Forecast Accuracy | Comparison to **yesterday only** | ≤2 |

### Changes from v5

- 7–8 paragraphs → 6
- **Merged:** Garden + Commute → `p2_garden_commute`
- **Merged:** Meals + Climate → `p4_meal_climate`
- **Consolidated:** Cardiac and Ménière's alerts moved into P1
- **Added:** Ménière's barometric/humidity alert detection
- **Added:** `rain_gear` boolean to metadata
- **Added:** `---CARDS---` JSON block (8→9 keys by end of v6)
- **Changed:** Single `meal` string replacing `meals_suggested` array
- **Changed:** Regen cycle 7 days → 14 days; radius 30km → 50km
- Outdoor paragraph now skippable if weather is unsafe

### Metadata Schema (v6) — 12 keys

```json
{
  "wardrobe":         "1-sentence",
  "rain_gear":        true | false,
  "commute_am":       "1-sentence",
  "commute_pm":       "1-sentence",
  "meal":             "pinyin dish name or null",
  "outdoor":          "1-sentence or null",
  "garden":           "3-5 word topic",
  "climate":          "1-sentence or null",
  "cardiac_alert":    true | false,
  "menieres_alert":   true | false,
  "forecast_oneliner":"bottom-line from P5",
  "accuracy_grade":   "spot on / close / off / first broadcast"
}
```

### Cards Schema (v6) — 9 keys

```json
{
  "wardrobe":    "1 sentence",
  "rain_gear":   "1 sentence",
  "commute":     "2 sentences",
  "meals":       "1 sentence",
  "hvac":        "1 sentence",
  "garden":      "2 sentences",
  "outdoor":     "2 sentences (includes Parkinson's safety language)",
  "air_quality": "1 sentence",
  "alert": { "text": "1–2 sentences", "level": "INFO | WARNING | CRITICAL" }
}
```

### Other Characteristics

- Word count: 320–350 words (EN) / 420–460 字 (ZH)
- Max tokens: 2000 (all runs)
- Regen cycle: every 14 days, 50km radius

### Bugs Fixed (v6 audit — all fixed 2026-03-07)

See `docs/audit/narration_pipeline_audit.md` for full detail.

| Bug | File | Fix |
|-----|------|-----|
| `outdoor_index` key mismatch (`score` → `overall_score`, etc.) | `web/routes.py` | Corrected key names; derived `best_window` and `top_activity` |
| `beaufort_desc` not set on `current` | `data/weather_processor.py` | Added alias `result["beaufort_desc"] = result["wind_text"]` |
| Commute/HVAC/Meals card fell back to full merged paragraph text | `web/routes.py` | Removed `or paragraphs.get(...)` short-circuit; computed fallbacks used instead |

---

## v7 (Current)

**Plan doc:** `docs/plans/processing/2026-03-07-narration-v7-restructure.md`
**Implemented:** 2026-03-07

### Motivation

The v6 opening paragraph (P1) was dense because it carried AQI on top of conditions and health alerts. P3 (outdoor) and P4 (meal) were two short paragraphs that read better merged. P5 (forecast) and P6 (accuracy) were disconnected; merging them gives one coherent forward-looking paragraph.

### Paragraph Structure (5 paragraphs, always present)

| Key | Title | Content | Max sentences |
|-----|-------|---------|---------------|
| `p1_conditions` | Current & Outlook | Current conditions, wardrobe, health alerts — **no AQI** | ≤4 |
| `p2_garden_commute` | Garden & Commute | Gardening tip + commute summary | ≤4 |
| `p3_outdoor_meal` | Outdoor & Meal | Outdoor activity + one dish | ≤4 |
| `p4_hvac_air` | HVAC & Air Quality | HVAC advice + AQI/window guidance | ≤2 |
| `p5_forecast_accuracy` | Forecast & Accuracy | 24h forecast (≤3 sent) + accuracy review (1 sent) | ≤4 |

### Changes from v6

| Area | v6 | v7 |
|------|----|----|
| Paragraph count | 6 | 5 |
| AQI location | P1 | P4 |
| Outdoor + Meal | separate P3 / P4 | merged → `p3_outdoor_meal` |
| Forecast + Accuracy | separate P5 / P6 | merged → `p5_forecast_accuracy` |
| Parkinson's phrasing | in P3 narration + outdoor card | **removed** |
| Accuracy coverage | yesterday only | last 3 days |
| Word count (EN) | 320–350 | 250–280 |
| Word count (ZH) | 420–460 字 | 340–370 字 |
| Max tokens (regular) | 2000 | **1000** |
| Max tokens (regen) | 2000 | 2000 (unchanged) |

### Metadata Schema (v7) — 12 keys (unchanged from v6)

```json
{
  "wardrobe":         "1-sentence",
  "rain_gear":        true | false,
  "commute_am":       "1-sentence",
  "commute_pm":       "1-sentence",
  "meal":             "single dish name in pinyin, or null",
  "outdoor":          "1-sentence Dad outing summary, or null",
  "garden":           "3-5 word gardening tip topic",
  "climate":          "1-sentence climate control summary, or null",
  "cardiac_alert":    true | false,
  "menieres_alert":   true | false,
  "forecast_oneliner":"bottom-line takeaway from P5",
  "accuracy_grade":   "spot on / close / off / first broadcast"
}
```

### Cards Schema (v7) — 9 keys (content constraints tightened)

```json
{
  "wardrobe":    "Exactly 1 sentence. Apparent temperature only. No rain/rain-gear mention.",
  "rain_gear":   "Exactly 1 sentence. Umbrella, raincoat, or boots.",
  "commute":     "Exactly 2 sentences. Morning and evening. Must use exact HINTS hazards.",
  "meals":       "Exactly 1 sentence. Weather-mood dish.",
  "hvac":        "Exactly 1 sentence. Must use exact HVAC mode from HINTS.",
  "garden":      "Exactly 2 sentences. Garden tasks and soil/plant care.",
  "outdoor":     "Exactly 2 sentences. MUST use exact top activity from HINTS. Reflect provided outdoor grade.",
  "air_quality": "Exactly 1 sentence. Good/Moderate/Unhealthy advisory.",
  "alert": { "text": "1–2 sentences. Health + commute only — NOT air quality.", "level": "INFO | WARNING | CRITICAL" }
}
```

### Files Modified

| File | Change |
|------|--------|
| `narration/llm_prompt_builder.py` | v7 module docstring; new 5-paragraph STRUCTURE block in EN + ZH prompts; word count; `_assign_paragraphs` keys; `_format_history` forecast key fallback; outdoor card description |
| `web/routes.py` | `_slice_narration()` paragraph list (6 → 5, new keys + titles) |
| `config.py` | `GEMINI_MAX_TOKENS` 2000 → 1000; `CLAUDE_MAX_TOKENS` 2000 → 1000; added `*_REGEN` variants at 2000 |
| `narration/gemini_client.py` | `max_tokens` kwarg; uses `max_tokens or GEMINI_MAX_TOKENS` |
| `narration/claude_client.py` | `max_tokens` kwarg; uses `max_tokens or CLAUDE_MAX_TOKENS` |
| `backend/pipeline.py` | Detects `regenerate_meal_lists`; passes regen token limit to client |

### Backward Compatibility

History records written under v5 or v6 still load correctly. `_format_history()` uses a fallback chain:

```python
forecast_key = (
    "p5_forecast_accuracy" if "p5_forecast_accuracy" in paras   # v7
    else "p5_forecast"     if "p5_forecast"          in paras   # v6
    else "p6_forecast"                                           # v5
)
```

v5 metadata fields (`meals_suggested`, `gardening_tip_topic`, `location_suggested`) are also handled in `_format_history()` so old history entries contribute to the accuracy and continuity sentences without any data migration.

---

## Summary Table

| | v5 | v6 | v7 |
|-|----|----|-----|
| Paragraphs | ~7–8 | 6 | **5** |
| EN word count | ~500–700 | 320–350 | **250–280** |
| ZH word count | — | 420–460 字 | **340–370 字** |
| AQI location | — | P1 | **P4** |
| Accuracy coverage | — | yesterday | **last 3 days** |
| Max tokens (regular) | — | 2000 | **1000** |
| Max tokens (regen) | — | 2000 | 2000 |
| Parkinson's phrasing | yes | yes | **removed** |
| Regen cycle | ~7 days | 14 days | 14 days |
| Regen radius | 30 km | 50 km | 50 km |
| `---CARDS---` block | no | yes (9 keys) | yes (9 keys, tightened) |
| Single `meal` field | no (array) | yes | yes |
