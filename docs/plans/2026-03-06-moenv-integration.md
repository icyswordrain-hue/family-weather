# MOENV Data Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate O3 (Ozone), PM2.5/PM10, Hourly AQI Forecasts, and Special Environmental Warnings from the MOENV API into the weather processing pipeline to provide richer context for the LLM Narrator.

**Architecture:** We will fix an existing silent bug in `fetch_forecast_aqi()`, add new dataset constants, expose O3 from the existing realtime fetch (PM2.5/PM10 already present), add `fetch_hourly_aqi()` and `fetch_environmental_warnings()` to `data/fetch_moenv.py`, and route all new fields through `data/weather_processor.py` into the final narrator payload.

> **Note:** `uv_s_01` (UV index) is explicitly out of scope for this integration.

**Tech Stack:** Python, `requests`

---

### Task 1: Fix existing silent bug in `fetch_forecast_aqi`

**Files:**
- Modify: `data/fetch_moenv.py`

**Context:** Line 171 has a string literal `"171"` as a dict key instead of `"status"`. The processor reads `raw_aqi_forecast.get("status")` which silently returns `None` today. This bug predates this integration and must be fixed first.

**Step 1: Write minimal fix**

In `fetch_forecast_aqi()` return dict (~line 168–174), change:
```python
"171": rec.get("majorpollutant"),
```
to:
```python
"status": rec.get("majorpollutant"),
```

**Step 2: Commit**

```bash
git add data/fetch_moenv.py
git commit -m "fix: correct \"status\" key typo in fetch_forecast_aqi return dict"
```

---

### Task 2: Add dataset constants to config + update imports

**Files:**
- Modify: `config.py`
- Modify: `data/fetch_moenv.py`

**Step 1: Add constants to config.py**

After the existing `MOENV_FORECAST_DATASET` line (~line 70):
```python
MOENV_HOURLY_FORECAST_DATASET = "aqx_p_322"   # Hourly AQI forecast
MOENV_WARNINGS_DATASET        = "aqx_p_136"   # Special environmental warnings
# uv_s_01 (UV index) — out of scope for this integration
```

**Step 2: Update import block in fetch_moenv.py**

The existing import block (lines 18–26) currently imports 6 constants. Add the two new ones:
```python
from config import (
    MOENV_API_KEY,
    MOENV_BASE_URL,
    MOENV_AQI_DATASET,
    MOENV_FORECAST_DATASET,
    MOENV_FORECAST_AREA,
    MOENV_STATION_NAME,
    MOENV_TIMEOUT,
    MOENV_HOURLY_FORECAST_DATASET,  # NEW
    MOENV_WARNINGS_DATASET,          # NEW
)
```

**Step 3: Commit**

```bash
git add config.py data/fetch_moenv.py
git commit -m "feat: add MOENV dataset constants for hourly forecast + warnings"
```

---

### Task 3: Expose O3 from realtime fetch + route PM2.5/PM10/O3 to processor

**Files:**
- Modify: `data/fetch_moenv.py`
- Modify: `data/weather_processor.py`

**Context:** `pm25` and `pm10` already exist in the `fetch_realtime_aqi()` return dict (lines 78–79). Only `o3` is new. Do not re-add the existing fields.

**Step 1: Add o3 to fetch_realtime_aqi return dict**

In `fetch_realtime_aqi()` return dict (~line 74–81), add only this one line:
```python
return {
    "station_name": rec.get("sitename"),
    "aqi": _safe_int(rec.get("aqi")),
    "status": rec.get("status"),
    "pm25": _safe_float(rec.get("pm2.5")),   # already present
    "pm10": _safe_float(rec.get("pm10")),    # already present
    "o3": _safe_float(rec.get("o3")),        # NEW
    "publish_time": rec.get("publishtime"),
}
```

**Step 2: Route fields through _process_current in weather_processor.py**

In `_process_current()`, after the existing AQI block (~line 382):
```python
# Particulates and ozone — pass through from realtime AQI
if aqi_realtime.get("pm25") is not None: result["pm25"] = aqi_realtime["pm25"]
if aqi_realtime.get("pm10") is not None: result["pm10"] = aqi_realtime["pm10"]
if aqi_realtime.get("o3")   is not None: result["o3"]   = aqi_realtime["o3"]
```

**Step 3: Commit**

```bash
git add data/fetch_moenv.py data/weather_processor.py
git commit -m "feat: expose O3 from realtime AQI and route PM2.5/PM10/O3 to narrator payload"
```

---

### Task 4: Fetch Hourly AQI Forecast (`aqx_p_322`)

**Files:**
- Modify: `data/fetch_moenv.py`
- Modify: `data/weather_processor.py`

**Step 1: Add fetch_hourly_aqi() to fetch_moenv.py**

