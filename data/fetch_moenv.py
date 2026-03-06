"""
fetch_moenv.py — MOENV Open Data API client.

Fetches real-time AQI and daily AQI forecast for Tucheng station.
"""

import json
import logging
import requests
import urllib3

# AI AGENT NOTE: Read inline comments labeled "AI AGENT NOTE" 
# throughout this file before modifying fetching or parsing logic.
# The MOENV API has dataset structural variations, SSL issues, and types.
# CRITICAL: See docs/reference/API_QUIRKS.md for known issues.
# NEVER write a loop to keep retrying if fields are missing - check the API response structure instead.

from config import (
    MOENV_API_KEY,
    MOENV_BASE_URL,
    MOENV_AQI_DATASET,
    MOENV_FORECAST_DATASET,
    MOENV_FORECAST_AREA,
    MOENV_STATION_NAME,
    MOENV_TIMEOUT,
    MOENV_HOURLY_FORECAST_DATASET,
    MOENV_WARNINGS_DATASET,
)
from data.helpers import _safe_float, _safe_int


logger = logging.getLogger(__name__)


def fetch_realtime_aqi() -> dict:
    """
    Fetch current real-time AQI for Tucheng station.

    Returns a dict with keys:
        station_name, aqi (int), status (str), publish_time (str)
    Raises RuntimeError on failure.
    """
    url = f"{MOENV_BASE_URL}/{MOENV_AQI_DATASET}"
    params = {
        "api_key": MOENV_API_KEY,
        "filters": f"sitename,EQ,{MOENV_STATION_NAME}",
        "format": "JSON",
        "limit": "1",
    }

    try:
        resp = requests.get(url, params=params, timeout=MOENV_TIMEOUT)
        resp.raise_for_status()
    except requests.exceptions.SSLError:
        # AI AGENT NOTE: MOENV API SSL & Timeouts
        # MOENV can experience timeouts and SSL configuration anomalies.
        # Always specify a timeout and handle SSLError by falling back to verify=False.
        logger.warning("MOENV realtime SSL verification failed, retrying with verify=False")
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        resp = requests.get(url, params=params, timeout=MOENV_TIMEOUT, verify=False)
        resp.raise_for_status()
    body = json.loads(resp.content)  # Use raw bytes → UTF-8 (bypasses requests encoding guessing)

    try:
        # AI AGENT NOTE: MOENV JSON Structural Variations
        # MOENV v2 API sometimes returns a direct top-level list `[{...}]` 
        # instead of the expected `{"records": [{...}]}`. Handle both variations.
        if isinstance(body, list):
             records = body
        else:
             records = body.get("records", [])
        if not records:
            raise ValueError(f"No AQI data returned for station '{MOENV_STATION_NAME}'")

        rec = records[0]
        return {
            "station_name": rec.get("sitename"),
            "aqi": _safe_int(rec.get("aqi")),
            "status": rec.get("status"),
            "pm25": _safe_float(rec.get("pm2.5")),
            "pm10": _safe_float(rec.get("pm10")),
            "o3": _safe_float(rec.get("o3")),
            "publish_time": rec.get("publishtime"),
        }

    except (KeyError, IndexError, TypeError) as exc:
        logger.error("Unexpected MOENV realtime AQI response: %s", exc)
        logger.debug("Response body: %s", body)
        raise RuntimeError(f"Failed to parse MOENV real-time AQI: {exc}") from exc


