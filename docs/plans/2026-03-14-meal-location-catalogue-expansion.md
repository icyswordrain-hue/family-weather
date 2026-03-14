# Meal & Location Catalogue Expansion + Opus Regen

**Date:** 2026-03-14

## Problem

The meal recommendation system had ~22 dishes across 4 hard-coded mood buckets in `meal_classifier.py`, and the location catalogue had 20 spots across 4 similarly hard-coded buckets in `locations.json`. Items were locked to a single mood bucket, and a single dish was selected randomly before being handed to the LLM — leaving Claude no room to reason about which option best fit today's conditions.

## Solution

### Flat catalogue with multi-mood tags

Both catalogues were restructured as flat JSON arrays. Each item carries a `moods` array so a dish or location can belong to more than one weather bucket (e.g., 牛肉麵 tagged for both `Cool & Damp` and `Cold`).

**Meal schema** (`data/meals.json`):
```json
{
  "name": "牛肉麵 (niú ròu miàn)",
  "moods": ["Cool & Damp", "Cold"],
  "description": "Slow-braised beef shank in rich soy or clear broth — Taiwan's national dish",
  "tags": ["noodles", "beef", "braised", "comfort"]
}
```

**Location schema** (`data/locations.json`):
```json
{
  "name": "Shulin Riverside Greenway",
  "moods": ["Nice", "Warm"],
  "activity": "cycling / jogging",
  "surface": "paved",
  "lat": 24.987, "lng": 121.428,
  "notes": "Local favourite, ~5km flat loop, shaded sections, water stations"
}
```

### Catalogue size

| Domain | Before | After |
|--------|--------|-------|
| Meals  | ~22    | 100   |
| Locations | 20  | 100   |

### LLM selection (Opus on regen)

Previously the pipeline randomly pre-selected one dish and passed it to the LLM. Now the **full filtered pool** (matching the current mood, excluding recent repeats) is passed to the model, and the LLM picks the best fit given the weather context.

Claude Opus 4.6 is used for regen sessions only — regular daily narration continues to use Sonnet 4.6 → Haiku 4.5. This keeps costs low while giving Opus the opportunity to make a more considered selection when the full expanded catalogue is presented.

### Regen cycle

Changed from every 14 days to every **30 days** — monthly, matching the pace at which seasonal meal and location preferences actually shift.

## Files Changed

| File | Change |
|------|--------|
| `data/meals.json` | New — 100-item flat catalogue |
| `data/locations.json` | Restructured — 100-item flat list, `moods` array added |
| `data/meal_classifier.py` | Loads from `meals.json`, filters by mood tag; returns `all_meals_detail` |
| `data/location_loader.py` | Returns `list[dict]` instead of `dict[str, list]` |
| `data/outdoor_scoring.py` | `_classify_outdoor_mood()` filters flat list by mood tag |
| `data/weather_processor.py` | Passes full filtered pool as `top_suggestions` / `top_locations` |
| `narration/llm_prompt_builder.py` | P3 instructions updated (EN + ZH) to direct LLM to reason over the full pool |
| `config.py` | `CLAUDE_REGEN_MODEL = claude-opus-4-6`; `REGEN_CYCLE_DAYS` 14 → 30 |
| `backend/pipeline.py` | Passes `model_override=CLAUDE_REGEN_MODEL` on regen sessions only |
| `tests/test_location_loader.py` | Updated for flat list structure; asserts 100-item count |

## Model Routing

```
Daily narration:   Sonnet 4.6  →  Haiku 4.5 fallback
Regen session:     Opus 4.6    →  Sonnet 4.6 fallback  (once per month)
Chat:              Haiku 4.5   (unchanged)
```
