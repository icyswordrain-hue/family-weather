# Narration v7 Restructure

**Date:** 2026-03-07
**Status:** Implemented

## Problem

The v6 narration had too much AQI information in P1, making the opening paragraph feel dense. Outdoor and meal content were split across two short paragraphs (P3, P4), and forecast + accuracy were two separate paragraphs (P5, P6) that read as disconnected. Total: 6 paragraphs, 320–350 words.

## Changes

### Paragraph Structure (6 → 5)

| Key | Title | Content | Sentences |
|-----|-------|---------|-----------|
| `p1_conditions` | Current & Outlook | Current conditions, wardrobe, health alerts — **no AQI** | ≤4 |
| `p2_garden_commute` | Garden & Commute | Garden tip + commute summary | ≤4 |
| `p3_outdoor_meal` | Outdoor & Meal | Outdoor activity + one dish | ≤4 |
| `p4_hvac_air` | HVAC & Air Quality | HVAC advice + AQI/window guidance | ≤2 |
| `p5_forecast_accuracy` | Forecast & Accuracy | 24h forecast (≤3 sent) + accuracy review (1 sent) | ≤4 |

**Merges:**
- P3 outdoor + P4 meal → new P3
- P5 forecast + P6 accuracy → new P5

**Moves:**
- AQI status removed from P1 → new P4

**Drops:**
- Parkinson's-specific phrasing from P3 narration and outdoor card

### Word Count

| Variant | Before | After |
|---------|--------|-------|
| EN | 320–350 words | 250–280 words |
| ZH | 420–460字 | 340–370字 |

### Accuracy Review

P5 accuracy now covers **last 3 days** (was yesterday only). History format already supports multiple days — no structural change required, just the prompt and key fallback chain.

### Output Token Budget

| Run type | Limit |
|----------|-------|
| Regular | 1000 (was 2000) |
| Regen (every 14 days) | 2000 (unchanged) |

## Files Modified

| File | Change |
|------|--------|
| `narration/llm_prompt_builder.py` | v7 docstring; new 5-paragraph STRUCTURE in EN + ZH prompts; word count; `_assign_paragraphs` keys; `_format_history` forecast key fallback; outdoor card description |
| `web/routes.py` | `_slice_narration()` paragraph list (6 → 5, new keys + titles) |
| `config.py` | `GEMINI_MAX_TOKENS` 2000→1000; `CLAUDE_MAX_TOKENS` 2000→1000; added `*_REGEN` variants at 2000 |
| `narration/gemini_client.py` | `max_tokens` kwarg; uses `max_tokens or GEMINI_MAX_TOKENS` |
| `narration/claude_client.py` | `max_tokens` kwarg; uses `max_tokens or CLAUDE_MAX_TOKENS` |
| `backend/pipeline.py` | Detects `regenerate_meal_lists`; passes regen token limit to client |

## Backward Compatibility

History records from v6 still load correctly. `_format_history()` checks `p5_forecast_accuracy` first, then falls back to `p5_forecast` and `p6_forecast`, so old history entries contribute to the accuracy sentence without any migration.
