"""
smoke_gemini.py — Verify that narration.gemini_client.generate_narration() works end-to-end.

Usage:
    python dev-tools/smoke_gemini.py
    python dev-tools/smoke_gemini.py --lang zh-TW
    python dev-tools/smoke_gemini.py --thinking-budget 512
    python dev-tools/smoke_gemini.py --thinking-budget 1024 --max-tokens 2800
"""
import logging
import os
import sys
import argparse

# Make project root importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

from dotenv import load_dotenv
load_dotenv()

from config import GEMINI_API_KEY, GEMINI_PRO_MODEL, GEMINI_FLASH_MODEL
from narration.gemini_client import generate_narration, _has_parseable_metadata

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", default="en", choices=["en", "zh-TW"])
    parser.add_argument("--thinking-budget", type=int, default=0, metavar="N",
                        help="Thinking token budget (0=disabled).")
    parser.add_argument("--max-tokens", type=int, default=None, metavar="N",
                        help="Override max_output_tokens (default: thinking_budget + 1800).")
    args = parser.parse_args()

    # Auto-scale ceiling: needs thinking_budget + ~700 output + headroom
    max_tokens = args.max_tokens or (args.thinking_budget + 1800)

    key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
    if not key:
        print("ERROR: GEMINI_API_KEY not set.")
        sys.exit(1)
    print(f"API key: {key[:6]}...{key[-4:]}")
    print(f"Pro model:      {GEMINI_PRO_MODEL}")
    print(f"Flash model:    {GEMINI_FLASH_MODEL}")
    print(f"Lang:           {args.lang}")
    print(f"thinking_budget:{args.thinking_budget}  max_tokens:{max_tokens}\n")

    # Use the real prompt builder with the same minimal fixture used in tests
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests"))
    from test_fallback_narrator import MINIMAL_PROCESSED
    from narration.llm_prompt_builder import build_prompt

    messages = build_prompt(MINIMAL_PROCESSED, history=[], today_date="2026-03-15")
    print(f"Built {len(messages)} message(s) via build_prompt()\n")

    try:
        text = generate_narration(messages, lang=args.lang, thinking_budget=args.thinking_budget, max_tokens=max_tokens)
    except Exception as exc:
        print(f"FAILURE: {type(exc).__name__}: {exc}")
        sys.exit(1)

    if not text:
        print("FAILURE: empty response.")
        sys.exit(1)

    metadata_ok = _has_parseable_metadata(text)
    print("--- Response preview (first 300 chars) ---")
    print(text[:300])
    print("...")
    print(f"\nmetadata_ok : {metadata_ok}")
    print(f"response len: {len(text)} chars")
    print(f"\n{'SUCCESS' if metadata_ok else 'WARNING: narration returned but metadata JSON is missing/unparseable'}")

if __name__ == "__main__":
    main()