def fetch_forecast_aqi() -> dict:
    """
    Fetch AQI forecast for the Northern Air Quality Zone (which covers New Taipei).
    Target dataset: AQF_P_01 (3-Day Regional Forecast).
    Prefers today's forecast; falls back to the next available date.
    Uses numeric AQI index when available.
    """
    from datetime import datetime, timezone, timedelta
    # AI AGENT NOTE: Timezone — explicitly construct UTC+8 offset rather than
    # relying on the server's local TZ (unlike weather_processor which uses naive
    # datetime.now() and requires the server to run in Asia/Taipei).  This is the
    # preferred pattern for any new code that needs the current Taipei date/time.
    _TAIPEI_TZ = timezone(timedelta(hours=8))
    today_str = datetime.now(_TAIPEI_TZ).strftime("%Y-%m-%d")

    url = f"{MOENV_BASE_URL}/{MOENV_FORECAST_DATASET}"
    params = {
        "api_key": MOENV_API_KEY,
        "format": "JSON",
        "limit": "100",
    }

    try:
        try:
            resp = requests.get(url, params=params, timeout=MOENV_TIMEOUT)
            resp.raise_for_status()
        except requests.exceptions.SSLError:
            # AI AGENT NOTE: MOENV API SSL & Timeouts
            # MOENV can experience timeouts and SSL configuration anomalies.
            # Always specify a timeout and handle SSLError by falling back to verify=False.
            logger.warning("MOENV forecast SSL verification failed, retrying with verify=False")
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            resp = requests.get(url, params=params, timeout=MOENV_TIMEOUT, verify=False)
            resp.raise_for_status()
        body = json.loads(resp.content.decode("utf-8", errors="ignore"))

        body = json.loads(resp.content.decode("utf-8", errors="ignore"))

        # AI AGENT NOTE: MOENV JSON Structural Variations
        # MOENV v2 API sometimes returns a direct top-level list `[{...}]` 
        # instead of the expected `{"records": [{...}]}`. Handle both variations.
        if isinstance(body, list):
            records = body
        else:
            records = body.get("records", [])

        if not records:
            logger.warning("No MOENV AQI forecast records found")
            return {"area": MOENV_FORECAST_AREA, "aqi": None, "status": None, "forecast_date": None}

        # Filter for target area (北部空品區 = Northern Air Quality Zone)
        area_records = [r for r in records if r.get("area") == MOENV_FORECAST_AREA]

        if not area_records:
            available = list(set(r.get("area") for r in records))
            logger.warning("No forecast for area '%s'. Available: %s", MOENV_FORECAST_AREA, available)
            return {"area": MOENV_FORECAST_AREA, "aqi": None, "status": None, "forecast_date": None}

        # Sort by date and prefer today's forecast
        # Sort-only helper — MOENV forecastdate strings have no TZ offset so no
        # stripping or conversion is needed; naive datetime is fine for ordering.
        def _parse_dt(x):
            try:
                # Expecting YYYY-MM-DD HH:MM:SS or similar
                return datetime.strptime(x.get("forecastdate", ""), "%Y-%m-%d %H:%M:%S")
            except Exception:
                return datetime.min

        area_records.sort(key=_parse_dt)
        today_records = [r for r in area_records if r.get("forecastdate", "").startswith(today_str)]
        rec = today_records[0] if today_records else area_records[0]

        # AI AGENT NOTE: MOENV AQI Value Discrepancies
        # The Forecast API often returns a string range (e.g., "51-100") instead of a single integer. 
        # The parsing logic must attempt _safe_int() but allow for string fallbacks.
        # Prefer numeric AQI index over text range if available.
        aqi_val = _safe_int(rec.get("aqi"))
        aqi_range = rec.get("aqi")  # May be a range like "51-100"

        return {
            "area": rec.get("area"),
            "aqi": aqi_val if aqi_val is not None else aqi_range,
            "status": rec.get("majorpollutant"),
            "forecast_date": rec.get("forecastdate"),
            "content": rec.get("content"),
        }

    except Exception as exc:
        logger.warning("Could not fetch MOENV AQI forecast: %s", exc)
        return {"area": MOENV_FORECAST_AREA, "aqi": None, "status": None, "forecast_date": None}


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
                "major_pollutant": r.get("majorpollutant"),
            }
            for r in area_records
        ]
    except Exception as exc:
        logger.warning("Could not fetch MOENV hourly AQI forecast: %s", exc)
        return []


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
                "title":        r.get("itemname") or r.get("alert_title") or r.get("title", "Environmental Warning"),
                "content":      f"{r.get('concentration', '')} {r.get('itemunit', '')}".strip() or r.get("content", ""),
                "publish_time": r.get("monitordate") or r.get("publishtime"),
            }
            for r in area_records
        ]
    except Exception as exc:
        logger.warning("Could not fetch MOENV warnings: %s", exc)
        return []


def fetch_all_aqi() -> dict:
    """Fetch real-time AQI, 3-day forecast, hourly forecast, and active warnings."""
    result = {}
    for key, fn, empty in [
        ("realtime",        fetch_realtime_aqi,          {}),
        ("forecast",        fetch_forecast_aqi,          []),
        ("hourly_forecast", fetch_hourly_aqi,            []),
        ("warnings",        fetch_environmental_warnings, []),
    ]:
        try:
            result[key] = fn()
        except Exception as exc:
            logger.warning("fetch_all_aqi: %s failed: %s", key, exc)
            result[key] = empty
    return result


# ── Helpers removed (moved to data.helpers) ───────────────────────────────────
