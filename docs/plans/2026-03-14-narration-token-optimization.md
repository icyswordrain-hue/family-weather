# Narration Token Optimization

**Date**: 2026-03-14
**Status**: Done

## What

Reduce wasted LLM tokens across narration generation, fallback chains, and chat,
plus harden the metadata parser against common LLM formatting quirks.

## Changes

### 1. Faster fallback entry (config.py)
- Primary Claude timeout: 240s → 90s (Sonnet 4.6 typically responds in 10–30s)
- Regen max_tokens: 2000 → 1500 (actual output ~800–1100 tokens)
- Normal max_tokens: 1000 → 1200 (metadata expansion needed headroom)

### 2. Anthropic prompt caching (claude_client.py)
- System prompt now uses `cache_control: {"type": "ephemeral"}` on both primary
  and fallback calls. The ~1300-token system prompt is cached for 5 minutes,
  so fallback attempts and consecutive narration runs avoid re-processing it.

### 3. Cross-provider fallback (pipeline.py)
- If the primary provider's full waterfall fails (e.g., Claude Sonnet → Haiku),
  the pipeline now tries the other provider (Gemini Pro → Flash) before falling
  back to the template narrator.
- `build_prompt()` failures are caught separately and fall back to template
  immediately (no point trying another LLM with a broken prompt).

### 4. Chat context caching (app.py)
- `build_chat_context()` output cached for 5 minutes keyed by `date:lang`.
- Avoids rebuilding ~1000 tokens of identical system prompt on rapid-fire
  chat conversations.

### 5. Parser resilience (llm_prompt_builder.py)
- `---METADATA---` separator match is now case-insensitive and whitespace-tolerant
  (regex: `-{3}\s*METADATA\s*-{3}`).
- Strips markdown code fences (```` ```json ... ``` ````) from metadata and regen
  JSON blocks before parsing.
- Better error logging on JSON parse failures (includes error message + 300 chars).

## Files Modified
- `config.py` — timeouts, max_tokens
- `narration/claude_client.py` — prompt caching
- `backend/pipeline.py` — cross-provider fallback, build_prompt error handling
- `app.py` — chat context cache, `time` import
- `narration/llm_prompt_builder.py` — parser resilience
- `tests/test_narration_parser.py` — 5 new parser resilience tests

## Token Impact (per-call estimates)

| Scenario | Before | After |
|----------|--------|-------|
| Normal narration (cache miss) | ~4400 tok | ~4400 tok (same, but cached system prompt on repeat) |
| Fallback fires | ~8100 tok | ~5500 tok (90s fail-fast + cached system prompt) |
| Regen day | ~5100 tok | ~4600 tok (tighter output limit) |
| Chat (repeat msgs) | ~1700 tok/msg | ~700 tok/msg (cached context) |
| Provider fully down | template only | tries other provider first |
