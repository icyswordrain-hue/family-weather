# Historical Station Data Caching

## Why Cache at All

The CWA `O-A0001-001` open data API returns only the **current observation snapshot**
for each station. Once a reading is superseded by the next hourly update, it is gone
from the API. There is no `timeFrom`/`timeTo` parameter, no rolling window, no replay.

A simple append-on-fetch strategy accumulates observations at each pipeline run with
zero extra API calls. This local archive unlocks:

- Pressure trend over 24h (Ménière's alert calculation)
- Intra-day temperature swing (cardiac alert improvement — deferred)
- Dew point history for outdoor score trend (deferred)
- Overnight AT low for cardiac risk window (deferred)
- CWA outage resilience: last known observation used when live fetch fails

---

## Format: JSONL

One JSON object per line. Each line is a self-contained, valid JSON document.

```jsonl
{"fetched_at":"2026-03-06T05:31:04+08:00","station_id":"72AI40","obs_time":"2026-03-06T05:20:00+08:00","AT":17.1,"RH":90.0,"WDSD":0.7,"PRES":1013.1,...,"dew_point_c":15.6,"dew_gap_c":1.5,"apparent_temp_c":14.8,"saturation_label":"near_saturated"}
```

JSONL was chosen because:
- Schema evolves over time — new fields require no migration
- Append is trivially safe (`open("a")`, write one line)
- Each line is independently valid — a crash affects only that line
- `dict.get()` handles records written before a new field was added

File is pruned to the last `STATION_HISTORY_DAYS` (default 7) days after each write.

---

## Schema

Raw CWA field names are preserved in the cache record. Derived fields are appended
at write time so they never need to be recomputed from incomplete inputs later.

| Field | Source | Notes |
|---|---|---|
| `fetched_at` | Pipeline | ISO-8601, UTC+8 — pruning key |
| `station_id` | CWA | Primary station ID |
| `obs_time` | CWA | Authoritative observation timestamp |
| `AT` | CWA | Apparent temperature from station (°C) |
| `RH` | CWA | Relative humidity (%) |
| `WDSD` | CWA | Wind speed (m/s) |
| `WDIR` | CWA | Wind direction (°) |
| `RAIN` | CWA | Precipitation (mm) |
| `PRES` | CWA | Air pressure (hPa) |
| `UVI` | CWA | UV index |
| `WxText` | CWA | Weather description (Chinese) |
| `dew_point_c` | Derived | Magnus formula |
| `dew_gap_c` | Derived | `AT − dew_point_c` |
| `apparent_temp_c` | Derived | Australian BOM formula |
| `saturation_label` | Derived | `near_saturated` / `clammy` / `humid` / `comfortable` / `dry` |

---

## Implementation

### New files

**`data/station_history.py`** — read-side access:

```python
def load_recent_station_history(hours: int = 24) -> list[dict]:
    """Return JSONL records from the last `hours` hours, oldest first."""

def pressure_change_24h(history: list[dict]) -> float | None:
    """hPa change from oldest to newest PRES reading. None if < 2 readings."""
```

**`data/helpers.py`** — thermal helpers shared across modules:

```python
def _dew_point(temp_c, rh) -> float          # Magnus formula
def _apparent_temp(temp_c, rh, wind_ms) -> float   # BOM formula
def _saturation_label(dew_gap) -> str
```

### Modified files

**`data/fetch_cwa.py`** — enrich JSONL write:
- `fetch_current_conditions()` builds a `cache_record = dict(merged)` with derived
  fields injected before writing to JSONL
- Returns the original `merged` dict unchanged (callers see CWA field names as before)
- Falls back to last JSONL record (marked `_stale=True`) when live fetch fails

**`data/health_alerts.py`** — upgrade Ménière's alert:
- `_detect_menieres_alert(current, station_history=None)` — removed stale
  broadcast-history pressure lookup; uses `pressure_change_24h(station_history)`
  with a 6 hPa/24h threshold (finer than the old 8 hPa single-step threshold)
- Falls gracefully when `station_history` is None or has < 2 records

**`data/weather_processor.py`**:
- `process(..., station_history=None)` — threads `station_history` to
  `_detect_menieres_alert` at step 10

**`app.py`**:
- Loads `station_history = load_recent_station_history(hours=24)` after
  `fetch_current_conditions()`, passes to `process()`

---

## Config

In `config.py` (already present):

```python
STATION_HISTORY_PATH  = LOCAL_DATA_DIR / "station_history.jsonl"
STATION_HISTORY_DAYS  = int(os.getenv("STATION_HISTORY_DAYS", 7))
```

---

## File Management

The cache grows at ~220 KB/year. No rotation is needed for years. The 7-day pruning
window is sufficient for all current alert calculations (24h trend).

On the Modal volume (`/data`), the JSONL file persists across pipeline invocations.
`volume.commit()` is called in `modal_app.py`'s `generate()` finally block.

---

## Deferred Features

These use cases will benefit from the cached derived fields but are not wired up yet:

- **Intra-day temp swing** → improve `_cardiac_alert()` with overnight AT low
- **Dew point trend** → outdoor score adjustment based on humidity trajectory
