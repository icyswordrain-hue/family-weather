"""outdoor_scoring.py — 0-100 outdoor suitability index and activity recommendations."""

import logging
from typing import Optional
import config as cfg
from data.scales import _beaufort_index, _val_to_scale, VIS_SCALE_5, PRECIP_SCALE_5
from data.location_loader import OUTDOOR_LOCATIONS

logger = logging.getLogger(__name__)

GRADE_THRESHOLDS = [
    (80, "A", "Excellent"),
    (65, "B", "Good"),
    (50, "C", "Fair"),
    (35, "D", "Poor"),
    (0,  "F", "Avoid"),
]

OUTDOOR_WEIGHTS_GENERAL = {
    "rain_active": -50, "rain_light": -25,
    "pop_high": -25, "pop_mid": -12,
    "at_extreme_hot": -30, "at_hot": -15, "at_cold": -10, "at_extreme_cold": -20,
    "heat_humidity": -10,
    "wind_strong": -35, "wind_moderate": -10,
    "rh_very_high": -20, "rh_high": -10,
    "aqi_unhealthy": -40, "aqi_sensitive": -15,
    "uvi_extreme": -15, "uvi_very_high": -8,
    "wet_ground": -8,
    "vis_very_poor": -30, "vis_poor": -20,
    "menieres_high": -35, "menieres_moderate": -20,
    "cardiac": -15,
}

OUTDOOR_WEIGHTS_BY_ACTIVITY: dict[str, dict] = {
    "strolling": { "wet_ground": -20 },
    "cycling": {
        "rain_active": -50, "rain_light": -40,
        "wind_strong": -40, "wind_moderate": -15,
        "wet_ground": -25, "vis_very_poor": -40, "vis_poor": -25,
    },
    "hiking": {
        "rain_light": -35, "at_hot": -20, "at_extreme_hot": -35,
        "aqi_sensitive": -20, "aqi_unhealthy": -45,
        "uvi_very_high": -12, "uvi_extreme": -20,
        "vis_poor": -30, "vis_very_poor": -45,
    },
    "picnic": {
        "wind_strong": -30, "wind_moderate": -15, "wet_ground": -10,
    },
    "swimming": {
        "rain_active": 0, "rain_light": 0, "pop_high": -10, "pop_mid": -5,
        "at_extreme_hot": 0, "at_hot": 0, "at_cold": -50, "at_extreme_cold": -80,
        "heat_humidity": 0, "wind_strong": -15, "wind_moderate": -5,
        "aqi_unhealthy": -20, "aqi_sensitive": -5, "uvi_extreme": -10, "uvi_very_high": -5,
        "wet_ground": 0,
    },
    "sports": {
        "at_extreme_hot": -35, "at_hot": -15, "heat_humidity": -20, "wet_ground": -20,
        "aqi_unhealthy": -40, "aqi_sensitive": -15,
    },
    "photography": {
        "rain_active": -15, "rain_light": 0, "pop_high": -5, "pop_mid": 0,
        "at_extreme_hot": -10, "at_hot": -5, "at_cold": -5, "at_extreme_cold": -15,
        "heat_humidity": -5, "wind_strong": -10, "wind_moderate": -5,
        "aqi_unhealthy": -20, "aqi_sensitive": -5, "uvi_extreme": 0, "uvi_very_high": 0,
        "wet_ground": 0, "vis_very_poor": -50, "vis_poor": -25,
    },
}

def _grade_score(score: int) -> tuple[str, str]:
    """Return (letter_grade, label) for a 0–100 outdoor score."""
    for threshold, grade, label in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade, label
    return "F", "Avoid"

def _compute_solar_load(uvi: int | None, wx_name: str | None) -> int:
    """Approximate radiant heat impact (0-100)."""
    if not uvi or not wx_name: return 0
    is_sunny = "晴" in wx_name
    is_cloudy = "陰" in wx_name or "雨" in wx_name
    base_load = min(100, uvi * 10)
    if is_sunny: return min(100, base_load + 20)
    elif is_cloudy: return max(0, base_load - 40)
    return base_load

