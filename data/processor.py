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
from typing import Optional, Any, cast

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


# ── Outdoor location pools (within 30km of 24.9955 N, 121.4279 E) ─────────────
# Each entry: {name, activity, surface, parkinsons_suitability (good/ok/avoid), lat, lng, notes}
# Grouped by weather mood: Nice / Warm / Cloudy & Breezy / Rainy or AQI-bad
OUTDOOR_LOCATIONS: dict[str, list[dict]] = {
    "Nice": [
        {"name": "Dahan River Bikeway (Yingge section)", "activity": "cycling / walking",
         "surface": "paved", "parkinsons": "good", "lat": 24.907, "lng": 121.349,
         "notes": "Flat riverside trail, well-shaded, easy parking at Yingge end"},
        {"name": "Jiaoban Mountain Trail (Sanxia)", "activity": "hiking",
         "surface": "dirt + stone steps", "parkinsons": "ok",
         "lat": 24.937, "lng": 121.373,
         "notes": "Short loop ~2.5km, good views of Sanxia valley; use trekking poles"},
        {"name": "Bitan Scenic Area (Xindian)", "activity": "walking / paddleboat",
         "surface": "paved promenade", "parkinsons": "good",
         "lat": 24.956, "lng": 121.541,
         "notes": "Suspension bridge, shaded banks, gentle terrain"},
        {"name": "Banqiao 435 Art Zone Garden", "activity": "strolling / tai chi",
         "surface": "paved", "parkinsons": "good", "lat": 25.011, "lng": 121.465,
         "notes": "Sculpture garden, flat, benches frequent; accessible toilets"},
        {"name": "Tucheng Chenfu Road Riverside Park", "activity": "walking / stretching",
         "surface": "paved", "parkinsons": "good", "lat": 24.974, "lng": 121.427,
         "notes": "10-min drive from Shulin, very flat, often breezy"},
        {"name": "Longmen Camping Meadow (Sanxia)", "activity": "walking / picnic",
         "surface": "grass + packed dirt", "parkinsons": "ok",
         "lat": 24.863, "lng": 121.371,
         "notes": "Open meadow by Sanxia River, beautiful on clear days; uneven ground"},
    ],
    "Warm": [
        {"name": "Shulin Riverside Greenway", "activity": "cycling / jogging",
         "surface": "paved", "parkinsons": "good", "lat": 24.987, "lng": 121.428,
         "notes": "Local favourite — 5km flat loop, shaded sections, water stations"},
        {"name": "Yingge Ceramics Museum Park", "activity": "strolling",
         "surface": "paved", "parkinsons": "good", "lat": 24.906, "lng": 121.345,
         "notes": "Outdoor sculpture garden, paved paths, interesting for all ages"},
        {"name": "Sanxia Old Street & Zushi Temple", "activity": "walking / culture",
         "surface": "cobblestone + paved", "parkinsons": "ok",
         "lat": 24.942, "lng": 121.369,
         "notes": "Best in morning before crowds; cobblestones can be tricky — bring a cane"},
        {"name": "Zhonghe Yuantong Mountain Trail", "activity": "hiking",
         "surface": "dirt + stone steps", "parkinsons": "ok",
         "lat": 24.996, "lng": 121.496,
         "notes": "Shaded climb ~3km, cooler than valley floor, good workout"},
        {"name": "Banqiao Lin Family Garden", "activity": "strolling / tai chi",
         "surface": "paved garden paths", "parkinsons": "good",
         "lat": 25.014, "lng": 121.462,
         "notes": "Historic garden, very flat, shaded by large banyan trees"},
        {"name": "Tamsui Old Street & Waterfront", "activity": "walking / boat",
         "surface": "paved", "parkinsons": "good", "lat": 25.170, "lng": 121.432,
         "notes": "Worth the 30km drive — waterfront promenade, sunset views"},
    ],
    "Cloudy & Breezy": [
        {"name": "Banqiao Station Underground Mall Walk", "activity": "indoor walking",
         "surface": "indoor tile", "parkinsons": "good", "lat": 25.014, "lng": 121.463,
         "notes": "Covered, climate-controlled, no wind; good fallback on breezy days"},
        {"name": "Sanxia Dasi Bikeway (lower section)", "activity": "cycling / e-bike",
         "surface": "paved", "parkinsons": "good", "lat": 24.924, "lng": 121.358,
         "notes": "Flat, riverside section sheltered by tree line; wind-protected"},
        {"name": "Tucheng Sports Center Indoor Track", "activity": "indoor walking",
         "surface": "rubberised track", "parkinsons": "good",
         "lat": 24.978, "lng": 121.431,
         "notes": "Fully covered 200m indoor track, climate-controlled, very accessible"},
        {"name": "Xinzhuang Lihui Park", "activity": "tai chi / stretching",
         "surface": "paved", "parkinsons": "good", "lat": 25.034, "lng": 121.445,
         "notes": "Large sheltered pavilions, community tai chi groups in morning"},
        {"name": "Shulin Community Center Courtyard", "activity": "light exercise",
         "surface": "paved", "parkinsons": "good", "lat": 24.994, "lng": 121.432,
         "notes": "Covered walkway, easy access, good for overcast days"},
    ],
    "Stay In": [
        {"name": "Banqiao Far Eastern Department Store Sky Garden", "activity": "indoor stroll",
         "surface": "indoor tile + outdoor terrace", "parkinsons": "good",
         "lat": 25.011, "lng": 121.464,
         "notes": "Rooftop garden accessible by elevator; protected terrace on drizzly days"},
        {"name": "Fuzhong Library Garden (Banciao)", "activity": "reading / light walk",
         "surface": "paved", "parkinsons": "good", "lat": 25.010, "lng": 121.460,
         "notes": "Quiet library garden courtyard, sheltered veranda, good AQI days only"},
        {"name": "Sanxia Visitor Center & Museum", "activity": "indoor culture",
         "surface": "indoor tile", "parkinsons": "good",
         "lat": 24.940, "lng": 121.368,
         "notes": "Fully indoor, free entry, interesting local history exhibits"},
    ],
}


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
    print("MB: Step 1 - Enrich current", flush=True)
    current_processed = _process_current(current, aqi["realtime"])

    # ── 2. Choose primary forecast location (Sanxia first, fallback Banqiao) ─
    primary_slots = forecasts.get("三峽區") or forecasts.get("板橋區") or []
    banqiao_slots = forecasts.get("板橋區") or []

    # ── 3. Segment the forecast ───────────────────────────────────────────────
    print("MB: Step 3 - Segment forecast calling...", flush=True)
    segmented = _segment_forecast(primary_slots)
    print(f"MB: Step 3 - Segmented done. Keys: {list(segmented.keys())}", flush=True)

    # ── 4. Enrich each segment ────────────────────────────────────────────────
    print("MB: Step 4 - Starting loop", flush=True)
    for seg_name, seg in segmented.items():
        print(f"MB: Step 4 - Processing {seg_name}", flush=True)
        if seg:
            seg["beaufort_desc"] = wind_ms_to_beaufort(seg.get("WS"))
            seg["precip_text"] = pop_to_text(seg.get("PoP6h"))
            seg["cloud_cover"] = wx_to_cloud_cover(seg.get("Wx"))
    print("MB: Step 4 - Loop done", flush=True)

    # ── 5. Low Deviation Detection ────────────────────────────────────────────
    print("MB: Step 5 - Transitions", flush=True)
    transitions = _detect_transitions(segmented, aqi)

    # ── 6. Commute windows ────────────────────────────────────────────────────
    print("MB: Step 6 - Commute", flush=True)
    morning_commute = _commute_window(primary_slots, 7, 8.5)
    evening_commute = _commute_window(primary_slots, 17, 18.5)

    # ── 7. Meal mood ─────────────────────────────────────────────────────────
    print("MB: Step 7 - Meal mood", flush=True)
    meal_mood = _classify_meal_mood(segmented)
    recent_meals = _extract_recent_meals(history, days=3)

    # Filter meal suggestions to avoid recent repeats
    filtered_meals = [s for s in meal_mood.get("all_suggestions", []) if not any(r in s for r in recent_meals)]
    
    # User Request: One meal per day (randomly Lunch or Dinner)
    import random
    if filtered_meals:
        chosen_meal = random.choice(filtered_meals)
        meal_label = random.choice(["Lunch", "Dinner"])
        # Format as "Lunch: Beef Noodle Soup"
        meal_mood["top_suggestions"] = [f"{meal_label}: {chosen_meal}"]
    else:
        # Fallback if all filtered out
        fallback = random.choice(meal_mood.get("all_suggestions", ["Sandwich"]))
        meal_mood["top_suggestions"] = [f"Meal: {fallback}"]

    # ── 7b. Outdoor location recommendations ─────────────────────────────────
    print("MB: Step 7b - Outdoor locations", flush=True)
    location_rec = _classify_outdoor_mood(segmented, aqi)
    recent_locations = _extract_recent_locations(history, days=3)

    # Filter locations to avoid recently suggested spots
    filtered_locations = [
        loc for loc in location_rec.get("all_locations", [])
        if loc["name"] not in recent_locations
    ]
    location_rec["top_locations"] = (filtered_locations if filtered_locations
                                     else location_rec.get("all_locations", []))

    # ── 8. Climate control & cardiac safety ───────────────────────────────────
    climate_recs = _climate_control(segmented, aqi)
    cardiac_alert = _cardiac_alert(segmented)

    # ── 9. Forecast AQI ──────────────────────────────────────────────────────
    raw_aqi_forecast = aqi.get("forecast", {})
    aqi_forecast = {
        "area": raw_aqi_forecast.get("area"),
        "aqi": raw_aqi_forecast.get("aqi_range"), # Normalize key
        "status": raw_aqi_forecast.get("status"),
        "forecast_date": raw_aqi_forecast.get("forecast_date"),
        "content": raw_aqi_forecast.get("content"),
    }

    # ── 10. Heads-up priority system ─────────────────────────────────────────
    heads_ups = _compute_heads_ups(
        segmented, morning_commute, evening_commute, aqi, cardiac_alert
    )

    return {
        "current": current_processed,
        "forecast_segments": segmented,
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
        "aqi_realtime": aqi["realtime"],
        "aqi_forecast": aqi_forecast,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _process_current(current: dict, aqi_realtime: dict) -> dict:
    """Enrich raw current-condition dict with derived fields."""
    result = dict(current)
    
    # Calculate more accurate AT (Feels-like)
    ta = current.get("AT") # In fetch_cwa, AirTemp is mapped to AT
    rh = current.get("RH")
    ws = current.get("WDSD")
    calculated_at = _calculate_apparent_temp(ta, rh, ws)
    if calculated_at is not None:
        result["AT"] = calculated_at

    result["beaufort_desc"] = wind_ms_to_beaufort(current.get("WDSD"))
    result["wind_dir_text"] = degrees_to_cardinal(current.get("WDIR"))
    result["cloud_cover"] = wx_to_cloud_cover(current.get("Wx"))
    result["aqi"] = aqi_realtime.get("aqi")
    result["aqi_status"] = translate_aqi_status(aqi_realtime.get("status"))
    result["visibility"] = current.get("visibility")
    return result


def _segment_forecast(slots: list[dict]) -> dict[str, Optional[dict]]:
    """
    Assign each 6-hour forecast slot to a named time segment.
    When multiple slots fall in the same segment, average numeric fields.
    """
    buckets: dict[str, list[dict[str, Any]]] = {s: [] for s in SEGMENT_ORDER}

    for slot in slots:
        try:
            dt = _parse_dt(slot["start_time"])
        except Exception:
            continue
        hour = dt.hour
        for seg_name, (lo, hi) in SEGMENTS.items():
            if lo <= hour < hi:
                # pyre-ignore[16]
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

        # AQI within 40 points (compare segment forecast AQI if available)
        # Use realtime AQI as baseline; future: per-segment AQI if available
        # For now, this check only fires if aqi_forecast differs significantly

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
        # pyre-ignore[6]
        "avg_at": round(float(avg_at), 1),
        # pyre-ignore[6]
        "avg_rh": round(float(avg_rh), 1),
        "is_rainy": is_rainy,
        "all_suggestions": suggestions,
    }