Add this function before `fetch_all_aqi()`:
```python
def fetch_hourly_aqi() -> list[dict]:
    """Fetch hourly AQI forecast for Northern area (aqx_p_322)."""
    url = f"{MOENV_BASE_URL}/{MOENV_HOURLY_FORECAST_DATASET}"
    params = {"api_key": MOENV_API_KEY, "format": "JSON", "limit": "100"}

    try:
        try:
            resp = requests.get(url, params=params, timeout=MOENV_TIMEOUT)
            resp.raise_for_status()
        except requests.exceptions.SSLError:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            resp = requests.get(url, params=params, timeout=MOENV_TIMEOUT, verify=False)
            resp.raise_for_status()

        body = json.loads(resp.content)
        records = body if isinstance(body, list) else body.get("records", [])
        area_records = [r for r in records if r.get("area") == MOENV_FORECAST_AREA]

        return [
            {
                "forecast_time":  r.get("forecastdate"),
                "aqi":            _safe_int(r.get("aqi")),
                "major_pollutant": r.get("majorpollutant"),  # dominant pollutant name, e.g. "PM2.5"
            }
            for r in area_records
        ]
    except Exception as exc:
        logger.warning("Could not fetch MOENV hourly AQI forecast: %s", exc)
        return []
```

**Step 2: Update processor**

In `data/weather_processor.py` `process()`, after the `aqi_forecast["summary_zh"]` line (~line 300):
```python
aqi_forecast["hourly"] = aqi.get("hourly_forecast", [])
```

**Step 3: Commit**

```bash
git add data/fetch_moenv.py data/weather_processor.py
git commit -m "feat: integrate hourly AQI forecast (aqx_p_322)"
```

---

### Task 5: Fetch Special Environmental Warnings (`aqx_p_136`)

**Files:**
- Modify: `data/fetch_moenv.py`
- Modify: `data/weather_processor.py`
- Modify: `docs/reference/API_QUIRKS.md`

**Pre-step (manual, before writing code):** Call `aqx_p_136` with the API key and `print()` one raw record to confirm actual field names. The field names `alert_title` and `content` are assumed — they are NOT documented in `API_QUIRKS.md`. Log confirmed names to `API_QUIRKS.md` before coding.

```bash
python -c "
import json, requests
from config import MOENV_API_KEY, MOENV_BASE_URL
resp = requests.get(f'{MOENV_BASE_URL}/aqx_p_136', params={'api_key': MOENV_API_KEY, 'format': 'JSON', 'limit': '1'}, timeout=20, verify=False)
print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
"
```

**Step 1: Add fetch_environmental_warnings() to fetch_moenv.py**

Add before `fetch_all_aqi()` (use confirmed field names from pre-step):
```python
def fetch_environmental_warnings() -> list[dict]:
    """Fetch active special environmental warnings (aqx_p_136)."""
    url = f"{MOENV_BASE_URL}/{MOENV_WARNINGS_DATASET}"
    params = {"api_key": MOENV_API_KEY, "format": "JSON"}

    try:
        try:
            resp = requests.get(url, params=params, timeout=MOENV_TIMEOUT)
            resp.raise_for_status()
        except requests.exceptions.SSLError:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            resp = requests.get(url, params=params, timeout=MOENV_TIMEOUT, verify=False)
            resp.raise_for_status()

        body = json.loads(resp.content)
        records = body if isinstance(body, list) else body.get("records", [])

        # Filter to Northern Taiwan — try both field names; fallback to all records
        area_records = [
            r for r in records
            if MOENV_FORECAST_AREA in str(r.get("area", "") or r.get("county", ""))
        ]
        if not area_records:
            area_records = records

        return [
            {
                "title":        r.get("alert_title") or r.get("title", "Environmental Warning"),
                "content":      r.get("content", ""),
                "publish_time": r.get("publishtime"),
            }
            for r in area_records
        ]
    except Exception as exc:
        logger.warning("Could not fetch MOENV warnings: %s", exc)
        return []
```

**Step 2: Replace fetch_all_aqi() with final state**

Replace the entire `fetch_all_aqi()` function with:
```python
def fetch_all_aqi() -> dict:
    """Fetch real-time AQI, 3-day forecast, hourly forecast, and active warnings."""
    return {
        "realtime":        fetch_realtime_aqi(),
        "forecast":        fetch_forecast_aqi(),
        "hourly_forecast": fetch_hourly_aqi(),
        "warnings":        fetch_environmental_warnings(),
    }
```

**Step 3: Update processor**

In `data/weather_processor.py` `process()`, after `aqi_forecast["hourly"]`:
```python
aqi_forecast["warnings"] = aqi.get("warnings", [])
```

**Step 4: Commit**

```bash
git add data/fetch_moenv.py data/weather_processor.py docs/reference/API_QUIRKS.md
git commit -m "feat: integrate MOENV environmental warnings (aqx_p_136)"
```

---

## Verification

1. **Fetcher smoke test:**
   ```bash
   python -c "from data.fetch_moenv import fetch_all_aqi; import json; print(json.dumps(fetch_all_aqi(), indent=2, default=str))"
   ```
   Confirm: `o3`/`pm25`/`pm10` in `realtime`; `hourly_forecast` is a list; `warnings` returns without error; `forecast["status"]` is no longer `None`.

2. **Processor smoke test:** Run `refresh.local()` in LOCAL mode and confirm the narrator payload JSON includes `pm25`/`pm10`/`o3` in `current`, and `hourly`/`warnings` in `aqi_forecast`.

3. **No retry loops:** None of the new functions may contain retry loops — missing fields must log a warning and return empty.
