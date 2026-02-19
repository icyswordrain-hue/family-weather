"""
fetch_cwa.py — CWA Open Data API client.

Fetches:
  - Current station observations from Banqiao station (O-A0003-001)
  - Township 36-hour forecasts for Sanxia and Banqiao (F-D0047-071)
"""

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
    Fetch latest automatic station observations for Banqiao (C0D660).

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
        "WeatherElement": "AT,RH,WDSD,WDIR,RAIN,Weather",
        "format": "JSON",
    }

    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    body = resp.json()

    try:
        records = body["records"]["Station"]
        if not records:
            raise ValueError(f"No station data returned for StationId={CWA_STATION_ID}")
        station = records[0]
        obs = station["WeatherElement"]

        def _val(element_name: str):
            """Return the numeric value for a named weather element, or None."""
            for el in obs if isinstance(obs, list) else obs.values():
                # The API returns a list of element dicts
                if isinstance(el, dict) and el.get("ElementName") == element_name:
                    v = el.get("ElementValue", [{}])
                    if isinstance(v, list) and v:
                        raw = v[0].get("ElementValue") or v[0].get("value")
                    else:
                        raw = v
                    try:
                        return float(raw)
                    except (TypeError, ValueError):
                        return raw
            return None

        # O-A0003-001 returns elements as a dict keyed by element name
        weather_elements = station.get("WeatherElement", {})

        def _get(key, sub="value"):
            """Extract a value from the WeatherElement dict."""
            el = weather_elements.get(key, {})
            if isinstance(el, dict):
                return el.get(sub) or el.get("ElementValue")
            return el

        return {
            "station_id": station.get("StationId"),
            "station_name": station.get("StationName"),
            "obs_time": station.get("ObsTime", {}).get("DateTime"),
            "AT": _safe_float(_get("AT")),
            "RH": _safe_float(_get("RH")),
            "WDSD": _safe_float(_get("WDSD")),
            "WDIR": _safe_float(_get("WDIR")),
            "RAIN": _safe_float(_get("RAIN")),
            "Wx": _safe_int(_get("Weather")),
        }

    except (KeyError, IndexError, TypeError) as exc:
        logger.error("Unexpected CWA current-conditions response structure: %s", exc)
        logger.debug("Response body: %s", body)
        raise RuntimeError(f"Failed to parse CWA current conditions: {exc}") from exc


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
        "ElementName": "AT,RH,WS,WD,PoP6h,Wx",
        "format": "JSON",
    }

    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    body = resp.json()

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
            el_name = element["ElementName"]
            for tv in element.get("Time", []):
                start = tv["StartTime"]
                end = tv["EndTime"]
                slot = time_slots.setdefault(start, {"start_time": start, "end_time": end})

                # Each element may have multiple values; pick the first meaningful one
                values = tv.get("ElementValue", [{}])
                raw = None
                for v in values:
                    # Try common key names
                    for key in ("ApparentTemperature", "RelativeHumidity",
                                "WindSpeed", "WindDirection",
                                "ProbabilityOfPrecipitation", "WeatherCode",
                                "value", "Value"):
                        if key in v:
                            raw = v[key]
                            break
                    if raw is not None:
                        break

                if el_name == "AT":
                    slot["AT"] = _safe_float(raw)
                elif el_name == "RH":
                    slot["RH"] = _safe_float(raw)
                elif el_name == "WS":
                    slot["WS"] = _safe_float(raw)
                elif el_name == "WD":
                    slot["WD"] = _safe_float(raw)
                elif el_name == "PoP6h":
                    slot["PoP6h"] = _safe_float(raw)
                elif el_name == "Wx":
                    slot["Wx"] = _safe_int(raw)

        # Return sorted by start_time
        return sorted(time_slots.values(), key=lambda s: s["start_time"])

    except (KeyError, IndexError, TypeError) as exc:
        logger.error("Unexpected CWA forecast response structure: %s", exc)
        logger.debug("Response body: %s", body)
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
