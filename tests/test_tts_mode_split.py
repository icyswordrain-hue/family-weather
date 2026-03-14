"""test_tts_mode_split.py — TDD for TTS mode split in _pipeline_steps.

TTS now only runs on the morning slot. These tests verify:
1. Morning slot synthesizes TTS for both languages
2. Non-morning slots skip TTS (audio_urls empty)
"""
import importlib
from unittest.mock import patch, MagicMock


def _collect_result(gen):
    for step in gen:
        if step.get("type") == "result":
            return step["payload"]
    return None


# ── Morning slot: TTS should be synthesised for both languages ───────────────

@patch("app.RUN_MODE", "LOCAL")
@patch("app.synthesise_with_cache", return_value="/local_assets/audio/test.mp3")
@patch("app.build_slices", return_value={})
@patch("app.save_day")
@patch("app.parse_narration_response", return_value={
    "paragraphs": {"P1": "Hello."}, "metadata": {}, "regen": None, "cards": {}
})
@patch("app.generate_narration_with_fallback", return_value=("Hello.", "gemini"))
@patch("app.process", return_value={"current": {}})
@patch("app.fetch_all_aqi", return_value={})
@patch("app.fetch_all_forecasts_7day", return_value={})
@patch("app.fetch_all_forecasts", return_value={})
@patch("app.fetch_current_conditions", return_value={})
@patch("app.load_history", return_value=[])
@patch("app.check_regen_cycle", return_value=False)
def test_morning_tts_is_eager(
    mock_regen, mock_hist, mock_cur, mock_fc, mock_7d, mock_aqi,
    mock_proc, mock_narr, mock_parse, mock_save, mock_slices, mock_tts
):
    import app
    result = _collect_result(app._pipeline_steps("2026-03-01", lang="en", slot="morning"))
    assert result is not None
    assert result["audio_urls"]["full_audio_url"] == "/local_assets/audio/test.mp3"
    # Called twice: once for zh-TW, once for en
    assert mock_tts.call_count == 2


# ── Non-morning slot: TTS should be skipped ──────────────────────────────────

@patch("app.RUN_MODE", "LOCAL")
@patch("app.synthesise_with_cache", return_value="/local_assets/audio/test.mp3")
@patch("app.build_slices", return_value={})
@patch("app.save_day")
@patch("app.parse_narration_response", return_value={
    "paragraphs": {"P1": "Hello."}, "metadata": {}, "regen": None, "cards": {}
})
@patch("app.generate_narration_with_fallback", return_value=("Hello.", "gemini"))
@patch("app.process", return_value={"current": {}})
@patch("app.fetch_all_aqi", return_value={})
@patch("app.fetch_all_forecasts_7day", return_value={})
@patch("app.fetch_all_forecasts", return_value={})
@patch("app.fetch_current_conditions", return_value={})
@patch("app.load_history", return_value=[])
@patch("app.check_regen_cycle", return_value=False)
def test_midday_tts_is_skipped(
    mock_regen, mock_hist, mock_cur, mock_fc, mock_7d, mock_aqi,
    mock_proc, mock_narr, mock_parse, mock_save, mock_slices, mock_tts
):
    import app
    result = _collect_result(app._pipeline_steps("2026-03-01", lang="en", slot="midday"))
    assert result is not None
    # TTS not called for non-morning slots
    mock_tts.assert_not_called()
    # audio_urls should be empty
    assert result["audio_urls"] == {}
