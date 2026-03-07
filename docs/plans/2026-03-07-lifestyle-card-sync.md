# Lifestyle Card Consistency Sync

**Date:** 2026-03-07
**Status:** Implemented

## Problem
The lifestyle view previously displayed conflicting information between the main text and the badges/sub-text (e.g., LLM suggesting "open windows" while the badge strictly said "cooling"). This occurred because the LLM generated its text independently of the rule-based backend engine which rendered the badges.

## Decision
Force the LLM to anchor its advice to the deterministic conclusions computed by the rule-engine.

1. **Explicit HINTS**: Inject the exact computed states into the `HINTS` section of the LLM prompt.
2. **Strict Instructions**: Modify the system prompt for `---CARDS---` (both EN and ZH) to explicitly instruct the LLM to conform to the provided hints.

## Files Changed
### `narration/llm_prompt_builder.py`
- Added logic to extract `outdoor_grade`, `climate_mode`, and `commute_hints` from `processed_data` and append them to the `HINTS` section.
- Updated `V6_SYSTEM_PROMPT` (EN) and `V6_SYSTEM_PROMPT_ZH` (ZH) to enforce alignment with the newly added hints.
