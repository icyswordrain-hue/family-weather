# Refactor: Fold Lifestyle Card Summarization into Main Narration LLM

**Date:** 2026-02-28
**Commit:** `3a4c505`
**Status:** Completed

## Problem

The broadcast pipeline made two LLM calls per request:

1. **Main narration LLM** (Claude Sonnet / Gemini) → 6 prose paragraphs + `---METADATA---` JSON
2. **Claude Haiku** (`narration/llm_summarizer.py`) → reads those paragraphs → 8 lifestyle card snippets

The Haiku call was redundant: it re-read prose the main LLM had just written, then produced card-sized summaries of information already present in `processed_data`. The alert card's structured fallback (`paragraphs.get("p1_summary")`) silently never fired because the key doesn't exist.

## Solution

Have the main LLM emit a `---CARDS---` JSON block directly after `---METADATA---`, following the same established separator pattern. The backend parser extracts it; `_slice_lifestyle()` reads `summaries` from `parsed["cards"]` as before — no change to the data contract with the frontend.

## Architecture Change

### Before

```
LLM (Sonnet/Gemini)
  → narration text
  → ---METADATA--- JSON

Haiku (llm_summarizer.py)
  ← reads narration paragraphs
  → summaries dict {wardrobe, rain_gear, commute, meals, hvac, garden, outdoor}

app.py
  summaries, _ = run_parallel_summarization(paragraphs, ...)
  build_slices(..., summaries=summaries)
```

### After

```
LLM (Sonnet/Gemini)
  → narration text
  → ---METADATA--- JSON
  → ---CARDS--- JSON {wardrobe, rain_gear, commute, meals, hvac, garden, outdoor, alert}

app.py
  summaries = parsed.get("cards", {})
  build_slices(..., summaries=summaries)
```

## The `---CARDS---` Block

Eight keys, same language as the narration paragraphs:

| Key | Length | Notes |
|-----|--------|-------|
| `wardrobe` | 2 sentences | Clothing based on AT and rain |
| `rain_gear` | 2 sentences | Umbrella/raincoat/boots decision |
| `commute` | 2 sentences | Morning and evening road conditions |
| `meals` | 2 sentences | Meal suggestion matching weather mood |
| `hvac` | 2 sentences | AC / heating / ventilation |
| `garden` | 4 sentences | Garden tasks and plant care |
| `outdoor` | 4 sentences | Dad's outing — Parkinson's safety and best window |
| `alert` | object | `{"text": "1–2 sentences", "level": "INFO\|WARNING\|CRITICAL"}` |

The `alert` object replaces the old rule-based cardiac/menieres/heads_ups logic. The LLM determines severity from P1 content:
- **CRITICAL** — cardiac or Ménière's health risk
- **WARNING** — significant weather or safety heads-up
- **INFO** — mild note or clear uneventful day (empty string `""` if nothing to flag)

`---REGEN---` (the 14-day database refresh block) is placed after `---CARDS---` when triggered, not after `---METADATA---`.

## Files Changed

| File | Change |
|------|--------|
| `narration/llm_prompt_builder.py` | Added `---CARDS---` block to EN and ZH system prompts; updated `parse_narration_response()` to split on `---CARDS---` then `---REGEN---` |
| `app.py` | Replaced `run_parallel_summarization()` call with `parsed.get("cards", {})`; removed dead AQI summary code |
| `web/routes.py` | Replaced structured cardiac/menieres/heads_ups alert construction with `summaries["alert"]`; removed `cardiac`/`menieres` params and unused imports |
| `backend/pipeline.py` | Removed `run_parallel_summarization()` and `summarize_for_lifestyle` import |
| `narration/llm_summarizer.py` | **Deleted** |
| `tests/test_narration_parser.py` | **New** — 12 tests: parser extraction, graceful missing block, regen coexistence, prompt content |
| `tests/test_pipeline.py` | Removed summarization tests |
| `tests/test_slices.py` | Updated alert assertions for new list-based structure |
| `tests/test_summarizer_prompts.py` | **Deleted** |

## Parser Logic

`parse_narration_response()` in `narration/llm_prompt_builder.py`:

```
raw_response
  → split "---METADATA---"
      ↳ narration_text (paragraphs)
      ↳ remainder
          → split "---CARDS---"
              ↳ metadata_text  → json.loads → result["metadata"]
              ↳ cards_and_regen
                  → split "---REGEN---"
                      ↳ cards_text  → json.loads → result["cards"]
                      ↳ regen_text  → json.loads → result["regen"]
```

`result["cards"]` initialises to `{}` so callers get safe empty-dict fallback if the block is absent.

## Alert Card Behaviour

`_slice_lifestyle()` in `web/routes.py`:

```python
alert_summary = summaries.get("alert", {})
if isinstance(alert_summary, dict):
    alert_text = alert_summary.get("text", "")
    alert_level = alert_summary.get("level", "INFO")
    _alert = [{"level": alert_level, "type": "General", "msg": alert_text}] if alert_text else []
else:
    _alert = []
```

The frontend receives the same `[{level, type, msg}]` list shape as before.

## Trade-offs

**Gains:**
- One fewer LLM call per request (lower latency, lower cost)
- Alert card now LLM-generated with proper severity signalling
- Fixes the silently-broken `paragraphs.get("p1_summary")` fallback
- Single source of truth: LLM writes the prose and the card summaries in one pass

**Risks / fallback behaviour:**
- If the LLM omits `---CARDS---`, `summaries` is `{}` and `_slice_lifestyle()` falls back to its existing computed defaults (paragraph text, rule-based wardrobe tips, etc.) — no user-visible breakage
- The LLM must now produce a larger response; tested prompt token budget is within model limits
- Alert severity is LLM-assessed, not rule-based — critical health alerts are no longer guaranteed if the LLM ignores P1 instructions (acceptable trade-off given the broken prior state)
