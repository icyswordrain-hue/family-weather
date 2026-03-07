# Heads-Up Alert Card — Architecture & Deduplication

## What the Card Does

The **Heads-Up** card is the first card in the Lifestyle view. It surfaces
time-sensitive alerts that warrant direct attention before the user reads the
rest of the broadcast. It renders only when the alert list is non-empty; on
clear days the card is absent entirely.

Three severity levels map to distinct visual treatments:

| Level | Card border | Icon |
|---|---|---|
| `CRITICAL` | Red | `alert.webp` |
| `WARNING` | Orange | `heads-up.webp` |
| `INFO` | Blue | `all-clear.webp` |

Each alert item in the list has three fields:

```json
{ "type": "Health" | "Commute" | "Air" | "General",
  "level": "CRITICAL" | "WARNING" | "INFO",
  "msg": "Human-readable message" }
```

The frontend (`app.js:920-964`) renders one row per item, using the `type`
field to choose a small inline icon (health cross, car, air-quality leaf, etc.).

---

## Alert Sources

Two independent code paths contribute entries to the alert list in
`_slice_lifestyle()` (`web/routes.py`):

### Path 1 — LLM Summary

1. `health_alerts.py:_compute_heads_ups()` generates a `heads_ups[]` array from
   live data. Relevant triggers:
   - Cardiac risk: morning AT ≤ 15 °C with PoP ≥ 50 % or AT ≤ 10 °C
   - Ménière's risk: 24 h pressure swing ≥ 6 hPa
   - Commute hazards: morning/evening hazard strings from the commute module
2. `heads_ups[]` is embedded in the JSON payload sent to the LLM.
3. The LLM prompt (`narration/llm_prompt_builder.py`) instructs P1 to open with
   these alerts, then produces a `---CARDS---` JSON whose `"alert"` key
   summarises **Health and Commute concerns only** (AQI is excluded by the
   prompt — see below).
4. `_slice_lifestyle()` extracts `summaries["alert"]["text"]` and, if non-empty,
   appends `{"type": "General", "level": ..., "msg": ...}` to `_alert`.

### Path 2 — Direct MOENV Injection

`_slice_lifestyle()` independently checks `aqi_forecast.aqi` and
`aqi_forecast.warnings` from the processed data:

```python
_AIR_ALERT_KEYWORDS = ("不良", "不健康", "有害", "建議減少", "建議室內", "避免戶外")
if isinstance(aqi_num, (int, float)) and aqi_num >= 150:
    for w in aqi_forecast.get("warnings", []):
        if any(kw in w for kw in _AIR_ALERT_KEYWORDS):
            _alert.append({"type": "Air", "level": "WARNING", "msg": w})
```

Conditions for injection:
- Forecast AQI ≥ 150 ("Unhealthy for Everyone" tier)
- Warning text contains at least one advisory keyword in Chinese

The threshold was deliberately set at 150 (not 100) to avoid surfacing the
ordinary daily MOENV narrative as a WARNING on moderate-AQI days.

---

## The Duplication Bug (fixed commit 068c811)

Before the fix, `_compute_heads_ups()` also appended an AQI alert when
**realtime AQI > 100**:

```python
# data/health_alerts.py:98-101 — STILL PRESENT, feeds heads_ups[] to LLM
if aqi_val and aqi_val > 100:
    status = aqi.get("realtime", {}).get("status", "Poor")
    alerts.append({"level": "WARNING", "type": "Air", "msg": f"AQI is {status} ({aqi_val})"})
```

The LLM received this in `heads_ups[]`, mentioned it in P1, and echoed it back
via `summaries["alert"]` → Path 1 injected a General alert about AQI.
Simultaneously, if forecast AQI ≥ 150 with keywords, Path 2 also injected an
Air alert. Result: two AQI-related rows in the card.

---

## Deduplication System

### `_dedup_alerts(alerts)` — `web/routes.py`

Applied as the **final step** in `_slice_lifestyle()` before the slice is
returned. It collapses multiple entries that cover the same topic into a single
winner.

**Step 1 — Type classification**

`_classify_alert_type(alert)` inspects the `type` field. If `type` is already
specific (`"Air"`, `"Health"`, `"Commute"`), it is returned unchanged. If
`type == "General"`, the message text is scanned case-insensitively against
three keyword tables:

```python
_AIR_CLASSIFY_KEYWORDS    = ("aqi", "air quality", "pm2.5", "pm10", "空氣", "ozone", "particulate")
_HEALTH_CLASSIFY_KEYWORDS = ("cardiac", "ménière", "menieres", "meniere",
                              "pressure drop", "pressure rise", "心臟", "梅尼爾")
_COMMUTE_CLASSIFY_KEYWORDS = ("commute", "traffic", "road", "通勤", "路況", "drive", "driving")
```

