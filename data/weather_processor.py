"""
processor.py — Orchestrates raw CWA + MOENV data into a structured, narration-ready payload.

Domain logic has been extracted to specialized modules:
  - data/scales.py          — scale tables and lookup helpers
  - data/health_alerts.py   — cardiac and Ménière's alert detection
  - data/meal_classifier.py — meal mood classification
  - data/outdoor_scoring.py — outdoor suitability index
  - data/location_loader.py — OUTDOOR_LOCATIONS from locations.json

Orchestration rules applied here:
  - Time segment grouping (Morning / Afternoon / Evening / Overnight)
  - Forecast enrichment (apparent temp, wind text, precip text)
  - Low Deviation Detection (meaningful transitions between segments)
  - Commute window interpolation (07:00–08:30, 17:00–18:30)
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, cast

from config import MEAL_FALLBACK_DISH, AQI_ALERT_THRESHOLD, LOCATION_LAT, LOCATION_LON
from data.solar import get_solar_times

logger = logging.getLogger(__name__)

from data.location_loader import OUTDOOR_LOCATIONS
from data.scales import (
    BEAUFORT_SCALE_5, UV_SCALE, PRES_SCALE_5, VIS_SCALE_5,
    _val_to_scale, _wind_to_level, _aqi_to_level, wind_ms_to_beaufort, _beaufort_index,
    wx_to_cloud_cover, degrees_to_cardinal, pop_to_text, translate_aqi_status, translate_pollutant,
    wx_to_pop, dew_gap_to_hum,
    pop_to_safe_minutes, safe_minutes_to_level, _wx_to_rain_risk,
)
from data.health_alerts import _cardiac_alert, _detect_menieres_alert, _compute_heads_ups
from data.meal_classifier import _classify_meal_mood, _extract_recent_meals
from data.outdoor_scoring import _compute_outdoor_index, _classify_outdoor_mood, _extract_recent_locations

AQI_STATUS_MAP = {
    "良好": {"en": "Expected to be Good", "zh_TW": "預測為「良好」"},
    "普通": {"en": "Expected to be Moderate", "zh_TW": "預測為「普通」"},
    "橘色提醒": {"en": "Expected to be Unhealthy for Sensitive Groups", "zh_TW": "預測為「橘色提醒」"},
    "紅害": {"en": "Expected to be Unhealthy", "zh_TW": "預測為「紅害」"},
    "紫爆": {"en": "Expected to be Very Unhealthy", "zh_TW": "預測為「紫爆」"},
}

def extract_aqi_summary(content: str, lang: str = "zh_TW") -> str:
    import re
    if not content:
        return "No forecast data available." if lang == "en" else "暫無預測資料。"
    
    # Try to find the status for Northern region (北部)
    match = re.search(r'北部[^「]*「([^」]+)」', content)
    if match:
        status_zh = match.group(1)
        if status_zh in AQI_STATUS_MAP:
            if lang == "en":
                return f"Tomorrow's air quality is {AQI_STATUS_MAP[status_zh]['en']}."
            else:
                return f"明日北部空氣品質{AQI_STATUS_MAP[status_zh]['zh_TW']}等級。"
                
    # Fallback to a truncated version of the raw content if regex fails
    return content[:100] + "..." if len(content) > 100 else content

# ── Time segment boundaries (local hour, 24h) ────────────────────────────────
SEGMENTS = {
    "Overnight": (0, 6),
    "Morning":   (6, 12),
    "Afternoon": (12, 18),
    "Evening":   (18, 24),
}

SEGMENT_ORDER = ["Morning", "Afternoon", "Evening", "Overnight"]

def _calculate_apparent_temp(ta: float | None, rh: float | None, ws: float | None) -> float | None:
    """Calculates apparent temperature (AT) using the Australian Bureau of Meteorology formula."""
    if ta is None or rh is None:
        return ta
    e = (rh / 100) * 6.105 * (2.71828 ** (17.27 * ta / (237.7 + ta)))
    return round(ta + 0.33 * e - 0.7 * (ws or 0) - 4.0, 1)

def _calculate_dew_point(temp_c: float | None, rh: float | None) -> float | None:
    """Magnus formula dew point approximation. Accurate to ±0.35°C."""
    import math
    if temp_c is None or rh is None or rh <= 0:
        return None
    a, b = 17.27, 237.7
    gamma = (a * temp_c / (b + temp_c)) + math.log(rh / 100)
    return round((b * gamma) / (a - gamma), 1)

def _calculate_dew_gap(temp_c: float | None, dew_point_c: float | None) -> float | None:
    """Degrees between air temperature and dew point. Smaller = clammier."""
    if temp_c is None or dew_point_c is None:
        return None
    return round(temp_c - dew_point_c, 1)

def _saturation_label(dew_gap_c: float) -> str:
    """Snake-case comfort label from dew gap, for LLM context and internal logic."""
    if dew_gap_c < 2:  return "near_saturated"
    if dew_gap_c < 5:  return "clammy"
    if dew_gap_c < 10: return "humid"
    if dew_gap_c < 15: return "comfortable"
    return "dry"

def _calculate_apparent_temp_from_dew(
    temp_c: float | None, dew_point_c: float | None, wind_ms: float | None
) -> float | None:
    """BOM AT using dew point as humidity input. Preferred over RH path when dew point is available."""
    import math
    if temp_c is None or dew_point_c is None:
        return None
    e = 6.105 * math.exp((17.27 * dew_point_c) / (237.7 + dew_point_c))
    return round(temp_c + (0.33 * e) - (0.70 * (wind_ms or 0)) - 4.00, 1)

def _parse_dt(dt_str: str) -> datetime:
    # AI AGENT NOTE: Timezone Stripping — read before editing.
    # CWA timestamps are always offset-aware: "2026-02-27T18:00:00+08:00" (UTC+8 / Asia/Taipei).
    # fromisoformat() returns an aware datetime.  Callers that compare against naive datetimes
    # (e.g. datetime.now()) MUST strip the tzinfo with .replace(tzinfo=None).  This is safe
    # ONLY because the wall-clock hour in the +08:00 timestamp matches Taipei local time, and
    # this server/script MUST be configured to run in Asia/Taipei (UTC+8).  If the server were
    # moved to another timezone the comparisons would silently produce wrong segment assignments.
    # Preferred alternative for new code: datetime.now(timezone(timedelta(hours=8)))
    # as used in fetch_moenv.fetch_forecast_aqi — that pattern is TZ-agnostic.
    return datetime.fromisoformat(dt_str)

# ── Public Entry Point ────────────────────────────────────────────────────────
# OUTDOOR_WEIGHTS extracted to data/outdoor_scoring.py
# OUTDOOR_LOCATIONS extracted to locations.json and served via location_loader.py


# ═══════════════════════════════════════════════════════════════════════════════
# Public entry point
# ═══════════════════════════════════════════════════════════════════════════════

def process(
    current: dict,
    forecasts: dict[str, list[dict]],
    aqi: dict,
    history: list[dict] | None = None,
    forecasts_7day: dict[str, list[dict]] | None = None,
    station_history: list[dict] | None = None,
) -> dict:
    """
    Main processing function.

    Args:
        current:   Output of fetch_cwa.fetch_current_conditions()
        forecasts: Output of fetch_cwa.fetch_all_forecasts()
        aqi:       Output of fetch_moenv.fetch_all_aqi()
        history:   Last N days of conversation history dicts (oldest first)

    Returns:
        A structured dict ready to be embedded in the Gemini narration prompt.
    """
    history = history or []

    # ── 1. Enrich current conditions ─────────────────────────────────────────
    logger.debug("Step 1 - Enrich current")
    current_processed = _process_current(current, aqi["realtime"])

    # ── 2. Choose primary forecast location (Sanxia first, fallback Banqiao) ─
    primary_slots = forecasts.get("三峽區") or forecasts.get("板橋區") or []
    banqiao_slots = forecasts.get("板橋區") or []

    # ── 2b. Choose 7-day primary forecast ────────────────────────────────────
    forecasts_7day = forecasts_7day or {}
    primary_7day_slots = forecasts_7day.get("三峽區") or forecasts_7day.get("板橋區") or []
    for slot in primary_7day_slots:
        # AT is already apparent temperature from the CWA API (MaxAT/MinAT) — do not recalculate
        slot["wind_text"] = wind_ms_to_beaufort(slot.get("WS"))
        
        pop = slot.get("PoP12h")
        if pop is None:
            pop = wx_to_pop(slot.get("Wx"))
            
        wx   = slot.get("Wx")
        risk = _wx_to_rain_risk(wx)
        if risk is None:
            safe_min = 720
        else:
            safe_min = pop_to_safe_minutes(pop, window_minutes=720, risk_pct=risk * 100)
        slot["safe_minutes"]  = safe_min
        slot["precip_level"], slot["precip_text"] = safe_minutes_to_level(safe_min)
        slot["cloud_cover"] = wx_to_cloud_cover(slot.get("Wx"))

    # ── 3. Segment the forecast ───────────────────────────────────────────────
    logger.debug("Step 3 - Segment forecast calling...")
    segmented = _segment_forecast(primary_slots)
    logger.debug("Step 3 - Segmented done. Keys: %s", list(segmented.keys()))

    # ── 4. Enrich each segment ────────────────────────────────────────────────
    logger.debug("Step 4 - Enriching segments")
    for seg_name, seg in segmented.items():
        if seg:
            # Use actual air temperature (T) as BOM formula input.
            # AT from the 36-hour API is CWA's pre-computed apparent temperature —
            # applying the formula to it would double-count humidity/wind.
            ta = seg.get("T") if seg.get("T") is not None else seg.get("AT")
            rh = seg.get("RH")
            ws = seg.get("WS")
            dew_point = _calculate_dew_point(ta, rh)
            dew_gap   = _calculate_dew_gap(ta, dew_point)
            feels_like = (
                _calculate_apparent_temp_from_dew(ta, dew_point, ws)
                or _calculate_apparent_temp(ta, rh, ws)
            )
            if feels_like is not None:
                seg["AT"] = feels_like
            seg["dew_point"]        = dew_point
            seg["dew_gap"]          = dew_gap
            seg["saturation_label"] = _saturation_label(dew_gap) if dew_gap is not None else None
            seg["hum_text"], seg["hum_level"] = dew_gap_to_hum(dew_gap)

            # 5-Level Metrics
            seg["wind_text"], seg["wind_level"] = _val_to_scale(ws, BEAUFORT_SCALE_5)
            seg["wind_dir_text"] = degrees_to_cardinal(seg.get("WD"))

            pop6h = seg.get("PoP6h")
            wx    = seg.get("Wx")
            risk  = _wx_to_rain_risk(wx)
            if risk is None:
                # No rain in forecast — full window safe
                safe_min = 360
            else:
                safe_min = pop_to_safe_minutes(pop6h, window_minutes=360, risk_pct=risk * 100)
            seg["safe_minutes"] = safe_min
            seg["precip_level"], seg["precip_text"] = safe_minutes_to_level(safe_min)
            seg["cloud_cover"] = wx_to_cloud_cover(seg.get("Wx"))

            # Add placeholders for text segments if needed
            seg["beaufort_desc"] = seg["wind_text"]

    # ── 5. Low Deviation Detection ────────────────────────────────────────────
    logger.debug("Step 5 - Transitions")
    transitions = _detect_transitions(segmented, aqi)

    # ── 6. Commute windows ────────────────────────────────────────────────────
    logger.debug("Step 6 - Commute")
    morning_commute = _commute_window(primary_slots, 7, 8.5, current)
    evening_commute = _commute_window(primary_slots, 17, 18.5, current)

    # ── 7. Meal mood ─────────────────────────────────────────────────────────
    logger.debug("Step 7 - Meal mood")
    meal_mood = _classify_meal_mood(segmented)
    recent_meals = _extract_recent_meals(history, days=3)

    # Filter meal suggestions to avoid recent repeats
    filtered_meals = [s for s in meal_mood.get("all_suggestions", []) if not any(r in s for r in recent_meals)]
    
    # Spec: Pick ONE dish for the day
    pool = filtered_meals if filtered_meals else meal_mood.get("all_suggestions", [MEAL_FALLBACK_DISH])
    dish = random.choice(pool) if pool else MEAL_FALLBACK_DISH
    meal_mood["top_suggestions"] = [dish]

    # ── 8. Climate control & cardiac safety ───────────────────────────────────
    climate_recs = _climate_control(segmented, aqi)
    cardiac_alert = _cardiac_alert(segmented)

    # ── 9. Forecast AQI ──────────────────────────────────────────────────────
    raw_aqi_forecast = aqi.get("forecast", {})
    aqi_forecast = {
        "area": raw_aqi_forecast.get("area"),
        "aqi": raw_aqi_forecast.get("aqi"),
        "status": translate_pollutant(raw_aqi_forecast.get("status")),
        "forecast_date": raw_aqi_forecast.get("forecast_date"),
        "content": raw_aqi_forecast.get("content"),
        "warnings": raw_aqi_forecast.get("warnings", []),
    }

    # ── 10. Heads-up priority system ─────────────────────────────────────────
    menieres_alert = _detect_menieres_alert(current_processed, station_history=station_history)
    heads_ups = _compute_heads_ups(
        segmented, morning_commute, evening_commute, aqi, cardiac_alert, menieres_alert
    )

    # ── 11. Outdoor index ────────────────────────────────────────────────────
    logger.debug("Step 11 - Outdoor index")
    outdoor_index = _compute_outdoor_index(
        current_processed, segmented,
        aqi["realtime"].get("aqi"),
        menieres_alert, cardiac_alert,
    )

    # ── 7b. Outdoor location recommendations (deferred until outdoor_index ready)
    logger.debug("Step 7b - Outdoor locations")
    location_rec = _classify_outdoor_mood(segmented, aqi, outdoor_index)
    recent_locations = _extract_recent_locations(history, days=3)

    # Filter locations to avoid recently suggested spots
    filtered_locations = [
        loc for loc in location_rec.get("all_locations", [])
        if loc["name"] not in recent_locations
    ]
    location_rec["top_locations"] = (filtered_locations if filtered_locations
                                     else location_rec.get("all_locations", []))

    aqi_forecast["hourly"] = aqi.get("hourly_forecast", [])
    aqi_forecast["summary_en"] = extract_aqi_summary(aqi_forecast.get("content", ""), "en")
    aqi_forecast["summary_zh"] = extract_aqi_summary(aqi_forecast.get("content", ""), "zh_TW")

    # ── 12. Solar times ───────────────────────────────────────────────────────
    today = datetime.now().date()
    solar = get_solar_times(today, LOCATION_LAT, LOCATION_LON)

    # Tag each forecast segment with is_daylight
    for seg_name, seg in segmented.items():
        if seg:
            seg_start = seg.get("start_time", "")
            seg_end   = seg.get("end_time", "")
            try:
                s_hour = _parse_dt(seg_start).replace(tzinfo=None).hour
                e_hour = _parse_dt(seg_end).replace(tzinfo=None).hour or 24
            except Exception:
                s_hour, e_hour = 0, 0
            sr_hour = int(solar["sunrise"].split(":")[0])
            ss_hour = int(solar["sunset"].split(":")[0])
            # Segment is daylight if it overlaps [sunrise_hour, sunset_hour)
            seg["is_daylight"] = s_hour < ss_hour and e_hour > sr_hour

    return {
        "current": current_processed,
        "forecast_segments": segmented,
        "forecast_7day": primary_7day_slots,
        "transitions": transitions,
        "heads_ups": heads_ups,
        "commute": {
            "morning": morning_commute,
            "evening": evening_commute,
        },
        "meal_mood": meal_mood,
        "recent_meals": recent_meals,
        "location_rec": location_rec,
        "recent_locations": recent_locations,
        "climate_control": climate_recs,
        "cardiac_alert": cardiac_alert,
        "menieres_alert": menieres_alert,
        "aqi_realtime": aqi["realtime"],
        "aqi_forecast": aqi_forecast,
        "outdoor_index": outdoor_index,
        "solar": solar,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _process_current(current: dict, aqi_realtime: dict) -> dict:
    """Enrich raw current-condition dict with derived fields."""
    result = dict(current)
    
    # 1. Temperature & Feels-like
    ta = current.get("AT")
    rh = current.get("RH")
    ws = current.get("WDSD")
    dew_point = _calculate_dew_point(ta, rh)
    dew_gap   = _calculate_dew_gap(ta, dew_point)
    calculated_at = (
        _calculate_apparent_temp_from_dew(ta, dew_point, ws)
        or _calculate_apparent_temp(ta, rh, ws)
    )
    if calculated_at is not None:
        result["AT"] = calculated_at
    result["dew_point"]       = dew_point
    result["dew_gap"]         = dew_gap
    result["saturation_label"] = _saturation_label(dew_gap) if dew_gap is not None else None

    # 2. Main Conditions & Icons
    wx_code = current.get("Wx")
    wx_source_text = current.get("WxText")
    result["Wx_text"] = wx_source_text or wx_to_cloud_cover(wx_code)
    
    # 3. 5-Level Metrics
    # UV
    uv_val = current.get("UVI")
    uv_txt, uv_lvl = _val_to_scale(uv_val, UV_SCALE)
    result["uv_text"] = uv_txt
    result["uv_level"] = uv_lvl
    
    # Humidity — dew-gap-based label is more stable than RH threshold
    hum_txt, hum_lvl = dew_gap_to_hum(dew_gap)
    result["hum_text"] = hum_txt
    result["hum_level"] = hum_lvl
    
    # Pressure
    pres_val = current.get("PRES")
    pres_txt, pres_lvl = _val_to_scale(pres_val, PRES_SCALE_5)
    result["pres_text"] = pres_txt
    result["pres_level"] = pres_lvl
    
    # Wind
    wind_ms = current.get("WDSD")
    result["wind_text"] = wind_ms_to_beaufort(wind_ms)
    result["wind_level"] = _wind_to_level(wind_ms)
    result["wind_dir_text"] = degrees_to_cardinal(current.get("WDIR"))

    # AQI
    aqi_val = aqi_realtime.get("aqi")
    result["aqi"] = aqi_val
    result["aqi_status"] = translate_aqi_status(aqi_realtime.get("status"))
    result["aqi_level"] = _aqi_to_level(aqi_val)
    if aqi_realtime.get("pm25") is not None: result["pm25"] = aqi_realtime["pm25"]
    if aqi_realtime.get("pm10") is not None: result["pm10"] = aqi_realtime["pm10"]
    if aqi_realtime.get("o3")   is not None: result["o3"]   = aqi_realtime["o3"]
    
    # Visibility
    vis_val = current.get("visibility")
    vis_txt, vis_lvl = _val_to_scale(vis_val, VIS_SCALE_5)
    result["vis_text"] = vis_txt
    result["vis_level"] = vis_lvl
    
    # Ground State
    rain_val = current.get("RAIN") or 0.0
    if rain_val > 0 or (wx_code is not None and wx_code >= 10):
        result["ground_state"] = "Wet"
        result["ground_level"] = 5
    else:
        result["ground_state"] = "Dry"
        result["ground_level"] = 1
        
    return result



def _segment_forecast(
    slots: list[dict],
    now: datetime | None = None,
) -> dict[str, Optional[dict]]:
    """
    Assign each forecast slot to a named time segment.
    Handles 6h slots and 12h slots (e.g. 18-06) that cover multiple segments.

    TIMEZONE CONTRACT:
      - CWA slot timestamps carry +08:00 (Asia/Taipei).  They are stripped to
        naive datetimes via .replace(tzinfo=None) so their wall-clock hours can
        be compared directly against the naive `now_dt`.
      - `now` defaults to datetime.now() (naive local time).  This is correct
        only when the process runs in Asia/Taipei (UTC+8).  Pass an explicit
        aware or naive Taipei datetime in tests or when running in another TZ.
      - Do NOT convert to UTC before comparing — the segment boundaries (6, 12,
        18, 0) are defined in Taipei local hours.
    """
    if not slots:
        return {s: None for s in SEGMENT_ORDER}

    # Sort slots by start time
    slots = sorted(slots, key=lambda x: x["start_time"])
    found: dict[str, Optional[dict]] = {s: None for s in SEGMENT_ORDER}
    # AI AGENT NOTE: datetime.now() is naive local time.  Must be Taipei (UTC+8)
    # to match the wall-clock hours embedded in the stripped CWA timestamps (see _parse_dt).
    now_dt = now or datetime.now()

    # 1. Determine starting segment based on current time
    current_hour = now_dt.hour
    start_idx = 0
    if 6 <= current_hour < 12:
        start_idx = 0 # Morning
    elif 12 <= current_hour < 18:
        start_idx = 1 # Afternoon
    elif 18 <= current_hour < 24:
        start_idx = 2 # Evening
    else:
        start_idx = 3 # Overnight

    # 2. Build target window sequence (next 4 segments)
    target_sequence = []
    current_seg_idx = start_idx
    target_day = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    for i in range(5):
        idx = int((current_seg_idx + i) % 4)
        seg_name = SEGMENT_ORDER[idx]
        lo, hi = SEGMENTS[seg_name]
        
        actual_day = target_day
        if i > 0:
            prev_lo, _ = SEGMENTS[SEGMENT_ORDER[int((current_seg_idx + i - 1) % 4)]]
            if lo < prev_lo:
                target_day += timedelta(days=1)
                actual_day = target_day
        else:
            if current_hour >= hi and hi <= 6:
                target_day += timedelta(days=1)
                actual_day = target_day
        
        target_sequence.append((seg_name, actual_day, int(lo), int(hi)))

    # 3. Fill the found dict using target windows
    for seg_name, day, lo, hi in target_sequence:
        # Skip if we already found a valid slot for this segment
        if found[seg_name] is not None:
            continue

        # Search for a slot that covers this day/hour window
        for slot in slots:
            try:
                # Strip +08:00 so wall-clock hours are comparable to naive now_dt.
                # Safe only when server TZ == Asia/Taipei — see _parse_dt docstring.
                s_dt = _parse_dt(slot["start_time"]).replace(tzinfo=None)
                e_dt = _parse_dt(slot["end_time"]).replace(tzinfo=None)

                # Normalize target start/end for comparison
                t_start = day + timedelta(hours=lo)
                t_end = day + timedelta(hours=hi)

                # F-D0047-069 returns hourly point-in-time slots where end_time == start_time.
                # In that case the midpoint interval check (s_dt <= t_mid < e_dt) always fails
                # because the interval is zero-width.  Fall back to a window check instead:
                # accept any slot whose timestamp falls within [t_start, t_end).
                if s_dt == e_dt:
                    if t_start <= s_dt < t_end:
                        found[seg_name] = dict(slot)
                        break
                else:
                    # Period-based slot: use midpoint-overlap check
                    t_mid = t_start + (t_end - t_start) / 2
                    if s_dt <= t_mid < e_dt:
                        found[seg_name] = dict(slot)
                        break
            except Exception:
                continue

    return cast(dict[str, Optional[dict]], found)


def _average_slots(slots: list[dict]) -> dict:
    """Average numeric fields across multiple time slots."""
    result = {"start_time": slots[0]["start_time"], "end_time": slots[-1]["end_time"]}
    numeric_keys = ["AT", "T", "RH", "WS", "WD", "PoP6h"]
    for key in numeric_keys:
        values = [float(s[key]) for s in slots if s.get(key) is not None]
        # pyre-ignore[6]: Pyre2 has trouble with round() overloads here
        result[key] = round(sum(values) / len(values), 1) if values else None
    # For Wx and wind direction, take the most common / last value
    result["Wx"] = slots[-1].get("Wx")
    return result


def _detect_transitions(
    segmented: dict[str, Optional[dict]],
    aqi: dict,
) -> list[dict]:
    """
    Apply Low Deviation Detection between adjacent segments.
    Returns a list of transition dicts describing breached thresholds.
    """
    transitions = []
    aqi_val = aqi.get("realtime", {}).get("aqi") or 0

    for i in range(len(SEGMENT_ORDER) - 1):
        a_name = SEGMENT_ORDER[i]
        b_name = SEGMENT_ORDER[i + 1]
        a = segmented.get(a_name)
        b = segmented.get(b_name)
        if a is None or b is None:
            continue
        
        # Explicitly narrowed for Pyre2
        assert a is not None
        assert b is not None

        breaches = []

        # Apparent temperature within 5°C
        if a.get("AT") is not None and b.get("AT") is not None:
            if abs(b["AT"] - a["AT"]) > 5:
                breaches.append({
                    "metric": "AT",
                    "from": a["AT"],
                    "to": b["AT"],
                    "delta": b["AT"] - a["AT"],
                })

        # PoP within 1 scale category
        a_pop = _pop_category(a.get("PoP6h"))
        b_pop = _pop_category(b.get("PoP6h"))
        if abs(b_pop - a_pop) > 1:
            breaches.append({
                "metric": "PoP6h",
                "from": pop_to_text(a.get("PoP6h")),
                "to": pop_to_text(b.get("PoP6h")),
            })

        # Relative Humidity within 20%
        if a.get("RH") is not None and b.get("RH") is not None:
            if abs(b["RH"] - a["RH"]) > 20:
                breaches.append({
                    "metric": "RH",
                    "from": a["RH"],
                    "to": b["RH"],
                    "delta": b["RH"] - a["RH"],
                })

        # Wind speed same or one Beaufort category apart
        a_bf = _beaufort_index(a.get("WS"))
        b_bf = _beaufort_index(b.get("WS"))
        if abs(b_bf - a_bf) > 2:
            breaches.append({
                "metric": "WS",
                "from": wind_ms_to_beaufort(a.get("WS")),
                "to": wind_ms_to_beaufort(b.get("WS")),
            })

        # Wind direction within 90 degrees
        if a.get("WD") is not None and b.get("WD") is not None:
            diff = abs(b["WD"] - a["WD"])
            if diff > 180:
                diff = 360 - diff
            if diff > 90:
                breaches.append({
                    "metric": "WD",
                    "from": degrees_to_cardinal(a["WD"]),
                    "to": degrees_to_cardinal(b["WD"]),
                })

        # Cloud cover in same classification
        a_cc = wx_to_cloud_cover(a.get("Wx"))
        b_cc = wx_to_cloud_cover(b.get("Wx"))
        if a_cc != b_cc:
            breaches.append({
                "metric": "CloudCover",
                "from": a_cc,
                "to": b_cc,
            })

        # AQI within 40 points — per-segment AQI not available from API,
        # so this threshold cannot be checked between adjacent segments.
        logger.debug("AQI transition check skipped: per-segment AQI data unavailable")

        if breaches:
            transitions.append({
                "from_segment": a_name,
                "to_segment": b_name,
                "breaches": breaches,
                "is_transition": True,
            })
        else:
            transitions.append({
                "from_segment": a_name,
                "to_segment": b_name,
                "breaches": [],
                "is_transition": False,
            })

    return transitions


def _commute_window(slots: list[dict], start_h: float, end_h: float,
                    current: dict | None = None) -> dict:
    """
    Interpolate or extract forecast data for a commute window.
    start_h and end_h are decimal hours (e.g. 7.0, 8.5).
    current: optional current conditions dict (for visibility data).
    """
    relevant = []
    for slot in slots:
        try:
            dt = _parse_dt(slot["start_time"])
            slot_hour = dt.hour + dt.minute / 60
        except Exception:
            continue
        # Include slot if it overlaps with the commute window
        if slot_hour < end_h and slot_hour + 6 > start_h:
            relevant.append(slot)

    if not relevant:
        return {}

    avg = _average_slots(relevant)
    # Use actual air temperature (T) as BOM formula input; fall back to AT only if T absent.
    ta = avg.get("T") if avg.get("T") is not None else avg.get("AT")
    feels_like = _calculate_apparent_temp(ta, avg.get("RH"), avg.get("WS"))
    if feels_like is not None:
        avg["AT"] = feels_like
    avg["beaufort_desc"] = wind_ms_to_beaufort(avg.get("WS"))
    avg["wind_dir_text"] = degrees_to_cardinal(avg.get("WD"))
    avg["precip_text"] = pop_to_text(avg.get("PoP6h"))
    avg["cloud_cover"] = wx_to_cloud_cover(avg.get("Wx"))
    avg["hazards"] = _detect_driving_hazards(avg, current)
    # Pass through visibility from current conditions for narration
    if isinstance(current, dict):
        curr_vis = current.get("visibility")
        if curr_vis is not None:
            avg["visibility"] = curr_vis
    return avg


def _detect_driving_hazards(slot: dict | None, current: dict | None = None) -> list[str]:
    """Flag notable driving hazards including rain, wind, and fog/visibility."""
    hazards = []
    if slot is None:
        return hazards
    pop = slot.get("PoP6h") or 0
    ws = slot.get("WS") or 0

    if pop >= 61:
        hazards.append("Heavy rain likely — roads may be slick")
    elif pop >= 41:
        hazards.append("Rain possible — allow extra stopping distance")

    bf = _beaufort_index(ws)
    if bf >= 6:
        hazards.append("Strong crosswinds — high-profile vehicles use caution")
    elif bf >= 5:
        hazards.append("Noticeable gusts — keep hands on the wheel")

    # Fog / poor visibility (use current conditions visibility if available)
    vis = None
    if current:
        vis = current.get("visibility")
    if vis is not None:
        try:
            vis_km = float(vis)
            if vis_km < 1.0:
                hazards.append(f"Dense fog ({vis_km}km visibility) — use fog lights, reduce speed")
            elif vis_km < 2.0:
                hazards.append(f"Low visibility ({vis_km}km) — possible fog, drive with extra caution")
        except (ValueError, TypeError):
            pass

    return hazards



# ── Local stubs (small utility functions not worth their own module) ───────────

@dataclass
class HvacDewPointAdvice:
    dehumidifier: str | None            # "strongly_recommended" | "recommended" | "consider" | None
    ac_mode: str | None                 # "cool" | "dry" | None
    windows: str | None                 # "open" | "close" | None
    reasons: list[str] = field(default_factory=list)


def _hvac_dew_point_advice(
    outdoor_temp_c: float,
    outdoor_dew_point_c: float,
    outdoor_dew_gap_c: float,
    indoor_temp_c: float | None = None,
    indoor_rh_pct: float | None = None,
) -> HvacDewPointAdvice:
    """Dew point-aware HVAC sub-recommendations (dehumidifier, AC mode, windows)."""
    advice = HvacDewPointAdvice(dehumidifier=None, ac_mode=None, windows=None)

    # 1. Dehumidifier — triggered by outdoor dew point, not raw RH
    if outdoor_dew_point_c >= 24:
        advice.dehumidifier = "strongly_recommended"
        advice.reasons.append(
            f"outdoor dew point {outdoor_dew_point_c}°C — oppressive moisture load, "
            "dehumidifier strongly recommended"
        )
    elif outdoor_dew_point_c >= 21:
        advice.dehumidifier = "recommended"
        advice.reasons.append(
            f"outdoor dew point {outdoor_dew_point_c}°C — muggy, dehumidifier recommended"
        )
    elif outdoor_dew_point_c >= 18:
        advice.dehumidifier = "consider"
        advice.reasons.append(
            f"outdoor dew point {outdoor_dew_point_c}°C — sticky, consider dehumidifier"
        )

    if indoor_temp_c is not None and indoor_rh_pct is not None:
        indoor_dew = _calculate_dew_point(indoor_temp_c, indoor_rh_pct)
        if indoor_dew is not None and indoor_dew >= 21 and advice.dehumidifier is None:
            advice.dehumidifier = "recommended"
            advice.reasons.append(
                f"indoor dew point {indoor_dew}°C — muggy inside, run dehumidifier"
            )

    # 2. AC mode: cool vs dry
    if outdoor_temp_c >= 26:
        if outdoor_dew_gap_c < 6 and outdoor_dew_point_c >= 18:
            advice.ac_mode = "dry"
            advice.reasons.append(
                f"dew gap only {outdoor_dew_gap_c}°C — air nearly saturated, "
                "AC dry mode addresses moisture better than cool mode"
            )
        else:
            advice.ac_mode = "cool"
            advice.reasons.append(
                f"temp {outdoor_temp_c}°C with manageable humidity — AC cool mode appropriate"
            )

    # 3. Window advice
    if indoor_temp_c is not None and indoor_rh_pct is not None:
        indoor_dew = _calculate_dew_point(indoor_temp_c, indoor_rh_pct)
        if indoor_dew is not None:
            delta = outdoor_dew_point_c - indoor_dew
            if delta <= -3:
                advice.windows = "open"
                advice.reasons.append(
                    f"outdoor dew point {outdoor_dew_point_c}°C is {abs(delta):.1f}°C lower "
                    f"than indoors ({indoor_dew}°C) — opening windows will help dry the house"
                )
            elif delta >= 3:
                advice.windows = "close"
                advice.reasons.append(
                    f"outdoor dew point {outdoor_dew_point_c}°C is {delta:.1f}°C higher "
                    f"than indoors ({indoor_dew}°C) — keep windows closed to avoid importing moisture"
                )
    else:
        if outdoor_dew_point_c >= 22:
            advice.windows = "close"
            advice.reasons.append(
                f"outdoor dew point {outdoor_dew_point_c}°C — keep windows closed "
                "to limit moisture infiltration"
            )
        elif outdoor_dew_point_c <= 12 and outdoor_temp_c >= 18:
            advice.windows = "open"
            advice.reasons.append(
                f"outdoor dew point {outdoor_dew_point_c}°C — dry outside, "
                "open windows to ventilate naturally"
            )

    return advice


def _climate_control(segmented: dict, aqi: dict) -> dict:
    """
    Dew point-aware climate control recommendations.

    Uses the Afternoon segment (hottest/most humid part of the day) as the
    representative sample for daily HVAC planning. Falls back to the first
    available segment if Afternoon is missing.
    """
    seg: dict | None = None
    for name in ("Afternoon", "Morning", "Evening", "Overnight"):
        if segmented.get(name):
            seg = segmented[name]
            break

    _empty = {"mode": "Off", "dehumidifier": None, "ac_mode": None, "windows": None,
               "dew_reasons": [], "recommendations": []}

    if seg is None:
        return _empty

    temp = seg.get("T") if seg.get("T") is not None else seg.get("AT")
    dew_point = seg.get("dew_point")
    dew_gap = seg.get("dew_gap")

    if temp is None or dew_point is None or dew_gap is None:
        return _empty

    advice = _hvac_dew_point_advice(
        outdoor_temp_c=temp,
        outdoor_dew_point_c=dew_point,
        outdoor_dew_gap_c=dew_gap,
    )

    # Primary mode drives P4 inclusion and the front-end badge
    if temp >= 26:
        mode = "cooling"
    elif dew_point >= 21:
        mode = "dehumidify"
    elif advice.windows == "open":
        mode = "fan"        # mild ventilation — P4 climate section skipped per prompt gate
    else:
        mode = "Off"

    return {
        "mode": mode,
        "dehumidifier": advice.dehumidifier,
        "ac_mode": advice.ac_mode,
        "windows": advice.windows,
        "dew_reasons": advice.reasons,
        "recommendations": [],
    }

def _pop_category(pop: float | None) -> int:
    """Return 0–5 category index for PoP6h."""
    if pop is None: return 0
    if pop <= 0:  return 0
    if pop <= 20: return 1
    if pop <= 40: return 2
    if pop <= 60: return 3
    if pop <= 80: return 4
    return 5

