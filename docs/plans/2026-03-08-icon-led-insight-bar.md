# 2026-03-08: Icon-Led Insight Bar for Lifestyle Cards

## Intent
The lifestyle cards previously used a mix of `.ls-badge` pills and `.ls-sub` grey text lines to display high-level data derived from the card. This led to an inconsistent visual hierarchy and caused long lines to wrap awkwardly on mobile screens. Additionally, the backend and frontend algorithms had slightly different tier-breaker logic for `top_activity`, causing the LLM to write stories about different activities than what was surfaced on the UI badge.

**Goal**: Standardize the data presentation across all Lifestyle cards into a single "Icon-Led Insight Bar" that ensures readability, consistency, and exact parity with the narration system.

## Changes Made

### 1. Unified CSS Component (`style.css`)
Introduced `.ls-insight`, replacing the ad-hoc combinations of sub-text and badges.
- Uses `var(--hover)` background rather than solid colors.
- Places a 16px `.brand-icon` inline with the insight text.
- Replaces legacy badge classes (except for alert cards, which explicitly retain their color-coded danger/warning badges).

### 2. UI Rewiring (`app.js`)
Replaced `mkBadge` and `mkSub` helper functions with a new `mkInsight` generator in `renderLifestyleView`.
- **Wardrobe**: Merged `feels_like` and `rain_gear` into a single line (`Feels Like 13° · ☂️ No precipitation gear expected`).
- **Commute**: Replaced the unordered hazard list with a single commute icon + primary hazard.
- **Garden**: Added a new single line insight for watering advice.
- **Outdoor**: Combined grade, best window, and top activity into a single insight line.
- **Meals & HVAC**: Transitioned their primary status (e.g., mood, heat/cool mode) from standalone color badges to the `.ls-insight` bar pattern.
- **Air Quality**: Moved to the end of the list and converted PM2.5/PM10 metrics into a single inline string.

### 3. Backend Data Alignment (`narration/llm_prompt_builder.py`)
Fixed an issue where the UI (`routes.py`) and the LLM builder had misaligned algorithms for picking the `top_activity`. 
- Ported the "photography" tie-breaker logic into `llm_prompt_builder.py`.
- Reinforced the system prompt to explicitly command the LLM: `"You MUST use the exact top outdoor activity provided in the HINTS section."`
- These steps ensure the LLM never hallucinates an activity that contradicts the one displayed on the outdoor card's `.ls-insight` bar.

### 4. Language Consistency
Fixed a localization bug in `app.js` where structural strings like `best_window` (e.g., "Morning", "Afternoon") were being rendered verbatim in English, even when `lang = "zh-TW"`. They are now passed through the `T.slots` dictionary, returning proper localized values (e.g., "早上").
