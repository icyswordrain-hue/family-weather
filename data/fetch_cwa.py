"""
fetch_cwa.py — CWA Open Data API client.

Fetches:
  - Current station observations from Banqiao station (466881 / O-A0003-001)
  - Township 36-hour forecasts for Sanxia and Banqiao (F-D0047-069)
  - Township 7-day forecasts for Sanxia and Banqiao (F-D0047-071)

TIMEZONE NOTE:
  All timestamps returned by the CWA API are in Asia/Taipei (UTC+8) and carry
  an explicit +08:00 offset, e.g. "2026-02-27T18:00:00+08:00".  This file
  intentionally uses datetime.strptime with [:19] slicing to obtain naive Taipei
  wall-clock datetimes for bucket arithmetic in fetch_forecast_7day().  Do NOT
  convert to UTC before aggregating — the 6-hour boundary that separates Day/Night
  buckets is defined in Taipei local time (midnight–06:00 = Night of previous day).
"""

import json
import logging
import requests
from datetime import datetime, timedelta

# AI AGENT NOTE: Read inline comments labeled "AI AGENT NOTE" 
# throughout this file before modifying fetching or parsing logic.
# The CWA API has significant quirks regarding SSL, casing, and encoding.
# CRITICAL: See docs/reference/API_QUIRKS.md for known issues.
# CRITICAL: See docs/reference/stations.txt before guessing Station IDs.
# CRITICAL: See docs/reference/cwa_7day_elements.json for exact dataset element names.
# NEVER write a while loop that retries API calls because a specific field is "missing" (like AT or PoP12h). 
# Missing fields mean your dataset ID or Chinese ElementName match is wrong, NOT a temporary network issue.

from config import (
    CWA_API_KEY,
    CWA_BASE_URL,
    CWA_CURRENT_DATASET,
    CWA_STATION_ID,
    CWA_FORECAST_DATASET,
    CWA_FORECAST_7DAY_DATASET,
    CWA_FORECAST_LOCATIONS,
    CWA_TIMEOUT,
)
from data.helpers import _safe_float, _safe_int

logger = logging.getLogger(__name__)


