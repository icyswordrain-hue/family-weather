"""pipeline.py — Isolated orchestration functions for the broadcast pipeline.

Extracted from app.py _pipeline_steps() per Phase 3 plan (A2).
The generator/SSE machinery stays in app.py; these functions contain the
pure business logic that is now independently testable.
"""
from __future__ import annotations

import logging
from datetime import datetime

from narration.llm_prompt_builder import build_prompt
from narration.fallback_narrator import build_narration
from backend.cache import NarrationCache, make_cache_key, _classify_time

# lang-aware cache — separate namespaces for EN and ZH results
_narration_cache = NarrationCache(ttl_seconds=1800)

# LLM clients — imported at module level so tests can patch them cleanly.
# We wrap in try/except so the module can still be imported even if a key is missing.
try:
    from narration.gemini_client import generate_narration as generate_gemini
except Exception:  # pragma: no cover
    generate_gemini = None  # type: ignore[assignment]

try:
    from narration.claude_client import generate_narration as generate_claude
except Exception:  # pragma: no cover
    generate_claude = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)



def check_regen_cycle(history: list[dict], date_str: str, cycle_days: int) -> bool:
    """Return True if a meal/location database regeneration should be triggered today.

    Scans history in reverse for the most recent entry flagged as a regen event.
    Returns True on first run (empty history) or when cycle_days have elapsed.
    """
    last_regen_date: datetime | None = None
    for day in reversed(history):
        meta = day.get("metadata", {})
        proc = day.get("processed_data", {})
        if meta.get("regen") or proc.get("regenerate_meal_lists"):
            raw = day.get("generated_at", "")[:10]
            try:
                last_regen_date = datetime.strptime(raw, "%Y-%m-%d")
                break
            except ValueError:
                continue

    if last_regen_date is None:
        return True  # No prior regen found → trigger on first run

    today_dt = datetime.strptime(date_str, "%Y-%m-%d")
    return (today_dt - last_regen_date).days >= cycle_days


def generate_narration_with_fallback(
    provider: str,
    processed: dict,
    history: list[dict],
    date_str: str,
    lang: str = 'en',
) -> tuple[str, str]:
    """Generate narration text via the given LLM provider, falling back to template.

    Args:
        provider: "GEMINI" or "CLAUDE" (case-insensitive comparison done internally)
        processed: Output of weather_processor.process()
        history:   Conversation history list
        date_str:  YYYY-MM-DD string for today

    Returns:
        (narration_text, source_label)
        source_label is "gemini", "claude", or "template".
    """
    # ── Cache check ────────────────────────────────────────────────────
    current = processed.get("current", {})
    city = "shulin"
    wx_text = current.get("beaufort_desc", current.get("weather_text", ""))
    hour = datetime.now().hour
    cache_key = make_cache_key(lang, city, wx_text, _classify_time(hour))

    cached = _narration_cache.get(cache_key)
    if cached:
        logger.info("Narration cache HIT: %s", cache_key)
        return cached

    provider_upper = provider.upper().strip()
    logger.info("Narration requested via provider: %s", provider_upper)
    try:
        messages = build_prompt(processed, history, date_str)
        if provider_upper == "GEMINI":
            if generate_gemini is None:
                logger.error("Gemini client is None (likely import failure or missing key)")
                raise RuntimeError("Gemini client not available")
            logger.info("Calling Gemini client...")
            text = generate_gemini(messages, lang=lang)
            logger.info("Gemini narration successful.")
            result = text, "gemini"
        elif provider_upper == "CLAUDE":
            if generate_claude is None:
                logger.error("Claude client is None (likely import failure or missing key)")
                raise RuntimeError("Claude client not available")
            logger.info("Calling Claude client...")
            text = generate_claude(messages, lang=lang)
            logger.info("Claude narration successful.")
            result = text, "claude"
        else:
            logger.error("Unsupported provider selected: %s", provider_upper)
            raise ValueError(f"Unknown provider: {provider}")
        
        # ── Cache store ────────────────────────────────────────────────────
        _narration_cache.set(cache_key, result)
        return result

    except Exception:
        logger.exception("Narration failed (%s), falling back to template:", provider_upper)
        text = build_narration(processed, date_str=date_str)
        return text, "template"


