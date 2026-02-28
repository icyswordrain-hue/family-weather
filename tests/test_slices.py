"""tests/test_slices.py — Unit tests for web/routes.py build_slices."""
from web.routes import build_slices

MINIMAL_BROADCAST = {
    "paragraphs": {
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


def test_overview_slice_has_no_heads_up_key():
    """Overview slice must not expose a heads_up key (alert lives in lifestyle only)."""
    slices = build_slices(MINIMAL_BROADCAST)
    assert "heads_up" not in slices["overview"]


def test_lifestyle_alert_empty_when_no_summaries():
    """Lifestyle alert is an empty list when summaries contains no alert."""
    slices = build_slices(MINIMAL_BROADCAST)
    assert slices["lifestyle"]["alert"] == []


def test_lifestyle_alert_populated_from_summaries():
    """Lifestyle alert is sourced from summaries['alert'] dict."""
    broadcast = dict(MINIMAL_BROADCAST)
    broadcast["summaries"] = {
        "alert": {"text": "Watch for afternoon storms.", "level": "WARNING"}
    }
    slices = build_slices(broadcast)
    alert_list = slices["lifestyle"]["alert"]
    assert len(alert_list) == 1
    assert alert_list[0]["level"] == "WARNING"
    assert alert_list[0]["msg"] == "Watch for afternoon storms."


def test_lifestyle_alert_empty_when_alert_text_blank():
    """Lifestyle alert is empty list when alert text is an empty string."""
    broadcast = dict(MINIMAL_BROADCAST)
    broadcast["summaries"] = {"alert": {"text": "", "level": "INFO"}}
    slices = build_slices(broadcast)
    assert slices["lifestyle"]["alert"] == []