def _extract_recent_meals(history: list[dict], days: int = 3) -> list[str]:
    """Extract meal suggestions from the last N days of history."""
    meals = []
    # pyre-ignore[6]
    for day in history[-days:]:
        day_meals = day.get("metadata", {}).get("meals_suggested", [])
        meals.extend(day_meals)
    return meals


def _classify_outdoor_mood(segmented: dict, aqi: dict) -> dict:
    """
    Classify the day's outdoor suitability and return a pool of curated
    locations within 30km of Shulin/Banqiao, filtered by weather mood.

    Mood categories:
      "Nice"           — clear, pleasant AT, low wind, good AQI
      "Warm"           — warm/hot but manageable, good AQI
      "Cloudy & Breezy" — overcast, windy, or marginal conditions
      "Stay In"        — rain likely, high AQI, or medically inadvisable
    """
    aqi_val = aqi.get("realtime", {}).get("aqi") or 0

    # Gather daytime conditions
    ats, rhs, pops = [], [], []
    is_rainy = False
    is_windy = False
    for seg_name in ["Morning", "Afternoon", "Evening"]:
        seg = segmented.get(seg_name)
        if not seg:
            continue
        if seg.get("AT") is not None:
            ats.append(seg["AT"])
        if seg.get("RH") is not None:
            rhs.append(seg["RH"])
        pop = seg.get("PoP6h") or 0
        pops.append(pop)
        if pop >= 61:
            is_rainy = True
        if _beaufort_index(seg.get("WS")) >= 5:
            is_windy = True

    avg_at = sum(ats) / len(ats) if ats else 20.0
    max_pop = max(pops) if pops else 0

    # Determine outdoor mood
    if is_rainy or aqi_val > 100:
        mood = "Stay In"
    elif is_windy or max_pop >= 41:
        mood = "Cloudy & Breezy"
    elif avg_at >= 30:
        mood = "Warm"
    else:
        mood = "Nice"

    all_locations = OUTDOOR_LOCATIONS.get(mood, OUTDOOR_LOCATIONS["Nice"])

    return {
        "mood": mood,
        # pyre-ignore[6]
        "avg_at": round(float(avg_at), 1),
        "aqi": aqi_val,
        "is_rainy": is_rainy,
        "is_windy": is_windy,
        "all_locations": all_locations,
        "top_locations": all_locations,   # overwritten by rotation filter in process()
    }


