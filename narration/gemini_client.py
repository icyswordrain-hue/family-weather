"""
gemini_client.py — Calls Google Gemini to generate the narration text.
Also extracts per-paragraph text and metadata from the response.
"""

from __future__ import annotations

import json
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

_METADATA_SEP = re.compile(r'-{3}\s*METADATA\s*-{3}', re.IGNORECASE)


def _has_parseable_metadata(text: str) -> bool:
    """Return True if text contains ---METADATA--- followed by valid JSON."""
    parts = _METADATA_SEP.split(text, maxsplit=1)
    if len(parts) < 2:
        return False
    remainder = parts[1].strip()
    remainder = remainder.split("---REGEN---", 1)[0]
    remainder = remainder.split("---CARDS---", 1)[0]
    remainder = re.sub(r'^```(?:json)?\s*\n?', '', remainder.strip(), flags=re.MULTILINE)
    remainder = re.sub(r'\n?```\s*$', '', remainder, flags=re.MULTILINE)
    try:
        json.loads(remainder.strip())
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def _load_system_prompt(lang: str = 'en') -> str:
    """Import the system prompt from prompt_builder to avoid duplication."""
    from narration.llm_prompt_builder import build_system_prompt
    return build_system_prompt(lang=lang)


def generate_narration(messages: list[dict], model_override: str | None = None, lang: str = 'en', system_prompt_override: str | None = None, max_tokens: int | None = None) -> str:
    """
    Send the prepared message list to Gemini and return the narration text.
    """
    system_prompt = system_prompt_override if system_prompt_override is not None else _load_system_prompt(lang)
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
        if not model_to_use.startswith("models/"):
            model_to_use = f"models/{model_to_use}"

        pro_timeout_ms = int(NARRATION_TIMEOUT_PRO) * 1000
        import os
        api_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
        client = genai.Client(api_key=api_key, http_options=genai.types.HttpOptions(timeout=pro_timeout_ms))
        logger.info("Attempting Gemini (%s) with %ds timeout", model_to_use, int(NARRATION_TIMEOUT_PRO))
        response = client.models.generate_content(
            model=model_to_use,
            contents=gemini_contents,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_tokens or GEMINI_MAX_TOKENS,
                temperature=0.7,
            ),
        )
        text = response.text or ""
        _truncated = False
        try:
            finish = response.candidates[0].finish_reason
            if finish and str(finish).upper() in ("MAX_TOKENS", "2"):
                _truncated = True
        except (IndexError, AttributeError):
            pass
        if _truncated and text and not _has_parseable_metadata(text):
            logger.warning("Gemini Pro (%s) truncated at max_tokens=%d with unparseable metadata — falling through to Flash.", model_to_use, max_tokens or GEMINI_MAX_TOKENS)
        elif _truncated:
            logger.warning("Gemini Pro response truncated (hit max_output_tokens=%d). METADATA block may be incomplete.", max_tokens or GEMINI_MAX_TOKENS)
            if text:
                return text.strip()
        elif text:
            return text.strip()
    except Exception as e:
        logger.error("Gemini Pro failed: %s: %s", type(e).__name__, e)
        logger.debug("Full traceback:", exc_info=True)

    # 2. Fallback Attempt: GEMINI_FLASH
    try:
        flash_model = GEMINI_FLASH_MODEL
        if not flash_model.startswith("models/"):
            flash_model = f"models/{flash_model}"

        flash_timeout_ms = int(NARRATION_TIMEOUT_FLASH) * 1000
        api_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
        client = genai.Client(api_key=api_key, http_options=genai.types.HttpOptions(timeout=flash_timeout_ms))
        logger.info("Attempting Gemini Flash fallback (%s) with %ds timeout", flash_model, int(NARRATION_TIMEOUT_FLASH))
        response = client.models.generate_content(
            model=flash_model,
            contents=gemini_contents,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_tokens or GEMINI_MAX_TOKENS,
                temperature=0.7,
            ),
        )
        text = response.text or ""
        try:
            finish = response.candidates[0].finish_reason
            if finish and str(finish).upper() in ("MAX_TOKENS", "2"):
                logger.warning("Gemini Flash (%s) truncated (hit max_output_tokens=%d). metadata_ok=%s",
                               flash_model, max_tokens or GEMINI_MAX_TOKENS, _has_parseable_metadata(text) if text else False)
        except (IndexError, AttributeError):
            pass
        if text:
            return text.strip()
        else:
            raise RuntimeError("Gemini Flash returned an empty response")
    except Exception as exc:
        logger.error("Gemini Flash fallback failed: %s: %s", type(exc).__name__, exc)
        logger.debug("Full traceback:", exc_info=True)
        raise RuntimeError(f"All Gemini models failed: {exc}") from exc

