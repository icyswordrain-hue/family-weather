# Dew Point & Apparent Temperature Implementation

**Goal:** Replace direct RH use with dew-point-derived signals throughout the processing
pipeline. RH is a ratio that shifts with temperature across the day — the same 70% RH reads
as comfortable at 15°C but oppressive at 30°C. Dew point is temperature-independent: it
measures absolute moisture and stays stable through the day, making it a more reliable input
for both apparent temperature calculation and comfort scoring.

**Architecture:**

1. Add four helper functions to `data/weather_processor.py`:
   - `_calculate_dew_point()` — Magnus formula
   - `_calculate_dew_gap()` — air temp minus dew point
   - `_saturation_label()` — snake-case comfort label for LLM context
   - `_calculate_apparent_temp_from_dew()` — BOM AT via dew point (preferred over RH path)
2. Add `dew_gap_to_hum()` to `data/scales.py` — title-case label + level for UI display
3. Replace humidity label source in `_process_current()` and the segment enrichment loop
4. Switch outdoor scoring humidity rules from RH thresholds to dew gap thresholds

**Commit:** `83def8b`
**Tech Stack:** Python

---

## Helper Functions (`data/weather_processor.py`)

```python
def _calculate_dew_point(temp_c: float | None, rh: float | None) -> float | None:
    """Magnus formula dew point approximation. Accurate to ±0.35°C."""
    import math
    if temp_c is None or rh is None or rh <= 0:
        return None
    a, b = 17.27, 237.7
    gamma = (a * temp_c / (b + temp_c)) + math.log(rh / 100)
    return round((b * gamma) / (a - gamma), 1)

def _calculate_dew_gap(temp_c: float | None, dew_point_c: float | None) -> float | None:
    """Degrees between air temperature and dew point. Smaller = clammier."""
    if temp_c is None or dew_point_c is None:
        return None
    return round(temp_c - dew_point_c, 1)

def _saturation_label(dew_gap_c: float) -> str:
    """Snake-case comfort label from dew gap, for LLM context and internal logic."""
    if dew_gap_c < 2:  return "near_saturated"
    if dew_gap_c < 5:  return "clammy"
    if dew_gap_c < 10: return "humid"
    if dew_gap_c < 15: return "comfortable"
    return "dry"

def _calculate_apparent_temp_from_dew(
    temp_c: float | None, dew_point_c: float | None, wind_ms: float | None
) -> float | None:
    """BOM AT using dew point as humidity input. Preferred over RH path."""
    import math
    if temp_c is None or dew_point_c is None:
        return None
    e = 6.105 * math.exp((17.27 * dew_point_c) / (237.7 + dew_point_c))
    return round(temp_c + (0.33 * e) - (0.70 * (wind_ms or 0)) - 4.00, 1)
```

---

## Scale Helper (`data/scales.py`)

`dew_gap_to_hum()` replaces `_hum_to_scale()` for all new code. `_hum_to_scale()` is
retained for backward-compat (history records carry old label strings).

```python
def dew_gap_to_hum(dew_gap_c: float | None) -> tuple[str, int]:
    """Map dew gap (°C) to (label, level). Level 1 = comfortable, 5 = worst."""
    if dew_gap_c is None:
        return "Unknown", 0
    if dew_gap_c < 2:  return "Near Saturated", 5
    if dew_gap_c < 5:  return "Clammy",          4
    if dew_gap_c < 10: return "Humid",            3
    if dew_gap_c < 15: return "Comfortable",      1
    return               "Dry",                   2
```

Label-to-level mapping rationale:
- `Comfortable` (gap 10–15°C) is level 1 — ideal
- `Dry` (gap ≥ 15°C) is level 2 — slightly suboptimal but not uncomfortable
- `Humid` (gap 5–10°C) is level 3 — noticeable
- `Clammy` (gap 2–5°C) is level 4 — unpleasant
- `Near Saturated` (gap < 2°C) is level 5 — worst, fog-adjacent

---

## Call Sequence

Applied in both `_process_current()` and the segment enrichment loop (`process()` step 4):

```python
ta = current.get("AT")           # actual air temp (current obs)
rh = current.get("RH")           # relative humidity %
ws = current.get("WDSD")         # wind speed m/s

dew_point = _calculate_dew_point(ta, rh)
dew_gap   = _calculate_dew_gap(ta, dew_point)

# AT via dew point path; fallback to RH path if dew_point unavailable
calculated_at = (
    _calculate_apparent_temp_from_dew(ta, dew_point, ws)
    or _calculate_apparent_temp(ta, rh, ws)
)

result["dew_point"]        = dew_point
result["dew_gap"]          = dew_gap
result["saturation_label"] = _saturation_label(dew_gap) if dew_gap is not None else None
result["hum_text"], result["hum_level"] = dew_gap_to_hum(dew_gap)
```

For segments, `ta = seg.get("T") if seg.get("T") is not None else seg.get("AT")` — actual
air temperature preferred over CWA's pre-computed apparent temperature to avoid
double-applying humidity/wind.

---

## Outdoor Scoring (`data/outdoor_scoring.py`)

