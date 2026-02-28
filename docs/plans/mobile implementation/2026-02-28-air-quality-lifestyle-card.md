# Air Quality Forecast → Lifestyle Card

> **Date:** 2026-02-28
> **Status:** Implemented

---

## The Problem

Air quality forecast data lived in a standalone "Tomorrow's Air Quality" section at the bottom of the **Dashboard view** (`ov-aqi-forecast`). It rendered raw MOENV regional narrative text — Chinese prose from the Ministry of Environment API, untranslated and inconsistent in tone with the rest of the UI.

This was inconsistent with the app's two-view philosophy:

- **Dashboard** — weather metrics, timeline, 24-hour and 7-day forecast
- **Lifestyle** — actionable, health-adjacent guidance: wardrobe, commute, outdoor, meals, HVAC

Air quality tomorrow is an actionable outdoor health consideration, not a raw data metric. It belongs alongside the Outdoor card, not at the bottom of a gauge dashboard.

---

## What Changed

### Lifestyle card — new `air_quality` card

A `💨 Air Quality` card now appears in the Lifestyle view between the Commute and Garden cards. It shows an LLM-authored one-sentence advisory calibrated to the forecast AQI level, with a colour-coded level badge for the major pollutant status.

- **`narration/llm_prompt_builder.py`** — Added `"air_quality"` field to the `---CARDS---` JSON block in both EN v6 and ZH v6 system prompts. The LLM is instructed to write exactly 1 sentence: reassure if Good (≤50), name the pollutant and flag sensitive groups if Moderate (51–100), recommend limiting outdoor exposure if Unhealthy or above.

- **`narration/fallback_narrator.py`** — Added `air_quality` generation in `_build_fallback_cards()`. Prefers `summary_en`/`summary_zh` from the processed MOENV data; falls back to AQI-level-based canned sentences in both EN and ZH. Handles range-format AQI strings (`"51-100"`) by parsing the lower bound.

- **`web/routes.py`** — Added `air_quality` card to `_slice_lifestyle()`. Text sourced from `summaries["air_quality"]` (LLM card), then `summary_zh`/`summary_en` MOENV extracts, then a placeholder. Card carries the raw `aqi` value and translated `status` for badge rendering.

- **`web/static/app.js`** — Added `// 5. Air Quality` card rendering in `renderLifestyleView()`, positioned between Commute and Garden. Uses the existing `T.air_quality` i18n key (already 'Air Quality' / '空氣品質' in both locales) and `aqiToLevel()` for badge colour. Removed the 33-line `ov-aqi-forecast` rendering block from the overview renderer.

- **`web/templates/dashboard.html`** — Removed the "明日空氣品質" / `ov-aqi-forecast` section from the Dashboard view.

### No changes to the data pipeline

The fetch layer (`fetch_moenv.py`), processing layer (`weather_processor.py`), and the parsed `aqi_forecast` structure are unchanged. The LLM already received `aqi_forecast` in `processed_data` — only the prompt output and rendering destination changed.

---

## Design Rationale

### Card always visible

The card renders even when AQI is Good. "Air tomorrow looks clean — no precautions needed." is positive confirmation, not noise. Hiding it on clean days would leave users uncertain whether air quality was checked at all — the same problem the alert card had before the verbosity fix.

### No duplication with HVAC card

The HVAC card already recommends running the air purifier when the current AQI exceeds 100. The Air Quality card covers tomorrow's *outdoor* forecast. These are complementary: one is indoor/now, the other is outdoor/tomorrow.

### Raw MOENV text retired

The removed dashboard section displayed unprocessed Chinese MOENV regional forecast prose. The new card text is LLM-authored in the active language, consistent in tone and length with all other lifestyle cards.
