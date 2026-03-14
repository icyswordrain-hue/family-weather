# Narration-Cards Unification — Eliminate Duplicate LLM Output

**Date:** 2026-03-14

## Problem

The LLM prompt produced **two overlapping outputs** in a single call:
- **P1-P5 paragraphs** (~600 output tokens) — flowing prose for TTS audio narration
- **---CARDS--- JSON** (~500 output tokens) — condensed card text + taglines for 8 lifestyle cards

The content overlapped heavily: wardrobe advice appeared in both P1 and the wardrobe card, commute details in both P2 and the commute card, etc. The CARDS schema in the system prompt also consumed ~350 input tokens. Total waste: **~850 tokens per LLM call**.

## Solution

Expand the existing `---METADATA---` JSON with card-specific fields (taglines, text summaries, alert details) and remove the entire `---CARDS---` block. The parser derives the `cards` dict from metadata fields via `_derive_cards_from_metadata()`, keeping the downstream data shape identical.

### New Metadata Fields Added

| Field | Purpose |
|-------|---------|
| `wardrobe_tagline` | ≤8 words imperative (wardrobe + rain gear) |
| `rain_gear_text` | 1 sentence — umbrella/raincoat/boots advice |
| `commute_tagline` | ≤8 words key commute condition |
| `meals_text` | 1 sentence meal suggestion |
| `meals_tagline` | ≤8 words food + weather mood |
| `outdoor_tagline` | ≤8 words activity + best time |
| `garden_text` | 2 sentences garden tasks |
| `garden_tagline` | ≤8 words garden task |
| `hvac_tagline` | ≤8 words climate action |
| `air_quality_summary` | 1 sentence AQI advisory |
| `air_quality_tagline` | ≤8 words air status |
| `alert_text` | 1-2 sentences health/commute risks |
| `alert_level` | INFO / WARNING / CRITICAL |

### Files Changed

| File | Change |
|------|--------|
| `narration/llm_prompt_builder.py` | Expanded METADATA schema (EN + ZH), removed CARDS block, added `_derive_cards_from_metadata()`, updated parser |
| `narration/fallback_narrator.py` | Merges card data into metadata instead of separate CARDS block, added `_truncate_tagline()` |
| `config.py` | Reduced `CLAUDE_MAX_TOKENS` and `GEMINI_MAX_TOKENS` from 1500 to 1000, regen from 2500 to 2000 |
| `tests/test_narration_parser.py` | Updated mock data and assertions for metadata-derived cards |
| `tests/test_fallback_narrator.py` | Updated to verify no CARDS block, expanded metadata fields present |

### Files Unchanged

`app.py`, `web/routes.py`, `web/static/app.js` — the `cards` dict shape is identical downstream, so no changes needed in the pipeline, route slicing, or frontend.

## Token Savings

| Component | Before | After | Savings |
|-----------|--------|-------|---------|
| System prompt: CARDS schema (input) | ~350 tok | 0 tok | ~350 tok |
| System prompt: METADATA schema (input) | ~100 tok | ~200 tok | -100 tok |
| Narration prose (output) | ~600 tok | ~600 tok | 0 |
| CARDS JSON (output) | ~500 tok | 0 tok | ~500 tok |
| Metadata JSON (output) | ~200 tok | ~300 tok | -100 tok |
| **Total** | | | **~650 tok** |

## Backward Compatibility

- Parser strips any legacy `---CARDS---` block if present (handles cached/in-flight responses)
- `_derive_cards_from_metadata()` returns `{}` if metadata is empty, matching prior behavior
- Fallback narrator produces the same card shapes via metadata merging