`dew_gap` added to both `cond` dicts in `_compute_outdoor_index()`. The three
humidity-related rules in `_score_conditions()` switched from RH thresholds to dew gap:

| Rule | Old condition | New condition |
|------|--------------|---------------|
| `heat_humidity` | `AT > 28 and RH > 75` | `AT > 28 and dew_gap < 10` |
| `rh_very_high` | `RH > OUTDOOR_RH_VERY_HIGH (90%)` | `dew_gap < 2` |
| `rh_high` | `RH > OUTDOOR_RH_HIGH (85%)` | `2 ≤ dew_gap < 5` |

Penalty key names (`rh_very_high`, `rh_high`, `heat_humidity`) and weight tables unchanged.

### Threshold equivalence

| Dew gap threshold | Approx. RH equivalent (at 25°C) |
|------------------|---------------------------------|
| < 2°C | RH ≈ 92% |
| < 5°C | RH ≈ 82% |
| < 10°C | RH ≈ 67% |

The dew-gap approach correctly distinguishes a cool night at 90% RH (dew_gap ≈ 1.6°C,
near_saturated) from a warm afternoon at 90% RH (dew_gap ≈ 2.4°C at 15°C vs ≈ 1.6°C at
28°C). RH alone cannot make this distinction.

---

## Frontend (`web/static/app.js`)

Two new entries added to the ZH metrics translation dict. "Humid", "Comfortable", and "Dry"
were already present from the old RH scale and cover the overlapping label names.

```javascript
'Near Saturated': '接近飽和', 'Clammy': '悶濕',
```

Old labels (Very Dry, Muggy, Very Humid, Oppressive) left in place — they remain valid for
any history data carrying the old `hum_text` values.

---

## What Was Not Changed

- 7-day forecast slots: CWA provides only MaxAT/MinAT, no RH/wind per slot — dew point
  cannot be computed there.
- The humidity gauge layout: `hum.val` still shows raw RH%, only the label changes.
- `_hum_to_scale()` in `data/scales.py`: retained, not deleted.
- `OUTDOOR_RH_VERY_HIGH` / `OUTDOOR_RH_HIGH` in `config.py`: retained (no longer used by
  outdoor scoring but may be referenced elsewhere).

---

## Follow-up: Two-Component Dew Point Penalty (`data/outdoor_scoring.py`)

**Commit:** `d0b3ec7`

The first pass (above) replaced the RH-based rules with dew_gap thresholds but kept the
same three rule slots (`heat_humidity`, `rh_very_high`, `rh_high`). This follow-up
replaces all three with a two-component system that separates **absolute muginess** from
**clamminess**, handling each as an independent penalty axis.

### Rationale

The dew_gap-only system could not represent absolute mugginess — a wide gap (say 8°C)
with a high absolute dew point (say 27°C) is still oppressive even though sweat evaporates
reasonably. Conversely, a narrow gap on a cool day (dp 16°C, gap 1.5°C) is clammy but not
muggy. The original `heat_humidity` combined rule (AT > 28 AND gap < 10) conflated both.

### New weight keys

| Key | Trigger | General penalty | Notes |
|---|---|---|---|
| `dp_oppressive` | dew_point ≥ 24°C | −20 | Sweat barely evaporates |
| `dp_muggy` | 21 ≤ dew_point < 24°C | −10 | Clearly unpleasant |
| `dp_sticky` | 18 ≤ dew_point < 21°C | −5 | Noticeable stickiness |
| `dew_gap_clammy` | dew_gap < 2°C | −15 | Near saturation |
| `dew_gap_humid` | 2 ≤ dew_gap < 5°C | −8 | Clammy |

Removed: `heat_humidity` (−10), `rh_very_high` (−20), `rh_high` (−10).

Both components can fire simultaneously. Maximum combined humidity penalty on a Taiwan
July afternoon (dp 30.8°C, gap 2.2°C): −20 + −15 = **−35**.

### dew_point_c now passed to score function

`seg["dew_point"]` was already computed in `weather_processor.py` but not forwarded to
`_score_conditions()`. Both `cond` dicts in `_compute_outdoor_index()` now include:

```python
"dew_point": seg.get("dew_point"),   # absolute dew point level (°C)
```

### Activity override changes

- **swimming**: all five dp/dew_gap keys set to 0 — humidity is irrelevant in the water.
- **sports**: `heat_humidity` replaced with `dp_oppressive (−20)`, `dp_muggy (−10)`,
  `dew_gap_clammy (−20)` — exertion amplifies both muggy and clammy conditions.
- **photography**: `heat_humidity (−5)` replaced with `dp_oppressive (−5)` — only
  extreme humidity affects a stationary photographer.

### Numerical examples (spec verification)

| Scenario | dp (°C) | gap (°C) | Expected penalty | Components firing |
|---|---|---|---|---|
| Winter comfort | 10.2 | 7.8 | 0 | none |
| Clammy spring (today) | 17.8 | 2.2 | −8 | dew_gap_humid only (dp just below 18) |
| Hot muggy summer | 27.5 | 7.5 | −20 | dp_oppressive only |
| Taiwan July misery | 30.8 | 2.2 | −35 | dp_oppressive + dew_gap_clammy |
