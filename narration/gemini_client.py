"""
gemini_client.py — Calls Google Gemini to generate the narration text.
Also extracts per-paragraph text and metadata from the response.
"""

from __future__ import annotations

import logging
import re

from google import genai

from config import (
    GEMINI_API_KEY,
    GEMINI_PRO_MODEL,
    GEMINI_FLASH_MODEL,
    GEMINI_MAX_TOKENS,
    NARRATION_TIMEOUT_PRO,
    NARRATION_TIMEOUT_FLASH,
)

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def _get_client(timeout: int = 120) -> genai.Client:
    """Lazy-initialise the Gemini client (singleton or per-timeout)."""
    global _client
    # Re-init if timeout changed significantly or first run
    if _client is None:
        _client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options={'timeout': timeout}
        )
    return _client


def _load_system_prompt() -> str:
    """Import the system prompt from prompt_builder to avoid duplication."""
    from narration.prompt_builder import build_system_prompt
    return build_system_prompt()


def generate_narration(messages: list[dict], model_override: str | None = None) -> str:
    """
    Send the prepared message list to Gemini and return the narration text.

    Args:
        messages: Output of prompt_builder.build_prompt()

    Returns:
        The full broadcast narration as a plain-text string.

    Raises:
        RuntimeError if the API call fails.
    """
    system_prompt = _load_system_prompt()
    gemini_contents = []
    for msg in messages:
        role = msg.get("role", "user")
        text = " ".join(p["text"] for p in msg.get("parts", []) if "text" in p)
        if text:
            gemini_contents.append(
                genai.types.Content(
                    role=role,
                    parts=[genai.types.Part(text=text)],
                )
            )

    # 1. Primary Attempt: GEMINI_PRO
    try:
        model_to_use = model_override or GEMINI_PRO_MODEL
        logger.info("Attempting Gemini (%s) with %ds timeout", model_to_use, NARRATION_TIMEOUT_PRO)
        client_pro = genai.Client(api_key=GEMINI_API_KEY, http_options={'timeout': NARRATION_TIMEOUT_PRO})
        response = client_pro.models.generate_content(
            model=model_to_use,
            contents=gemini_contents,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=GEMINI_MAX_TOKENS,
                temperature=0.7,
            ),
        )
        text = response.text or ""
        if text:
            return text.strip()
    except Exception as exc:
        logger.warning("Gemini Pro failed or timed out: %s", exc)

    # 2. Fallback Attempt: GEMINI_FLASH
    try:
        logger.info("Attempting Gemini Flash fallback (%s) with %ds timeout", GEMINI_FLASH_MODEL, NARRATION_TIMEOUT_FLASH)
        client_flash = genai.Client(api_key=GEMINI_API_KEY, http_options={'timeout': NARRATION_TIMEOUT_FLASH})
        response = client_flash.models.generate_content(
            model=GEMINI_FLASH_MODEL,
            contents=gemini_contents,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=GEMINI_MAX_TOKENS,
                temperature=0.7,
            ),
        )
        text = response.text or ""
        if text:
            return text.strip()
        else:
            raise RuntimeError("Gemini Flash returned an empty response")
    except Exception as exc:
        logger.error("Gemini Flash fallback also failed: %s", exc)
        raise RuntimeError(f"All Gemini models failed: {exc}") from exc

