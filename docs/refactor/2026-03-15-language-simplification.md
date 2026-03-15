# Language Simplification: Backend Localisation + Prompt Consolidation

## Goal
Reduce frontend complexity by moving all data localisation (metric labels, weather text, locations, slots, transitions) from JavaScript to Python backend slices. Consolidate the duplicated LLM system prompts into a single template.

## Problem
The frontend (`app.js`) contained ~110 lines of translation dictionaries and 4 localisation functions that translated data at render time:
- `WEATHER_TEXT_EN` (17 entries) — CWA Chinese weather text to English
- `LOCATION_EN` (22 entries) — Chinese station/district names to English
- `T.metrics` (~50 entries per language) — metric labels bidirectional
- `T.slots` (5 entries) — segment names
- `T.transitions` (16 entries) — transition display labels
- `localiseMetric()`, `localiseWeatherText()`, `localiseLocation()`, `localisePrecipText()`

This was redundant because `build_slices()` already receives a `lang` parameter and already localises lifestyle card text. Since slices are pre-computed for both languages on every `/api/broadcast` call, the backend can serve fully localised data.

Additionally, `llm_prompt_builder.py` had two nearly identical 70-line system prompts (`V7_SYSTEM_PROMPT` for English, `V7_SYSTEM_PROMPT_ZH` for Chinese) that duplicated the paragraph structure rules and metadata schema.

## Solution

### Part 1: Backend Localisation (`web/routes.py`)

Added translation dicts and helper functions at module level:
- `_WEATHER_TEXT_EN`, `_LOCATION_EN`, `_LOCATION_ZH`, `_METRIC_ZH`, `_SLOT_ZH`, `_TRANSITION_ZH`
- `_loc_metric()`, `_loc_weather()`, `_loc_location()`, `_loc_precip()`, `_loc_slot()`, `_loc_transition()`

Updated `_slice_current()` and `_slice_overview()` to accept `lang` and return pre-localised text:
- `weather_text`, `location`, all metric `.text` fields, `ground_state`, `outdoor.label`
- Timeline `display_name` (localised), `slot_key` (always English for transition lookup)
- `outdoor_label`, `precip_text` in timeline segments
- Transition breaches gain a pre-computed `display` field

`cloud_cover` intentionally stays English — it's used as an icon lookup key in the frontend.

### Part 2: Frontend Cleanup (`web/static/app.js`)

Removed ~110 lines:
- All translation dicts (`WEATHER_TEXT_EN`, `LOCATION_EN`, `T.metrics`, `T.slots`, `T.transitions`)
- All localisation functions
- ~15 render call sites simplified to use slice data directly
- Transition breach rendering reduced from 25-line metric-by-metric switch to 3-line `b.display` loop

Kept: `TRANSLATIONS` for static UI labels (~40 strings per language), `T.cloudCover` for 7-day forecast.

### Part 3: LLM Prompt Consolidation (`narration/llm_prompt_builder.py`)

Replaced two duplicate 70-line prompts with:
- `_V7_LANG_CONFIG` dict — language-specific values (role text, language rules, word count, dish/location naming, metadata examples)
- `_build_v7_prompt(lang)` — assembles the shared template with config values

Structural instructions (P1-P5 paragraph rules, style guidelines) are written once in English. The LLM follows English instructions while outputting in the target language. Backward-compatible aliases preserved.

## Net effect
- **app.js**: -191 lines removed, +9 added (net -182)
- **routes.py**: +66 lines (localisation maps + helpers moved from frontend)
- **llm_prompt_builder.py**: net -91 lines (template dedup)
- **Total**: ~207 fewer lines across the codebase

## Files Changed
- `web/routes.py` — localisation dicts, `_slice_current(lang)`, `_slice_overview(lang)`, `_localise_transitions()`
- `web/static/app.js` — removed translation dicts/functions, simplified render calls
- `narration/llm_prompt_builder.py` — `_V7_LANG_CONFIG`, `_build_v7_prompt()`