def _extract_recent_locations(history: list[dict], days: int = 3) -> list[str]:
    """Extract location names suggested in the last N days of history."""
    locations = []
    # pyre-ignore[6]
    for day in history[-days:]:
        loc = day.get("metadata", {}).get("location_suggested", "")
        if loc:
            locations.append(loc)
    return locations


def _climate_control(segmented: dict, aqi: dict) -> dict:
    """
    Apply climate control logic and return recommendations.
    """
    recs: dict[str, Any] = {
        "mode": None,          # "cooling" | "heating" | "fan" | "none"
        "set_temp": None,
        "estimated_hours": 0,
        "dehumidify": False,
        "windows_open": False,
        "notes": [],
    }

    aqi_val = aqi.get("realtime", {}).get("aqi") or 0
    hours_hot: int = 0
    hours_cold: int = 0
    hours_optional_ac: int = 0
    hours_optional_heat: int = 0

    for seg_name in SEGMENT_ORDER:
        seg = segmented.get(seg_name)
        if not seg:
            continue
        at = seg.get("AT")
        rh = seg.get("RH") or 0

        if at is None:
            continue

        if at >= 30 or rh >= 80:
            # pyre-ignore[58]
            hours_hot += 6
        elif 26 <= at < 30 and 60 <= rh < 80:
            # pyre-ignore[58]
            hours_optional_ac += 6
        elif at <= 14:
            # pyre-ignore[58]
            hours_cold += 6
        elif 15 <= at <= 18:
            # pyre-ignore[58]
            hours_optional_heat += 6

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
    elif hours_optional_heat > 0:
        recs["mode"] = "heating_optional"
        recs["estimated_hours"] = hours_optional_heat
        recs["notes"].append("Layering indoors recommended; space heater briefly in morning or evening if needed")
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


