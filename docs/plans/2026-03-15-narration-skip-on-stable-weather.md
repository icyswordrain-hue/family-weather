# Narration Skip on Stable Weather

## Goal
Reduce LLM API costs by skipping narration regeneration (and TTS synthesis) when weather conditions haven't meaningfully changed since the previous broadcast.

## Problem
The existing `_conditions_changed()` function (AT ±3°C, rain toggle, dew point ±3°C) only gated the **midday** slot, skipping the entire pipeline. Morning, evening, and overnight refreshes always triggered LLM calls. The 30-minute TTL cache in `backend/cache.py` helped but expired regardless of whether weather actually changed.

## Solution
Generalized the condition-change check to gate **all narration calls**, not just midday. After weather data is processed (step 3) but before narration (step 4), the pipeline:

1. Loads the previous broadcast for the same date via `load_broadcast(date_str)`
2. Compares `processed["current"]` against the previous broadcast's `processed_data["current"]` using the same `_conditions_changed()` thresholds
3. If unchanged and not a regen cycle → reuses previous narration text, paragraphs, metadata, summaries, and audio URL (skipping both LLM and TTS)

The processed weather data still updates every run, so the dashboard stays fresh — only the narration + TTS are skipped.

## Thresholds (unchanged from existing midday check)
| Signal | Threshold |
|--------|-----------|
| Apparent temperature (AT) | ≥ 3°C shift |
| Precipitation (RAIN) | Onset or cessation |
| Dew point | ≥ 3°C shift |

## Bypass conditions
- **Regen cycle** (`regenerate_meal_lists=True`): always generates fresh narration
- **No previous broadcast**: first run of the day always generates narration
- **Check failure**: any exception falls through to normal narration generation

## What stayed the same
- **Midday full-pipeline skip** (app.py lines 363–379): more aggressive optimization that skips data fetching entirely
- **30-min TTL cache** (backend/cache.py): secondary fast-path within the LLM call itself
- **Regen cycle**: always bypasses both the cache and this check

## Files changed
- `app.py` — Added pre-narration condition-change check in `_pipeline_steps()` (lines 513–605)
- `tests/test_narration_skip.py` — 8 tests for `_conditions_changed()` thresholds
