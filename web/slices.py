"""
slices.py — Extracts view-specific data slices from the full broadcast.

Views:
  current   — Real-time metrics (Big Gauges)
  overview  — Timeline, Trend Chart, Alerts
  lifestyle — Wardrobe, Commute, Outdoor, Meals, HVAC
  narration — Full text script
  context   — Dynamic Right Panel data (Rain Text, Location)
"""

from __future__ import annotations
from typing import cast, Optional


def build_slices(broadcast: dict) -> dict:
    """
    Build per-view data slices from a broadcast record.

    Args:
        broadcast: Dict with at minimum 'paragraphs', 'metadata', 'processed_data'.

    Returns:
        Dict with keys 'current', 'overview', 'lifestyle', 'narration', 'context'.
    """
    paragraphs = broadcast.get("paragraphs", {})
    processed = broadcast.get("processed_data", {})
    summaries = broadcast.get("summaries", {})

    current_data = processed.get("current", {})
    forecast_segs = processed.get("forecast_segments", {})
    climate = processed.get("climate_control", {})
    cardiac = processed.get("cardiac_alert")
    menieres = processed.get("menieres_alert")
    commute = processed.get("commute", {})
    aqi_realtime = processed.get("aqi_realtime", {})
    aqi_forecast = processed.get("aqi_forecast", {})
    transitions = processed.get("transitions", [])
    heads_ups = processed.get("heads_ups", [])

    meta = broadcast.get("metadata", {})

    return {
        "current": _slice_current(current_data, aqi_realtime),
        "overview": _slice_overview(forecast_segs, cardiac, menieres, paragraphs, commute, heads_ups, aqi_forecast, transitions),
        "lifestyle": _slice_lifestyle(current_data, commute, climate, paragraphs, processed, summaries),
        "narration": _slice_narration(paragraphs, meta),
    }


# ── View Slices ──────────────────────────────────────────────────────────────

def _slice_current(current: dict, aqi_realtime: dict | None = None) -> dict:
    """Current View: Real-time conditions with 5-level insights."""
    aqi_realtime = aqi_realtime or {}
    return {
        "temp": current.get("AT"),
        "obs_time": current.get("obs_time"),
        "location": current.get("station_name"),
        "weather_code": current.get("Wx"),
        "weather_text": current.get("Wx_text"),
        "ground_state": current.get("ground_state", "Dry"),
        "ground_level": current.get("ground_level", 1),

        # 5-Level Metrics
        "hum": {
            "val": current.get("RH"),
            "text": current.get("hum_text", "Normal"),
            "level": current.get("hum_level", 3)
        },
        "wind": {
            "val": current.get("WDSD"),
            "text": current.get("wind_text", "Calm"),
            "level": current.get("wind_level", 1),
            "dir": current.get("wind_dir_text")
        },
        "aqi": {
            "val": current.get("aqi"),
            "text": current.get("aqi_status", "Good"),
            "level": current.get("aqi_level", 1),
            "pm25": aqi_realtime.get("pm25"),
            "pm10": aqi_realtime.get("pm10"),
        },
        "vis": {
            "val": current.get("visibility"),
            "text": current.get("vis_text", "Good"),
            "level": current.get("vis_level", 1)
        },
        "uv": {
            "val": current.get("UVI"),
            "text": current.get("uv_text", "Low"),
            "level": current.get("uv_level", 1)
        },
        "pres": {
            "val": current.get("PRES"),
            "text": current.get("pres_text", "Normal"),
            "level": current.get("pres_level", 3)
        }
    }


def _slice_overview(
    segments: dict,
    cardiac: dict | None,
    menieres: dict | None,
    paragraphs: dict,
    commute: dict | None = None,
    heads_ups: list | None = None,
    aqi_forecast: dict | None = None,
    transitions: list | None = None,
) -> dict:
    """Overview View: Timeline, Alerts, AQI Forecast, Transitions."""
    commute = commute or {}
    heads_ups = heads_ups or []
    aqi_forecast = aqi_forecast or {}
    transitions = transitions or []

    timeline_list = []
    for name, seg in segments.items():
        if seg:
            seg_copy = dict(seg)
            seg_copy["display_name"] = name
            timeline_list.append(seg_copy)

    timeline_list.sort(key=lambda x: x["start_time"])

    commute_hazards = (
        commute.get("morning", {}).get("hazards", []) +
        commute.get("evening", {}).get("hazards", [])
    )

    return {
        "timeline": timeline_list,
        "aqi_forecast": aqi_forecast,
        "transitions": transitions,
        "alerts": {
            "cardiac": cardiac,
            "menieres": menieres,
            "heads_up": paragraphs.get("heads_up") or paragraphs.get("p1_summary"),
            "heads_ups": heads_ups,
            "commute_hazards": commute_hazards,
        },
    }


