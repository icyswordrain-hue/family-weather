"""pipeline.py — Isolated orchestration functions for the broadcast pipeline.

Extracted from app.py _pipeline_steps() per Phase 3 plan (A2).
The generator/SSE machinery stays in app.py; these functions contain the
pure business logic that is now independently testable.
"""
from __future__ import annotations

import logging
from datetime import datetime

from config import CST
from narration.llm_prompt_builder import build_prompt
from narration.fallback_narrator import build_narration
from backend.cache import NarrationCache, make_cache_key, _classify_time

# lang-aware cache — separate namespaces for EN and ZH results
_narration_cache = NarrationCache(ttl_seconds=1800)

# LLM clients — imported at module level so tests can patch them cleanly.
# We wrap in try/except so the module can still be imported even if a key is missing.
try:
    from narration.gemini_client import generate_narration as generate_gemini
except Exception as e:  # pragma: no cover
    logging.getLogger(__name__).error("Failed to import gemini_client: %s", e)
    generate_gemini = None  # type: ignore[assignment]

try:
    from narration.claude_client import generate_narration as generate_claude
except Exception as e:  # pragma: no cover
    logging.getLogger(__name__).error("Failed to import claude_client: %s", e)
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
    hour = datetime.now(CST).hour
    cache_key = make_cache_key(lang, city, wx_text, _classify_time(hour))

    provider_upper = provider.upper().strip()
    is_regen = bool(processed.get("regenerate_meal_lists"))

    cached = _narration_cache.get(cache_key)
    if cached and not is_regen:
        logger.info("Narration cache HIT: %s", cache_key)
        return cached
    logger.info("Narration requested via provider: %s (regen=%s)", provider_upper, is_regen)

    from config import GEMINI_MAX_TOKENS_REGEN, CLAUDE_MAX_TOKENS_REGEN, CLAUDE_REGEN_MODEL
    try:
        messages = build_prompt(processed, history, date_str)
    except Exception:
        logger.exception("build_prompt failed, falling back to template:")
        text = build_narration(processed, date_str=date_str, history=history, lang=lang)
        return text, "template"

    def _try_claude(msgs):
        if generate_claude is None:
            raise RuntimeError("Claude client not available")
        return generate_claude(
            msgs,
            lang=lang,
            max_tokens=CLAUDE_MAX_TOKENS_REGEN if is_regen else None,
            model_override=CLAUDE_REGEN_MODEL if is_regen else None,
        ), "claude"

    def _try_gemini(msgs):
        if generate_gemini is None:
            raise RuntimeError("Gemini client not available")
        return generate_gemini(
            msgs, lang=lang, max_tokens=GEMINI_MAX_TOKENS_REGEN if is_regen else None
        ), "gemini"

    # Build ordered attempt list: primary provider first, then cross-provider fallback
    if provider_upper == "CLAUDE":
        attempts = [("claude", _try_claude), ("gemini", _try_gemini)]
    elif provider_upper == "GEMINI":
        attempts = [("gemini", _try_gemini), ("claude", _try_claude)]
    else:
        logger.error("Unsupported provider selected: %s", provider_upper)
        text = build_narration(processed, date_str=date_str, history=history, lang=lang)
        return text, "template"

    for label, attempt_fn in attempts:
        try:
            logger.info("Calling %s client...", label)
            text, source = attempt_fn(messages)
            logger.info("%s narration successful.", label.capitalize())
            result = text, source
            if not is_regen:
                # Only cache if the response contains parseable metadata;
                # truncated responses with broken JSON would poison the cache.
                if "---METADATA---" in text.upper():
                    _narration_cache.set(cache_key, result)
                else:
                    logger.warning("Skipping cache — response missing ---METADATA--- separator")
            return result
        except Exception:
            logger.exception("Narration failed (%s):", label)

    # All LLM providers exhausted — fall back to template
    logger.warning("All LLM providers failed, falling back to template narrator")
    text = build_narration(processed, date_str=date_str, history=history, lang=lang)
    return text, "template"