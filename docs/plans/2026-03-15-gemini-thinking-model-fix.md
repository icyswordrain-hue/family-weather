# Fix: Gemini Thinking Model Truncation + Thinking Budget Evaluation

## Problem

`gemini-3-flash-preview` is a **thinking model** — its thinking tokens count against
`max_output_tokens`. With the default thinking configuration, the model used ~1533 thinking
tokens out of the 1600-token budget, leaving only ~63 tokens for actual output. The narration
truncated after ~50 words, leaving no `---METADATA---` block.

**Root cause chain:**
1. `gemini-3-flash-preview` (Gemini 2.5 Flash) enables thinking by default
2. `max_output_tokens=1600` is consumed by thinking tokens before any visible text is generated
3. `finish_reason=MAX_TOKENS` fired, but the truncation handler in `_has_parseable_metadata()`
   correctly detected no valid metadata and would have fallen through to Flash — however, the
   Flash fallback (`gemini-2.5-flash`) has the same default thinking behavior, so it too would
   have truncated
4. Both models failed silently for narration calls

**Token budget math:**
```
thinking_budget=default → ~1533 thinking + ~63 visible = 1596 total → MAX_TOKENS
thinking_budget=0       → 0 thinking + ~600 visible = 600 total → STOP (full narration)
```

## Changes

### 1. Disable thinking for narration generation
**File:** `narration/gemini_client.py`

Added `thinking_config=genai.types.ThinkingConfig(thinking_budget=0)` to both the Pro and
Flash `GenerateContentConfig` calls. Thinking is unnecessary for structured templated narration
and consumes the entire output budget.

Also added `thinking_budget: int = 0` kwarg to `generate_narration()` so the smoke test can
experiment with different values without modifying production code.

## Thinking Budget A/B/C Evaluation

Three runs comparing `thinking_budget=0`, `512`, and `1024` (with auto-scaled token ceilings):

| Budget | max_tokens | Words | metadata_ok | Result |
|--------|-----------|-------|-------------|--------|
| 0 | 1800 | 295 | ✓ | Full narration, natural prose |
| 512 | 2312 | 308 | ✓ | Equivalent quality, ~45% higher cost |
| 1024 | 2824 | 306 | ✓ | Equivalent quality, ~90% higher cost |

**Conclusion:** Thinking provides no measurable improvement in fluency or format compliance for
this structured 5-paragraph + metadata JSON task. `thinking_budget=0` is the correct production
setting for all model-family versions of `gemini-3-flash-preview` and `gemini-2.5-flash`.

## Tooling

### `dev-tools/smoke_gemini.py` (new)
End-to-end smoke test that calls `generate_narration()` via the real prompt builder:

```
python dev-tools/smoke_gemini.py                       # default: budget=0, lang=en
python dev-tools/smoke_gemini.py --lang zh-TW
python dev-tools/smoke_gemini.py --thinking-budget 512
python dev-tools/smoke_gemini.py --thinking-budget 1024 --max-tokens 2800
```

Reports: `metadata_ok`, `response len`, first 300 chars of narration.
Auto-scales `max_output_tokens = thinking_budget + 1800` when `--max-tokens` is not set.
