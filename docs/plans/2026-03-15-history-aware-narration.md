# History-Aware Narration Context

**Date**: 2026-03-15
**Status**: Done

## What

The narration prompt previously used history only for P5 forecast accuracy comparison.
Paragraphs P1–P4 were written as if each day existed in a vacuum — no trend awareness,
no repetition avoidance, no pattern recognition. This change adds three context blocks
to the LLM prompt so narration is more connected across days.

## Token Impact

Baseline user message: ~1,450 tokens. New blocks add ~87 tokens typical (~6%),
~185 worst case (~13%). The system prompt gains 3 STYLE directives (~40 tokens).
Well within budget — the DATA JSON alone is ~1,250 tokens.

## Changes

### 1. `[TRENDS]` block — `_format_trends()` (llm_prompt_builder.py)

Computes today-vs-yesterday deltas and emits a pipe-delimited line when changes
are notable. Only fires when thresholds are met:

- Temperature: ≥4°C swing
- Humidity: ≥10% swing
- AQI: >15 points vs history average (improving/worsening)
- Rain: ≥2-day streak (checks `Wx_text` and `precip_text` for rain keywords)

Example output:
```
[TRENDS]
Temp: +6°C vs yesterday | RH: -12% | AQI: improving (3 days) | Rain: 2-day streak
```

### 2. `[RECENT_NARRATION]` block — `_format_recent_narration()` (llm_prompt_builder.py)

Extracts last 2–3 days of narration metadata (`meal`, `garden`, `outdoor_tagline`,
`wardrobe_tagline`) via `get_lang_data()` so the LLM can avoid repeating the same
dish, garden topic, or tagline phrasing.

Example output:
```
[RECENT_NARRATION]
Yesterday: meal=lu rou fan | garden="prune herbs" | outdoor="Great for cycling"
2 days ago: meal=beef noodle soup | garden="water seedlings"
```

### 3. `[PATTERNS]` block — `_format_patterns()` (llm_prompt_builder.py)

Detects recurring conditions across history and emits bullet points:

- Rainy commute streak (≥2 days, checks commute hazards for rain keywords)
- Extended poor outdoor grades (≥3 days D/F, notes when today improves)
- Sustained moderate+ AQI (≥2 days above 100)

Example output:
```
[PATTERNS]
- Rainy commute: 3 days in a row (including today)
- Outdoor: today's B grade is the best in 4 days
```

### 4. Prompt STYLE additions (llm_prompt_builder.py)

Three new directives in the system prompt STYLE section:

- **Trend awareness**: Weave `[TRENDS]` comparisons into relevant paragraphs naturally
- **Variety**: Use `[RECENT_NARRATION]` to avoid repeating meals, gardens, taglines
- **Pattern continuity**: Acknowledge `[PATTERNS]` streaks briefly instead of treating days as isolated

### 5. `build_prompt()` signature (llm_prompt_builder.py + pipeline.py)

Added `lang: str = 'en'` parameter to `build_prompt()` so `_format_recent_narration()`
can extract the correct language's metadata. Updated call site in `pipeline.py`.

## Files Modified

- `narration/llm_prompt_builder.py` — 3 new helpers, `build_prompt()` lang param, 3 STYLE directives
- `backend/pipeline.py` — pass `lang=lang` to `build_prompt()`
