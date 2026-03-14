---
date: "2026-03-14"
title: "Expand Activity Suggestion Pool (8 → 16)"
status: "Implemented"
---

# Expand Activity Suggestion Pool

## Context

The outdoor scoring system had only 8 activities in `OUTDOOR_WEIGHTS_BY_ACTIVITY`.
Adding 8 more activities increases variety in the `top_activity` hint passed to
the LLM, producing more diverse daily recommendations.

## New Activities

| Activity | Key weather sensitivities |
|----------|--------------------------|
| `jogging` | AQI-sensitive, humidity penalty, wet ground |
| `fishing` | Rain-tolerant, wind-sensitive, wet ground neutral |
| `bird_watching` | Visibility-critical, rain penalty, quiet conditions |
| `tai_chi` | Needs dry flat ground, moderate wind OK |
| `temple_visit` | Most weather-resilient (covered/shaded), scores high in rain |
| `market_stroll` | Rain-sensitive (outdoor markets), moderate wind OK |
| `riverside_walk` | Wet ground penalty (flooding risk), visibility matters |
| `gardening` | UV/rain sensitive, wet ground neutral (it's soil) |

## Files Changed

### `data/outdoor_scoring.py`
- Added 8 new entries to `OUTDOOR_WEIGHTS_BY_ACTIVITY` with weather-specific
  penalty overrides. Total activities: 16.

### `data/locations.json`
- Tagged 8 existing locations with new activity types:
  - Fishing: Bitan, Sanxia Chengfu Riverside, Dahan River (Tucheng)
  - Temple visit: Sanxia Zushi Temple, Shulin Sanhe Temple
  - Market stroll: Sanxia Old Street, Xinzhuang Night Market
  - Bird watching: Guandu Nature Park, Xinhai Wetlands, Dahan River (Tucheng)
  - Riverside walk: Bitan, Sanxia Chengfu Riverside

### `narration/llm_prompt_builder.py` (prior commit)
- Removed last Parkinson's references from docstring comments.

## How It Works

No code changes needed beyond the weight definitions — the scoring engine
iterates `OUTDOOR_WEIGHTS_BY_ACTIVITY` automatically, and the `top_activity`
string flows through to the LLM prompt as a hint. The LLM matches activities
to locations using the `activity` field in `locations.json`.

## Verification

```bash
pytest tests/  # 188 passed
```
