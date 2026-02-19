"""
fetch_cwa.py — CWA Open Data API client.

Fetches:
  - Current station observations from Banqiao station (C0AC70)
  - Township 36-hour forecasts for Sanxia and Banqiao (F-D0047-071)
"""

import json
import logging
import requests
from config import (
    CWA_API_KEY,
    CWA_BASE_URL,
    CWA_CURRENT_DATASET,
    CWA_STATION_ID,
    CWA_FORECAST_DATASET,
    CWA_FORECAST_LOCATIONS,
)

logger = logging.getLogger(__name__)


def fetch_current_conditions() -> dict:
    """
    Fetch latest automatic station observations for Banqiao (C0AC70).

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
        "WeatherElement": "AirTemperature,RelativeHumidity,WindSpeed,WindDirection,Now,Weather,Visibility",
        "format": "JSON",
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        
        # Robust decoding: skip invalid characters (e.g. Big5 artifacts)
        # This prevents 3rd party encoding guesses from introducing mojibake or crashes
        raw_text = resp.content.decode("utf-8", errors="ignore")
        body = json.loads(raw_text)

        records = body.get("records", {}).get("Station", [])
        if not records:
            raise ValueError(f"No station data returned for StationId={CWA_STATION_ID}")
        
        station = records[0]
        # O-A0001-001 structure: WeatherElement is a dict
        obs = station.get("WeatherElement", {})

        # Parse numeric values
        at = _safe_float(obs.get("AirTemperature"))
        rh = _safe_float(obs.get("RelativeHumidity"))
        ws = _safe_float(obs.get("WindSpeed"))
        wd = _safe_float(obs.get("WindDirection"))
        vis = _safe_float(obs.get("Visibility"))
        
        # Rain is nested in Now -> Precipitation
        rain_now = obs.get("Now", {}).get("Precipitation")
        rain = _safe_float(rain_now)

        # Weather code might be missing or -99
        wx_raw = obs.get("Weather")
        wx = _safe_int(wx_raw)
        if wx is not None and wx < 0:
            wx = None

        return {
            "station_id": station.get("StationId"),
            "station_name": station.get("StationName"),
            "obs_time": station.get("ObsTime", {}).get("DateTime"),
            "AT": at, # Using AirTemp as proxy for AT
            "RH": rh,
            "WDSD": ws,
            "WDIR": wd,
            "RAIN": rain, 
            "Wx": wx,
            "visibility": vis,
        }

    except Exception as exc:
        logger.error("CWA current-conditions fetch failed: %s", exc)
        # logger.debug("Response body: %s", body)
        raise RuntimeError(f"Failed to fetch CWA current conditions: {exc}") from exc


def fetch_forecast(location_name: str = "三峽區") -> list[dict]:
    """
    Fetch 36-hour township forecast for the given location name.

    Returns a list of time-element dicts, each containing:
        start_time, end_time,
        AT (apparent temp °C), RH (%), WS (m/s), WD (°),
        PoP6h (%), Wx (weather code int)

    Each dict covers a 6-hour window.
    """
    url = f"{CWA_BASE_URL}/{CWA_FORECAST_DATASET}"
    params = {
        "Authorization": CWA_API_KEY,
        "LocationName": location_name,
        # "ElementName" filter removed to get all elements
        "format": "JSON",
    }

    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    
    # Robust decoding
    raw_text = resp.content.decode("utf-8", errors="ignore")
    body = json.loads(raw_text)

    try:
        locations = body["records"]["Locations"][0]["Location"]
        target = next(
            (loc for loc in locations if loc["LocationName"] == location_name),
            None,
        )
        if target is None:
            raise ValueError(f"Location '{location_name}' not found in forecast response")

        # Build a time-indexed dict: start_time → element values
        time_slots: dict[str, dict] = {}

        for element in target.get("WeatherElement", []):
            # Inspect first value to guess element type
            time_list = element.get("Time", [])
            if not time_list:
                continue
            
            first_val = time_list[0].get("ElementValue", [{}])[0]
            val_keys = first_val.keys()

            for tv in time_list:
                start = tv["StartTime"]
                end = tv["EndTime"]
                slot = time_slots.setdefault(start, {"start_time": start, "end_time": end})

                values = tv.get("ElementValue", [{}])
                v = values[0] if values else {}

                # Map based on keys found
                if "ApparentTemperature" in val_keys: # Strict match unlikely, usually Max/Min
                    slot["AT"] = _safe_float(v.get("ApparentTemperature"))
                elif "MaxApparentTemperature" in val_keys:
                    slot["MaxAT"] = _safe_float(v.get("MaxApparentTemperature"))
                elif "MinApparentTemperature" in val_keys:
                    slot["MinAT"] = _safe_float(v.get("MinApparentTemperature"))
                elif "RelativeHumidity" in val_keys:
                    slot["RH"] = _safe_float(v.get("RelativeHumidity"))
                elif "WindSpeed" in val_keys:
                    slot["WS"] = _safe_float(v.get("WindSpeed"))
                elif "WindDirection" in val_keys:
                    slot["WD"] = _safe_float(v.get("WindDirection"))
                elif "ProbabilityOfPrecipitation" in val_keys:
                    slot["PoP6h"] = _safe_float(v.get("ProbabilityOfPrecipitation"))
                elif "WeatherCode" in val_keys:
                    slot["Wx"] = _safe_int(v.get("WeatherCode"))

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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