def fetch_current_conditions() -> dict:
    """
    Fetch latest manual station observations for Banqiao (466881).

    Returns a dict with keys:
        station_id, station_name, obs_time,
        AT (apparent temp °C), RH (%), WDSD (m/s), WDIR (°),
        RAIN (mm past 2h), Wx (weather code int)
    Raises RuntimeError on API failure.
    """
    url = f"{CWA_BASE_URL}/{CWA_CURRENT_DATASET}"
    params = {
        "Authorization": CWA_API_KEY,
        "StationId": CWA_STATION_ID,
        "WeatherElement": "AirTemperature,RelativeHumidity,WindSpeed,WindDirection,Now,Weather,Visibility,AirPressure,UVIndex",
        "format": "JSON",
    }

    try:
        try:
            resp = requests.get(url, params=params, timeout=(5, CWA_TIMEOUT))
            resp.raise_for_status()
        except requests.exceptions.SSLError:
            # AI AGENT NOTE: CWA API SSL Certificate Issues
            # The API often has SSL certificate issues (specifically Missing Subject Key Identifier).
            # Workaround: Always handle SSLError by falling back to verify=False.
            logger.warning("CWA SSL verification failed, retrying with verify=False")
            resp = requests.get(url, params=params, timeout=(5, CWA_TIMEOUT), verify=False)
            resp.raise_for_status()
        
        # Robust decoding
        raw_text = resp.content.decode("utf-8", errors="ignore")
        body = json.loads(raw_text)

        records = body.get("records", {}).get("Station", [])
        if not records:
            raise ValueError(f"No station data returned for StationId={CWA_STATION_ID}")
        
        station = records[0]
        # O-A0001-001 (Auto) vs O-A0003-001 (Manual)
        # Auto: WeatherElement is a dict? No, actually CWA structure varies.
        # Manual: WeatherElement is a dict.
        obs = station.get("WeatherElement", {})
        
        # Helper to get value
        def _get_val(key, default=None):
            if isinstance(obs, dict):
                 return obs.get(key, default)
            # If obs is list (some datasets?), would need iteration
            return default

        # Parse numeric values
        at = _safe_float(_get_val("AirTemperature"))
        rh = _safe_float(_get_val("RelativeHumidity"))
        ws = _safe_float(_get_val("WindSpeed"))
        wd = _safe_float(_get_val("WindDirection"))
        pres = _safe_float(_get_val("AirPressure"))
        uvi = _safe_float(_get_val("UVIndex"))
        
        # Visibility: Check 'Visibility' first, then 'VisibilityDescription'
        vis_raw = _get_val("Visibility")
        vis = _safe_float(vis_raw)
        
        if vis is None:
            vis_desc = _get_val("VisibilityDescription")
            if vis_desc:
                # Handle formats like "11-15", ">30", "15", etc.
                cleaned_desc = str(vis_desc).strip().replace(">", "").replace("<", "")
                if "-" in cleaned_desc:
                    try:
                        low, high = map(float, cleaned_desc.split("-"))
                        vis = (low + high) / 2
                    except:
                        pass
                else:
                    vis = _safe_float(cleaned_desc)
                
                if vis is None:
                    logger.warning(f"Visibility parsing failed for description: {vis_desc}")
        
        # Rain is nested in Now -> Precipitation for Manual?
        # Manual: 'Now': {'Precipitation': '1.0'}
        now = _get_val("Now", {})
        rain = _safe_float(now.get("Precipitation"))

        # Weather code might be missing or -99
        wx_raw = _get_val("Weather")
        wx = _safe_int(wx_raw)
        if wx is not None and wx < 0:
            wx = None

        # Return text description if available (for manual stations)
        wx_text = str(wx_raw) if wx_raw and not isinstance(wx_raw, (int, float)) else None

        return {
            "station_id": station.get("StationId"),
            "station_name": station.get("StationName"),
            "obs_time": station.get("ObsTime", {}).get("DateTime"),
            "AT": at, 
            "RH": rh,
            "WDSD": ws,
            "WDIR": wd,
            "RAIN": rain, 
            "Wx": wx,
            "WxText": wx_text,
            "visibility": vis,
            "PRES": pres,
            "UVI": uvi,
        }

    except Exception as exc:
        logger.error("CWA current-conditions fetch failed: %s", exc)
        raise RuntimeError(f"Failed to fetch CWA current conditions: {exc}") from exc


