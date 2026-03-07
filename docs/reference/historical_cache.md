# Historical Station Data Caching

## Why Cache at All

The CWA `O-A0001-001` open data API returns only the **current observation snapshot**
for each station. Once a reading is superseded by the next hourly update, it is gone
from the API. There is no `timeFrom`/`timeTo` parameter, no rolling window, no replay.

The CODiS archive (`codis.cwa.gov.tw`) holds historical data but only through an
unofficial, undocumented web interface with no guaranteed stability.

The practical solution is to **cache each observation locally at fetch time**. Since the
pipeline already calls the API three times a day (05:30, 11:30, 17:30 Taipei), a simple
append-on-fetch strategy accumulates ~1,095 records per year with zero extra API calls.
This local archive unlocks:

- Pressure trend over 24h (Ménière's alert calculation)
- Intra-day temperature swing (cardiac alert calculation)
- Dew point history for the outdoor score trend
- Overnight AT low for cardiac risk window
- Any future feature that needs "what was it like yesterday afternoon"

---

## What to Cache

Derived fields should be cached alongside raw readings. Computing them at cache time
costs nothing and avoids re-deriving them later from incomplete inputs.

```
obs_time          ISO-8601 timestamp from station (authoritative)
fetched_at        Pipeline fetch time (for debugging lag)
temp_c            AirTemperature
rh_pct            RelativeHumidity
pressure_hpa      AirPressure
wind_speed_ms     WindSpeed
wind_dir_deg      WindDirection
precip_mm         Now/Precipitation
peak_gust_ms      GustInfo/PeakGustSpeed
dew_point_c       Derived via Magnus formula
dew_gap_c         temp_c - dew_point_c
apparent_temp_c   Derived via BOM AT formula
saturation_label  near_saturated / clammy / humid / comfortable / dry
```

---

## Format Choice: JSONL vs CSV

Neither is wrong. They make different tradeoffs that suit different working styles.
Read both sections and choose one.

---

### Option A — JSONL (Newline-Delimited JSON)

One JSON object per line. Each line is a self-contained, valid JSON document.

```jsonl
{"obs_time":"2026-02-28T17:00:00+08:00","fetched_at":"2026-02-28T17:31:04","temp_c":20.1,"rh_pct":85.0,"pressure_hpa":1019.9,"wind_speed_ms":2.1,"wind_dir_deg":90.0,"precip_mm":0.0,"peak_gust_ms":3.4,"dew_point_c":17.8,"dew_gap_c":2.3,"apparent_temp_c":18.4,"saturation_label":"clammy"}
{"obs_time":"2026-02-28T11:00:00+08:00","fetched_at":"2026-02-28T11:30:51","temp_c":19.3,"rh_pct":82.0,...}
```

**Pros**

- **Schema flexibility.** Adding a new field (e.g. `aqi` from MOENV, `uv_index`) requires
  no migration. New records just have the extra key; old records don't, and that's fine.
  Python's `dict.get()` handles missing keys naturally.
- **Append is trivially safe.** `open("file", "a")` and write one line. No parsing, no
  locking issues, no risk of corrupting existing data.
- **Each line is independently valid.** A half-written line from a crash affects only that
  line. The rest of the file is unharmed.
- **Reads naturally into Python.** `[json.loads(l) for l in f]` — no dependency needed.
- **Pairs well with pandas.** `pd.read_json("file.jsonl", lines=True)` works directly.
- **Field names are self-documenting.** The file is readable by a human without a schema
  reference.

**Cons**

- **Larger file size.** Field names are repeated on every line. At ~200 bytes/record,
  1,095 records/year ≈ 220 KB/year. Negligible, but worth knowing.
- **Not natively openable in Excel** without a conversion step. Not a concern for a
  developer-managed pipeline, but matters if anyone wants to inspect data manually.
- **Slightly slower to read in bulk** compared to CSV when using pandas on large files,
  because JSON parsing is heavier than CSV parsing. Irrelevant at this data volume.

**When to choose JSONL:** You expect to add fields over time, you want the file to be
human-readable and self-documenting, or you're uncomfortable with CSV's edge cases around
commas in values and quoting rules.

---

### Option B — CSV

Standard comma-separated values with a header row.

```csv
obs_time,fetched_at,temp_c,rh_pct,pressure_hpa,wind_speed_ms,wind_dir_deg,precip_mm,peak_gust_ms,dew_point_c,dew_gap_c,apparent_temp_c,saturation_label
2026-02-28T17:00:00+08:00,2026-02-28T17:31:04,20.1,85.0,1019.9,2.1,90.0,0.0,3.4,17.8,2.3,18.4,clammy
2026-02-28T11:00:00+08:00,2026-02-28T11:30:51,19.3,82.0,...
```

**Pros**

- **Compact.** Field names appear once. Same 1,095 records ≈ 80 KB/year.
- **Universally readable.** Opens directly in Excel, Numbers, Google Sheets — useful if
  a non-developer family member or a doctor ever wants to inspect pressure trend data.
- **Fastest pandas ingestion.** `pd.read_csv()` is highly optimized. Meaningless at this
  volume, but good habit.
- **Familiar to most developers.** Easy to inspect with `head`, `cut`, `awk` on the
  command line.

**Cons**

- **Schema is rigid.** Adding a new column to an existing CSV requires either a migration
  script (rewrite the file with the new header) or accepting that old rows have fewer
  columns than new rows — which breaks most parsers unless handled carefully.
- **Header management is fragile.** On first write you need to write the header; on
  subsequent appends you must not. This requires a file-existence check on every fetch.
- **Special character risk.** If any value ever contains a comma (e.g. a weather
  description string), quoting rules must be applied correctly. The `csv` stdlib module
  handles this, but it's a latent trap if you ever write the file manually.
- **No self-description.** Without the header row, a row of numbers is meaningless. If
  the header is ever accidentally duplicated or lost, the file is harder to recover.

**When to choose CSV:** You want the file to be inspectable in a spreadsheet, your field
schema is stable and unlikely to grow, or you want the smallest possible file footprint.

---

## Recommendation Summary

| Concern | JSONL | CSV |
|---|---|---|
| Schema evolves over time | ✅ Easy | ⚠️ Needs migration |
| Human-readable without tooling | ✅ Self-documenting | ⚠️ Need header context |
| Spreadsheet inspection | ❌ Needs conversion | ✅ Native |
| File size | ~220 KB/yr | ~80 KB/yr |
| Append safety | ✅ Trivial | ⚠️ Header check needed |
| Crash resilience | ✅ Per-line | ✅ Per-line |
| Pandas support | ✅ | ✅ |
| Extra dependencies | None | None (`csv` stdlib) |

For this project, **JSONL has a slight edge** because the data schema is actively
evolving (MOENV AQI integration, UV index, future fields) and the file sizes are
trivially small either way. But CSV is a completely reasonable choice if you want
spreadsheet access.

---

## Implementation

Whichever format you choose, the caching logic lives in `fetch_cwa.py` and is called
from the main pipeline in `main.py` before `processor.py` receives the data.

### JSONL Implementation

```python
# fetch_cwa.py
import json
import math
import logging
from datetime import datetime
from pathlib import Path

from config import STATION_HISTORY_PATH  # e.g. Path("data/station_history.jsonl")

log = logging.getLogger(__name__)


def _dew_point(temp_c: float, rh: float) -> float:
    """Magnus formula. Accurate to ±0.35°C."""
    a, b = 17.27, 237.7
    gamma = (a * temp_c / (b + temp_c)) + math.log(rh / 100)
    return round((b * gamma) / (a - gamma), 1)


def _apparent_temp(temp_c: float, rh: float, wind_ms: float) -> float:
    """Australian BOM apparent temperature formula."""
    e = (rh / 100) * 6.105 * math.exp((17.27 * temp_c) / (237.7 + temp_c))
    return round(temp_c + (0.33 * e) - (0.70 * wind_ms) - 4.00, 1)


def _saturation_label(gap: float) -> str:
    if gap < 2:  return "near_saturated"
    if gap < 5:  return "clammy"
    if gap < 10: return "humid"
    if gap < 15: return "comfortable"
    return "dry"


def cache_observation(raw_station: dict) -> dict:
    """
    Derive computed fields, build cache record, append to JSONL file.
    Returns the enriched record for immediate use by processor.py.
    raw_station: the Station dict from O-A0001-001 response.
    """
    we = raw_station["WeatherElement"]
    temp   = float(we["AirTemperature"])
    rh     = float(we["RelativeHumidity"])
    wind   = float(we["WindSpeed"])
    press  = float(we["AirPressure"])
    precip = we["Now"]["Precipitation"]
    gust   = we["GustInfo"]["PeakGustSpeed"]

    # Coerce CWA special codes to None
    def _clean(v):
        try:
            return float(v)
        except (ValueError, TypeError):
            return None  # covers "X", "-99", "-98", "T"

    dew   = _dew_point(temp, rh)
    gap   = round(temp - dew, 1)
    at    = _apparent_temp(temp, rh, wind)

    record = {
        "obs_time":         raw_station["ObsTime"]["DateTime"],
        "fetched_at":       datetime.now().isoformat(timespec="seconds"),
        "temp_c":           temp,
        "rh_pct":           rh,
        "pressure_hpa":     press,
        "wind_speed_ms":    wind,
        "wind_dir_deg":     _clean(we["WindDirection"]),
        "precip_mm":        _clean(precip),
        "peak_gust_ms":     _clean(gust),
        "dew_point_c":      dew,
        "dew_gap_c":        gap,
        "apparent_temp_c":  at,
        "saturation_label": _saturation_label(gap),
    }

    STATION_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STATION_HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    log.info(f"Cached observation: {record['obs_time']}  "
             f"T={temp}°C  DP={dew}°C  AT={at}°C  gap={gap}°C")
    return record
```

### CSV Implementation

```python
# fetch_cwa.py  (CSV variant — replace cache_observation above)
import csv
import math
import logging
from datetime import datetime
from pathlib import Path

from config import STATION_HISTORY_PATH  # e.g. Path("data/station_history.csv")

log = logging.getLogger(__name__)

FIELDNAMES = [
    "obs_time", "fetched_at", "temp_c", "rh_pct", "pressure_hpa",
    "wind_speed_ms", "wind_dir_deg", "precip_mm", "peak_gust_ms",
    "dew_point_c", "dew_gap_c", "apparent_temp_c", "saturation_label",
]

# ... (same _dew_point, _apparent_temp, _saturation_label, _clean helpers as above)

def cache_observation(raw_station: dict) -> dict:
    # ... (same derivation logic as JSONL version)

    record = { ... }  # same fields

    STATION_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_header = not STATION_HISTORY_PATH.exists()

    with STATION_HISTORY_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(record)

    log.info(f"Cached observation: {record['obs_time']}  ...")
    return record
```

### Reading Back History (Both Formats)

```python
# processor.py — reading the last N hours of history

import json
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import STATION_HISTORY_PATH

def load_recent_history(hours: int = 24) -> list[dict]:
    """Return cached records from the last `hours` hours."""
    if not STATION_HISTORY_PATH.exists():
        return []

    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours)

    # JSONL
    if STATION_HISTORY_PATH.suffix == ".jsonl":
        records = []
        with STATION_HISTORY_PATH.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                obs = datetime.fromisoformat(r["obs_time"])
                if obs.tzinfo is None:
                    obs = obs.replace(tzinfo=timezone(timedelta(hours=8)))
                if obs >= cutoff:
                    records.append(r)
        return records

    # CSV
    df = pd.read_csv(STATION_HISTORY_PATH, parse_dates=["obs_time"])
    df["obs_time"] = pd.to_datetime(df["obs_time"], utc=True)
    return df[df["obs_time"] >= cutoff].to_dict("records")


def pressure_change_24h(history: list[dict]) -> float | None:
    """
    Returns hPa change over last 24h. Positive = rising, negative = falling.
    Returns None if insufficient data.
    """
    if len(history) < 2:
        return None
    pressures = [r["pressure_hpa"] for r in history if r.get("pressure_hpa")]
    if len(pressures) < 2:
        return None
    return round(pressures[-1] - pressures[0], 1)
```

---

## Wiring into main.py

```python
# main.py — in the refresh pipeline

from fetch_cwa import fetch_station_raw, cache_observation
from processor import process, load_recent_history, pressure_change_24h

def run_pipeline():
    raw = fetch_station_raw(CWA_API_KEY, station_id="C0AJ80")

    # Cache first, then process
    enriched = cache_observation(raw)
    history  = load_recent_history(hours=24)

    processed = process(
        station=enriched,
        history=history,
        pressure_delta_24h=pressure_change_24h(history),
        # ... other inputs
    )
    # rest of pipeline unchanged
```

---

## Config Addition

Add to `config.py`:

```python
from pathlib import Path

# Historical observation cache
STATION_HISTORY_PATH = Path(
    os.getenv("STATION_HISTORY_PATH", "data/station_history.jsonl")
    # Change extension to .csv if using CSV format
)

# How many hours of history to load for alert calculations
HISTORY_WINDOW_HOURS = int(os.getenv("HISTORY_WINDOW_HOURS", 24))
```

---

## File Management

The cache grows at ~220 KB/year (JSONL) or ~80 KB/year (CSV). No rotation is needed
for years. If you ever want to trim it:

```python
def trim_history(keep_days: int = 90):
    """Rewrite history file keeping only the last `keep_days` days."""
    records = load_recent_history(hours=keep_days * 24)
    STATION_HISTORY_PATH.write_text("")  # truncate
    for r in records:
        with STATION_HISTORY_PATH.open("a") as f:
            f.write(json.dumps(r) + "\n")  # JSONL variant
```

On Cloud Run, the container filesystem is ephemeral — the history file will be lost on
each redeploy unless you mount a persistent volume or write to Cloud Storage. See the
deployment note in `docs/deployment.md` for options.

> **Deployment note:** If running on Cloud Run without a persistent volume, consider
> writing `STATION_HISTORY_PATH` to a mounted Cloud Storage bucket via gcsfuse, or
> periodically uploading the file to GCS and restoring it on container start. The
> simplest approach for a low-traffic family dashboard is a small Cloud Storage bucket
> with a startup script that pulls the latest cache file before the pipeline runs.

---

## Forecast Cache (`forecast_cache.json`)

Added 2026-03-07 (commit 4ecb294). Mirrors the station-history fallback pattern for
CWA forecast data so that a CWA outage does not produce a blank broadcast.

### What it stores

A single JSON file (not JSONL — forecasts are not a time-series, only the latest matters):

```json
{
  "cached_at": "2026-03-07T10:09:31+08:00",
  "36h": {
    "樹林區": [ { "start_time": "...", "end_time": "...", "AT": 19.0, ... }, ... ],
    "板橋區": [ ... ]
  },
  "7d": {
    "樹林區": [ { "start_time": "...", "AT": 18.0, "PoP12h": 20, ... }, ... ],
    "板橋區": [ ... ]
  }
}
```

### Path config

```python
# config.py
FORECAST_CACHE_PATH = Path(
    os.environ.get("FORECAST_CACHE_PATH", os.path.join(LOCAL_DATA_DIR, "forecast_cache.json"))
)
```

- LOCAL → `local_data/forecast_cache.json`
- MODAL → `/data/forecast_cache.json` (persisted on Modal volume `family-weather-data`)

### Write / read strategy

`fetch_all_forecasts(errors)` and `fetch_all_forecasts_7day(errors)`:

1. Read the current cache file once at the start of the function.
2. For each location in `CWA_FORECAST_LOCATIONS`:
   - **Success** → store in `result` and `fresh` dict.
   - **Failure** → if the cache has slots for that location, use them and record
     `errors[loc] = "(cached YYYY-MM-DDTHH:MM)"`. Otherwise `result[loc] = []` and
     record the real exception string.
3. After the loop, if any locations were freshly fetched, call `_write_forecast_cache(key, fresh)`.
   This does a **read-modify-write** so only the newly-fetched locations overwrite the cache;
   stale-filled locations are not written back.

### Surfacing to the user

- **Log messages:** `⚠ 36h forecast stale: using cache for 樹林區, 板橋區 (cached 2026-03-07T10:09)`
- **Status chips:** `_chip_state()` in `app.py` inspects `errors[loc]` — if all non-empty
  slots have `"(cached..."` values the chip state is `"stale"` (amber), same as CWA chip.

### Private helpers in `fetch_cwa.py`

```python
_read_forecast_cache() -> dict          # read file or return {}; non-fatal
_write_forecast_cache(key, data) -> None  # read-modify-write; non-fatal
```

---

## AQI Observation Cache (`aqi_history.jsonl`)

Added 2026-03-07 (commit fb0ca86). MOENV publishes no hourly AQI forecast
dataset — `AQF_P_01` is the only AQF endpoint in their catalogue and it
provides a 3-day daily regional forecast only. The dataset previously used
for sub-daily data (`aqx_p_322`) turned out to be a daily per-pollutant
concentration table; its `area` filter never matched so `fetch_hourly_aqi()`
silently returned `[]`. This cache is the replacement.

### What it stores

One JSON object per line, one line per pipeline run:

```jsonl
{"obs_time":"2026-03-07T05:00:00","aqi":62,"pm25":18.4,"pm10":null,"o3":22.1,"status":"普通"}
{"obs_time":"2026-03-07T11:00:00","aqi":70,"pm25":21.0,"pm10":null,"o3":28.5,"status":"普通"}
{"obs_time":"2026-03-07T17:00:00","aqi":55,"pm25":14.2,"pm10":null,"o3":19.0,"status":"良好"}
```

All values are sourced from `fetch_realtime_aqi()` (station `土城`, dataset
`aqx_p_432`). `obs_time` is the MOENV `publishtime` normalised to full
ISO 8601 (`YYYY-MM-DDTHH:MM:SS`) so `datetime.fromisoformat()` works across
Python versions.

### Path config

```python
# config.py
AQI_HISTORY_PATH = Path(
    os.environ.get("AQI_HISTORY_PATH", os.path.join(LOCAL_DATA_DIR, "aqi_history.jsonl"))
)
```

- LOCAL → `local_data/aqi_history.jsonl`
- MODAL → `/data/aqi_history.jsonl` (persisted on Modal volume `family-weather-data`)

### Write / read strategy

`fetch_all_aqi()` in `data/fetch_moenv.py`:

1. Fetch realtime AQI (`fetch_realtime_aqi()`).
2. **Immediately** call `_cache_aqi_reading(realtime)` — appends one line.
   The write must precede step 3 so the current reading is included.
3. Fetch 3-day forecast (`fetch_forecast_aqi()`).
4. Call `fetch_hourly_aqi()` — reads today's lines from the JSONL, deduplicates
   by `obs_time`, returns sorted `[{forecast_time, aqi, major_pollutant}, ...]`.

`_cache_aqi_reading()` is a best-effort write: failures log a warning and are
not re-raised so a filesystem error never breaks the broadcast pipeline.

### Surfacing to the user

`_compute_aqi_peak_window(hourly)` in `web/routes.py` receives today's
observed readings and returns:

- `"11:00–16:00"` — if any reading has AQI ≥ 100 (shows the contiguous bad window)
- `"Peak at 11:00 (AQI 70)"` — otherwise, shows the single worst observation

This string appears as a sub-line on the **Air Quality** lifestyle card.
With 3 pipeline runs per day the window is coarse but meaningful; accuracy
improves automatically as more readings accumulate across the day.

### Growth and retention

3 readings/day × 365 = ~1,095 lines/year ≈ 100 KB/year. No rotation is
needed. Unlike `station_history.jsonl` (used for 24 h pressure/temp trends),
`aqi_history.jsonl` is only read for today's date, so old entries are inert
but harmless.
