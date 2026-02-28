"""scales.py — Centrally defines 5-level and 13-level weather scales and lookup helpers."""

from typing import Optional

# ── 13-Level Beaufort scale — wind speed (m/s) upper bounds ─────────────────────
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

# ── 5-Level Scales ────────────────────────────────────────────────────────────

BEAUFORT_SCALE_5 = [
    (1.5,  "Calm", 1),
    (5.4,  "Breezy", 2),
    (10.7, "Windy", 3),
    (17.1, "Strong", 4),
    (float("inf"), "Stormy", 5),
]

UV_SCALE = [
    (2,  "Low", 1),
    (5,  "Moderate", 2),
    (7,  "High", 3),
    (10, "Very High", 4),
    (float("inf"), "Extreme", 5),
]


PRES_SCALE_5 = [
    (1000, "Low", 5),
    (1008, "Unsettled", 4),
    (1018, "Normal", 3),
    (1025, "Stable", 2),
    (float("inf"), "High", 1),
]

VIS_SCALE_5 = [
    (1.0,  "Very Poor", 5),
    (2.0,  "Poor", 4),
    (5.0,  "Fair", 3),
    (10.0, "Good", 2),
    (float("inf"), "Excellent", 1),
]

PRECIP_SCALE_5 = [
    (0,   "Dry", 1),
    (20,  "Very Unlikely", 1),
    (40,  "Unlikely", 2),
    (60,  "Possible", 3),
    (80,  "Likely", 4),
    (100, "Very Likely", 5),
]

# ── Lookups ───────────────────────────────────────────────────────────────────

def _hum_to_scale(val: float | None) -> tuple[str, int]:
    """Map relative humidity (%) to (label, level) on a comfort-centred scale.
    Level 1 is ideal (41–60%); severity increases in both dry and humid directions.
    Retained for backward-compat; prefer dew_gap_to_hum() for new code.
    """
    if val is None:
        return "Unknown", 0
    if val <= 30:
        return "Very Dry", 3
    if val <= 40:
        return "Dry", 2
    if val <= 60:
        return "Comfortable", 1
    if val <= 70:
        return "Muggy", 2
    if val <= 80:
        return "Humid", 3
    if val <= 90:
        return "Very Humid", 4
    return "Oppressive", 5

def dew_gap_to_hum(dew_gap_c: float | None) -> tuple[str, int]:
    """Map dew gap (°C) to (label, level).
    Dew gap = air_temp - dew_point.  Smaller gap = air closer to saturation = clammier.
    Level 1 = comfortable, 5 = worst.
    """
    if dew_gap_c is None:
        return "Unknown", 0
    if dew_gap_c < 2:  return "Near Saturated", 5
    if dew_gap_c < 5:  return "Clammy",          4
    if dew_gap_c < 10: return "Humid",            3
    if dew_gap_c < 15: return "Comfortable",      1
    return               "Dry",                   2

def _val_to_scale(val: float | None, scale: list[tuple]) -> tuple[str, int]:
    """Helper to map a numeric value to a (text, level) tuple based on a scale."""
    if val is None:
        return "Unknown", 0
    for item in scale:
        threshold, label, level = item[0], item[1], item[2]
        if val <= threshold:
            return label, level
    return "Extreme", 5

def _wind_to_level(ms: float | None) -> int:
    """Map wind speed (m/s) to 1-5 level."""
    if ms is None: return 0
    if ms <= 1.5: return 1
    if ms <= 5.4: return 2
    if ms <= 10.7: return 3
    if ms <= 17.1: return 4
    return 5

def _aqi_to_level(aqi: int | None) -> int:
    """Map AQI to 1-5 level."""
    if aqi is None: return 0
    if aqi <= 50: return 1
    if aqi <= 100: return 2
    if aqi <= 150: return 3
    if aqi <= 200: return 4
    return 5

def wind_ms_to_beaufort(ms: float | None) -> str:
    """Map wind speed (m/s) to Beaufort text."""
    if ms is None: return "Unknown"
    for threshold, label in BEAUFORT_SCALE:
        if ms <= threshold:
            return label
    return "Hurricane force"

def _beaufort_index(ms: float | None) -> int:
    """Get the 0-12 index of the Beaufort scale."""
    if ms is None: return 0
    for i, (threshold, _) in enumerate(BEAUFORT_SCALE):
        if ms <= threshold:
            return i
    return 12

def wx_to_cloud_cover(wx_code: int | None) -> str:
    """Map Wx code to Sunny / Mixed Clouds / Overcast / Rain."""
    if wx_code is None: return "Unknown"
    if wx_code <= 1: return "Sunny"
    if wx_code <= 3: return "Fair"
    if wx_code <= 7: return "Mixed Clouds"
    if wx_code <= 10: return "Overcast"
    return "Rain"

def degrees_to_cardinal(deg: float | None) -> str:
    """Map degrees (0-360) to 16 cardinal points."""
    if deg is None: return "Unknown"
    deg %= 360
    points = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
              "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return points[int((deg + 11.25) / 22.5) % 16]

def pop_to_text(pop: float | None) -> str:
    """Map PoP % to descriptive text."""
    if pop is None: return "Unknown"
    if pop <= 0: return "Dry"
    if pop <= 20: return "Very Unlikely"
    if pop <= 40: return "Unlikely"
    if pop <= 60: return "Possible"
    if pop <= 80: return "Likely"
    return "Very Likely"

def translate_aqi_status(status: str | None) -> str:
    """Translate AQI status to English."""
    mapping = {
        "良好": "Good",
        "普通": "Moderate",
        "對敏感族群不健康": "Unhealthy for Sensitive Groups",
        "不健康": "Unhealthy",
        "非常不健康": "Very Unhealthy",
        "危害": "Hazardous"
    }
    return mapping.get(status or "", status or "Unknown")

def translate_pollutant(name: str | None) -> str:
    """Translate common pollutant names."""
    mapping = {
        "細懸浮微粒": "PM2.5",
        "懸浮微粒": "PM10",
        "臭氧": "O3",
        "二氧化氮": "NO2",
        "二氧化硫": "SO2",
        "一氧化碳": "CO"
    }
    return mapping.get(name or "", name or "Unknown")


def wx_to_pop(wx_code: int | None) -> int | None:
    """Map Wx code to estimated PoP fallback percentage."""
    if wx_code is None:
        return None
    if wx_code <= 3:
        return 0     # Clear/Fair
    if wx_code <= 7:
        return 20    # Cloudy/Overcast
    if wx_code <= 14:
        return 50   # Showers
    return 80                     # Thunderstorms (15+)
