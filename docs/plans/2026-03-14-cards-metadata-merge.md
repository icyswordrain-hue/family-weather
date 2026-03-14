# Fold ---CARDS--- into ---METADATA--- & Deepen Meal/Location Prompts

**Date:** 2026-03-14

## Problem

The LLM prompt required two separate JSON output blocks: `---METADATA---` (compact tracking fields) and `---CARDS---` (verbose card text + taglines). This doubled output token cost (~500 extra tokens per broadcast) and created a fragile parsing pipeline with two JSON blocks to validate. Meanwhile, meal and location recommendations lacked depth — the LLM picked a dish/location by name but never explained *why* it fit the weather, despite having rich `description`, `tags`, and `notes` data available in the input.

## Solution

### 1. Merge CARDS into expanded METADATA

**Before:** LLM outputs `---METADATA---` JSON + `---CARDS---` JSON (two blocks, ~900 tokens total).

**After:** LLM outputs a single `---METADATA---` JSON with card text and tagline fields inlined:

```json
{
  "wardrobe": "1-sentence advice",
  "wardrobe_tagline": "≤8 words",
  "rain_gear": true,
  "rain_gear_text": "1 sentence",
  "meals_text": "1 sentence",
  "meals_tagline": "≤8 words",
  "outdoor_tagline": "≤8 words",
  "garden_text": "2 sentences",
  "garden_tagline": "≤8 words",
  "alert_text": "...",
  "alert_level": "INFO",
  ...
}
```

Cards are derived at parse time by `_derive_cards_from_metadata()` in `llm_prompt_builder.py`. Legacy responses containing `---CARDS---` are still handled gracefully.

### 2. Deepen P3 prompt instructions (EN + ZH)

**Before (meals):** "Choose ONE dish from `top_suggestions`... favour warming dishes when cool and damp."

**After (meals):** "Choose ONE dish from `top_meals_detail`... reference its `description` or `tags` to explain how it complements the weather (e.g., 'cooling jelly clears the heat')."

**Before (locations):** "Choose ONE location from `top_locations`... favour surface type, shade, and accessibility."

**After (locations):** "Choose ONE location from `top_locations`... use its `notes` (shade, surface, terrain) to explain why it suits the conditions."

Card instructions for meals and outdoor also updated to request weather-specific reasoning.

### 3. Supporting fixes

- **Midday skip check** moved from `refresh()` route into `_pipeline_steps()` so it uses the correct storage backend (local file vs GCS) regardless of `RUN_MODE`.
- **TTS local cache** now checks for existing files before re-rendering, and uses date subdirectories matching MODAL layout.
- **Max tokens** reduced: `CLAUDE_MAX_TOKENS` / `GEMINI_MAX_TOKENS` 1500→1000, regen 2500→2000.

## Files changed

| File | Change |
|------|--------|
| `narration/llm_prompt_builder.py` | Removed `---CARDS---` block from EN + ZH prompts; expanded `---METADATA---` with card fields; added `_derive_cards_from_metadata()`; updated P3 instructions for depth |
| `narration/fallback_narrator.py` | Merged card data into metadata output; added `_truncate_tagline()` helper |
| `config.py` | Reduced `MAX_TOKENS` constants (no more CARDS block) |
| `app.py` | Moved midday skip check into `_pipeline_steps()` |
| `narration/tts_client.py` | Added local TTS cache hit check + date subdirectories |

## Data flow (updated)

```
LLM output:
  P1–P5 narration paragraphs
  ---METADATA---
  { ...expanded JSON with card fields... }
  ---REGEN--- (optional, every 14 days)
  { meals/locations refresh }

parse_narration_response():
  1. Split on ---METADATA---
  2. Parse paragraphs → result["paragraphs"]
  3. Handle legacy ---CARDS--- (strip if present)
  4. Parse metadata JSON → result["metadata"]
  5. _derive_cards_from_metadata() → result["cards"]
  6. Parse ---REGEN--- if present → result["regen"]
```
