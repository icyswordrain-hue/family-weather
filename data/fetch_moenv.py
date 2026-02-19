"""
fetch_moenv.py — MOENV Open Data API client.

Fetches real-time AQI and daily AQI forecast for Tucheng station.
"""

import logging
import requests
from config import (
    MOENV_API_KEY,
    MOENV_BASE_URL,
    MOENV_AQI_DATASET,
    MOENV_STATION_NAME,
)

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

    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    body = resp.json()

    try:
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
    Fetch today's AQI forecast for the Tucheng / Zhonghe area.

    The MOENV forecast API (aqx_p_02) returns county-level daily forecasts.
    We look for New Taipei City (新北市) entry and return the day's AQI range.

    Returns a dict with keys:
        area, aqi_range (str, e.g. "51-100"), status (str), forecast_date (str)
    Falls back gracefully with a warning if the forecast is unavailable.
    """
    url = f"{MOENV_BASE_URL}/aqx_p_02"
    params = {
        "api_key": MOENV_API_KEY,
        "format": "JSON",
        "filters": "area,EQ,新北市",
        "limit": "1",
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        body = resp.json()

        records = body.get("records", [])
        if not records:
            logger.warning("No MOENV AQI forecast found for 新北市")
            return {"area": "新北市", "aqi_range": None, "status": None, "forecast_date": None}

        rec = records[0]
        return {
            "area": rec.get("area"),
            "aqi_range": rec.get("aqi"),
            "status": rec.get("status"),
            "forecast_date": rec.get("forecastdate"),
        }

    except Exception as exc:
        logger.warning("Could not fetch MOENV AQI forecast: %s", exc)
        return {"area": "新北市", "aqi_range": None, "status": None, "forecast_date": None}


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
