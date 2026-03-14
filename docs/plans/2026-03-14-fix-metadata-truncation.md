# Fix: Lifestyle Cards Showing Fallback Text Due to METADATA Truncation

**Date:** 2026-03-14
**Status:** Implemented

## Problem

After a cloud refresh, lifestyle cards displayed generic rule-based fallback text
(e.g., "Light jacket or sweater") instead of LLM-generated card text, even though
narration audio played fresh LLM content correctly.

## Root Cause

The LLM response contains narration paragraphs (P1-P5) followed by a
`---METADATA---` JSON block. Card text is derived from this JSON.

With `max_output_tokens=1200`, the token budget was too tight:
- Narration (250-280 words) ~ 500 tokens
- METADATA JSON (22 fields) ~ 700 tokens
- Total ~ 1200 tokens — right at the limit

When the LLM ran slightly verbose, the response hit the token ceiling and the
JSON was truncated mid-string. `json.loads()` failed silently, `cards` became
`{}`, and all lifestyle cards fell through to rule-based defaults in
`_slice_lifestyle()`. The narration text (before the separator) was always
intact, so TTS continued working.

Neither LLM client checked the stop/finish reason, making truncation invisible.

## Changes

1. **Reduced narration word count by 10%** (`narration/llm_prompt_builder.py`)
   - EN: 250-280 → 225-250 words
   - ZH: 340-370 → 305-335 characters

2. **Increased token limits** (`config.py`)
   - Normal: 1200 → 1400
   - Regen: 1500 → 1800

3. **Added truncation detection** (`narration/claude_client.py`, `narration/gemini_client.py`)
   - Claude: check `response.stop_reason == "max_tokens"`
   - Gemini: check `response.candidates[0].finish_reason`
   - Both log warnings when truncation is detected

4. **Improved parse failure diagnostics** (`narration/llm_prompt_builder.py`)
   - Enhanced `JSONDecodeError` warning to hint at token truncation as likely cause

5. **Added test** (`tests/test_narration_parser.py`)
   - `test_parse_truncated_metadata_returns_empty_cards` — verifies graceful
     degradation when METADATA JSON is truncated mid-string

## Files Modified

- `config.py`
- `narration/llm_prompt_builder.py`
- `narration/claude_client.py`
- `narration/gemini_client.py`
- `tests/test_narration_parser.py`
