"""
processor.py — Applies all Data Processing Rules from the v4 prompt.

Transforms raw CWA + MOENV data into a structured, narration-ready payload.
Rules applied:
  - Time segment grouping (Night/Morning/Afternoon/Evening)
  - Precipitation scale conversion (0-5 text)
  - Cloud cover classification (Sunny / Mixed Clouds / Overcast)
  - Beaufort wind speed descriptions
  - Apparent temperature extraction (ignores standard temp)
  - Low Deviation Detection (identifies meaningful transitions)
  - Commute window interpolation (07:00–08:30, 17:00–18:30)
  - Meal mood classification
  - Climate control & cardiac safety logic
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ── Time segment boundaries (local hour, 24h) ────────────────────────────────
SEGMENTS = {
    "Night":     (0, 6),
    "Morning":   (6, 12),
    "Afternoon": (12, 18),
    "Evening":   (18, 24),
}

SEGMENT_ORDER = ["Night", "Morning", "Afternoon", "Evening"]

# ── Beaufort scale — wind speed (m/s) upper bounds ───────────────────────────
BEAUFORT_SCALE = [
    (0.3,  "Calm"),
    (1.5,  "Light air"),
    (3.3,  "Light breeze"),
    (5.4,  "Gentle breeze"),
    (7.9,  "Moderate breeze"),
    (10.7, "Fresh breeze"),
    (13.8, "Strong breeze"),
    (17.1, "Near gale"),
    (20.7, "Gale"),
    (24.4, "Strong gale"),
    (28.4, "Storm"),
    (32.6, "Violent storm"),
    (float("inf"), "Hurricane force"),
]

# ── Precipitation text scale ──────────────────────────────────────────────────
PRECIP_SCALE = [
    (20,  "Very Unlikely"),
    (40,  "Unlikely"),
    (60,  "Moderate Chance"),
    (80,  "Likely"),
    (100, "Very Likely"),
]


# ═══════════════════════════════════════════════════════════════════════════════
# Public entry point
# ═══════════════════════════════════════════════════════════════════════════════

def process(
    current: dict,
    forecasts: dict[str, list[dict]],
    aqi: dict,
    history: list[dict] | None = None,
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
    current_processed = _process_current(current, aqi["realtime"])

    # ── 2. Choose primary forecast location (Sanxia first, fallback Banqiao) ─
    primary_slots = forecasts.get("三峽區") or forecasts.get("板橋區") or []
    banqiao_slots = forecasts.get("板橋區") or []

    # ── 3. Segment the forecast ───────────────────────────────────────────────
    segmented = _segment_forecast(primary_slots)

    # ── 4. Enrich each segment ────────────────────────────────────────────────
    for seg_name, seg in segmented.items():
        if seg:
            seg["beaufort_desc"] = wind_ms_to_beaufort(seg.get("WS"))
            seg["precip_text"] = pop_to_text(seg.get("PoP6h"))
            seg["cloud_cover"] = wx_to_cloud_cover(seg.get("Wx"))

    # ── 5. Low Deviation Detection ────────────────────────────────────────────
    transitions = _detect_transitions(segmented, aqi)

    # ── 6. Commute windows ────────────────────────────────────────────────────
    morning_commute = _commute_window(primary_slots, 7, 8.5)
    evening_commute = _commute_window(primary_slots, 17, 18.5)

    # ── 7. Meal mood ─────────────────────────────────────────────────────────
    meal_mood = _classify_meal_mood(segmented)
    recent_meals = _extract_recent_meals(history, days=3)

    # ── 8. Climate control & cardiac safety ───────────────────────────────────
    climate_recs = _climate_control(segmented, aqi)
    cardiac_alert = _cardiac_alert(segmented)

    # ── 9. Forecast AQI ──────────────────────────────────────────────────────
    aqi_forecast = aqi.get("forecast", {})

    return {
        "current": current_processed,
        "forecast_segments": segmented,
        "transitions": transitions,
        "commute": {
            "morning": morning_commute,
            "evening": evening_commute,
        },
        "meal_mood": meal_mood,
        "recent_meals": recent_meals,
        "climate_control": climate_recs,
        "cardiac_alert": cardiac_alert,
        "aqi_realtime": aqi["realtime"],
        "aqi_forecast": aqi_forecast,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _process_current(current: dict, aqi_realtime: dict) -> dict:
    """Enrich raw current-condition dict with derived fields."""
    result = dict(current)
    result["beaufort_desc"] = wind_ms_to_beaufort(current.get("WDSD"))
    result["wind_dir_text"] = degrees_to_cardinal(current.get("WDIR"))
    result["cloud_cover"] = wx_to_cloud_cover(current.get("Wx"))
    result["aqi"] = aqi_realtime.get("aqi")
    result["aqi_status"] = aqi_realtime.get("status")
    return result


def _segment_forecast(slots: list[dict]) -> dict[str, Optional[dict]]:
    """
    Assign each 6-hour forecast slot to a named time segment.
    When multiple slots fall in the same segment, average numeric fields.
    """
    buckets: dict[str, list[dict]] = {s: [] for s in SEGMENT_ORDER}

    for slot in slots:
        try:
            dt = _parse_dt(slot["start_time"])
        except Exception:
            continue
        hour = dt.hour
        for seg_name, (lo, hi) in SEGMENTS.items():
            if lo <= hour < hi:
                buckets[seg_name].append(slot)
                break

    segmented: dict[str, Optional[dict]] = {}
    for seg_name in SEGMENT_ORDER:
        seg_slots = buckets[seg_name]
        if not seg_slots:
            segmented[seg_name] = None
        elif len(seg_slots) == 1:
            segmented[seg_name] = dict(seg_slots[0])
        else:
            segmented[seg_name] = _average_slots(seg_slots)

    return segmented


def _average_slots(slots: list[dict]) -> dict:
    """Average numeric fields across multiple time slots."""
    result = {"start_time": slots[0]["start_time"], "end_time": slots[-1]["end_time"]}
    numeric_keys = ["AT", "RH", "WS", "WD", "PoP6h"]
    for key in numeric_keys:
        values = [s[key] for s in slots if s.get(key) is not None]
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
        if abs(b_bf - a_bf) > 1:
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


def _commute_window(slots: list[dict], start_h: float, end_h: float) -> dict:
    """
    Interpolate or extract forecast data for a commute window.
    start_h and end_h are decimal hours (e.g. 7.0, 8.5).
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
    avg["beaufort_desc"] = wind_ms_to_beaufort(avg.get("WS"))
    avg["precip_text"] = pop_to_text(avg.get("PoP6h"))
    avg["cloud_cover"] = wx_to_cloud_cover(avg.get("Wx"))
    avg["hazards"] = _detect_driving_hazards(avg)
    return avg