def _compute_heads_ups(
    segmented: dict,
    morning_commute: dict,
    evening_commute: dict,
    aqi: dict,
    cardiac_alert: Optional[dict],
) -> list[str]:
    """
    Generate 0–3 heads-up alerts — the most actionable items for the listener.
    These appear as the very first sentences of the broadcast.
    """
    alerts: list[str] = []

    # 1. Cardiac alert is highest priority
    if cardiac_alert and cardiac_alert.get("triggered"):
        alerts.append(f"Health alert: {cardiac_alert['reason']} — keep warm and avoid sudden cold exposure.")

    # 2. High precipitation in any upcoming segment
    for seg_name in ["Morning", "Afternoon", "Evening"]:
        seg = segmented.get(seg_name)
        if seg and (seg.get("PoP6h") or 0) >= 61:
            alerts.append(f"Grab an umbrella — rain is {'Likely' if seg['PoP6h'] < 81 else 'Very Likely'} this {seg_name.lower()}.")
            break  # Only one rain alert

    # 3. AQI warning
    aqi_val = aqi.get("realtime", {}).get("aqi") or 0
    if aqi_val > 100:
        alerts.append(f"AQI is {aqi_val} — keep windows closed and limit outdoor time, especially for Dad.")

    # 4. Low visibility (fog/mist)
    vis = segmented.get("current", {}).get("visibility")
    if vis is not None and vis < 2.0:
        alerts.append(f"Visibility is low ({vis}km) due to fog or mist — please be extra careful if driving.")

    # 4. Commute hazards
    for label, commute in [("morning", morning_commute), ("evening", evening_commute)]:
        for hazard in commute.get("hazards", []):
            if len(alerts) < 3:
                alerts.append(f"{label.capitalize()} commute: {hazard}.")

    # pyre-ignore[6]
    return alerts[:3]  # Max 3


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


