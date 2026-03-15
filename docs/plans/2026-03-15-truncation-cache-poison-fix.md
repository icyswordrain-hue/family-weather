# Fix: Truncated Metadata Cache Poisoning

## Problem

Claude narration hits `max_tokens=1400` and truncates the `---METADATA---` JSON block.
The truncated response is returned as "success," cached for 30 minutes, and every
subsequent parse yields empty metadata/cards — frontend lifestyle cards show nothing.

**Root cause chain:**
1. `claude_client.py` logs a warning on truncation but returns the text anyway
2. `generate_narration_with_fallback()` caches the broken text for 30 min
3. `parse_narration_response()` fails on the truncated JSON → `metadata={}`, `cards={}`
4. Frontend reads from `summaries` (derived from `cards`) → empty lifestyle cards

**Secondary issues found:**
- Cache key uses `datetime.now().hour` (server timezone) instead of Taipei — wrong in Modal (UTC)
- CLAUDE.md claimed no cross-provider waterfall, but pipeline.py has one
- zh-TW CJK tokenization needs more headroom than the 1400-token budget allowed

## Changes

### 1. Truncation detection with fallback retry
**Files:** `narration/claude_client.py`, `narration/gemini_client.py`

Added `_has_parseable_metadata()` — checks if `---METADATA---` is followed by valid JSON.
When the primary model truncates with unparseable metadata, it falls through to the
internal fallback model (Haiku / Flash) instead of returning broken text.

### 2. Cache validation
**File:** `backend/pipeline.py`

Cache only stores responses containing `---METADATA---`. Truncated responses
without the separator are returned but not cached, preventing 30-min poison windows.

### 3. Taipei timezone for cache key
**File:** `backend/pipeline.py`

Changed `datetime.now().hour` → `datetime.now(CST).hour` so Modal (UTC) servers
produce correct time-of-day classification for cache keys.

### 4. Token budget increase
**File:** `config.py`

- `CLAUDE_MAX_TOKENS` / `GEMINI_MAX_TOKENS`: 1400 → 1600
- `CLAUDE_MAX_TOKENS_REGEN` / `GEMINI_MAX_TOKENS_REGEN`: 1800 → 2000

Gives zh-TW CJK tokenization enough headroom to complete the metadata block.

### 5. CLAUDE.md accuracy
**File:** `CLAUDE.md`

Updated narration provider docs to describe the actual two-tier fallback chain:
internal (Sonnet→Haiku) → cross-provider (Claude→Gemini) → template.
