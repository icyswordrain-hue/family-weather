"""
gemini_client.py — Calls Vertex AI Gemini Flash to generate the narration text.
Also extracts per-paragraph text and metadata from the response.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig, Part, Content

from config import (
    GCP_PROJECT_ID,
    GCP_REGION,
    GEMINI_MODEL,
    GEMINI_MAX_TOKENS,
)

logger = logging.getLogger(__name__)

_model: Optional[GenerativeModel] = None


def _get_model() -> GenerativeModel:
    """Lazy-initialise the Vertex AI Gemini model (singleton)."""
    global _model
    if _model is None:
        vertexai.init(project=GCP_PROJECT_ID, location=GCP_REGION)
        _model = GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=_load_system_prompt(),
        )
    return _model


def _load_system_prompt() -> str:
    """Import the system prompt from prompt_builder to avoid duplication."""
    from narration.prompt_builder import build_system_prompt
    return build_system_prompt()


def generate_narration(messages: list[dict]) -> str:
    """
    Send the prepared message list to Gemini and return the narration text.

    Args:
        messages: Output of prompt_builder.build_prompt()

    Returns:
        The full broadcast narration as a plain-text string.

    Raises:
        RuntimeError if the API call fails.
    """
    model = _get_model()

    # Convert our message format to Vertex AI Content objects
    contents = []
    for msg in messages:
        role = msg.get("role", "user")
        parts = [Part.from_text(p["text"]) for p in msg.get("parts", [])]
        contents.append(Content(role=role, parts=parts))

    config = GenerationConfig(
        max_output_tokens=GEMINI_MAX_TOKENS,
        temperature=0.7,        # conversational warmth
        top_p=0.9,
    )

    try:
        response = model.generate_content(contents, generation_config=config)
        text = response.text
        if not text:
            raise RuntimeError("Gemini returned an empty response")
        return text.strip()
    except Exception as exc:
        logger.error("Gemini API call failed: %s", exc)
        raise RuntimeError(f"Gemini narration generation failed: {exc}") from exc


def extract_paragraphs(narration_text: str) -> dict[str, str]:
    """
    Attempt to extract individual paragraphs from the narration text.

    Paragraphs are identified by position (P1–P7) since the output is
    plain text. We split on double newlines and assign sequentially.

    Returns a dict with keys p1_current through p7_accountability.
    The mapping is best-effort — the model may merge or omit paragraphs
    depending on conditional rules.
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

    paragraphs: dict[str, str] = {}
    for i, chunk in enumerate(raw_chunks):
        if i < len(para_keys):
            paragraphs[para_keys[i]] = chunk

    # Ensure all keys exist (empty string if not present)
    for key in para_keys:
        paragraphs.setdefault(key, "")

    return paragraphs


def extract_metadata(narration_text: str, meal_suggestions: list[str]) -> dict:
    """
    Extract structured metadata from the narration text for history storage.

    Args:
        narration_text:   Full narration output.
        meal_suggestions: List of dish name strings that were offered to the model.

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
    for dish in meal_suggestions:
        # Match the Chinese characters portion before the parenthetical
        chinese = dish.split("(")[0].strip()
        if chinese and chinese in narration_text:
            metadata["meals_suggested"].append(chinese)

    # Look for a location mention (heuristic: text in 「」 or known keywords)
    location_match = re.search(r"[「]([^」]{2,20})[」]", narration_text)
    if location_match:
        metadata["location_suggested"] = location_match.group(1)

    # Look for activity keywords
    for activity in ["hiking", "biking", "kite", "walking", "jogging", "cycling"]:
        if activity.lower() in narration_text.lower():
            metadata["activity_suggested"] = activity
            break

    # Gardening topic — extract first mention of a plant or gardening term
    gardening_match = re.search(
        r"(seedling|transplant|watering|pruning|fertiliz|harvest|sowing|compost|soil|pot|seedbed)",
        narration_text, re.IGNORECASE
    )
    if gardening_match:
        metadata["gardening_tip_topic"] = gardening_match.group(1).lower()

    return metadata
