"""
slices.py — Extracts per-user profile slices from the full broadcast.

Each profile receives only the paragraph subsets and current-condition
fields relevant to their view. The dashboard JS uses these slices to
render the correct cards per profile.

Profiles:
  me      — Full view (all paragraphs)
  spouse  — Heads-up + commute + meals
  dad     — Heads-up + outdoor health + current icons (accessibility-first)
  kids    — Icon + feels-like + wardrobe tip
"""

from __future__ import annotations


def build_slices(broadcast: dict) -> dict:
    """
    Build per-profile data slices from a broadcast record.

    Args:
        broadcast: Dict with at minimum 'paragraphs', 'metadata', 'processed_data'.

    Returns:
        Dict with keys 'me', 'spouse', 'dad', 'kids'.
    """
    paragraphs = broadcast.get("paragraphs", {})
    metadata = broadcast.get("metadata", {})
    processed = broadcast.get("processed_data", {})

    current = processed.get("current", {})
    climate = processed.get("climate_control", {})
    cardiac = processed.get("cardiac_alert")
    meal_mood = processed.get("meal_mood", {})
    commute = processed.get("commute", {})

    return {
        "me": _slice_me(paragraphs),
        "spouse": _slice_spouse(paragraphs, commute),
        "dad": _slice_dad(paragraphs, current, cardiac),
        "kids": _slice_kids(current, paragraphs),
    }


# ── Profile slices ────────────────────────────────────────────────────────────

def _slice_me(paragraphs: dict) -> dict:
    """Full view — all paragraphs as ordered cards."""
    return {
        "profile": "me",
        "cards": [
            {"id": "current", "title": "Now",         "text": paragraphs.get("p1_current", "")},
            {"id": "commute", "title": "Commute",     "text": paragraphs.get("p2_commute", "")},
            {"id": "health",  "title": "Garden & Dad","text": paragraphs.get("p3_garden_health", "")},
            {"id": "meals",   "title": "Meals",       "text": paragraphs.get("p4_meals", ""),
             "omit_if_empty": True},
            {"id": "climate", "title": "Climate",     "text": paragraphs.get("p5_climate_cardiac", ""),
             "omit_if_empty": True},
            {"id": "forecast","title": "Forecast",    "text": paragraphs.get("p6_forecast", "")},
            {"id": "accuracy","title": "Accuracy",    "text": paragraphs.get("p7_accountability", "")},
        ],
        "show_raw_data_toggle": True,
    }


def _slice_spouse(paragraphs: dict, commute: dict) -> dict:
    """Spouse view — heads-up + commute + meals."""
    return {
        "profile": "spouse",
        "cards": [
            {"id": "alerts",  "title": "Alerts & Wardrobe", "text": _extract_heads_up(paragraphs.get("p1_current", ""))},
            {"id": "commute", "title": "Commute",            "text": paragraphs.get("p2_commute", "")},
            {"id": "meals",   "title": "Meals",              "text": paragraphs.get("p4_meals", ""),
             "omit_if_empty": True},
        ],
        "commute_hazards": {
            "morning": commute.get("morning", {}).get("hazards", []),
            "evening": commute.get("evening", {}).get("hazards", []),
        },
    }


def _slice_dad(paragraphs: dict, current: dict, cardiac_alert: dict | None) -> dict:
    """
    Dad view — accessibility-first, large text.
    Cardiac warning is surfaced as a top-level flag for CSS styling.
    """
    has_cardiac_warning = cardiac_alert is not None and cardiac_alert.get("triggered", False)

    cards = []

    # Heads-up + cardiac warning first
    heads_up_text = _extract_heads_up(paragraphs.get("p1_current", ""))
    climate_text = paragraphs.get("p5_climate_cardiac", "")
    alert_text = (heads_up_text + "\n\n" + climate_text).strip() if climate_text else heads_up_text

    cards.append({
        "id": "alerts",
        "title": "Today's Alerts",
        "text": alert_text,
        "cardiac_warning": has_cardiac_warning,
    })

    # Outdoor activity recommendation
    cards.append({
        "id": "outdoor",
        "title": "Going Outside?",
        "text": paragraphs.get("p3_garden_health", ""),
    })

    # Current conditions as simple summary
    cards.append({
        "id": "conditions",
        "title": "Right Now",
        "text": _simple_conditions(current),
        "icon": _weather_icon(current.get("cloud_cover", "")),
        "aqi": current.get("aqi"),
        "aqi_status": current.get("aqi_status"),
    })

    return {
        "profile": "dad",
        "cards": cards,
        "accessibility": {
            "min_font_size": "24px",
            "high_contrast": True,
            "large_tap_targets": True,
        },
        "cardiac_warning": has_cardiac_warning,
    }


