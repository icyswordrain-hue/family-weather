"""tests/test_narration_parser.py — Tests for parse_narration_response() ---CARDS--- extraction
and for ---CARDS--- presence in the EN/ZH system prompts.
"""
import pytest
from narration.llm_prompt_builder import (
    parse_narration_response,
    V6_SYSTEM_PROMPT_EN,
    V6_SYSTEM_PROMPT_ZH,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

MOCK_METADATA = (
    '{"wardrobe": "light jacket", "rain_gear": false, "commute_am": "clear",'
    ' "commute_pm": "clear", "meal": null, "outdoor": null, "garden": "watering",'
    ' "climate": null, "cardiac_alert": false, "menieres_alert": false,'
    ' "forecast_oneliner": "warm day", "accuracy_grade": "spot on"}'
)

MOCK_CARDS = (
    '{"wardrobe": "Wear a light jacket. Temps will be mild.",'
    ' "rain_gear": "No rain expected. Leave the umbrella at home.",'
    ' "commute": "Morning drive looks clear. Evening should be smooth.",'
    ' "meals": "A warm soup suits the cool evening. Keep lunch light.",'
    ' "hvac": "No HVAC needed today. Open a window for fresh air.",'
    ' "garden": "Check soil moisture in the morning. Tomatoes may need watering.'
    ' Avoid pruning in afternoon heat. Mulch retains moisture well.",'
    ' "outdoor": "Conditions are excellent for a walk. Choose flat routes for Dad.'
    ' Mid-morning is the best window. Bring water and sunscreen.",'
    ' "alert": {"text": "A pleasant day overall.", "level": "INFO"}}'
)

MOCK_RESPONSE = f"""P1 conditions paragraph.

P2 garden and commute paragraph.

P5 forecast paragraph.

P6 accuracy paragraph.

---METADATA---
{MOCK_METADATA}

---CARDS---
{MOCK_CARDS}
"""

MOCK_RESPONSE_WITH_REGEN = (
    MOCK_RESPONSE
    + '\n---REGEN---\n{"meals": {"hot_humid": ["beef noodles"]}, "locations": {}}\n'
)


# ── parse_narration_response() tests ─────────────────────────────────────────

def test_parse_extracts_cards():
    result = parse_narration_response(MOCK_RESPONSE)
    cards = result.get("cards", {})
    assert "wardrobe" in cards
    assert "outdoor" in cards
    assert "alert" in cards
    assert len(cards["wardrobe"].split(".")) >= 2


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


# ── System prompt tests ───────────────────────────────────────────────────────

_CARD_KEYS = ["wardrobe", "rain_gear", "commute", "meals", "hvac", "garden", "outdoor", "alert"]


def test_en_system_prompt_contains_cards_separator():
    assert "---CARDS---" in V6_SYSTEM_PROMPT_EN


def test_en_system_prompt_contains_all_card_keys():
    for key in _CARD_KEYS:
        assert f'"{key}"' in V6_SYSTEM_PROMPT_EN, f"Missing key '{key}' in EN prompt"


def test_zh_system_prompt_contains_cards_separator():
    assert "---CARDS---" in V6_SYSTEM_PROMPT_ZH


def test_zh_system_prompt_contains_all_card_keys():
    for key in _CARD_KEYS:
        assert f'"{key}"' in V6_SYSTEM_PROMPT_ZH, f"Missing key '{key}' in ZH prompt"
