"""tests/test_slices.py — Unit tests for web/routes.py build_slices."""
from web.routes import build_slices

MINIMAL_BROADCAST = {
    "paragraphs": {
        "heads_up": "Watch for afternoon storms.",
        "p1_conditions": "Sunny morning.",
        "p2_garden_commute": "Garden is fine.",
        "p3_outdoor": "Great for walking.",
        "p4_meal_climate": "Light meals recommended.",
    },
    "metadata": {},
    "processed_data": {
        "current": {"AT": 25, "RH": 60, "WDSD": 3, "PRES": 1013, "UVI": 5,
                    "Wx": "1", "aqi": 50, "aqi_status": "Good", "aqi_level": 1,
                    "hum_text": "Normal", "hum_level": 2, "wind_text": "Light",
                    "wind_level": 1, "uv_text": "Low", "uv_level": 1,
                    "pres_text": "Normal", "pres_level": 3, "vis_text": "Good",
                    "vis_level": 1, "ground_state": "Dry", "ground_level": 1},
        "forecast_segments": {},
        "forecast_7day": [],
        "climate_control": {"mode": "Off"},
        "cardiac_alert": None,
        "menieres_alert": None,
        "commute": {},
        "aqi_realtime": {},
        "aqi_forecast": {},
        "transitions": [],
        "heads_ups": [],
        "outdoor_index": {},
    },
    "summaries": {},
}

def test_overview_has_no_heads_up_from_paragraphs():
    """Dashboard overview slice must NOT contain heads_up sourced from LLM paragraphs."""
    slices = build_slices(MINIMAL_BROADCAST)
    assert "heads_up" not in slices["overview"]["alerts"]

def test_lifestyle_has_heads_up_card():
    """Lifestyle slice must expose heads_up text from LLM paragraphs as alert card."""
    slices = build_slices(MINIMAL_BROADCAST)
    assert slices["lifestyle"]["alert"] == "Watch for afternoon storms."

def test_lifestyle_alert_is_none_when_no_paragraphs():
    """Lifestyle alert field is None when paragraphs are absent."""
    broadcast = dict(MINIMAL_BROADCAST)
    broadcast["paragraphs"] = {}
    slices = build_slices(broadcast)
    assert slices["lifestyle"]["alert"] is None
