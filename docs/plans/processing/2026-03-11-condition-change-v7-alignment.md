# Condition Change Logic — v7 Alignment

**Date:** 2026-03-11

---

## Background

Two separate "condition change" systems exist in the codebase. Both were written before v7, and the question was raised whether they still made sense and whether they should be unified.

---

## The Two Systems

### System 1 — `_conditions_changed()` (midday gate)

**File:** `app.py:296`

Runs *before* `process()` as a lightweight pre-flight check. Compares the live CWA station reading against the morning broadcast's `processed_data["current"]` to decide if a full midday pipeline run is warranted.

**Problems found (all from v5-era field names):**

| Check | Old code | CWA raw key | Effect |
|-------|----------|-------------|--------|
| Temperature | `"temp"` | `AT` | Always 0 vs 0 — never triggered |
| Precipitation | `"precip_mm"` | `RAIN` | Always 0 vs 0 — never triggered |
| Dew point | `"dew_point"` (default 0) | not present on raw obs | 0 vs real value (15–25 °C) — **always** triggered |
| AQI | `"aqi"` | not in raw CWA fetch | Compared 0/"good" vs real — false positive when morning AQI > 50 |
| Outdoor score | `"score_label"` | not present | Both None — never triggered |
| Alerts | `"alerts"` | not present | Both [] — never triggered |

Net effect: the dew-point check fired on every run, making `changed=True` nearly always true. The midday skip optimisation was a silent no-op.

### System 2 — `_detect_transitions()` (forecast transition enrichment)

**File:** `data/weather_processor.py:546`

Runs *inside* `process()` as step 5. Compares adjacent time segments (Morning→Afternoon→Evening→Overnight) for meaningful weather shifts across 6 metrics (AT > 5 °C, RH > 20 %, PoP > 1 category, WS > 2 Beaufort, WD > 90°, cloud cover class change). Output is stored in `processed_data["transitions"]` and consumed by:

- Frontend Overview timeline cards (`app.js`)
- Fallback narrator (`narration/fallback_narrator.py:164`) — top 2 `is_transition: true` entries
- LLM JSON data — present in the `DATA:` blob but previously unreferenced in the system prompt

---

## Unification Considered — Rejected

Extracting a shared `_breach_pair()` primitive was considered to unify the threshold logic. Rejected because:

- Two callers with **intentionally different thresholds** (AT ≥ 3 °C gate vs AT > 5 °C narrative): no DRY benefit
- Gate output is a boolean; breach objects are never displayed or stored
- Existing fix already makes the gate functional — YAGNI
- Adding current→Morning as a transitions list entry would mix past-state and future-state in the same array, corrupting the LLM instruction ("use the first entry as your 1 key transition")

---

## Changes Made

### `app.py:296–330` — field-name fix

- `"temp"` → `"AT"` (CWA raw apparent temperature key)
- `"precip_mm"` → `"RAIN"` (CWA raw precipitation key)
- Dew point: derived inline via `_calc_dew_point(AT, RH)` instead of defaulting to 0
- Dropped `alerts`, `aqi`, `score_label` — all require a full pipeline run; unavailable on the raw station fetch
- Added import: `from data.helpers import _dew_point as _calc_dew_point`

### `narration/llm_prompt_builder.py:70` — P5 prompt alignment

Added explicit reference to `transitions[].is_transition` in the P5 block:

> "The `transitions` array in the data flags segments where significant change occurs (is_transition: true) — use the first such entry as your 1 key transition; skip stable stretches."

Previously the system prompt said "cover only the 1 key transition" with no pointer to the pre-computed list, leaving the LLM to re-derive the signal from raw segment data.

---

## Token Impact

None. `transitions` was already in the LLM JSON payload; the prompt tweak adds a clarifying instruction but no new data. Output token budget (1000 for regular runs) is unaffected.

Current LLM input token landscape for reference:

| Source | Approx. tokens |
|--------|---------------|
| `aqi_forecast.hourly` (removed by `_slim_for_llm`) | 300–450 saved |
| `transitions` (3 entries, kept) | 150–600 |
| `forecast_36h` segments | 800–1200 |
| History block | 200–500 |
| System prompt | ~600 |
| **Typical total** | 2500–4000 |
