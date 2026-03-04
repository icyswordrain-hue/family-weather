# 2026-03-05 — Fix Station Location & -99 Sentinel Values

## Summary

Corrected the CWA station configuration: the old home station `466881` (新北) is
physically located in Xindian, not near the family home. Replaced it with the
closest verified station and added proper work-commute station support.

## Changes

### `config.py`
- `CWA_STATION_ID` changed from `466881` → `72AI40` (桃改臺北, Shulin District)
- `CWA_FORECAST_LOCATIONS` changed from `["三峽區", "板橋區"]` → `["樹林區", "板橋區"]`
- Added work/commute station constants:
  - `CWA_WORK_STATION_ID = "C0AJ80"` — Banqiao auto-station (primary)
  - `CWA_WORK_DATASET = "O-A0001-001"`
  - `CWA_SYNOPTIC_STATION_ID = "466881"` — Xindian manual (UV/vis fallback)
  - `CWA_SYNOPTIC_DATASET = "O-A0003-001"`

### `data/helpers.py`
- `safe_float` and `safe_int` now treat `-99.0` and `-999.0` as `None`.
- These are CWA sentinel values for instruments that are not installed or not
  reporting. Previously they silently poisoned threshold checks (e.g. UV index
  appearing as -99 would never trigger "Very High" or "Extreme" alerts).

### `data/fetch_cwa.py`
- New function `fetch_work_conditions()` implementing the two-station merge:
  - Primary call: `C0AJ80` (O-A0001-001) for real local temp/RH/wind/pressure
  - Fallback call: `466881` (O-A0003-001) fills `UVIndex`, `Visibility`, `Weather`
  - Primary fields always win; fallback only fills `None` slots

### `docs/reference/API_QUIRKS.md`
- Added entries #5, #6, #7 documenting:
  - Station ID validity and verified township mapping table
  - `-99`/`-999` sentinel values and the `safe_float` fix
  - Two-station merge pattern for work conditions

### `web/static/app.js`
- `LOCATION_EN` expanded with station-name → English label mappings:
  - `桃改臺北` / `樹林` → `"Shulin Station"` (home)
  - `板橋` → `"Banqiao Station"` (work)
  - `新北` → `"Xindian Stn."` (synoptic fallback, now rarely shown)
  - Township district aliases: `樹林區` → `"Shulin"`, `板橋區` → `"Banqiao"`
- `localiseLocation()` extended for zh-TW: maps raw station names to
  friendly labels (`桃改臺北` → `樹林站`, `板橋` → `板橋站`)
- Boot step text updated: "CWA Banqiao Station" → "CWA Shulin Station"

## Verification

Tested live against CWA API (2026-03-05 07:00 CST):
- `72AI40` home: `AT=18.4`, `UVI=None` (was `-99`), `PRES=None` (not instrumented)
- Work merge: `AT=18.6`, `UVI=0.0`, `PRES=1011.0` ✓
- All three forecast townships (`樹林區`, `板橋區`, `三峽區`) resolve: 56 × 36hr slots, 14 × 7-day slots ✓
