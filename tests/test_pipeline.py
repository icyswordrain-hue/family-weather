"""tests/test_pipeline.py — Unit tests for backend/pipeline.py (TS3 / A2).

TDD: these tests were written before the implementation.
All external calls (build_prompt, generate_gemini, generate_claude, build_narration) are mocked.
"""
from unittest.mock import patch
from backend.pipeline import (
    check_regen_cycle,
    generate_narration_with_fallback,
)

import pytest
from backend.pipeline import _narration_cache

@pytest.fixture(autouse=True)
def clear_cache():
    _narration_cache.clear()

# ── check_regen_cycle ─────────────────────────────────────────────────────────

def test_regen_triggers_on_empty_history():
    """No history → first run → should trigger regen."""
    assert check_regen_cycle([], "2026-02-22", 14) is True

def test_regen_skips_if_recent():
    """Last regen 2 days ago → within cycle → skip."""
    history = [{"generated_at": "2026-02-20T00:00:00+08:00",
                "metadata": {"regen": True}}]
    assert check_regen_cycle(history, "2026-02-22", 14) is False

def test_regen_triggers_after_cycle():
    """Last regen 21 days ago → past 14-day cycle → trigger."""
    history = [{"generated_at": "2026-02-01T00:00:00+08:00",
                "metadata": {"regen": True}}]
    assert check_regen_cycle(history, "2026-02-22", 14) is True

def test_regen_triggers_exactly_at_boundary():
    """Exactly 14 days since last regen → trigger."""
    history = [{"generated_at": "2026-02-08T00:00:00+08:00",
                "metadata": {"regen": True}}]
    assert check_regen_cycle(history, "2026-02-22", 14) is True

def test_regen_skips_one_day_before_boundary():
    """13 days since last regen → still within cycle → skip."""
    history = [{"generated_at": "2026-02-09T00:00:00+08:00",
                "metadata": {"regen": True}}]
    assert check_regen_cycle(history, "2026-02-22", 14) is False

def test_regen_uses_most_recent_regen_entry():
    """Only the most recent regen entry in history should matter."""
    history = [
        {"generated_at": "2026-01-01T00:00:00+08:00", "metadata": {"regen": True}},
        {"generated_at": "2026-02-20T00:00:00+08:00", "metadata": {"regen": True}},
    ]
    assert check_regen_cycle(history, "2026-02-22", 14) is False

# ── generate_narration_with_fallback ──────────────────────────────────────────

@patch("backend.pipeline.build_prompt")
@patch("backend.pipeline.generate_gemini")
def test_narration_gemini_success(mock_gemini, mock_prompt):
    mock_prompt.return_value = []
    mock_gemini.return_value = "Today is nice."
    text, source = generate_narration_with_fallback("GEMINI", {}, [], "2026-02-22")
    assert text == "Today is nice."
    assert source == "gemini"

@patch("backend.pipeline.build_prompt")
@patch("backend.pipeline.generate_claude")
def test_narration_claude_success(mock_claude, mock_prompt):
    mock_prompt.return_value = []
    mock_claude.return_value = "Cloudy with rain."
    text, source = generate_narration_with_fallback("CLAUDE", {}, [], "2026-02-22")
    assert text == "Cloudy with rain."
    assert source == "claude"

@patch("backend.pipeline.build_prompt", side_effect=Exception("API error"))
@patch("backend.pipeline.build_narration")
def test_narration_falls_back_on_llm_error(mock_template, mock_prompt):
    mock_template.return_value = "Template narration."
    text, source = generate_narration_with_fallback("GEMINI", {}, [], "2026-02-22")
    assert source == "template"
    assert text == "Template narration."

@patch("backend.pipeline.build_prompt", return_value=[])
@patch("backend.pipeline.generate_gemini", side_effect=Exception("network timeout"))
@patch("backend.pipeline.build_narration")
def test_narration_fallback_text_not_empty(mock_template, mock_gemini, mock_prompt):
    mock_template.return_value = "Fallback text here."
    text, source = generate_narration_with_fallback("GEMINI", {}, [], "2026-02-22")
    assert len(text) > 0
    assert source == "template"

# ── build_system_prompt i18n ──────────────────────────────────────────────────

from narration.llm_prompt_builder import build_system_prompt

def test_build_system_prompt_en_returns_english_prompt():
    prompt = build_system_prompt(lang='en')
    assert 'English' in prompt or 'english' in prompt.lower()

def test_build_system_prompt_zh_returns_chinese_prompt():
    prompt = build_system_prompt(lang='zh-TW')
    assert '繁體中文' in prompt or 'Traditional Chinese' in prompt

def test_build_system_prompt_unknown_lang_falls_back_to_en():
    prompt = build_system_prompt(lang='fr')
    # Unknown lang → safe fallback to English
    assert '---METADATA---' in prompt

def test_zh_system_prompt_requires_chinese_output():
    """ZH prompt must instruct Chinese output and not say 'English only'."""
    prompt = build_system_prompt(lang='zh-TW')
    assert "繁體中文" in prompt
    assert "English only" not in prompt

def test_zh_metadata_block_stays_english():
    """ZH prompt must still instruct METADATA JSON keys in English."""
    prompt = build_system_prompt(lang='zh-TW')
    assert "---METADATA---" in prompt
    assert '"wardrobe"' in prompt
    assert '"accuracy_grade"' in prompt

def test_en_prompt_unchanged():
    """EN prompt must still contain 'English only' rule."""
    prompt = build_system_prompt(lang='en')
    assert "English only" in prompt
