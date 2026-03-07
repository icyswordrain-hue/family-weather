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


def test_lifestyle_alert_includes_moenv_warning_when_aqi_elevated():
    """Air warning injected from aqi_forecast.warnings when AQI >= 150 AND text contains alert keywords."""
    broadcast = {**MINIMAL_BROADCAST,
                 "processed_data": {**MINIMAL_BROADCAST["processed_data"],
                                    "aqi_forecast": {"aqi": 160, "warnings": ["空氣品質不良，建議減少戶外活動。"]}}}
    slices = build_slices(broadcast)
    alert_list = slices["lifestyle"]["alert"]
    air_items = [a for a in alert_list if a["type"] == "Air"]
    assert len(air_items) == 1
    assert air_items[0]["level"] == "WARNING"
    assert "空氣品質" in air_items[0]["msg"]


def test_lifestyle_alert_no_moenv_warning_when_aqi_below_threshold():
    """No Air warning injected when AQI < 150 (threshold raised from 100)."""
    broadcast = {**MINIMAL_BROADCAST,
                 "processed_data": {**MINIMAL_BROADCAST["processed_data"],
                                    "aqi_forecast": {"aqi": 110, "warnings": ["空氣品質不良，建議減少戶外活動。"]}}}
    slices = build_slices(broadcast)
    alert_list = slices["lifestyle"]["alert"]
    assert not any(a["type"] == "Air" for a in alert_list)


def test_lifestyle_alert_no_moenv_warning_without_keywords():
    """No Air warning injected when AQI >= 150 but content lacks alert keywords."""
    broadcast = {**MINIMAL_BROADCAST,
                 "processed_data": {**MINIMAL_BROADCAST["processed_data"],
                                    "aqi_forecast": {"aqi": 160, "warnings": ["今日東北季風增強，北部天氣晴朗。"]}}}
    slices = build_slices(broadcast)
    alert_list = slices["lifestyle"]["alert"]
    assert not any(a["type"] == "Air" for a in alert_list)


def test_lifestyle_alert_dedup_llm_and_moenv_air_alerts():
    """When the LLM alert mentions AQI *and* MOENV also injects an Air alert, only one
    AQI-related entry survives in the final list (no duplicate air quality rows)."""
    broadcast = {
        **MINIMAL_BROADCAST,
        "summaries": {"alert": {"text": "AQI is poor today, limit outdoor exposure.", "level": "WARNING"}},
        "processed_data": {
            **MINIMAL_BROADCAST["processed_data"],
            "aqi_forecast": {"aqi": 160, "warnings": ["空氣品質不良，建議減少戶外活動。"]},
        },
    }
    slices = build_slices(broadcast)
    alert_list = slices["lifestyle"]["alert"]
    # Both the LLM General alert (mentions "aqi") and the MOENV Air alert qualify as Air.
    # After dedup, only one Air-category entry should remain.
    air_related = [a for a in alert_list if "aqi" in a.get("msg", "").lower() or "空氣" in a.get("msg", "")]
    assert len(air_related) == 1, f"Expected 1 air-related alert, got {len(air_related)}: {alert_list}"


def test_lifestyle_alert_dedup_keeps_critical_over_warning_same_type():
    """Dedup retains CRITICAL over WARNING when two alerts share the same effective type."""
    from web.routes import _dedup_alerts
    alerts = [
        {"type": "Air", "level": "WARNING", "msg": "AQI elevated."},
        {"type": "Air", "level": "CRITICAL", "msg": "Hazardous air — stay indoors."},
    ]
    result = _dedup_alerts(alerts)
    assert len(result) == 1
    assert result[0]["level"] == "CRITICAL"


def test_lifestyle_alert_dedup_prefers_specific_type_over_general_on_equal_severity():
    """When a 'General' LLM alert and a specific-type alert share the same severity and topic,
    the specific-type entry wins."""
    from web.routes import _dedup_alerts
    alerts = [
        {"type": "General", "level": "WARNING", "msg": "AQI is poor today."},  # reclassified as Air
        {"type": "Air",     "level": "WARNING", "msg": "空氣品質不良，建議減少戶外活動。"},
    ]
    result = _dedup_alerts(alerts)
    assert len(result) == 1
    assert result[0]["type"] == "Air"


def test_lifestyle_alert_dedup_keeps_distinct_types():
    """Alerts of different types are all preserved after dedup."""
    from web.routes import _dedup_alerts
    alerts = [
        {"type": "Health",  "level": "CRITICAL", "msg": "Cardiac risk."},
        {"type": "Commute", "level": "WARNING",  "msg": "Heavy rain on highway."},
        {"type": "Air",     "level": "WARNING",  "msg": "空氣品質不良。"},
    ]
    result = _dedup_alerts(alerts)
    assert len(result) == 3
