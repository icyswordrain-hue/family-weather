# Tagline Fallback for Lifestyle Cards

**Date**: 2026-03-14
**Status**: Done

## What

Lifestyle card taglines (~8-word summaries shown when collapsed) disappeared
when the LLM response omitted the `---METADATA---` JSON block. Without metadata,
`parse_narration_response()` produces no card/tagline fields and the `summaries`
dict only contains `_best_window` and `_top_activity`.

## Root Cause

Not a code regression. The Claude Sonnet 4.6 response for the current broadcast
didn't include `---METADATA---`, so `_derive_cards_from_metadata()` returned
all-empty strings. The frontend's `if (tagline)` guard correctly skipped
rendering them.

## Fix

**File: `web/routes.py`**

1. Added `_truncate_tagline()` helper (same logic as
   `narration/fallback_narrator.py:_truncate_tagline`) — truncates to 8 words
   for English, 16 chars for Chinese.
2. Added a fallback block at the end of `_slice_lifestyle()` that auto-generates
   taglines from card text when the LLM didn't provide them. Covers all 7 card
   types: wardrobe, commute, hvac, meals, garden, outdoor, air_quality.
