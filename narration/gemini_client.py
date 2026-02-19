"""
gemini_client.py — Calls Anthropic Claude to generate the narration text.
Also extracts per-paragraph text and metadata from the response.

Note: This module is still named gemini_client.py for import compatibility,
but now uses the Anthropic Claude API under the hood.
"""

from __future__ import annotations

import logging
import re

import anthropic

from config import (
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    GEMINI_MAX_TOKENS,
)

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    """Lazy-initialise the Anthropic client (singleton)."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic(
            api_key=ANTHROPIC_API_KEY,
            timeout=60.0,
        )
    return _client


def _load_system_prompt() -> str:
    """Import the system prompt from prompt_builder to avoid duplication."""
    from narration.prompt_builder import build_system_prompt
    return build_system_prompt()


def generate_narration(messages: list[dict]) -> str:
    """
    Send the prepared message list to Claude and return the narration text.

    Args:
        messages: Output of prompt_builder.build_prompt()

    Returns:
        The full broadcast narration as a plain-text string.

    Raises:
        RuntimeError if the API call fails.
    """
    client = _get_client()
    system_prompt = _load_system_prompt()

    # Convert our message format to Anthropic messages format
    # Each message has role + parts[{text}]; flatten parts into a single string
    claude_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        text = " ".join(p["text"] for p in msg.get("parts", []) if "text" in p)
        if text:
            claude_messages.append({"role": role, "content": text})

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=GEMINI_MAX_TOKENS,
            system=system_prompt,
            messages=claude_messages,
            temperature=0.7,
        )
        text = response.content[0].text if response.content else ""
        if not text:
            raise RuntimeError("Claude returned an empty response")
        return text.strip()
    except Exception as exc:
        logger.error("Claude API call failed: %s", exc)
        raise RuntimeError(f"Claude narration generation failed: {exc}") from exc


def extract_paragraphs(narration_text: str) -> dict[str, str]:
    """
    Extract individual paragraphs from the narration text using content heuristics.

    Paragraphs are identified by keyword matching, not sequential position,
    because P4 and P5 may be conditionally omitted by Claude.

    Returns a dict with keys p1_current through p7_accountability.
    """
    para_keys = [
        "p1_current",
        "p2_commute",
        "p3_garden_health",
        "p4_meals",
        "p5_climate_cardiac",
        "p6_forecast",
        "p7_accountability",
    ]

    # Split on blank lines; filter empty chunks
    raw_chunks = [c.strip() for c in re.split(r"\n{2,}", narration_text) if c.strip()]

    # Content-based keyword matchers (checked in priority order)
    _HEURISTICS = [
        ("p7_accountability", ["forecast accuracy", "forecast called for", "actual reading", "solid call", "prediction", "verdict", "call overall", "yesterday's forecast"]),
        ("p5_climate_cardiac", ["The AC", "air condition", "indoor air", "keep it set", "heater", "climate control", "dehumidify", "heating mode", "cooling mode", "cardiac alert", "heart health"]),
        ("p4_meals", ["lunch", "dinner", "dish", "meal suggestion", "niú", "miàn", "guō", "fàn", "tāng", "jī"]),
        ("p3_garden_health", ["gardening", "parkinson", "outdoor activity", "dad", "seedling", "plant", "prune", "soil"]),
        ("p2_commute", ["commute", "drive", "traffic", "road conditions", "shulin", "sanxia", "route"]),
        ("p6_forecast", ["today's story", "unfolding story", "bottom line", "throughout the day", "overnight"]),
    ]

    paragraphs: dict[str, str] = {}
    used_indices: set[int] = set()

    # First pass: match chunks to paragraph keys using heuristics
    for key, keywords in _HEURISTICS:
        for i, chunk in enumerate(raw_chunks):
            if i in used_indices:
                continue
            chunk_lower = chunk.lower()
            if any(kw.lower() in chunk_lower for kw in keywords):
                paragraphs[key] = chunk
                used_indices.add(i)
                break

    # P1 is always the first unmatched chunk (current conditions / heads-up)
    for i, chunk in enumerate(raw_chunks):
        if i not in used_indices:
            paragraphs["p1_current"] = chunk
            used_indices.add(i)
            break

    # Ensure all keys exist (empty string if not present)
    for key in para_keys:
        paragraphs.setdefault(key, "")

    return paragraphs


def extract_metadata(
    narration_text: str,
    meal_suggestions: list[str],
    location_suggestions: list[str] = [],
) -> dict:
    """
    Extract structured metadata from the narration text for history storage.

    Args:
        narration_text:       Full narration output (English with pinyin).
        meal_suggestions:     Dish name strings offered to the model.
        location_suggestions: Location names from the curated pool (for exact matching).

    Returns:
        Dict with meals_suggested, gardening_tip_topic, location_suggested,
        activity_suggested.
    """
    metadata: dict = {
        "meals_suggested": [],
        "gardening_tip_topic": "",
        "location_suggested": "",
        "activity_suggested": "",
    }

    # Detect which dish names from the suggestion pool appear in the narration
    # Since narration is now in English with pinyin, match the pinyin portion
    text_lower = narration_text.lower()
    for dish in meal_suggestions:
        # Extract pinyin portion from format: "涼麵 (liáng miàn, cold sesame noodles)"
        pinyin_match = re.search(r"\(([^)]+?)(?:,|\))", dish)
        if pinyin_match:
            pinyin = pinyin_match.group(1).strip().lower()
            if pinyin in text_lower:
                metadata["meals_suggested"].append(dish.split("(")[0].strip())
        else:
            dish_clean = dish.split("(")[0].strip()
            if dish_clean and dish_clean.lower() in text_lower:
                metadata["meals_suggested"].append(dish_clean)

    # Match location names from the curated pool (exact name matching for rotation dedup)
    if location_suggestions:
        for loc_name in location_suggestions:
            if loc_name.lower() in text_lower:
                metadata["location_suggested"] = loc_name
                break

    # Fallback: regex pattern for Taipei-area place names
    if not metadata["location_suggested"]:
        location_patterns = [
            r"(\b(?:Banqiao|Shulin|Sanxia|Yingge|Tucheng|Zhonghe|Xinzhuang|Tamsui|Bitan|Daan|Zhongshan)\b[^.]{0,30}(?:park|trail|riverside|plaza|forest|garden|bikeway|greenway|museum|center|courtyard))",
            r"(\b(?:park|trail|riverside|plaza|garden|bikeway|greenway)\b)",
        ]
        for pattern in location_patterns:
            location_match = re.search(pattern, narration_text, re.IGNORECASE)
            if location_match:
                metadata["location_suggested"] = location_match.group(1).strip()
                break

    # Look for activity keywords
    for activity in ["hiking", "biking", "kite", "walking", "jogging", "cycling",
                     "tai chi", "stretching", "strolling", "paddleboat", "e-bike"]:
        if activity.lower() in text_lower:
            metadata["activity_suggested"] = activity
            break

    # Gardening topic — extract first mention of a plant or gardening term
    gardening_match = re.search(
        r"(seedling|transplant|watering|pruning|fertiliz|harvest|sowing|compost|soil|pot|seedbed|mulch|weed|pest|herb)",
        narration_text, re.IGNORECASE
    )
    if gardening_match:
        metadata["gardening_tip_topic"] = gardening_match.group(1).lower()

    return metadata

