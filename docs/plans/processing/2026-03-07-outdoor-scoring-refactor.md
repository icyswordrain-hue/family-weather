# Outdoor Scoring Refactor — Dew Point Double-Count Fix & Photography Surfacing

**Date:** 2026-03-07

---

## 1. Remove dp_oppressive/dp_muggy/dp_sticky double-count (`data/outdoor_scoring.py`)

### Problem

The scoring function applied two independent humidity penalties to the same physical
phenomenon. Apparent Temperature (AT) is computed from temp + humidity + wind via the
BOM Heat Index formula — high dew point already inflates AT on hot humid days. Then
`dp_oppressive/dp_muggy/dp_sticky` penalised the same absolute dew point again:

| Scenario | AT penalty | dp_oppressive penalty | Total |
|---|---|---|---|
| 30°C air, dp 24°C → AT ≈ 35°C | −57 (cap) | −12 | −69 (double-counted) |

`dew_gap_clammy` / `dew_gap_humid` are **not** double-counting — they measure
near-saturation discomfort at cool/mild temperatures where the AT formula barely moves
(e.g. 18°C air, dp 17°C → AT ≈ 20.6°C, penalty ≈ 0, but the air is clearly clammy).

### Changes

Removed from `_score_conditions()` rules list:
- `dp_oppressive` rule (dew_point ≥ 24°C)
- `dp_muggy` rule (21 ≤ dew_point < 24°C)
- `dp_sticky` rule (18 ≤ dew_point < 21°C)

Removed from `OUTDOOR_WEIGHTS_GENERAL`:
- `dp_oppressive: -12, dp_muggy: -6, dp_sticky: -3`

Removed from activity overrides:
- `sports`: `dp_oppressive: -20, dp_muggy: -10`
- `photography`: `dp_oppressive: -5`
- `swimming`: `dp_oppressive: 0, dp_muggy: 0, dp_sticky: 0` (now redundant)

Also removed dead `at_extreme_hot / at_hot / at_cold / at_extreme_cold` keys from all
dicts — these were never emitted by the rules list after the continuous AT penalty was
introduced, so they had no effect.

---

## 2. Raise AT quadratic penalty cap (`data/outdoor_scoring.py`)

### Problem

The old cap of −50 created a wide plateau: AT = 34°C through AT = 40°C all scored
identically (50, "Manageable"). A 40°C feels-like day should be F (Stay In).

### Change

```python
# Before
penalty = max(-50, -int((abs(diff) ** 2) / 2.5))

# After
penalty = max(-75, -int((abs(diff) ** 2) / 2.5))
```

New reference points (divisor 2.5, cap −75):

| AT | diff | penalty | score | grade |
|---|---|---|---|---|
| 22°C | 0 | 0 | 100 | A |
| 27°C | +5 | −10 | 90 | A |
| 32°C | +10 | −40 | 60 | B |
| 34°C | +12 | −57 | 43 | D |
| 36°C | +14 | −78 → cap −75 | 25 | F |
| 37°C+ | ≥+15 | cap −75 | 25 | F |

Cap triggers at diff = ±14 (AT ≥ 36°C hot / AT ≤ 8°C cold). Every integer AT inside
the cap yields a unique, strictly worsening score — no plateaus.

---

## 3. Photography solar penalties (`data/outdoor_scoring.py`)

### Rationale

Portrait photography suffers on clear sunny days (harsh shadows, squinting, blown
highlights). Overcast/cloudy days act as a natural softbox — the ideal condition. The
existing `solar_extreme` rule (solar_load > 80) fired a caution label but had zero
weight; sunny days scored identically to cloudy days for photography.

Additionally, sunny UVI=6 → solar_load = 80, which missed the `> 80` threshold entirely.

### Changes

Added `solar_high` rule to cover the 50–80 solar_load band:
```python
("solar", c.get("solar_load"), lambda v: v is not None and 50 < v <= 80, "solar_high", "caution", "bright_sunlight"),
```

Added to photography activity overrides:
```python
"solar_extreme": -30,   # blazing noon sun — harsh portrait shadows
"solar_high":   -15,    # moderately bright sun — still unflattering
```

No change to `OUTDOOR_WEIGHTS_GENERAL` — general activities' solar impact is already
captured by `uvi_extreme` / `uvi_very_high`.

Resulting photography scores (AT=26°C, no other penalties):

| Conditions | solar_load | rule | photo penalty | score | grade |
|---|---|---|---|---|---|
| Overcast, UVI 8 | 40 | none | 0 | ~94 | A |
| Morning, UVI 2 | 20 | none | 0 | ~96 | A |
| Sunny, UVI 6 | 80 | solar_high | −15 | ~79 | A |
| Sunny, UVI 7 | 90 | solar_extreme | −30 | ~64 | B |
| Sunny, UVI 10 | 100 | solar_extreme | −30 | ~64 | B |

---

## 4. Surface photography in card and narration (`narration/llm_prompt_builder.py`, `web/routes.py`)

### Problem

Photography never appeared in the outdoor card or narration despite having a computed
score. Two causes:

1. **LLM prompt** — the outdoor card instruction said "Recommend an outdoor activity for
   Dad" with no reference to `outdoor_index.activities`. The LLM wrote generic
   recommendations (walking, hiking) from weather intuition.

2. **Tie-breaking** — `max(_acts, key=score)` returns the first maximum in dict insertion
   order. On cloudy days where all activities score ~94, `strolling` (first key) always
   won over `photography` (last key).

### Changes

**`narration/llm_prompt_builder.py` — `build_prompt()`:**

Pre-computes the top activity and injects it as a plain-text HINTS line:
```python
_acts = processed_data.get("outdoor_index", {}).get("activities", {})
top_activity = max(_acts, key=lambda k: _acts[k]["score"]) if _acts else "unknown"

# In user_message f-string:
HINTS:
- Top outdoor activity by score: {top_activity}
Generate today's broadcast.
```

**`narration/llm_prompt_builder.py` — `---CARDS---` instruction (EN + ZH):**
```
# Before:
"outdoor": "Exactly 2 sentences. Outdoor activity for Dad — best time window and any weather caution."
# After:
"outdoor": "Exactly 2 sentences. Use the top outdoor activity from the HINTS section. Best time window and any weather caution."
```

**`web/routes.py` — `top_activity` tie-breaking:**
```python
_max_score = max(v["score"] for v in _acts.values())
_tied = [k for k, v in _acts.items() if v["score"] == _max_score]
top_activity = "photography" if ("photography" in _tied and _max_score >= 80) else _tied[0]
```

Photography wins ties when conditions are good (score ≥ 80), reflecting the fact that
a clear-sky overcast day with no other hazards is ideal for outdoor portrait sessions.
