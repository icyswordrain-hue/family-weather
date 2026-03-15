"""
claude_client.py — Calls Anthropic Claude to generate the narration text.
"""

from __future__ import annotations

import json
import logging
import re
import anthropic

from config import (
    CLAUDE_MODEL,
    CLAUDE_MAX_TOKENS,
    ANTHROPIC_API_KEY,
    NARRATION_TIMEOUT_PRO,
)
logger = logging.getLogger(__name__)

_METADATA_SEP = re.compile(r'-{3}\s*METADATA\s*-{3}', re.IGNORECASE)


def _has_parseable_metadata(text: str) -> bool:
    """Return True if text contains ---METADATA--- followed by valid JSON."""
    parts = _METADATA_SEP.split(text, maxsplit=1)
    if len(parts) < 2:
        return False
    remainder = parts[1].strip()
    # Strip optional ---REGEN--- and ---CARDS--- sections
    remainder = remainder.split("---REGEN---", 1)[0]
    remainder = remainder.split("---CARDS---", 1)[0]
    remainder = re.sub(r'^```(?:json)?\s*\n?', '', remainder.strip(), flags=re.MULTILINE)
    remainder = re.sub(r'\n?```\s*$', '', remainder, flags=re.MULTILINE)
    try:
        json.loads(remainder.strip())
        return True
    except (json.JSONDecodeError, ValueError):
        return False

_client: anthropic.Anthropic | None = None

def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        import os
        api_key = os.environ.get("ANTHROPIC_API_KEY") or ANTHROPIC_API_KEY
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        _client = anthropic.Anthropic(api_key=api_key, max_retries=0)
    return _client


def _load_system_prompt(lang: str = 'en') -> str:
    """Import the system prompt from prompt_builder."""
    from narration.llm_prompt_builder import build_system_prompt
    return build_system_prompt(lang=lang)


def generate_narration(messages: list[dict], model_override: str | None = None, lang: str = 'en', system_prompt_override: str | None = None, max_tokens: int | None = None) -> str:
    """
    Send the prepared message list to Claude and return the narration text.

    Args:
        messages: Output of prompt_builder.build_prompt() (Gemini format).
                 We need to convert this to Claude format.

    Returns:
        The full broadcast narration as a plain-text string.

    Raises:
        RuntimeError if the API call fails.
    """
    client = _get_client()
    system_prompt = system_prompt_override if system_prompt_override is not None else _load_system_prompt(lang)
    system_with_cache = [
        {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}},
    ]

    # Convert Gemini-style messages (role='model'/'user', parts=[{text}])
    # to Claude-style messages (role='assistant'/'user', content=str)
    claude_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        # Gemini uses 'model', Claude uses 'assistant'
        if role == "model":
            role = "assistant"

        text = " ".join(p["text"] for p in msg.get("parts", []) if "text" in p)
        if text:
            claude_messages.append({"role": role, "content": text})

    # 1. Primary Attempt
    try:
        model_to_use = model_override or CLAUDE_MODEL
        logger.info("Attempting Claude (%s) with %.1fs timeout", model_to_use, float(NARRATION_TIMEOUT_PRO))
        response = client.messages.create(
            model=model_to_use,
            max_tokens=max_tokens or CLAUDE_MAX_TOKENS,
            system=system_with_cache,
            messages=claude_messages,
            temperature=0.7,
            timeout=float(NARRATION_TIMEOUT_PRO),
        )
        text_blocks = [block.text for block in response.content if block.type == "text"]
        text = "".join(text_blocks)
        if response.stop_reason == "max_tokens":
            if text and not _has_parseable_metadata(text):
                logger.warning("Claude (%s) truncated at max_tokens=%d with unparseable metadata — falling through to fallback model.", model_to_use, max_tokens or CLAUDE_MAX_TOKENS)
            else:
                logger.warning("Claude response truncated (hit max_tokens=%d). METADATA block may be incomplete.", max_tokens or CLAUDE_MAX_TOKENS)
                if text:
                    return text.strip()
        elif text:
            return text.strip()
    except Exception as exc:
        logger.warning("Claude primary failed or timed out: %s", exc)

    # 2. Fallback Attempt (Haiku)
    from config import CLAUDE_FALLBACK_MODEL, NARRATION_TIMEOUT_FLASH
    try:
        logger.info("Attempting Claude fallback (%s) with %.1fs timeout", CLAUDE_FALLBACK_MODEL, float(NARRATION_TIMEOUT_FLASH))
        response = client.messages.create(
            model=CLAUDE_FALLBACK_MODEL,
            max_tokens=max_tokens or CLAUDE_MAX_TOKENS,
            system=system_with_cache,
            messages=claude_messages,
            temperature=0.7,
            timeout=float(NARRATION_TIMEOUT_FLASH),
        )
        text_blocks = [block.text for block in response.content if block.type == "text"]
        text = "".join(text_blocks)
        if response.stop_reason == "max_tokens":
            logger.warning("Claude fallback (%s) truncated (hit max_tokens=%d). metadata_ok=%s",
                           CLAUDE_FALLBACK_MODEL, max_tokens or CLAUDE_MAX_TOKENS, _has_parseable_metadata(text) if text else False)
        if text:
            return text.strip()
    except Exception as exc:
        logger.error("Claude fallback failed: %s", exc)
        raise RuntimeError(f"Claude narration generation failed: {exc}") from exc

    raise RuntimeError("Claude returned empty response from both models")
