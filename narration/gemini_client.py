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

def _load_system_prompt(lang: str = 'en') -> str:
    """Import the system prompt from prompt_builder to avoid duplication."""
    from narration.llm_prompt_builder import build_system_prompt
    return build_system_prompt(lang=lang)


def generate_narration(messages: list[dict], model_override: str | None = None, lang: str = 'en') -> str:
    """
    Send the prepared message list to Gemini and return the narration text.
    """
    system_prompt = _load_system_prompt(lang)
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

    # Use a fresh client with a long timeout to avoid ReadTimeout
    client = genai.Client(api_key=GEMINI_API_KEY, http_options={'timeout': 120})

    # 1. Primary Attempt: GEMINI_PRO
    try:
        model_to_use = model_override or GEMINI_PRO_MODEL
        if not model_to_use.startswith("models/"):
            model_to_use = f"models/{model_to_use}"
            
        logger.info("Attempting Gemini (%s) with 120s timeout", model_to_use)
        response = client.models.generate_content(
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
    except Exception as e:
        logger.error("Gemini Pro failed: %s: %s", type(e).__name__, e)
        logger.debug("Full traceback:", exc_info=True)

    # 2. Fallback Attempt: GEMINI_FLASH
    try:
        flash_model = GEMINI_FLASH_MODEL
        if not flash_model.startswith("models/"):
            flash_model = f"models/{flash_model}"
            
        logger.info("Attempting Gemini Flash fallback (%s) with 120s timeout", flash_model)
        response = client.models.generate_content(
            model=flash_model,
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
        logger.error("Gemini Flash fallback failed: %s: %s", type(exc).__name__, exc)
        logger.debug("Full traceback:", exc_info=True)
        raise RuntimeError(f"All Gemini models failed: {exc}") from exc

