"""
fetch_moenv.py — MOENV Open Data API client.

Fetches real-time AQI and daily AQI forecast for Tucheng station.
"""

import json
import logging
import requests
import urllib3
from config import (
    MOENV_API_KEY,
    MOENV_BASE_URL,
    MOENV_AQI_DATASET,
    MOENV_FORECAST_DATASET,
    MOENV_FORECAST_AREA,
    MOENV_STATION_NAME,
)

# Disable SSL warnings for MOENV API
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

    resp = requests.get(url, params=params, timeout=15, verify=False)
    resp.raise_for_status()
    body = json.loads(resp.content)  # Use raw bytes → UTF-8 (bypasses requests encoding guessing)

    try:
        # MOENV v2 API returns a list directly, or a dict with "records"
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
    """
    url = f"{MOENV_BASE_URL}/{MOENV_FORECAST_DATASET}"
    params = {
        "api_key": MOENV_API_KEY,
        "format": "JSON",
        # "filters": f"area,EQ,{MOENV_FORECAST_AREA}", # Filter in Python to avoid query encoding issues
        "limit": "100",
    }

    try:
        resp = requests.get(url, params=params, timeout=15, verify=False)
        resp.raise_for_status()
        body = json.loads(resp.content)  # Use raw bytes → UTF-8 (bypasses requests encoding guessing)

        if isinstance(body, list):
            records = body
        else:
            records = body.get("records", [])

        if not records:
            logger.warning("No MOENV AQI forecast records found")
            return {"area": MOENV_FORECAST_AREA, "aqi_range": None, "status": None, "forecast_date": None}

        # Filter for target area (北部空品區 = Northern Air Quality Zone)
        area_records = [r for r in records if r.get("area") == MOENV_FORECAST_AREA]

        if not area_records:
            available = list(set(r.get("area") for r in records))
            logger.warning("No forecast for area '%s'. Available: %s", MOENV_FORECAST_AREA, available)
            return {"area": MOENV_FORECAST_AREA, "aqi_range": None, "status": None, "forecast_date": None}

        # Sort by date
        area_records.sort(key=lambda x: x.get("forecastdate", ""))

        # Pick the earliest available forecast (usually tomorrow if past publication time)
        # Ideally we want Today if available, else Tomorrow.
        rec = area_records[0]

        return {
            "area": rec.get("area"),
            "aqi_range": rec.get("aqi"),
            "status": rec.get("majorpollutant"), # Or content?
            "forecast_date": rec.get("forecastdate"),
            "content": rec.get("content"),
        }

    except Exception as exc:
        logger.warning("Could not fetch MOENV AQI forecast: %s", exc)
        return {"area": MOENV_FORECAST_AREA, "aqi_range": None, "status": None, "forecast_date": None}


def fetch_all_aqi() -> dict:
    """Fetch both real-time and forecast AQI and return as a single dict."""
    realtime = fetch_realtime_aqi()
    forecast = fetch_forecast_aqi()
    return {
        "realtime": realtime,
        "forecast": forecast,
    }


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