def _slice_lifestyle(current: dict, commute: dict, climate: dict, paragraphs: dict, processed: dict, summaries: dict | None = None) -> dict:
    """Lifestyle View: Wardrobe, Rain Gear, Commute, Outdoor, Meals, HVAC."""
    summaries = summaries or {}
    
    # 1. Wardrobe & Rain Gear
    at = current.get("AT")
    rain_recent = (current.get("RAIN") or 0) > 0
    
    wardrobe_text = summaries.get("wardrobe")
    if not wardrobe_text:
        wardrobe_text = _wardrobe_tip(at, rain_recent)
        
    rain_gear_text = summaries.get("rain_gear")
    if not rain_gear_text:
        rain_gear_text = "No precipitation gear expected." if not rain_recent else "Carry an umbrella."

    # 2. Commute (v6: p2_garden_commute contains garden + commute)
    commute_text = summaries.get("commute") or paragraphs.get("p2_garden_commute")
    if not commute_text:
        am = commute.get("morning", {}).get("hazards", [])
        pm = commute.get("evening", {}).get("hazards", [])
        if am:
            commute_text = f"Morning alert: {am[0]}."
        elif pm:
            commute_text = f"Evening alert: {pm[0]}."
        else:
            commute_text = "Traffic conditions look normal."

    # 3. HVAC (v6: p4_meal_climate contains meals + climate control)
    hvac_text = summaries.get("hvac") or paragraphs.get("p4_meal_climate")
    if not hvac_text:
        hvac_mode = climate.get("mode", "Off")
        rh = current.get("RH", 0)
        aqi = current.get("aqi", 0)
        hvac_parts = [f"System: {hvac_mode}."]
        if int(rh or 0) > 70:
            hvac_parts.append("Dehumidifier recommended.")
        elif int(aqi or 0) > 100:
            hvac_parts.append("Air purifier recommended.")
        hvac_text = " ".join(hvac_parts)

    # 4. Meals (v6: p4_meal_climate)
    meals_text = summaries.get("meals") or paragraphs.get("p4_meal_climate")
    if not meals_text:
        meal_mood_data = processed.get("meal_mood", {})
        meal_suggestions = meal_mood_data.get("top_suggestions", []) or meal_mood_data.get("all_suggestions", [])
        if meal_suggestions:
            meals_text = f"Suggested: {', '.join(meal_suggestions[:2])}."
        else:
            meals_text = "No specific suggestions."

    # 5. Garden (v6: first sentence of p2_garden_commute) & Outdoor (v6: p3_outdoor)
    garden_text = summaries.get("garden")
    outdoor_text = summaries.get("outdoor") or paragraphs.get("p3_outdoor")

    if not garden_text:
        p2 = paragraphs.get("p2_garden_commute", "")
        if p2:
            parts = p2.split(". ", 1)
            garden_text = parts[0] + "."
        else:
            garden_text = "Check soil moisture."

    if not outdoor_text:
        top_loc = processed.get("location_rec", {}).get("top_locations", [])
        activity = top_loc[0].get("activity") if top_loc else None
        outdoor_text = f"Great day for {activity}." if activity else "Good day for a walk."

    # Outdoor location structured data (first top location from processor)
    top_locations = processed.get("location_rec", {}).get("top_locations", [])
    location_obj = top_locations[0] if top_locations else None

    # Meal mood category
    meal_mood = processed.get("meal_mood", {}).get("mood")

    return {
        "wardrobe": {
            "text": wardrobe_text,
            "feels_like": at,
        },
        "rain_gear": {
            "text": rain_gear_text,
        },
        "commute": {
            "text": commute_text,
            "hazards": commute.get("morning", {}).get("hazards", []) + commute.get("evening", {}).get("hazards", [])
        },
        "hvac": {
            "text": hvac_text,
            "mode": climate.get("mode", "Off")
        },
        "meals": {
            "text": meals_text,
            "mood": meal_mood,
        },
        "garden": {
            "text": garden_text,
        },
        "outdoor": {
            "text": outdoor_text,
            "location": location_obj,
        }
    }


def _slice_narration(paragraphs: dict, metadata: dict) -> dict:
    """Narration View: Full text and metadata."""
    
    # Determined source/model from metadata (saved in main.py)
    source = metadata.get("narration_source", "template").title() # "Gemini", "Claude", "Template"
    model = metadata.get("narration_model", "Unknown")

    # Fallback legacy logic if missing
    if source == "Template" and "gemini" in metadata.get("llm_model", "").lower():
        source = "Gemini"

    return {
        "paragraphs": [
            {"title": "Current & Outlook",    "text": paragraphs.get("p1_conditions", "")},
            {"title": "Garden & Commute",     "text": paragraphs.get("p2_garden_commute", "")},
            {"title": "Outdoor with Dad",     "text": paragraphs.get("p3_outdoor", "")},
            {"title": "Meals & Climate",      "text": paragraphs.get("p4_meal_climate", "")},
            {"title": "Forecast",             "text": paragraphs.get("p5_forecast", "")},
            {"title": "Yesterday's Accuracy", "text": paragraphs.get("p6_accuracy", "")},
        ],
        "meta": {
            "model": model,
            "source": source,
        }
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _wardrobe_tip(at: float | None, rain: bool) -> str:
    """Generate simple wardrobe advice."""
    parts = []
    if rain:
        parts.append("Rain gear needed ☔")
    
    if at is None:
        return "Check forecast."
        
    if at < 15:
        parts.append("Heavy coat & layers 🧥")
    elif at < 20:
        parts.append("Light jacket or sweater 🧥")
    elif at < 26:
        parts.append("Comfortable / T-shirt 👕")
    else:
        parts.append("Light clothing & sunscreen 🌞")
        
    return " + ".join(parts)
