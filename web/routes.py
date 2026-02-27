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
    forecast_7day = processed.get("forecast_7day", [])
    climate = processed.get("climate_control", {})
    cardiac = processed.get("cardiac_alert")
    menieres = processed.get("menieres_alert")
    commute = processed.get("commute", {})
    aqi_realtime = processed.get("aqi_realtime", {})
    aqi_forecast = processed.get("aqi_forecast", {})
    transitions = processed.get("transitions", [])
    heads_ups = processed.get("heads_ups", [])

    meta = broadcast.get("metadata", {})
    outdoor_index = processed.get("outdoor_index", {})

    return {
        "current": _slice_current(current_data, aqi_realtime),
        "overview": _slice_overview(forecast_segs, cardiac, menieres, commute, heads_ups, aqi_forecast, transitions, outdoor_index, forecast_7day),
        "lifestyle": _slice_lifestyle(current_data, commute, climate, paragraphs, processed, summaries, outdoor_index),
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
    commute: dict | None = None,
    heads_ups: list | None = None,
    aqi_forecast: dict | None = None,
    transitions: list | None = None,
    outdoor_index: dict | None = None,
    forecast_7day: list | None = None,
) -> dict:
    """Overview View: Timeline, Alerts, AQI Forecast, Transitions."""
    commute = commute or {}
    heads_ups = heads_ups or []
    aqi_forecast = aqi_forecast or {}
    transitions = transitions or []
    outdoor_index = outdoor_index or {}
    forecast_7day = forecast_7day or []

    timeline_list = []
    for name, seg in segments.items():
        if seg:
            seg_copy = dict(seg)
            seg_copy["display_name"] = name
            seg_grade_data = outdoor_index.get("segments", {}).get(name, {})
            seg_copy["outdoor_score"] = seg_grade_data.get("score")
            seg_copy["outdoor_grade"] = seg_grade_data.get("grade")
            timeline_list.append(seg_copy)

    timeline_list.sort(key=lambda x: x["start_time"])

    commute_hazards = (
        commute.get("morning", {}).get("hazards", []) +
        commute.get("evening", {}).get("hazards", [])
    )

    return {
        "timeline": timeline_list,
        "weekly_timeline": forecast_7day[:14],
        "aqi_forecast": {
            **aqi_forecast,
        },
        "transitions": transitions,
        "alerts": {
            "cardiac": cardiac,
            "menieres": menieres,
            "heads_ups": heads_ups,
            "commute_hazards": commute_hazards,
        },
    }


def _slice_lifestyle(current: dict, commute: dict, climate: dict, paragraphs: dict, processed: dict, summaries: dict | None = None, outdoor_index: dict | None = None) -> dict:
    """Lifestyle View: Wardrobe, Rain Gear, Commute, Outdoor, Meals, HVAC."""
    if not isinstance(summaries, dict):
        summaries = {}
    if not isinstance(climate, dict):
        climate = {"mode": "Off"}
    
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

    # Outdoor text only
    if not outdoor_text:
        outdoor_text = "Good day for a walk."

    outdoor_index = outdoor_index or {}

    # Meal mood category
    meal_mood = processed.get("meal_mood", {}).get("mood")

    # Alert card: prefer structured heads_ups list; fall back to LLM paragraph wrapped in same shape
    _alert = processed.get("heads_ups") or []
    if not _alert:
        _fallback = paragraphs.get("heads_up") or paragraphs.get("p1_summary")
        if _fallback:
            _alert = [{"level": "WARNING", "type": "General", "msg": _fallback}]

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
            "score": outdoor_index.get("score"),
            "grade": outdoor_index.get("grade"),
            "label": outdoor_index.get("label"),
            "top_activity": outdoor_index.get("top_activity"),
            "activity_scores": outdoor_index.get("activity_scores", {}),
            "parkinsons_safe": outdoor_index.get("parkinsons_safe", True),
            "best_window": outdoor_index.get("best_window"),
        },
        "alert": _alert,
    }


def _slice_narration(paragraphs: dict, metadata: dict) -> dict:
    """Narration View: Full text and metadata."""

    # Determined source/model from metadata (saved in main.py)
    source = metadata.get("narration_source", "template").title() # "Gemini", "Claude", "Template"
    model = metadata.get("narration_model", "Unknown")

    # Fallback legacy logic if missing
    if source == "Template" and "gemini" in metadata.get("llm_model", "").lower():
        source = "Gemini"

    # Paragraph section titles — use language-neutral keys.
    # The frontend TRANSLATIONS object maps these to the display language.
    # For the narration view the section titles are rendered from the paragraph
    # keys, so we embed a `key` field alongside `text` to allow the frontend
    # to translate if desired, while `title` stays in a neutral readable form.
    return {
        "paragraphs": [
            {"key": "p1", "title": "Current & Outlook",    "text": paragraphs.get("p1_conditions", "")},
            {"key": "p2", "title": "Garden & Commute",     "text": paragraphs.get("p2_garden_commute", "")},
            {"key": "p3", "title": "Outdoor with Dad",     "text": paragraphs.get("p3_outdoor", "")},
            {"key": "p4", "title": "Meals & Climate",      "text": paragraphs.get("p4_meal_climate", "")},
            {"key": "p5", "title": "Forecast",             "text": paragraphs.get("p5_forecast", "")},
            {"key": "p6", "title": "Yesterday's Accuracy", "text": paragraphs.get("p6_accuracy", "")},
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
