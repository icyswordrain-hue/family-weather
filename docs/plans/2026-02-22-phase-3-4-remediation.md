# Phase 3 & Phase 4 Remediation Plan

> **For Execution Agents:** REQUIRED SUB-SKILL: Use `superpowers:test-driven-development` and `systematic-debugging` to implement this layout. Implement minimal verifiable segments.

**Goal:** Resolve architectural tech debt, separate concerns in `weather_processor.py` and `app.py`, improve test coverage, and clear out dead code (Phase 3 & 4 of Audit Report).

## Execution Strategy
The `Architect` has dictated that execution agents follow strict Test-Driven Development (TDD) principles. Refactoring will be done incrementally to prevent regressions.

---

## Proposed Changes

### 1. Refactor `weather_processor.py` (A1, A5, SM3)
- **Problem:** `weather_processor.py` is a 1,500+ line God module.
- **Plan:**
  1. **Configuration Extraction:** Move `OUTDOOR_LOCATIONS` (80 lines) to `data/locations.json`. Write a loader in `data/utils.py`.
  2. **Domain Splits:** Extract logic into focused modules:
     - `data/scales.py` (AQI, UV, Wind scales)
     - `data/health_alerts.py` (Cardiac, Ménière's detection)
     - `data/meal_classifier.py` (Menu sets and rules)
     - `data/outdoor_scoring.py` (Scoring and grade definitions)
  3. **Deterministic Testing:** Modify `_segment_forecast(..., now: datetime = None)` to accept a `now` parameter overriding `datetime.now()`, improving testability.

### 2. Refactor `app.py` Pipeline (A2)
- **Problem:** `_pipeline_steps()` mixes orchestration, data generation, and persistence.
- **Plan:**
  1. Extract `_pipeline_steps()` into `backend/pipeline.py`.
  2. Create isolated functions for `check_regen_cycle()`, `generate_narration_with_fallback()`, and `parallel_summarization()`.

### 3. Cleanup & Dead Code Removal (DC1, DC2, A4, P1, D1)
- **Problem:** Stale design notes, unused models, duplicated helpers.
- **Plan:**
  1. Delete `narration/narration_utils.py` entirely (grep confirms it's unused).
  2. In `history/conversation.py`, strip out the 80 lines of commented-out design documentation.
  3. Delete `renderHealthCard()`, `makeCard()`, and `aqiClass()` from `web/static/app.js` (unused).
  4. Move `_safe_float` and `_safe_int` into `data/helpers.py`.

### 4. Comprehensive Test Suite (TS3)
- **Problem:** Zero code coverage on core logic and routing.
- **Plan:**
  1. Use pytest to build deterministic unit tests for `data/outdoor_scoring.py`, `data/health_alerts.py`, and `data/meal_classifier.py`.
  2. Build mock-based tests for `backend/pipeline.py`.

## Verification Plan

### Automated Tests
- Run `pytest tests/ -v` to ensure 100% pass rate post-refactoring.
- Ensure mocked testing prevents external API calls during `pipeline.py` testing.

### Manual Verification
- Launch the Flask server and run a refresh (`POST /api/refresh`).
- Verify SSE stream works correctly and data is functionally equivalent to pre-refactor states.