def _score_conditions(c: dict, weights: dict) -> tuple[int, list[str], list[str]]:
    """Apply penalty weights to conditions using rules."""
    score = 100
    blockers: list[str] = []
    cautions: list[str] = []

    rules = [
        ("rain", c.get("rain", 0), lambda v: (v or 0) > 5, "rain_active", "blocker", "active_rain"),
        ("rain", c.get("rain", 0), lambda v: 1 < (v or 0) <= 5, "rain_light", "caution", "light_rain"),
        ("pop", c.get("pop"), lambda v: v is not None and v > 70, "pop_high", "caution", "rain_likely"),
        ("pop", c.get("pop"), lambda v: v is not None and 40 < v <= 70, "pop_mid", "caution", "rain_possible"),
        ("at", c.get("at"), lambda v: v is not None and v > cfg.OUTDOOR_TEMP_EXTREME_HOT, "at_extreme_hot", "caution", "extreme_heat"),
        ("at", c.get("at"), lambda v: v is not None and cfg.OUTDOOR_TEMP_HOT < v <= cfg.OUTDOOR_TEMP_EXTREME_HOT, "at_hot", "caution", "hot"),
        ("at", c.get("at"), lambda v: v is not None and v < cfg.OUTDOOR_TEMP_EXTREME_COLD, "at_extreme_cold", "caution", "extreme_cold"),
        ("at", c.get("at"), lambda v: v is not None and cfg.OUTDOOR_TEMP_EXTREME_COLD <= v < cfg.OUTDOOR_TEMP_COLD, "at_cold", "caution", "cold"),
        ("heat_humidity", (c.get("at"), c.get("rh")), lambda v: v[0] is not None and v[0] > 28 and v[1] is not None and v[1] > 75, "heat_humidity", "caution", "heat_humidity"),
        ("rh", c.get("rh"), lambda v: v is not None and v > cfg.OUTDOOR_RH_VERY_HIGH, "rh_very_high", "caution", "very_humid"),
        ("rh", c.get("rh"), lambda v: v is not None and cfg.OUTDOOR_RH_HIGH < v <= cfg.OUTDOOR_RH_VERY_HIGH, "rh_high", "caution", "humid"),
        ("ws", c.get("ws"), lambda v: v is not None and _beaufort_index(v) >= 7, "wind_strong", "blocker", "strong_wind"),
        ("ws", c.get("ws"), lambda v: v is not None and 5 <= _beaufort_index(v) < 7, "wind_moderate", "caution", "moderate_wind"),
        ("aqi", c.get("aqi"), lambda v: v is not None and v > cfg.OUTDOOR_AQI_UNHEALTHY, "aqi_unhealthy", "blocker", "poor_air"),
        ("aqi", c.get("aqi"), lambda v: v is not None and cfg.OUTDOOR_AQI_SENSITIVE < v <= cfg.OUTDOOR_AQI_UNHEALTHY, "aqi_sensitive", "caution", "moderate_air"),
        ("uvi", c.get("uvi"), lambda v: v is not None and v >= cfg.OUTDOOR_UVI_EXTREME, "uvi_extreme", "caution", "extreme_uv"),
        ("uvi", c.get("uvi"), lambda v: v is not None and cfg.OUTDOOR_UVI_VERY_HIGH <= v < cfg.OUTDOOR_UVI_EXTREME, "uvi_very_high", "caution", "very_high_uv"),
        ("ground_wet", c.get("ground_wet"), lambda v: v is True, "wet_ground", "caution", "wet_ground"),
        ("vis", c.get("vis"), lambda v: v is not None and v < cfg.OUTDOOR_VIS_VERY_POOR, "vis_very_poor", "blocker", "dense_fog"),
        ("vis", c.get("vis"), lambda v: v is not None and cfg.OUTDOOR_VIS_VERY_POOR <= v < cfg.OUTDOOR_VIS_POOR, "vis_poor", "caution", "low_vis"),
        ("solar", c.get("solar_load"), lambda v: v is not None and v > 80, "solar_extreme", "caution", "harsh_sunlight"),
    ]

    for _, val, condition, penalty_key, rule_type, label in rules:
        if condition(val):
            score += weights.get(penalty_key, 0)
            if rule_type == "blocker": blockers.append(label)
            else: cautions.append(label)

    return max(0, min(100, score)), blockers, cautions

