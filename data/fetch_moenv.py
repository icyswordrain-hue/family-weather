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
    AQI_HISTORY_PATH,
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

        content_text = rec.get("content") or ""
        paragraphs = [p.strip() for p in content_text.split("\n") if p.strip()]
        return {
            "area": rec.get("area"),
            "aqi": aqi_val if aqi_val is not None else aqi_range,
            "status": rec.get("majorpollutant"),
            "forecast_date": rec.get("forecastdate"),
            "content": rec.get("content"),
            "warnings": paragraphs[:1],
        }

    except Exception as exc:
        logger.warning("Could not fetch MOENV AQI forecast: %s", exc)
        return {"area": MOENV_FORECAST_AREA, "aqi": None, "status": None, "forecast_date": None}


def _cache_aqi_reading(realtime: dict) -> None:
    """Append one realtime AQI snapshot to the local JSONL history cache.

    The cache is written each pipeline run so fetch_hourly_aqi() can return
    today's observed readings (no hourly forecast dataset exists in MOENV).
    Timestamps are normalised to ISO 8601 with seconds so fromisoformat() works
    across Python versions.
    """
    obs_time = realtime.get("publish_time")
    aqi = realtime.get("aqi")
    if not obs_time or aqi is None:
        return
    # "2026-03-07 10:00" → "2026-03-07T10:00:00"
    obs_time_iso = str(obs_time).replace(" ", "T")
    if len(obs_time_iso) == 16:
        obs_time_iso += ":00"
    record = {
        "obs_time": obs_time_iso,
        "aqi":      aqi,
        "pm25":     realtime.get("pm25"),
        "pm10":     realtime.get("pm10"),
        "o3":       realtime.get("o3"),
        "status":   realtime.get("status"),
    }
    try:
        AQI_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with AQI_HISTORY_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as exc:
        logger.warning("Could not cache AQI reading: %s", exc)


def fetch_hourly_aqi() -> list[dict]:
    """Return today's observed AQI readings from the local history cache.

    MOENV has no hourly AQI forecast endpoint — aqx_p_322 (used previously)
    is a daily per-station concentration dataset, not a forecast, and its area
    filter never matched.  Instead, each pipeline run caches the realtime
    Tucheng reading via _cache_aqi_reading(); this function reads back those
    snapshots for the current Taipei date so _compute_aqi_peak_window() can
    show today's observed peak.
    """
    from datetime import datetime, timezone, timedelta
    _TAIPEI_TZ = timezone(timedelta(hours=8))
    today_str = datetime.now(_TAIPEI_TZ).strftime("%Y-%m-%d")

    if not AQI_HISTORY_PATH.exists():
        return []

    seen: dict[str, dict] = {}  # deduplicate by obs_time
    try:
        with AQI_HISTORY_PATH.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    obs_time = r.get("obs_time", "")
                    if obs_time.startswith(today_str) and r.get("aqi") is not None:
                        seen[obs_time] = {
                            "forecast_time":   obs_time,
                            "aqi":             r["aqi"],
                            "major_pollutant": r.get("status"),
                        }
                except Exception:
                    continue
    except Exception as exc:
        logger.warning("Could not read AQI history: %s", exc)
        return []
    return sorted(seen.values(), key=lambda x: x["forecast_time"])


def fetch_all_aqi() -> dict:
    """Fetch real-time AQI, 3-day forecast, and today's observed AQI readings."""
    result: dict = {}

    # Realtime must be cached before fetch_hourly_aqi reads the history file.
    try:
        result["realtime"] = fetch_realtime_aqi()
        _cache_aqi_reading(result["realtime"])
    except Exception as exc:
        logger.warning("fetch_all_aqi: realtime failed: %s", exc)
        result["realtime"] = {}

    for key, fn, empty in [
        ("forecast",        fetch_forecast_aqi, {}),
        ("hourly_forecast", fetch_hourly_aqi,   []),
    ]:
        try:
            result[key] = fn()
        except Exception as exc:
            logger.warning("fetch_all_aqi: %s failed: %s", key, exc)
            result[key] = empty
    return result


# ── Helpers removed (moved to data.helpers) ───────────────────────────────────
