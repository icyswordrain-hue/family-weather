"""tests/test_narration_parser.py — Tests for parse_narration_response() card derivation
from expanded ---METADATA--- fields and system prompt structure.
"""
import pytest
from narration.llm_prompt_builder import (
    parse_narration_response,
    V7_SYSTEM_PROMPT_EN,
    V7_SYSTEM_PROMPT_ZH,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

MOCK_METADATA = (
    '{"wardrobe": "light jacket", "wardrobe_tagline": "Light jacket; no rain gear needed.",'
    ' "rain_gear": false, "rain_gear_text": "No rain expected. Leave the umbrella at home.",'
    ' "commute_am": "Morning drive looks clear.", "commute_pm": "Evening should be smooth.",'
    ' "commute_tagline": "Clear roads, normal commute.",'
    ' "meal": null, "meals_text": "A warm soup suits the cool evening.",'
    ' "meals_tagline": "Warm soup for a cool evening.",'
    ' "outdoor": "Conditions are excellent for a walk.", "outdoor_tagline": "Great for walking — head out mid-morning.",'
    ' "garden": "watering", "garden_text": "Check soil moisture in the morning. Tomatoes may need watering.",'
    ' "garden_tagline": "Check soil; water tomatoes.",'
    ' "climate": "No HVAC needed today.", "hvac_tagline": "Open windows — no AC needed.",'
    ' "air_quality_summary": "Tomorrow air looks clean — no precautions needed.",'
    ' "air_quality_tagline": "Clean air — no precautions.",'
    ' "alert_text": "A pleasant day overall.", "alert_level": "INFO",'
    ' "cardiac_alert": false, "menieres_alert": false,'
    ' "forecast_oneliner": "warm day", "accuracy_grade": "spot on"}'
)

MOCK_RESPONSE = f"""P1 conditions paragraph.

P2 garden and commute paragraph.

P3 outdoor and meal paragraph.

P4 hvac and air quality paragraph.

P5 forecast paragraph.

---METADATA---
{MOCK_METADATA}
"""

MOCK_RESPONSE_WITH_REGEN = (
    MOCK_RESPONSE
    + '\n---REGEN---\n{"meals": {"hot_humid": ["beef noodles"]}, "locations": {}}\n'
)


# ── parse_narration_response() tests ─────────────────────────────────────────

def test_parse_derives_cards_from_metadata():
    result = parse_narration_response(MOCK_RESPONSE)
    cards = result.get("cards", {})
    assert "wardrobe" in cards
    assert "outdoor" in cards
    assert "alert" in cards
    assert cards["wardrobe"] == "light jacket"


def test_parse_cards_alert_is_dict():
    result = parse_narration_response(MOCK_RESPONSE)
    alert = result["cards"]["alert"]
    assert isinstance(alert, dict)
    assert alert["level"] == "INFO"
    assert "pleasant" in alert["text"]


def test_parse_cards_missing_gracefully():
    response = "P1.\n\nP2.\n\nP5.\n\nP6.\n\n---METADATA---\n{}"
    result = parse_narration_response(response)
    assert result.get("cards", {}) == {}


def test_parse_cards_and_regen_coexist():
    result = parse_narration_response(MOCK_RESPONSE_WITH_REGEN)
    cards = result.get("cards", {})
    assert "wardrobe" in cards
    regen = result.get("regen")
    assert regen is not None
    assert "meals" in regen


def test_parse_metadata_still_works():
    result = parse_narration_response(MOCK_RESPONSE)
    meta = result.get("metadata", {})
    assert meta.get("accuracy_grade") == "spot on"
    assert meta.get("rain_gear") is False


def test_parse_paragraphs_still_assigned():
    result = parse_narration_response(MOCK_RESPONSE)
    paragraphs = result.get("paragraphs", {})
    assert "p1_conditions" in paragraphs
    assert "p2_garden_commute" in paragraphs


def test_commute_card_combines_am_pm():
    result = parse_narration_response(MOCK_RESPONSE)
    commute = result["cards"]["commute"]
    assert "Morning" in commute
    assert "Evening" in commute


def test_taglines_populated_from_metadata():
    result = parse_narration_response(MOCK_RESPONSE)
    cards = result["cards"]
    assert cards["wardrobe_tagline"] == "Light jacket; no rain gear needed."
    assert cards["commute_tagline"] == "Clear roads, normal commute."
    assert cards["meals_tagline"] == "Warm soup for a cool evening."


# ── System prompt tests ───────────────────────────────────────────────────────

_METADATA_KEYS = [
    "wardrobe", "wardrobe_tagline", "rain_gear", "rain_gear_text",
    "commute_am", "commute_pm", "commute_tagline",
    "meal", "meals_text", "meals_tagline",
    "outdoor", "outdoor_tagline",
    "garden", "garden_text", "garden_tagline",
    "climate", "hvac_tagline",
    "air_quality_summary", "air_quality_tagline",
    "alert_text", "alert_level",
    "cardiac_alert", "menieres_alert",
    "forecast_oneliner", "accuracy_grade",
]


def test_en_system_prompt_contains_metadata_separator():
    assert "---METADATA---" in V7_SYSTEM_PROMPT_EN


def test_en_system_prompt_no_cards_separator():
    assert "---CARDS---" not in V7_SYSTEM_PROMPT_EN


def test_en_system_prompt_contains_all_metadata_keys():
    for key in _METADATA_KEYS:
        assert f'"{key}"' in V7_SYSTEM_PROMPT_EN, f"Missing key '{key}' in EN prompt"


def test_zh_system_prompt_contains_metadata_separator():
    assert "---METADATA---" in V7_SYSTEM_PROMPT_ZH


def test_zh_system_prompt_no_cards_separator():
    assert "---CARDS---" not in V7_SYSTEM_PROMPT_ZH


def test_zh_system_prompt_contains_all_metadata_keys():
    for key in _METADATA_KEYS:
        assert f'"{key}"' in V7_SYSTEM_PROMPT_ZH, f"Missing key '{key}' in ZH prompt"


# ── Parser resilience tests ──────────────────────────────────────────────────

def test_parse_metadata_with_code_fences():
    """LLM wraps metadata JSON in markdown code fences."""
    response = f"P1.\n\nP2.\n\nP3.\n\nP4.\n\nP5.\n\n---METADATA---\n```json\n{MOCK_METADATA}\n```"
    result = parse_narration_response(response)
    assert result["metadata"].get("wardrobe") == "light jacket"
    assert result["cards"].get("wardrobe") == "light jacket"


def test_parse_metadata_case_insensitive_separator():
    """LLM uses lowercase separator."""
    response = f"P1.\n\nP2.\n\nP3.\n\nP4.\n\nP5.\n\n---metadata---\n{MOCK_METADATA}"
    result = parse_narration_response(response)
    assert result["metadata"].get("wardrobe") == "light jacket"
    assert result["cards"].get("wardrobe") == "light jacket"


def test_parse_metadata_spaced_separator():
    """LLM uses spaces within the dashes."""
    response = f"P1.\n\nP2.\n\nP3.\n\nP4.\n\nP5.\n\n--- METADATA ---\n{MOCK_METADATA}"
    result = parse_narration_response(response)
    assert result["metadata"].get("wardrobe") == "light jacket"
    assert result["cards"].get("wardrobe") == "light jacket"


def test_parse_no_metadata_returns_empty():
    """When no separator exists at all, metadata and cards are empty."""
    response = "P1.\n\nP2.\n\nP3.\n\nP4.\n\nP5."
    result = parse_narration_response(response)
    assert result["metadata"] == {}
    assert result["cards"] == {}


def test_parse_truncated_metadata_returns_empty_cards():
    """When METADATA JSON is truncated mid-string, cards should be empty (not crash)."""
    truncated = (
        "P1 conditions.\n\nP2 garden.\n\nP3 outdoor.\n\nP4 hvac.\n\nP5 forecast.\n\n"
        "---METADATA---\n"
        '{"wardrobe": "light jacket", "commute_am": "Clear morn'  # truncated
    )
    result = parse_narration_response(truncated)
    assert result["metadata"] == {}
    assert result["cards"] == {}
    assert "P1 conditions." in result["full_text"]


def test_parse_regen_with_code_fences():
    """LLM wraps regen JSON in markdown code fences."""
    response = (
        f"P1.\n\nP2.\n\nP3.\n\nP4.\n\nP5.\n\n---METADATA---\n{MOCK_METADATA}\n"
        '---REGEN---\n```json\n{"meals": {"hot_humid": ["noodles"]}, "locations": {}}\n```'
    )
    result = parse_narration_response(response)
    assert result["regen"] is not None
    assert "meals" in result["regen"]
