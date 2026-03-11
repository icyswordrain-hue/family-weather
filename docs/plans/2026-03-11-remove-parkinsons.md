---
date: "2026-03-11"
title: "Remove Parkinson's Phrasing and Logic"
status: "Implemented"
---

# Remove Parkinson's Phrasing and Logic

The user specified that Dad does not have Parkinson's. The codebase previously contained several hardcoded assumptions, data fields, and LLM instructions geared toward Parkinson's-safe outdoor activity.

This plan documents the removal of all such phrasing and logic, while preserving the "outdoor activity with Dad" framing.

## Changes Made

### 1. `narration/fallback_narrator.py`
- Removed the `parkinsons` property read in the P3 (Outdoor & Meal) prose generation.
- Removed the conditional sentences appending "Parkinson's friendly" or "Manageable for Parkinson's".
- Updated the outdoor lifestyle card (English and Traditional Chinese) to drop the `parkinsons_safe` check and instead use a generic "with Dad" framing (e.g., "推薦帶爸爸前往...").

### 2. `web/routes.py`
- Dropped the `parkinsons_safe` key from the `outdoor` slice constructed in `_slice_lifestyle` so it is no longer exposed to the frontend.

### 3. `narration/llm_prompt_builder.py`
- Removed the `"parkinsons": "good|ok|avoid"` requirement from the `REGEN` location schema definition.
- Rewrote the location generation system instruction to remove all mentions of Parkinson's, changing the focus to "terrain difficulty, shade availability, seating, and general accessibility".

### 4. `data/locations.json`
- Stripped the `"parkinsons": "good" | "ok"` field from all 184+ location entries.

### 5. `tests/test_location_loader.py`
- Updated `test_location_has_required_fields` to assert on the `"surface"` field instead of the now-deleted `"parkinsons"` field.

## Verification
- Locations are still correctly categorised by weather mood.
- The `weather_processor.py` logic never used the `parkinsons` field for filtering (only for appending strings in the fallback narrator), so the pool of suggested locations remains unchanged.
- The LLM prompt no longer wastes tokens asking for Parkinson's assessments.
