# Metadata Parser Resilience

**Date**: 2026-03-14
**Status**: Done

## Problem

LLM narration generates correctly but lifestyle cards show generic fallback text
instead of personalised LLM advice. The `---METADATA---` JSON block that feeds
card content is sometimes missing or unparseable due to:

1. LLM wrapping JSON in markdown code fences (`` ```json ... ``` ``)
2. LLM using variant separators (`---metadata---`, `--- METADATA ---`)
3. Token budget (1000) too tight — response truncated before metadata completes
4. `lang` not passed to `build_slices()` during refresh — fallback text always English

## Changes

### 1. Resilient separator matching (`narration/llm_prompt_builder.py`)

Replaced literal `split("---METADATA---")` with case-insensitive, whitespace-tolerant
regex: `r'-{3}\s*METADATA\s*-{3}'`.

### 2. Code fence stripping (`narration/llm_prompt_builder.py`)

Added `re.sub()` to strip `` ```json `` / `` ``` `` wrappers from both metadata and
regen text blocks before `json.loads()`.

### 3. Better error logging (`narration/llm_prompt_builder.py`)

On `json.JSONDecodeError`, log the error details and first 300 chars of raw metadata
text for debugging.

### 4. Pass `lang` to `build_slices()` (`app.py`)

Added `lang=lang` to the `build_slices()` call in `_pipeline_steps()` so fallback
card text uses the correct language.

### 5. NDJSON diagnostics (`app.py`)

Added pipeline log messages that surface metadata extraction status:
- Warning when `---METADATA---` block is missing
- Confirmation with card field count on success

### 6. Token budget increase (`config.py`)

Bumped `CLAUDE_MAX_TOKENS` and `GEMINI_MAX_TOKENS` from 1000 to 1200 to prevent
truncation before the metadata JSON completes.

### 7. Tests (`tests/test_narration_parser.py`)

Five new test cases: code fences, lowercase separator, spaced separator, missing
metadata, and regen with code fences.