def _compute_outdoor_index(current: dict, segmented: dict, aqi_val: int | None, menieres_alert: dict | None, cardiac_alert: dict | None) -> dict:
    """Compute suitcase index for each segment."""
    uvi = current.get("UVI")
    rain = current.get("RAIN") or 0.0
    ground_wet = current.get("ground_state") == "Wet"
    vis = current.get("visibility")

    health_penalty = 0
    if menieres_alert and menieres_alert.get("triggered"):
        sev = menieres_alert.get("severity")
        health_penalty += OUTDOOR_WEIGHTS_GENERAL["menieres_high" if sev == "high" else "menieres_moderate"]
    if cardiac_alert and cardiac_alert.get("triggered"):
        health_penalty += OUTDOOR_WEIGHTS_GENERAL["cardiac"]

    segments = {}
    for name in ["Morning", "Afternoon", "Evening"]:
        seg = segmented.get(name)
        if not seg: continue
        
        cond = {
            "at": seg.get("AT"), "rh": seg.get("RH"), "ws": seg.get("WS"),
            "pop": seg.get("PoP6h"), "aqi": aqi_val, "uvi": uvi,
            "rain": rain, "ground_wet": ground_wet, "vis": vis,
            "solar_load": _compute_solar_load(uvi, seg.get("WxText") or seg.get("cloud_cover")),
        }
        score, blockers, cautions = _score_conditions(cond, OUTDOOR_WEIGHTS_GENERAL)
        score = max(0, score + health_penalty)
        grade, label = _grade_score(score)
        
        segments[name] = {
            "score": score, "grade": grade, "label": label,
            "blockers": blockers, "cautions": cautions
        }

    # Per-activity picks
    activity_scores = {}
    best_seg = max(segments.values(), key=lambda x: x["score"]) if segments else {"score": 0}
    
    for activity, overrides in OUTDOOR_WEIGHTS_BY_ACTIVITY.items():
        weights = {**OUTDOOR_WEIGHTS_GENERAL, **overrides}
        # Use Afternoon cond as proxy for activity scoring
        afternoon = segmented.get("Afternoon") or next((v for v in segmented.values() if v is not None), {})
        cond = {
            "at": afternoon.get("AT"), "rh": afternoon.get("RH"), "ws": afternoon.get("WS"),
            "pop": afternoon.get("PoP6h"), "aqi": aqi_val, "uvi": uvi,
            "rain": rain, "ground_wet": ground_wet, "vis": vis,
            "solar_load": _compute_solar_load(uvi, afternoon.get("WxText")),
        }
        score, _, _ = _score_conditions(cond, weights)
        score = max(0, score + health_penalty)
        grade, label = _grade_score(score)
        activity_scores[activity] = {"score": score, "grade": grade, "label": label}

    return {
        "overall_score": best_seg["score"],
        "overall_grade": best_seg.get("grade", "F"),
        "overall_label": best_seg.get("label", "Avoid"),
        "segments": segments,
        "activities": activity_scores
    }

def _classify_outdoor_mood(segmented: dict, aqi: dict, outdoor_index: dict) -> dict:
    """Pick location categories base on weather mood."""
    # Determine mood
    mood = "Stay In"
    score = outdoor_index.get("overall_score", 0)
    
    # Simple mood logic
    if score >= 75: mood = "Nice"
    elif score >= 55: mood = "Warm"
    elif score >= 35: mood = "Cloudy & Breezy"
    
    all_locs = OUTDOOR_LOCATIONS.get(mood, [])
    return {
        "mood": mood,
        "all_locations": all_locs,
        "top_locations": all_locs[:3]
    }

def _extract_recent_locations(history: list[dict], days: int = 3) -> list[str]:
    """Extract location names from history."""
    locs = []
    for day in history[-days:]:
        day_locs = day.get("metadata", {}).get("locations_suggested", [])
        locs.extend(day_locs)
    return locs