def _detect_driving_hazards(slot: dict) -> list[str]:
    """Flag notable driving hazards."""
    hazards = []
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

    return hazards


def _classify_meal_mood(segmented: dict) -> dict:
    """
    Classify the day into one of four meal moods using daytime segments.
    Uses Afternoon as the primary driver, with Morning as secondary.
    """
    # Gather daytime apparent temperatures and humidity
    ats = []
    rhs = []
    is_rainy = False

    for seg_name in ["Morning", "Afternoon", "Evening"]:
        seg = segmented.get(seg_name)
        if seg:
            if seg.get("AT") is not None:
                ats.append(seg["AT"])
            if seg.get("RH") is not None:
                rhs.append(seg["RH"])
            if (seg.get("PoP6h") or 0) >= 61:
                is_rainy = True

    avg_at = sum(ats) / len(ats) if ats else 20.0
    avg_rh = sum(rhs) / len(rhs) if rhs else 60.0

    if avg_at >= 30 and avg_rh >= 70:
        mood = "Hot & Humid"
        suggestions = [
            "涼麵 (liáng miàn, cold sesame noodles)",
            "愛玉冰 (ài yù bīng)",
            "涼拌小黃瓜 (marinated cucumber)",
            "竹筍湯 (bamboo shoot soup)",
            "豆花 (dòuhuā) with shaved ice",
        ]
    elif avg_at >= 22 and avg_rh < 70:
        mood = "Warm & Pleasant"
        suggestions = [
            "滷肉飯 (lǔ ròu fàn)",
            "蚵仔煎 (ô-á-tsian)",
            "鹹酥雞 (yán sū jī)",
            "便當 (biàndāng) with assorted sides",
            "水餃 (shuǐ jiǎo)",
            "炒米粉 (chǎo mǐ fěn)",
        ]
    elif avg_at >= 15 or is_rainy:
        mood = "Cool & Damp"
        suggestions = [
            "牛肉麵 (niú ròu miàn)",
            "麻油雞 (má yóu jī)",
            "藥燉排骨 (herbal pork rib soup)",
            "火鍋 (huǒ guō)",
            "鹹粥 (savory congee)",
            "四神湯 (sì shén tāng)",
        ]
    else:
        mood = "Cold"
        suggestions = [
            "薑母鴨 (jiāng mǔ yā)",
            "羊肉爐 (yáng ròu lú)",
            "麻辣鍋 (málà hot pot)",
            "燒酒雞 (shāo jiǔ jī)",
            "花生豬腳湯 (peanut pig trotter soup)",
        ]

    return {
        "mood": mood,
        "avg_at": round(avg_at, 1),
        "avg_rh": round(avg_rh, 1),
        "is_rainy": is_rainy,
        "all_suggestions": suggestions,
    }


