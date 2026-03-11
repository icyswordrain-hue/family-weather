"""tests/test_fallback_narrator.py — Unit tests for the fallback narrator CARDS output."""
from narration.fallback_narrator import build_narration
from narration.llm_prompt_builder import parse_narration_response

MINIMAL_PROCESSED = {
    "current": {"AT": 22.0, "RH": 75, "RAIN": 0, "beaufort_desc": "Light breeze", "wind_dir_text": "N"},
    "commute": {
        "morning": {"AT": 20.0, "precip_text": "Unlikely", "beaufort_desc": "Calm", "wind_dir_text": "N", "hazards": []},
        "evening": {"AT": 23.0, "precip_text": "Unlikely", "beaufort_desc": "Calm", "wind_dir_text": "S", "hazards": []},
    },
    "climate_control": {"mode": "Off", "estimated_hours": 0, "set_temp": None, "notes": []},
    "meal_mood": {"mood": "Warm & Pleasant", "top_suggestions": ["滷肉飯"], "all_suggestions": ["滷肉飯"]},
    "forecast_segments": {
        "Morning": {"AT": 20.0, "precip_text": "Unlikely", "cloud_cover": "Partly Cloudy"},
        "Afternoon": {"AT": 25.0, "precip_text": "Unlikely", "cloud_cover": "Sunny"},
    },
    "transitions": [],
    "heads_ups": [],
    "cardiac_alert": None,
    "menieres_alert": None,
    "outdoor_index": {"grade": "B", "label": "Good", "score": 75, "best_window": "9am–11am", "top_activity": "walking", "activity_scores": {}},
    "location_rec": {"top_locations": [{"name": "Dahan River Bikeway", "activity": "cycling", "surface": "paved", "notes": "Flat paved path."}], "mood": "Nice"},
    "aqi_realtime": {"aqi": 40, "status": "Good"},
    "aqi_forecast": {},
    "recent_meals": [],
    "recent_locations": [],
}


def test_fallback_produces_cards_block():
    """build_narration must include a parseable ---CARDS--- JSON block."""
    text = build_narration(MINIMAL_PROCESSED, date_str="2026-02-28")
    assert "---CARDS---" in text


def test_cards_have_all_required_keys():
    """Parsed cards must have wardrobe, rain_gear, commute, meals, hvac, garden, outdoor, alert."""
    text = build_narration(MINIMAL_PROCESSED, date_str="2026-02-28")
    parsed = parse_narration_response(text)
    cards = parsed["cards"]
    for key in ("wardrobe", "rain_gear", "commute", "meals", "hvac", "garden", "outdoor", "alert"):
        assert key in cards, f"Missing card key: {key}"


def test_alert_card_has_text_and_level():
    """Alert card must be a dict with 'text' and 'level'."""
    text = build_narration(MINIMAL_PROCESSED, date_str="2026-02-28")
    parsed = parse_narration_response(text)
    alert = parsed["cards"]["alert"]
    assert isinstance(alert, dict)
    assert "text" in alert
    assert "level" in alert
    assert alert["level"] in ("INFO", "WARNING", "CRITICAL")


def test_metadata_block_present_and_parseable():
    """build_narration must include a parseable ---METADATA--- JSON block."""
    text = build_narration(MINIMAL_PROCESSED, date_str="2026-02-28")
    parsed = parse_narration_response(text)
    assert "garden" in parsed["metadata"]
    assert "accuracy_grade" in parsed["metadata"]


def test_history_garden_continuity():
    """Yesterday's garden topic from history should appear in the garden card."""
    history = [{"generated_at": "2026-02-27T08:00:00+08:00", "metadata": {"garden": "soil moisture check"}}]
    text = build_narration(MINIMAL_PROCESSED, date_str="2026-02-28", history=history)
    parsed = parse_narration_response(text)
    assert "soil moisture check" in parsed["cards"]["garden"]


def test_no_alert_when_no_heads_ups():
    """With no heads_ups and no cardiac/menieres, alert text should be a brief all-clear message and level INFO."""
    text = build_narration(MINIMAL_PROCESSED, date_str="2026-02-28")
    parsed = parse_narration_response(text)
    alert = parsed["cards"]["alert"]
    assert alert["level"] == "INFO"
    assert alert["text"] == "All clear today."


def test_zh_cards_use_chinese():
    """ZH lang should produce Chinese text in card fields."""
    text = build_narration(MINIMAL_PROCESSED, date_str="2026-02-28", lang="zh-TW")
    parsed = parse_narration_response(text)
    # Chinese characters appear in at least one card
    all_text = " ".join(str(v) for v in parsed["cards"].values() if isinstance(v, str))
    assert any('\u4e00' <= c <= '\u9fff' for c in all_text), "Expected Chinese characters in ZH cards"