def fetch_forecast(location_name: str = "三峽區") -> list[dict]:
    """
    Fetch 36-hour township forecast for the given location name.
    """
    url = f"{CWA_BASE_URL}/{CWA_FORECAST_DATASET}"
    params = {
        "Authorization": CWA_API_KEY,
        "format": "JSON",
        "locationName": location_name,
    }

    try:
        resp = requests.get(url, params=params, timeout=(5, CWA_TIMEOUT))
        resp.raise_for_status()
    except requests.exceptions.SSLError:
            # AI AGENT NOTE: CWA API SSL Certificate Issues
            # The API often has SSL certificate issues (specifically Missing Subject Key Identifier).
            # Workaround: Always handle SSLError by falling back to verify=False.
        logger.warning("CWA forecast SSL verification failed, retrying with verify=False")
        resp = requests.get(url, params=params, timeout=(5, CWA_TIMEOUT), verify=False)
        resp.raise_for_status()
    
    # Robust decoding
    # AI AGENT NOTE: Character Encoding on Windows
    # When printing CWA API responses to the Windows console using print(r.content.decode('utf-8')),
    # it can produce Mojibake due to the terminal's default codepage not supporting the characters.
    # This is just a console printing issue; json.loads parses the text correctly in the app.
    raw_text = resp.content.decode("utf-8", errors="ignore")
    body = json.loads(raw_text)

    try:
        # Handle casing differences (Locations vs locations)
        # AI AGENT NOTE: Capitalization & Structure Inconsistencies
        # The JSON response structure randomly uses different casing for its keys. 
        # It may return Locations or locations, Location or location, WeatherElement or weatherElement.
        # Workaround: Always use resilient .get() fallbacks.
        records = body.get("records", {})
        locs_wrapper = records.get("Locations", []) or records.get("locations", [])
        if not locs_wrapper:
             raise ValueError("No Locations found in forecast response")
             
        locations = locs_wrapper[0].get("Location", []) or locs_wrapper[0].get("location", [])
        
        target = next(
            (loc for loc in locations if loc.get("LocationName", "") == location_name or loc.get("locationName", "") == location_name),
            None,
        )
        if target is None:
            # Fallback for Banqiao/Pan-chiao naming?
            # Or log available names
            avail = [l.get("LocationName") or l.get("locationName") for l in locations]
            logger.warning(f"Location '{location_name}' not found. Available: {avail[:5]}...")
            raise ValueError(f"Location '{location_name}' not found in forecast response")

        # Build a time-indexed dict: start_time → element values
        time_slots: dict[str, dict] = {}
        
        # Handle WeatherElement casing
        we_list = target.get("WeatherElement", []) or target.get("weatherElement", [])

        for element in we_list:
            # Inspect first value to guess element type
            time_list = element.get("Time", []) or element.get("time", [])
            if not time_list:
                continue
            
            # Case-insensitive ElementName
            el_name = element.get("ElementName") or element.get("elementName")
            
            for tv in time_list:
                start = tv.get("StartTime") or tv.get("startTime") or tv.get("DataTime") or tv.get("dataTime")
                end = tv.get("EndTime") or tv.get("endTime") or start
                if not start: continue
                
                slot = time_slots.setdefault(start, {"start_time": start, "end_time": end})

                values = tv.get("ElementValue", []) or tv.get("elementValue", [])
                v = values[0] if values else {}
                
                # Extract value from the first key in the dict (e.g. {'Temperature': '20'} -> '20')
                # But we should use the KEY to decide what it is, because ElementName is Chinese/Mojibake
                
                # Check keys in v
                if "probabilityOfPrecipitation" in v or "ProbabilityOfPrecipitation" in v or "PoP" in v or "PoP12h" in v:
                     val = v.get("probabilityOfPrecipitation") or v.get("ProbabilityOfPrecipitation") or v.get("PoP") or v.get("PoP12h")
                     slot["PoP6h"] = _safe_float(val)
                     
                elif "ApparentTemperature" in v:
                    slot["AT"] = _safe_float(v.get("ApparentTemperature"))
                    
                elif "Temperature" in v:
                    # Use T as backup for AT
                    t_val = _safe_float(v.get("Temperature"))
                    if t_val is not None:
                         # Store as AT if AT is missing
                         if slot.get("AT") is None:
                             slot["AT"] = t_val
                             
                elif "RelativeHumidity" in v:
                    slot["RH"] = _safe_float(v.get("RelativeHumidity"))
                    
                elif "WindSpeed" in v:
                    slot["WS"] = _safe_float(v.get("WindSpeed"))
                    
                elif "WindDirection" in v:
                    slot["WD"] = _safe_float(v.get("WindDirection"))
                    
                elif "WeatherCode" in v or "Weather" in v:
                    wx_code = v.get("WeatherCode")
                    if wx_code:
                        slot["Wx"] = _safe_int(wx_code)
                    else:
                        # Try parsing v.get("value") as int
                        slot["Wx"] = _safe_int(v.get("value"))

        # Post-process slots
        results = []
        for slot in sorted(time_slots.values(), key=lambda s: s["start_time"]):
            # Calculate AT average if Min/Max exist
            if "MaxAT" in slot and "MinAT" in slot:
                if slot["MaxAT"] is not None and slot["MinAT"] is not None:
                    slot["AT"] = (slot["MaxAT"] + slot["MinAT"]) / 2.0
                elif slot["MaxAT"] is not None:
                    slot["AT"] = slot["MaxAT"]
                elif slot["MinAT"] is not None:
                    slot["AT"] = slot["MinAT"]
            
            # Ensure required keys exist (default None)
            for k in ("AT", "RH", "WS", "WD", "PoP6h", "Wx"):
                slot.setdefault(k, None)
            
            results.append(slot)

        return results

    except (KeyError, IndexError, TypeError) as exc:
        logger.error("Unexpected CWA forecast response structure: %s", exc)
        # logger.debug("Response body: %s", body)
        raise RuntimeError(f"Failed to parse CWA forecast for '{location_name}': {exc}") from exc


