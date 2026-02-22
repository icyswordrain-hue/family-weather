# Outdoor Suitability Index & Activity-Based Modifications

This document details the logic for the outdoor suitability index and the backend mechanisms for activity-based modifications.

## 1. Outdoor Suitability Index (0–100)

The index evaluates forecast segments using specific penalty weights.

### Penalty Weights (`OUTDOOR_WEIGHTS_GENERAL`)
Starting from 100, the score is reduced by weather conditions:

| Metric | Condition | Penalty | Type |
|---|---|---|---|
| **Precipitation** | Rain > 5mm | -50 | Blocker |
| | PoP > 70% | -25 | Caution |
| **Wind** | Beaufort ≥ 7 | -35 | Blocker |
| **AQI** | AQI > 150 | -40 | Blocker |
| **Visibility** | Vis < 1.0km | -30 | Blocker |

### Health Penalties
- **Ménière's Alert**: -35 (High) / -20 (Moderate)
- **Cardiac Alert**: -15

---

## 2. Activity-Based Modifications

Specific activities override general weights to better reflect their unique requirements.

### Logic Mechanism
The `_score_conditions(c: dict, weights: dict)` helper allows passing custom weight dictionaries. Functions like `_compute_outdoor_index` iterate through `OUTDOOR_WEIGHTS_BY_ACTIVITY` to apply these overrides.

### Current Activity Pool & Examples
- **Strolling**: Base activity.
- **Cycling**: Sensitive to wind (-40) and wet ground (-25).
- **Hiking**: High penalties for heat (-35) and sensitive AQI (-20).
- **Swimming**: Ignores rain (0) and heat humidity (0), but blocked by cold (-50).
- **Photography**: Penalty for poor visibility (-50), neutral to light rain (0).

## 3. Mood Classification & Recommendations
The final **Outdoor Mood** ("Nice", "Warm", "Cloudy & Breezy", "Stay In") is derived from the index score and average temperature. This mood then filters the curated pool of `OUTDOOR_LOCATIONS` for the user.