If a keyword matches, the effective type is promoted to that category. Unmatched
General alerts stay `"General"`.

**Step 2 — Per-type winner selection**

Alerts are grouped by effective type. Within each group:

1. **Severity wins**: `CRITICAL` (3) > `WARNING` (2) > `INFO` (1)
2. **Specificity wins on tie**: a non-General type beats `"General"` when severity
   is equal

```python
_ALERT_SEVERITY = {"CRITICAL": 3, "WARNING": 2, "INFO": 1}

def _dedup_alerts(alerts):
    best: dict[str, dict] = {}
    for a in alerts:
        key = _classify_alert_type(a)
        prev = best.get(key)
        if prev is None:
            best[key] = a
        else:
            score_a = _ALERT_SEVERITY.get(a.get("level", "INFO"), 0)
            score_p = _ALERT_SEVERITY.get(prev.get("level", "INFO"), 0)
            if score_a > score_p:
                best[key] = a
            elif (score_a == score_p
                  and a.get("type") != "General"
                  and prev.get("type") == "General"):
                best[key] = a
    return list(best.values())
```

Distinct types (e.g. Health + Commute + Air on a bad day) are all preserved —
dedup only removes entries that share the same effective type.

---

## LLM Prompt Constraint

The `alert` card instruction in `V6_SYSTEM_PROMPT` (EN and ZH) explicitly
excludes AQI:

> **EN:** "Summarise today's health risks (cardiac, Ménière's) and commute
> hazards from P1. Do NOT include air quality — that has its own dedicated card.
> If nothing significant to flag, leave this as an empty string."

> **ZH:** "摘要 P1 中的健康風險（心臟、梅尼爾氏症）及通勤危險。不要包含空氣品質資訊
> ——那已有專屬卡片。若無特別需要提醒的事項，請留空字串。"

This eliminates the most common source of the duplicate at generation time.
`_dedup_alerts()` then acts as a safety net for any remaining cross-path
overlap.

The empty-string instruction also means the heads-up card does not render at
all on uneventful days (previously the LLM always wrote "All clear today."
which produced an INFO card even when nothing needed attention).

---

## Data Flow Summary

```
health_alerts._compute_heads_ups()
    │  heads_ups[] — cardiac, menieres, commute
    │  (AQI entry also present when realtime AQI > 100,
    │   but LLM is instructed to ignore it for the alert card)
    ▼
LLM narration → summaries["alert"] = {"text": ..., "level": ...}
    │  Health + Commute summary only
    ▼
_slice_lifestyle()
    ├─ Path 1: LLM alert → _alert (type: "General", if text non-empty)
    └─ Path 2: MOENV forecast warnings → _alert (type: "Air", if AQI ≥ 150 + keywords)
    │
    ▼
_dedup_alerts(_alert)
    │  Classifies General alerts by keyword
    │  Keeps one winner per effective type (highest severity, then specificity)
    ▼
lifestyle["alert"]  →  heads-up card in frontend
```

---

## Adding a New Alert Source

1. Append your entry to `_alert` in `_slice_lifestyle()` with the appropriate
   `type` (`"Health"`, `"Commute"`, `"Air"`, or `"General"`).
2. If the new source can overlap with the LLM General alert, add distinctive
   keywords to the relevant `_*_CLASSIFY_KEYWORDS` tuple so `_classify_alert_type()`
   can promote the General entry to the same type and dedup will collapse them.
3. Add a test in `tests/test_slices.py` asserting the expected post-dedup count
   for the new source + LLM combination.

---

## Test Coverage

`tests/test_slices.py` covers the following scenarios:

| Test | What it checks |
|---|---|
| `test_lifestyle_alert_empty_when_no_summaries` | No summaries → empty list |
| `test_lifestyle_alert_populated_from_summaries` | LLM alert flows through |
| `test_lifestyle_alert_empty_when_alert_text_blank` | Empty LLM text → empty list |
| `test_lifestyle_alert_includes_moenv_warning_when_aqi_elevated` | MOENV path fires at AQI ≥ 150 + keywords |
| `test_lifestyle_alert_no_moenv_warning_when_aqi_below_threshold` | Threshold gate (< 150) |
| `test_lifestyle_alert_no_moenv_warning_without_keywords` | Keyword gate |
| `test_lifestyle_alert_dedup_llm_and_moenv_air_alerts` | Both paths fire → one Air entry |
| `test_lifestyle_alert_dedup_keeps_critical_over_warning_same_type` | Severity winner |
| `test_lifestyle_alert_dedup_prefers_specific_type_over_general_on_equal_severity` | Specificity tiebreak |
| `test_lifestyle_alert_dedup_keeps_distinct_types` | Different types all preserved |
