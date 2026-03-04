# API Quirks and Knowledge Base

This document tracks known issues, structures, and workarounds for the external APIs used in this project. Review this before debugging or modifying API interactions.

## ⚠️ Timezone Contract (Read First)

All timestamps throughout this codebase use **Asia/Taipei (UTC+8)** as the single reference timezone.

| Layer | Format | Why |
|-------|--------|-----|
| CWA API response | `"2026-02-27T18:00:00+08:00"` (offset-aware) | API always emits `+08:00` |
| Parsed for comparisons | Naive wall-clock via `.replace(tzinfo=None)` | Segment boundaries (0/6/12/18 h) are Taipei local |
| Frontend timestamps | ISO string with `+08:00` preserved | `new Date("…+08:00")` renders correctly regardless of browser locale |
| `datetime.now()` | Naive local time | Process **must** run in Asia/Taipei; if TZ is wrong, segment assignments silently break |

**Rules:**
- **Never convert CWA timestamps to UTC** before comparing to segment boundaries — the boundaries are Taipei-local hours.
- **Never remove `.replace(tzinfo=None)`** from `_parse_dt` callers without also making `datetime.now()` timezone-aware and consistent.
- Bucket start strings in `fetch_forecast_7day` embed `+08:00` explicitly so the JavaScript `Date` constructor parses them correctly in any locale.

---

## CWA (Central Weather Administration) Open Data API

1. **SSL Certificate Issues**
   - The CWA API often has SSL certificate issues (specifically `Missing Subject Key Identifier` or `CERTIFICATE_VERIFY_FAILED`).
   - **Workaround:** When making requests, always handle the `requests.exceptions.SSLError` by falling back to `verify=False` in the request, and suppress the `InsecureRequestWarning`.

2. **Capitalization & Structure Inconsistencies**
   - The JSON response structure randomly uses different casing for its keys. It may return `Locations` or `locations`, `Location` or `location`, `WeatherElement` or `weatherElement`.
   - **Workaround:** Always use resilient `.get()` fallbacks, e.g.:
     ```python
     locs_wrapper = records.get("Locations", []) or records.get("locations", [])
     ```

3. **Character Encoding on Windows**
   - When printing CWA API responses to the Windows console using `print(r.content.decode('utf-8'))`, it can produce Mojibake due to the terminal's default codepage not supporting the Chinese characters. This is just a console printing issue; `r.json()` parses the text correctly in the app.

4. **Dataset Selection by Frontend View**
   Different frontend views require different CWA dataset IDs (which represent regional areas rather than hardware stations) and parse different subsets of fields:

   - **Dashboard View (Current Conditions)**
     - **Dataset:** `O-A0003-001` (Manual Stations, e.g., Banqiao Station `466881`)
     - **Fields Present:** `AT` (Apparent Temp), `RH`, `WDSD` (Wind Speed), `WDIR` (Wind Dir), `RAIN`, `Wx`, `WxText`, `visibility`, `PRES`, `UVI`.

   - **24-Hour Forecast View**
     - **Dataset:** `F-D0047-069` (New Taipei City 36-hour forecast, point-in-time slots)
     - **Fields Present:** `AT` (with `Temperature` fallback), `RH`, `WS`, `WD`, `PoP6h`, `Wx`.

   - **7-Day Forecast View**
     - **Dataset:** `F-D0047-071` (New Taipei City 7-day forecast, 12-hour period slots)
     - **Fields Present:** `MaxAT`, `MinAT`, `AT`, `RH`, `WS`, `PoP12h`, `Wx`.
   
   - *Note:* Do not mix these up. The `F-D0047` series specifically targets New Taipei City data, while its target "locations" represent townships (e.g., 三峽區, 板橋區) rather than concrete observing stations.

5. **Station ID Validity — Always Verify Against `stations.txt`**
   - Not every station ID that exists informally is recognised by the CWA API. Example: `C0AJ8` returns zero results in both `O-A0001-001` and `O-A0003-001`. The correct sibling auto-station is `C0AJ80`.
   - Station `466881` ("新北") is a **Manual synoptic station** in **新店區 (Xindian)**, not in Banqiao or Shulin. Do not assume the label "新北" means it is geographically near the family's home address.
   - Verified station-to-township mapping (confirmed 2026-03-05):

     | StationId | Name | Township | Dataset |
     |---|---|---|---|
     | `466881` | 新北 | 新店區 | O-A0003-001 (Manual) |
     | `72AI40`  | 桃改臺北 | 樹林區 | O-A0003-001 (Manual) |
     | `72AI40`  | 樹林 | 樹林區 | O-A0001-001 (Auto) |
     | `C0AJ80`  | 板橋 | 板橋區 | O-A0001-001 (Auto) |

6. **`-99` / `-999` Sentinel Values (Missing Observations)**
   - Several auto and manual stations return `-99` (or occasionally `-999`) as a sentinel for instruments that are not installed or not reporting. Fields confirmed to return `-99` for `72AI40` on `O-A0003-001`: `AirPressure`, `UVIndex`, `VisibilityDescription`.
   - **Critical:** `safe_float("-99")` parses silently to `-99.0`. This poisons downstream threshold logic (e.g. UV ≥ 8 = "Very High" never fires; negative pressure skews any pressure-derived calculation).
   - **Workaround:** `safe_float` and `safe_int` in `data/helpers.py` must map `-99.0` and `-999.0` to `None` before returning.

