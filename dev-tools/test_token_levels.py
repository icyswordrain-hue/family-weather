"""
test_token_levels.py — Diagnostic: test narration at 3 token levels for both providers.

Usage:
    RUN_MODE=LOCAL python dev-tools/test_token_levels.py

Requires ANTHROPIC_API_KEY and GEMINI_API_KEY in .env or environment.
Fetches live weather data, builds a real prompt (normal + regen), then calls
each provider at 1600 / 2200 / 2800 max_tokens (no thinking) and reports
truncation stats.  Total: 12 API calls (2 providers × 3 levels × 2 modes).
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import sys
import time

# Force UTF-8 output on Windows (cp950 can't print checkmarks)
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Ensure project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("RUN_MODE", "LOCAL")

from dotenv import load_dotenv
load_dotenv()

import anthropic
from google import genai

from config import (
    CLAUDE_MODEL,
    GEMINI_PRO_MODEL,
    GEMINI_API_KEY,
    ANTHROPIC_API_KEY,
    HISTORY_DAYS,
    NARRATION_TIMEOUT_PRO,
)
from narration.llm_prompt_builder import build_prompt, build_system_prompt
from narration.claude_client import _has_parseable_metadata

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("token_levels")

TOKEN_LEVELS = [1600, 2200, 2800]
_METADATA_SEP = re.compile(r'-{3}\s*METADATA\s*-{3}', re.IGNORECASE)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _word_count(text: str) -> int:
    """Count words in the narration portion (before ---METADATA---)."""
    parts = _METADATA_SEP.split(text, maxsplit=1)
    narration = parts[0] if parts else text
    return len(narration.split())


def _has_regen(text: str) -> bool:
    return "---REGEN---" in text.upper()


def _char_count(text: str) -> int:
    """Count characters in the narration portion (useful for zh-TW)."""
    parts = _METADATA_SEP.split(text, maxsplit=1)
    narration = parts[0].strip() if parts else text.strip()
    return len(narration)


# ── Data fetching (mirrors app.py _pipeline_steps) ──────────────────────────

def _fetch_and_process():
    """Fetch weather data, return (processed, history) for prompt building."""
    from data.fetch_cwa import fetch_current_conditions, fetch_all_forecasts, fetch_all_forecasts_7day
    from data.fetch_moenv import fetch_all_aqi
    from data.weather_processor import process
    from history.conversation import load_history

    logger.info("Fetching CWA current conditions...")
    current = fetch_current_conditions()

    logger.info("Fetching CWA 36h forecasts...")
    forecasts = fetch_all_forecasts({})

    logger.info("Fetching CWA 7-day forecasts...")
    forecasts_7day = fetch_all_forecasts_7day({})

    logger.info("Fetching MOENV AQI...")
    aqi = fetch_all_aqi()

    logger.info("Loading history...")
    history = load_history(days=HISTORY_DAYS)

    logger.info("Processing weather data...")
    from data.station_history import load_recent_station_history
    station_history = load_recent_station_history(hours=24)
    processed = process(current, forecasts, aqi, history, forecasts_7day, station_history=station_history)

    return processed, history


def _build_prompts(processed: dict, history: list[dict]) -> tuple[list[dict], list[dict]]:
    """Build normal and regen prompt messages."""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")

    # Normal prompt
    normal_messages = build_prompt(processed, history, today_date=today)

    # Regen prompt — set the flag so build_prompt includes ---REGEN--- instructions
    import copy
    regen_processed = copy.deepcopy(processed)
    regen_processed["regenerate_meal_lists"] = True
    regen_messages = build_prompt(regen_processed, history, today_date=today)

    return normal_messages, regen_messages


# ── Provider calls ───────────────────────────────────────────────────────────

def _call_claude(messages: list[dict], max_tokens: int, label: str) -> dict:
    """Call Claude API directly, return stats dict."""
    api_key = os.environ.get("ANTHROPIC_API_KEY") or ANTHROPIC_API_KEY
    client = anthropic.Anthropic(api_key=api_key, max_retries=0)
    system_prompt = build_system_prompt(lang="zh-TW")

    # Convert Gemini-style messages to Claude-style
    claude_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        if role == "model":
            role = "assistant"
        text = " ".join(p["text"] for p in msg.get("parts", []) if "text" in p)
        if text:
            claude_messages.append({"role": role, "content": text})

    t0 = time.time()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
        messages=claude_messages,
        temperature=0.7,
        timeout=float(NARRATION_TIMEOUT_PRO),
    )
    elapsed = time.time() - t0

    text = "".join(b.text for b in response.content if b.type == "text")
    return {
        "provider": "claude",
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "used_tokens": response.usage.output_tokens,
        "stop_reason": response.stop_reason,
        "metadata_ok": _has_parseable_metadata(text) if text else False,
        "has_regen": _has_regen(text) if text else False,
        "chars": _char_count(text) if text else 0,
        "elapsed": round(elapsed, 1),
        "label": label,
    }


def _call_gemini(messages: list[dict], max_tokens: int, label: str) -> dict:
    """Call Gemini API directly, return stats dict."""
    api_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
    system_prompt = build_system_prompt(lang="zh-TW")

    model = GEMINI_PRO_MODEL
    if not model.startswith("models/"):
        model = f"models/{model}"

    gemini_contents = []
    for msg in messages:
        role = msg.get("role", "user")
        text = " ".join(p["text"] for p in msg.get("parts", []) if "text" in p)
        if text:
            gemini_contents.append(
                genai.types.Content(role=role, parts=[genai.types.Part(text=text)])
            )

    timeout_ms = int(NARRATION_TIMEOUT_PRO) * 1000
    client = genai.Client(api_key=api_key, http_options=genai.types.HttpOptions(timeout=timeout_ms))

    t0 = time.time()
    response = client.models.generate_content(
        model=model,
        contents=gemini_contents,
        config=genai.types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
            temperature=0.7,
            thinking_config=genai.types.ThinkingConfig(thinking_budget=0),
        ),
    )
    elapsed = time.time() - t0

    text = response.text or ""

    # Extract finish reason
    try:
        finish = str(response.candidates[0].finish_reason).upper()
    except (IndexError, AttributeError):
        finish = "UNKNOWN"

    # Extract token count
    try:
        used = response.usage_metadata.candidates_token_count
    except (AttributeError, TypeError):
        used = -1

    return {
        "provider": "gemini",
        "model": GEMINI_PRO_MODEL,
        "max_tokens": max_tokens,
        "used_tokens": used,
        "stop_reason": finish,
        "metadata_ok": _has_parseable_metadata(text) if text else False,
        "has_regen": _has_regen(text) if text else False,
        "chars": _char_count(text) if text else 0,
        "elapsed": round(elapsed, 1),
        "label": label,
    }


def _make_error(provider: str, model: str, max_tokens: int, label: str, err: Exception) -> dict:
    return {
        "provider": provider, "model": model, "max_tokens": max_tokens,
        "used_tokens": -1, "stop_reason": f"ERROR", "metadata_ok": False,
        "has_regen": False, "chars": 0, "elapsed": 0, "label": label,
        "_error": str(err),
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 100)
    print("  Token Level Diagnostic — narration truncation test (normal + regen)")
    print(f"  Levels: {TOKEN_LEVELS}")
    print(f"  Claude model: {CLAUDE_MODEL}")
    print(f"  Gemini model: {GEMINI_PRO_MODEL}")
    print(f"  Current config: CLAUDE_MAX_TOKENS=1600, CLAUDE_MAX_TOKENS_REGEN=2000")
    print(f"  Current config: GEMINI_MAX_TOKENS=1600, GEMINI_MAX_TOKENS_REGEN=2000")
    print("=" * 100)
    print()

    processed, history = _fetch_and_process()
    normal_msgs, regen_msgs = _build_prompts(processed, history)
    print(f"\nPrompts built. Normal: {len(normal_msgs)} msg(s), Regen: {len(regen_msgs)} msg(s).")
    print(f"Starting 12 API calls (2 providers x 3 levels x 2 modes)...\n")

    results = []

    # ── Normal runs ──────────────────────────────────────────────────────
    print("=" * 60)
    print("  NORMAL (no regen)")
    print("=" * 60)

    for level in TOKEN_LEVELS:
        print(f"── Claude normal @ {level} ──")
        try:
            r = _call_claude(normal_msgs, level, "normal")
            results.append(r)
            ok = "Y" if r["metadata_ok"] else "N"
            print(f"   stop={r['stop_reason']}  used={r['used_tokens']}  meta={ok}  chars={r['chars']}  {r['elapsed']}s")
        except Exception as e:
            print(f"   FAILED: {e}")
            results.append(_make_error("claude", CLAUDE_MODEL, level, "normal", e))

    for level in TOKEN_LEVELS:
        print(f"── Gemini normal @ {level} ──")
        try:
            r = _call_gemini(normal_msgs, level, "normal")
            results.append(r)
            ok = "Y" if r["metadata_ok"] else "N"
            print(f"   stop={r['stop_reason']}  used={r['used_tokens']}  meta={ok}  chars={r['chars']}  {r['elapsed']}s")
        except Exception as e:
            print(f"   FAILED: {e}")
            results.append(_make_error("gemini", GEMINI_PRO_MODEL, level, "normal", e))

    # ── Regen runs ───────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  REGEN (regenerate_meal_lists=True)")
    print("=" * 60)

    for level in TOKEN_LEVELS:
        print(f"── Claude regen @ {level} ──")
        try:
            r = _call_claude(regen_msgs, level, "regen")
            results.append(r)
            ok = "Y" if r["metadata_ok"] else "N"
            rg = "Y" if r["has_regen"] else "N"
            print(f"   stop={r['stop_reason']}  used={r['used_tokens']}  meta={ok}  regen={rg}  chars={r['chars']}  {r['elapsed']}s")
        except Exception as e:
            print(f"   FAILED: {e}")
            results.append(_make_error("claude", CLAUDE_MODEL, level, "regen", e))

    for level in TOKEN_LEVELS:
        print(f"── Gemini regen @ {level} ──")
        try:
            r = _call_gemini(regen_msgs, level, "regen")
            results.append(r)
            ok = "Y" if r["metadata_ok"] else "N"
            rg = "Y" if r["has_regen"] else "N"
            print(f"   stop={r['stop_reason']}  used={r['used_tokens']}  meta={ok}  regen={rg}  chars={r['chars']}  {r['elapsed']}s")
        except Exception as e:
            print(f"   FAILED: {e}")
            results.append(_make_error("gemini", GEMINI_PRO_MODEL, level, "regen", e))

    # ── Summary tables ───────────────────────────────────────────────────
    header = f"{'Provider':<10} {'Mode':<7} {'MaxTok':>6} {'Used':>6} {'Stop':<16} {'Meta':>4} {'Regen':>5} {'Chars':>5} {'Time':>6}"
    sep = "-" * 100

    print("\n" + "=" * 100)
    print("  SUMMARY")
    print("=" * 100)
    print(header)
    print(sep)

    normal_results = [r for r in results if r["label"] == "normal"]
    regen_results = [r for r in results if r["label"] == "regen"]

    for r in normal_results:
        meta = "Y" if r["metadata_ok"] else "N"
        regen = "Y" if r["has_regen"] else "-"
        print(f"{r['provider']:<10} {r['label']:<7} {r['max_tokens']:>6} {r['used_tokens']:>6} {r['stop_reason']:<16} {meta:>4} {regen:>5} {r['chars']:>5} {r['elapsed']:>5.1f}s")

    print(sep)
    for r in regen_results:
        meta = "Y" if r["metadata_ok"] else "N"
        regen = "Y" if r["has_regen"] else "N"
        print(f"{r['provider']:<10} {r['label']:<7} {r['max_tokens']:>6} {r['used_tokens']:>6} {r['stop_reason']:<16} {meta:>4} {regen:>5} {r['chars']:>5} {r['elapsed']:>5.1f}s")

    print("=" * 100)

    # ── Recommendations ──────────────────────────────────────────────────
    print("\n  RECOMMENDATIONS")
    print(sep)
    for provider in ["claude", "gemini"]:
        normal = [r for r in normal_results if r["provider"] == provider and r["used_tokens"] > 0]
        regen = [r for r in regen_results if r["provider"] == provider and r["used_tokens"] > 0]

        if normal:
            max_normal = max(r["used_tokens"] for r in normal)
            # Find lowest level where it didn't truncate
            ok_levels = [r["max_tokens"] for r in normal if r["stop_reason"] not in ("max_tokens", "FINISHREASON.MAX_TOKENS")]
            rec_normal = min(ok_levels) if ok_levels else f">{TOKEN_LEVELS[-1]}"
            print(f"  {provider} normal:  peak usage = {max_normal} tokens.  Recommended max_tokens = {rec_normal}")

        if regen:
            max_regen = max(r["used_tokens"] for r in regen)
            ok_levels = [r["max_tokens"] for r in regen if r["stop_reason"] not in ("max_tokens", "FINISHREASON.MAX_TOKENS")]
            rec_regen = min(ok_levels) if ok_levels else f">{TOKEN_LEVELS[-1]}"
            print(f"  {provider} regen:   peak usage = {max_regen} tokens.  Recommended max_tokens = {rec_regen}")

    print(sep)


if __name__ == "__main__":
    main()