def _extract_recent_meals(history: list[dict], days: int = 3) -> list[str]:
    """Extract meal suggestions from the last N days of history."""
    meals = []
    for day in history[-days:]:
        day_meals = day.get("metadata", {}).get("meals_suggested", [])
        meals.extend(day_meals)
    return meals


def _climate_control(segmented: dict, aqi: dict) -> dict:
    """
    Apply climate control logic and return recommendations.
    """
    recs = {
        "mode": None,          # "cooling" | "heating" | "fan" | "none"
        "set_temp": None,
        "estimated_hours": 0,
        "dehumidify": False,
        "windows_open": False,
        "notes": [],
    }

    aqi_val = aqi.get("realtime", {}).get("aqi") or 0
    hours_hot = 0
    hours_cold = 0
    hours_optional_ac = 0

    for seg_name in SEGMENT_ORDER:
        seg = segmented.get(seg_name)
        if not seg:
            continue
        at = seg.get("AT")
        rh = seg.get("RH") or 0

        if at is None:
            continue

        if at >= 30 or rh >= 80:
            hours_hot += 6
        elif 26 <= at < 30 and 60 <= rh < 80:
            hours_optional_ac += 6
        elif at <= 14:
            hours_cold += 6

    # Determine primary mode
    if hours_cold > 0:
        recs["mode"] = "heating"
        recs["set_temp"] = "20–22°C"
        recs["estimated_hours"] = hours_cold
        recs["notes"].append("Use electric heater or AC heat-pump mode during coldest hours")
    elif hours_hot > 0:
        recs["mode"] = "cooling"
        recs["set_temp"] = "26–27°C"
        recs["estimated_hours"] = hours_hot
    elif hours_optional_ac > 0:
        recs["mode"] = "dehumidify"
        recs["dehumidify"] = True
        recs["estimated_hours"] = hours_optional_ac
        recs["notes"].append("Fan or dehumidify mode preferred over full cooling")
    else:
        recs["mode"] = "fan"
        recs["estimated_hours"] = 0

    # Window / AQI guidance
    if aqi_val > 100:
        recs["windows_open"] = False
        recs["notes"].append(f"AQI at {aqi_val} — keep windows closed, use air purifier in recirculation mode")
    elif recs["mode"] in ("fan", None):
        recs["windows_open"] = True
        recs["notes"].append("Good AQI — open windows for natural ventilation")

    return recs