def _slice_kids(current: dict, paragraphs: dict) -> dict:
    """Kids view — cartoon icon, feels-like, wardrobe tip, fun fact."""
    at = current.get("AT")
    cloud = current.get("cloud_cover", "Unknown")
    rain_recent = (current.get("RAIN") or 0) > 0

    feels_like = _kids_feels_like(at, cloud, rain_recent)
    wardrobe = _kids_wardrobe(at, rain_recent)
    fun_fact = _kids_fun_fact(current)
    icon = _weather_icon(cloud, rain=rain_recent)

    return {
        "profile": "kids",
        "icon": icon,
        "feels_like": feels_like,
        "wardrobe": wardrobe,
        "fun_fact": fun_fact,
        "icon_label": cloud,
    }


# ── Helper functions ──────────────────────────────────────────────────────────

def _extract_heads_up(p1_text: str) -> str:
    """
    Extract just the heads-up portion of Paragraph 1.
    Since P1 is plain text, we take the first 2 sentences as the heads-up.
    """
    if not p1_text:
        return ""
    # Split on sentence boundaries (。.!?)
    import re
    sentences = re.split(r"(?<=[。.!?！？])\s*", p1_text.strip())
    return " ".join(sentences[:3]).strip()


def _simple_conditions(current: dict) -> str:
    """Generate a one-line conditions description for the Dad view."""
    at = current.get("AT")
    cloud = current.get("cloud_cover", "")
    wind = current.get("beaufort_desc", "")
    aqi = current.get("aqi")

    parts = []
    if at is not None:
        parts.append(f"Feels like {at:.0f}°C")
    if cloud:
        parts.append(cloud)
    if wind and wind != "Unknown":
        parts.append(wind)
    if aqi is not None:
        parts.append(f"AQI {aqi}")

    return " · ".join(parts)


def _weather_icon(cloud_cover: str, rain: bool = False) -> str:
    """Map cloud cover classification to an icon name."""
    if rain:
        return "rainy"
    mapping = {
        "Sunny/Clear": "sunny",
        "Mixed Clouds": "partly-cloudy",
        "Overcast": "cloudy",
    }
    return mapping.get(cloud_cover, "cloudy")


def _kids_feels_like(at: float | None, cloud: str, rain: bool) -> str:
    """Generate a kid-friendly feels-like description."""
    if at is None:
        return "Today's weather is a mystery! 🌈"
    if rain:
        return f"It's rainy and feels like {at:.0f}°C ☔"
    if at >= 30:
        return f"Super hot! It feels like {at:.0f}°C 🌞"
    if at >= 24:
        return f"Nice and warm — feels like {at:.0f}°C 😊"
    if at >= 18:
        return f"A little cool — feels like {at:.0f}°C 🍃"
    if at >= 12:
        return f"Chilly! It feels like {at:.0f}°C 🧥"
    return f"Very cold! Feels like {at:.0f}°C 🥶"


def _kids_wardrobe(at: float | None, rain: bool) -> str:
    """Generate a kid-friendly wardrobe tip."""
    parts = []
    if rain:
        parts.append("Rain jacket and boots! ☔")
    if at is None:
        return "Check with a grown-up about what to wear!"
    if at < 15:
        parts.append("Big warm coat 🧥 + hat + scarf")
    elif at < 22:
        parts.append("Light jacket or sweater 👕")
    elif at < 28:
        parts.append("T-shirt and comfortable pants 😎")
    else:
        parts.append("Cool summer clothes 🌞 — and drink water!")
    return " ".join(parts)


def _kids_fun_fact(current: dict) -> str:
    """Generate a simple weather fun fact based on current conditions."""
    aqi = current.get("aqi") or 0
    wind = current.get("beaufort_desc", "Calm")
    cloud = current.get("cloud_cover", "")

    if aqi > 100:
        return "The air has lots of tiny particles today — it's good to stay indoors! 🏠"
    if "Gentle" in wind or "Moderate" in wind or "Fresh" in wind:
        return "The wind is strong enough to fly a kite today! 🪁"
    if cloud == "Sunny/Clear":
        return "The sun is shining bright — don't forget sunscreen! ☀️"
    if cloud == "Overcast":
        return "Clouds are like giant fluffy blankets in the sky! ☁️"
    return "Every day has different weather — that's what makes it fun! 🌤️"
