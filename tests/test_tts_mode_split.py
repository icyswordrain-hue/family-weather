"""test_tts_mode_split.py — TDD for Task 1: TTS mode split in _pipeline_steps."""
import importlib
from unittest.mock import patch, MagicMock


def _collect_result(gen):
    for step in gen:
        if step.get("type") == "result":
            return step["payload"]
    return None


# ── LOCAL mode: TTS should be synthesised eagerly ─────────────────────────────

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
def test_local_tts_is_eager(
    mock_regen, mock_hist, mock_cur, mock_fc, mock_7d, mock_aqi,
    mock_proc, mock_narr, mock_parse, mock_save, mock_slices, mock_tts
):
    import app
    result = _collect_result(app._pipeline_steps("2026-03-01", lang="en"))
    assert result is not None
    assert result["audio_urls"]["full_audio_url"] == "/local_assets/audio/test.mp3"
    mock_tts.assert_called_once()


# ── CLOUD mode: TTS should remain None ────────────────────────────────────────

@patch("app.RUN_MODE", "CLOUD")
@patch("app.synthesise_with_cache")
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
def test_cloud_tts_is_deferred(
    mock_regen, mock_hist, mock_cur, mock_fc, mock_7d, mock_aqi,
    mock_proc, mock_narr, mock_parse, mock_save, mock_slices, mock_tts
):
    import app
    result = _collect_result(app._pipeline_steps("2026-03-01", lang="en"))
    assert result is not None
    assert result["audio_urls"]["full_audio_url"] is None
    mock_tts.assert_not_called()


# Task 2 — transcript invariant (unit-level; JS tested manually)
# Documented here as a spec contract, not an automated test.
# The render() guard removal is verified in Manual Verification below.