def _cardiac_alert(segmented: dict) -> Optional[dict]:
    """
    Check for cardiac arrest risk triggers.
    Returns an alert dict if a trigger is found, otherwise None.
    """
    ats = {seg: segmented[seg].get("AT") for seg in SEGMENT_ORDER if segmented.get(seg)}

    at_values = [(seg, at) for seg, at in ats.items() if at is not None]
    if len(at_values) < 2:
        return None

    # Check for 10°C drop between consecutive segments
    for i in range(len(SEGMENT_ORDER) - 1):
        a = SEGMENT_ORDER[i]
        b = SEGMENT_ORDER[i + 1]
        at_a = ats.get(a)
        at_b = ats.get(b)
        if at_a is not None and at_b is not None:
            if at_a - at_b >= 10:
                return {
                    "triggered": True,
                    "reason": f"Temperature drops {at_a - at_b:.0f}°C from {a} to {b}",
                    "from_segment": a,
                    "to_segment": b,
                    "from_at": at_a,
                    "to_at": at_b,
                }

    # Check overnight low below 10°C
    night_at = ats.get("Night")
    if night_at is not None and night_at < 10:
        return {
            "triggered": True,
            "reason": f"Overnight low is {night_at}°C — below 10°C threshold",
            "from_segment": "Night",
            "to_segment": None,
            "from_at": night_at,
            "to_at": None,
        }

    # Check same-day swing ≥ 15°C
    all_ats = [at for _, at in at_values]
    swing = max(all_ats) - min(all_ats)
    if swing >= 15:
        return {
            "triggered": True,
            "reason": f"Same-day temperature swing of {swing:.0f}°C",
            "from_segment": None,
            "to_segment": None,
            "from_at": min(all_ats),
            "to_at": max(all_ats),
        }

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Conversion utilities (also used by other modules)
# ═══════════════════════════════════════════════════════════════════════════════

def wind_ms_to_beaufort(ms: float | None) -> str:
    """Convert wind speed in m/s to a descriptive Beaufort scale label."""
    if ms is None:
        return "Unknown"
    for threshold, label in BEAUFORT_SCALE:
        if ms <= threshold:
            return label
    return "Hurricane force"


def _beaufort_index(ms: float | None) -> int:
    """Return the numeric Beaufort index (0–12) for a given m/s value."""
    if ms is None:
        return 0
    for i, (threshold, _) in enumerate(BEAUFORT_SCALE):
        if ms <= threshold:
            return i
    return 12


def pop_to_text(pop: float | None) -> str:
    """Convert PoP6h percentage to 5-point text scale."""
    if pop is None:
        return "Unknown"
    for threshold, label in PRECIP_SCALE:
        if pop <= threshold:
            return label
    return "Very Likely"


def _pop_category(pop: float | None) -> int:
    """Return 0–4 category index for PoP6h."""
    if pop is None:
        return 0
    for i, (threshold, _) in enumerate(PRECIP_SCALE):
        if pop <= threshold:
            return i
    return 4


def wx_to_cloud_cover(wx: int | None) -> str:
    """Convert CWA Wx code to cloud cover classification."""
    if wx is None:
        return "Unknown"
    if 1 <= wx <= 3:
        return "Sunny/Clear"
    if 4 <= wx <= 6:
        return "Mixed Clouds"
    return "Overcast"


def degrees_to_cardinal(deg: float | None) -> str:
    """Convert wind direction in degrees to an 8-point cardinal label."""
    if deg is None:
        return "Unknown"
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = round(deg / 45) % 8
    return directions[idx]


def _parse_dt(dt_str: str) -> datetime:
    """Parse ISO-8601-like datetime string from CWA API."""
    # CWA returns "2026-02-18 06:00:00" or "2026-02-18T06:00:00+08:00"
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {dt_str!r}")
