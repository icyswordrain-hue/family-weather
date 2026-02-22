"""pipeline.py — Isolated orchestration functions for the broadcast pipeline.

Extracted from app.py _pipeline_steps() per Phase 3 plan (A2).
The generator/SSE machinery stays in app.py; these functions contain the
pure business logic that is now independently testable.
"""
from __future__ import annotations

import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from narration.llm_prompt_builder import build_prompt
from narration.fallback_narrator import build_narration
from narration.llm_summarizer import summarize_for_lifestyle, summarize_aqi_forecast

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
    provider_upper = provider.upper()
    try:
        messages = build_prompt(processed, history, date_str)
        if provider_upper == "GEMINI":
            if generate_gemini is None:
                raise RuntimeError("Gemini client not available")
            text = generate_gemini(messages)
            return text, "gemini"
        elif provider_upper == "CLAUDE":
            if generate_claude is None:
                raise RuntimeError("Claude client not available")
            text = generate_claude(messages)
            return text, "claude"
        else:
            raise ValueError(f"Unknown provider: {provider}")
    except Exception as exc:
        logger.warning("Narration failed (%s), falling back to template: %s", provider, exc)
        text = build_narration(processed, date_str=date_str)
        return text, "template"



def run_parallel_summarization(
    paragraphs: dict,
    aqi_forecast_raw: str,
) -> tuple[dict, str | None]:
    """Run lifestyle summarization and (optionally) AQI summary concurrently.

    Args:
        paragraphs:       Parsed narration paragraphs dict from parse_narration_response()
        aqi_forecast_raw: Raw AQI forecast content string; if empty, AQI summary is skipped.

    Returns:
        (lifestyle_summaries, aqi_summary_en)
        aqi_summary_en is None if aqi_forecast_raw was falsy.
    """
    aqi_summary_en: str | None = None

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_lifestyle = executor.submit(summarize_for_lifestyle, paragraphs)
        future_aqi = None
        if aqi_forecast_raw:
            future_aqi = executor.submit(summarize_aqi_forecast, aqi_forecast_raw)

        summaries = future_lifestyle.result()
        if future_aqi:
            aqi_summary_en = future_aqi.result()

    return summaries, aqi_summary_en