def translate_aqi_status(status_cn: str | None) -> str:
    """Translate MOENV Chinese AQI status labels to English."""
    if not status_cn:
        return "Unknown"
    
    mapping = {
        "良好": "Good",
        "普通": "Moderate",
        "對敏感族群不健康": "Unhealthy for Sensitive Groups",
        "對所有族群不健康": "Unhealthy",
        "非常不健康": "Very Unhealthy",
        "危害": "Hazardous",
    }
    # Handle partial matches or raw input
    for cn, en in mapping.items():
        if cn in status_cn:
            return en
    return status_cn if status_cn.isascii() else "Unknown"


def _calculate_apparent_temp(ta: float | None, rh: float | None, ws: float | None) -> float | None:
    """
    Calculate Apparent Temperature (Feels-like) using the simplified formula:
    AT = Ta + 0.33 * e - 0.70 * ws - 4.00
    where e (vapor pressure) = (rh / 100) * 6.105 * exp(17.27 * Ta / (237.7 + Ta))
    """
    if ta is None or rh is None:
        return ta
    
    import math
    try:
        # Assertions for Pyre2 narrowing
        assert ta is not None
        assert rh is not None
        ws_val: float = ws if ws is not None else 0.0
        
        # Vapor pressure (e)
        e = (rh / 100.0) * 6.105 * math.exp(17.27 * ta / (237.7 + ta))
        at = ta + 0.33 * e - 0.70 * ws_val - 4.00
        # pyre-ignore[6]
        return round(at, 1)
    except Exception:
        return ta


def _parse_dt(dt_str: str) -> datetime:
    """Parse ISO-8601-like datetime string from CWA API."""
    # CWA returns "2026-02-18 06:00:00" or "2026-02-18T06:00:00+08:00"
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {dt_str!r}")
