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

---

## Follow-up — 2026-03-14: Remove AQI Detail Tagline

The `AQI · PM2.5 · PM10 µg/m³` detail insight added above was removed from the Air Quality card extras. Raw sensor numbers are not actionable; the `peak_window` warning and `purifier_advice` insights already carry the useful information.

**Change:** Deleted the `parts` / `textLine` block in `renderLifestyleView()` (`app.js`). The `peak_window` and `purifier_advice` extras are retained unchanged.

---

## Follow-up — 2026-03-14: Fix Lifestyle Tagline Language Toggle

**Problem:** Three lifestyle card taglines did not update on language toggle:

| Card | Field | Root cause |
| --- | --- | --- |
| **Meals** | `data.meals.mood` | English enum (`"Hot & Humid"` etc.) not in `T.metrics['zh-TW']` |
| **HVAC** | `data.hvac.mode` | English enum (`"cooling"` etc.) not in `T.metrics['zh-TW']` |
| **Air Quality** | `data.air_quality.purifier_advice` | Backend sentence not wrapped in `localiseMetric()`, and no mapping existed in either direction |

**Fix (`app.js`):**

1. Added to `TRANSLATIONS['zh-TW'].metrics`:
   - Meal moods: `'Hot & Humid'` → `'炎熱潮濕'`, `'Warm & Pleasant'` → `'溫暖舒適'`, `'Cool & Damp'` → `'涼爽潮濕'`, `'Cold'` → `'寒冷'`
   - HVAC modes: `'Off'`, `'fan'`, `'cooling'`, `'heating'`, `'heating_optional'`, `'dehumidify'` → Chinese equivalents
   - English purifier advice sentences → Chinese (3 strings)

2. Added `TRANSLATIONS['en'].metrics` (new) with Chinese purifier advice sentences → English, for the reverse-toggle case (broadcast generated in zh-TW, user switches to en).

3. Wrapped `data.air_quality.purifier_advice` in `localiseMetric()` in `renderLifestyleView()`.

**Note:** `meals.mood` and `hvac.mode` are always English enum values from the Python backend regardless of broadcast language — only one direction of mapping is needed. `purifier_advice` is a localized sentence from the backend, requiring both directions.