def fetch_all_forecasts() -> dict[str, list[dict]]:
    """Fetch forecasts for all configured locations and return as a dict."""
    result = {}
    for loc in CWA_FORECAST_LOCATIONS:
        try:
            result[loc] = fetch_forecast(loc)
        except Exception as exc:
            logger.warning("Could not fetch forecast for %s: %s", loc, exc)
            result[loc] = []
    return result


def fetch_forecast_7day(location_name: str = "三峽區") -> list[dict]:
    """
    Fetch 7-day township forecast (F-D0047-075) for the given location name.
    """
    url = f"{CWA_BASE_URL}/{CWA_FORECAST_7DAY_DATASET}"
    params = {
        "Authorization": CWA_API_KEY,
        "format": "JSON",
        "locationName": location_name,
    }

    try:
        resp = requests.get(url, params=params, timeout=(5, CWA_TIMEOUT))
        resp.raise_for_status()
    except requests.exceptions.SSLError:
        # AI AGENT NOTE: CWA API SSL Certificate Issues
        # The API often has SSL certificate issues (specifically Missing Subject Key Identifier).
        # Workaround: Always handle SSLError by falling back to verify=False.
        logger.warning("CWA 7-day forecast SSL verification failed, retrying with verify=False")
        resp = requests.get(url, params=params, timeout=(5, CWA_TIMEOUT), verify=False)
        resp.raise_for_status()
    
    raw_text = resp.content.decode("utf-8", errors="ignore")
    body = json.loads(raw_text)

    try:
        records = body.get("records", {})
        locs_wrapper = records.get("Locations", []) or records.get("locations", [])
        if not locs_wrapper:
             raise ValueError("No Locations found in 7-day forecast response")
             
        locations = locs_wrapper[0].get("Location", []) or locs_wrapper[0].get("location", [])
        
        target = next(
            (loc for loc in locations if loc.get("LocationName", "") == location_name or loc.get("locationName", "") == location_name),
            None,
        )
        if target is None:
            raise ValueError(f"Location '{location_name}' not found in 7-day forecast response")

        time_slots: dict[str, dict] = {}
        we_list = target.get("WeatherElement", []) or target.get("weatherElement", [])

        for element in we_list:
            time_list = element.get("Time", []) or element.get("time", [])
            if not time_list:
                continue
            
            el_name = (element.get("ElementName") or element.get("elementName") or "").strip()
            
            for tv in time_list:
                # 7-day forecast uses DataTime for some elements and StartTime for others
                start = tv.get("DataTime") or tv.get("dataTime") or tv.get("StartTime") or tv.get("startTime")
                end = tv.get("EndTime") or tv.get("endTime") or start
                if not start: continue
                
                slot = time_slots.setdefault(start, {"start_time": start, "end_time": end})
                values = tv.get("ElementValue", []) or tv.get("elementValue", [])
                v = values[0] if values else {}
                
                # Use ElementName as primary driver if keys are generic
                if "MaxApparentTemperature" in v or el_name == "最高體感溫度":
                     slot["MaxAT"] = _safe_float(v.get("MaxApparentTemperature") or v.get("value"))
                elif "MinApparentTemperature" in v or el_name == "最低體感溫度":
                     slot["MinAT"] = _safe_float(v.get("MinApparentTemperature") or v.get("value"))
                elif "ApparentTemperature" in v or el_name == "體感溫度":
                     slot["AT"] = _safe_float(v.get("ApparentTemperature") or v.get("value"))
                elif "RelativeHumidity" in v or el_name == "相對濕度" or el_name == "平均相對濕度":
                     val = v.get("RelativeHumidity") or v.get("value")
                     slot["RH"] = _safe_float(val)
                elif "WindSpeed" in v or el_name == "風速":
                     val = v.get("WindSpeed") or v.get("value")
                     slot["WS"] = _safe_float(val)
                elif "ProbabilityOfPrecipitation" in v or "降雨機率" in el_name:
                     val = v.get("ProbabilityOfPrecipitation") or v.get("value")
                     slot["PoP12h"] = _safe_float(val)
                elif "WeatherCode" in v or "天氣現象" in el_name:
                     wx_code = v.get("WeatherCode")
                     if wx_code:
                         slot["Wx"] = _safe_int(wx_code)
                     elif "Weather" in v:
                         w_val = v.get("Weather")
                         if isinstance(w_val, str) and any(c.isdigit() for c in w_val):
                             slot["Wx"] = _safe_int("".join(filter(str.isdigit, w_val)))
                     elif v.get("value"):
                         slot["Wx"] = _safe_int(v.get("value"))

        results = []
        aggregated = {}

        for slot in sorted(time_slots.values(), key=lambda s: s["start_time"]):
            st_str = slot["start_time"]
            try:
                # Slice [:19] strips the +08:00 offset, giving a naive Taipei wall-clock
                # datetime.  This is intentional — see module-level TIMEZONE NOTE.
                dt = datetime.strptime(st_str[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

            # Shift back 6 hours so that 00:00–05:59 "belongs" to the previous
            # calendar Day's Night bucket rather than the next Day bucket.
            # Example: 2026-02-28T03:00 → adj 2026-02-27T21:00 → Night of Feb 27.
            adj_dt = dt - timedelta(hours=6)
            is_night = adj_dt.hour >= 12
            logical_date = adj_dt.strftime("%Y-%m-%d")
            bucket_key = f"{logical_date}_{'Night' if is_night else 'Day'}"
            
            if bucket_key not in aggregated:
                # Canonical start times for each bucket, with explicit +08:00 so
                # the frontend can parse them correctly regardless of browser locale.
                canonical_hr = "18:00:00" if is_night else "06:00:00"
                bucket_start = f"{logical_date}T{canonical_hr}+08:00"
                aggregated[bucket_key] = {
                    "start_time": bucket_start,
                    "AT_list": [],
                    "MaxAT_list": [],
                    "MinAT_list": [],
                    "RH_list": [],
                    "WS_list": [],
                    "PoP12h_list": [],
                    "Wx_list": []
                }
            
            b = aggregated[bucket_key]
            if slot.get("MaxAT") is not None: b["MaxAT_list"].append(slot["MaxAT"])
            if slot.get("MinAT") is not None: b["MinAT_list"].append(slot["MinAT"])
            if slot.get("AT") is not None: b["AT_list"].append(slot["AT"])
            if slot.get("RH") is not None: b["RH_list"].append(slot["RH"])
            if slot.get("WS") is not None: b["WS_list"].append(slot["WS"])
            if slot.get("PoP12h") is not None: b["PoP12h_list"].append(slot["PoP12h"])
            if slot.get("Wx") is not None: b["Wx_list"].append(slot["Wx"])

        for b_key, b in aggregated.items():
            final_slot = {"start_time": b["start_time"]}
            
            def _avg(lst):
                return round(sum(lst) / len(lst), 1) if lst else None
            def _max(lst):
                return max(lst) if lst else None
                
            if b_key.endswith("_Night"):
                final_slot["AT"] = _avg(b["MinAT_list"]) or _avg(b["AT_list"])
            else:
                final_slot["AT"] = _avg(b["MaxAT_list"]) or _avg(b["AT_list"])
            final_slot["RH"] = _avg(b["RH_list"])
            final_slot["WS"] = _avg(b["WS_list"])
            final_slot["PoP12h"] = _max(b["PoP12h_list"])
            final_slot["Wx"] = b["Wx_list"][0] if b["Wx_list"] else None
            
            results.append(final_slot)

        # Sort aggregated results sequentially
        results.sort(key=lambda s: s["start_time"])

        return results

    except (KeyError, IndexError, TypeError) as exc:
        logger.error("Unexpected CWA 7-day forecast response structure: %s", exc)
        raise RuntimeError(f"Failed to parse CWA 7-day forecast for '{location_name}': {exc}") from exc


def fetch_all_forecasts_7day() -> dict[str, list[dict]]:
    """Fetch 7-day forecasts for all configured locations and return as a dict."""
    result = {}
    for loc in CWA_FORECAST_LOCATIONS:
        try:
            result[loc] = fetch_forecast_7day(loc)
        except Exception as exc:
            logger.warning("Could not fetch 7-day forecast for %s: %s", loc, exc)
            result[loc] = []
    return result


# ── Helpers removed (moved to data.helpers) ───────────────────────────────────