7. **Two-Station Merge Pattern for Work/Commute Conditions**
   - `C0AJ80` (Banqiao auto, `O-A0001-001`) provides good local readings but **lacks** `UVIndex`, `Visibility`, and rich `Weather` text.
   - `466881` (Xindian manual, `O-A0003-001`) provides the full synoptic set but is geographically further away.
   - **Pattern:** Fetch `C0AJ80` first; for any field that comes back `None`, fall back to the matching field from `466881`. Fields that `C0AJ80` supplies always take priority.
   - Relevant config constants to define: `CWA_WORK_STATION_ID = "C0AJ80"`, `CWA_WORK_DATASET = "O-A0001-001"`, `CWA_SYNOPTIC_STATION_ID = "466881"`.

8. **Reference Files & Looping Hazard**
   - **`docs/reference/stations.txt`**: Contains verified Station IDs (e.g., `466881` for Banqiao). Always consult this file instead of guessing station IDs.
   - **`docs/reference/cwa_7day_elements.json`**: Contains the exact Chinese element names returned by the 7-day API. The API often changes the keys or uses Chinese strings like `"最高體感溫度"` instead of English keys like `"MaximumApparentTemperature"`.
   - **CRITICAL:** Do not write loops that continuously retry fetching if a field is "missing" (e.g., `AT` or `PoP12h`). If a field is missing, it is usually because the dataset ID is wrong or the Chinese ElementName was not matched correctly. Read the reference JSON instead of looping over API calls.

6. **Mixed Timestamp Key Within F-D0047-069**
   - Point-in-time elements (`Temperature`, `RelativeHumidity`, `WindSpeed`) use `DataTime` as the timestamp key.
   - Period-based elements (`PoP6h`, `Wx`) use `StartTime`/`EndTime` as the timestamp key.
   - **Workaround:** Always check for `DataTime`/`dataTime` as a fallback after `StartTime`/`EndTime` when extracting slot timestamps. If you remove this fallback, temperatures will silently become `null` and render as `0°` in the UI.

7. **F-D0047-069: Point-in-Time Slots (`end_time == start_time`)**
   - All elements in F-D0047-069 are hourly point-in-time slots where `EndTime == StartTime` (zero-width interval).
   - The `_segment_forecast` function's original midpoint check `s_dt <= t_mid < e_dt` always evaluates `False` on a zero-width interval, causing all segments to return `None` and the 24-Hour Forecast section to render empty.
   - **Workaround:** Detect when `s_dt == e_dt` and use a window check (`t_start <= s_dt < t_end`) instead. Period-based slots (from 7-day datasets) still use the midpoint-overlap check.

8. **F-D0047-071: Missing PoP12h After Day 3**
   - The CWA API intentionally only provides `12小時降雨機率` (`PoP12h`) for the first 3 days (72 hours) of the 7-day forecast due to decreasing forecasting accuracy.
   - **Alternatives:**
     - **Mapping `Wx` Codes:** The `天氣現象` (`Wx` Weather Code) is provided for all 7 days. Rain probability can be inferred categorically by mapping the code (e.g., Codes 8-14 = Showers, 15-18 = Thunderstorms).
     - **UI Fallback:** The frontend should be designed to handle `null` PoP percentages for Days 4-7 gracefully, relying on the rendered weather icon (derived from the `Wx` code) instead.

## MOENV (Ministry of Environment) API

1. **SSL & Timeouts**
   - Similar to CWA, MOENV can experience timeouts and SSL configuration anomalies. Always specify a timeout (e.g. `timeout=20`), and handle `requests.exceptions.SSLError` by falling back to `verify=False`.

2. **Mapping Mismatch: Station vs. Region**
   Unlike the CWA API which consistently uses Township strings (e.g., `三峽區`) for both 24h and 7-day datasets, the MOENV API has a structural split:
   - **Real-time API (`aqx_p_432`)**: Uses specific physical hardware stations. You must filter by `sitename` (e.g., `土城` for Tucheng).
   - **Forecast API (`AQF_P_01`)**: Uses broad regional zones instead of specific stations or townships. You must filter by `area` (e.g., `北部` for the entire Northern Air Quality Zone). 
   - *Note:* Do not attempt to query the forecast API using a station name like `土城`; it will return empty results.

3. **AQI Value Discrepancies**
   - The Realtime API returns an integer `aqi` value.
   - The Forecast API often returns a string range (e.g., `"51-100"`) instead of a single integer. The parsing logic must use `_safe_int()` but allow for string fallbacks.

4. **English/Chinese Responses**
   - Some fields are inherently in Chinese without an English counterpart from the API. When English is requested, the pipeline may need to pass the Chinese text to an LLM for translation.

5. **JSON Structural Variations**
   - MOENV v2 API sometimes returns a direct top-level list `[{...}]` instead of the expected `{"records": [{...}]}`. Always handle both variations flexibly when extracting `records`.
