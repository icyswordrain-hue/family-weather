"""tests/test_narration_skip.py — Tests for v2 schema migration and get_lang_data.

Note: _conditions_changed was removed from app.py as part of the pipeline
simplification (5 layers → 2). Condition awareness is now handled by the
narration cache key (temp_bucket + rain_flag in backend/cache.py).
"""
import pytest
from history.conversation import _normalize_broadcast, get_lang_data


class TestV2SchemaMigration:
    """Verify _normalize_broadcast converts v1 entries to v2."""

    def _v1_entry(self):
        return {
            "generated_at": "2026-03-15T06:15:00+08:00",
            "raw_data": {"current": {}},
            "processed_data": {"current": {"AT": 25}},
            "narration_text": "Good morning.",
            "paragraphs": {"p1_current": "Good morning."},
            "metadata": {"narration_source": "claude"},
            "audio_urls": {"full_audio_url": "/audio/test.mp3"},
            "summaries": {"comfort": "Fine"},
        }

    def test_v1_migrates_to_v2(self):
        v1 = self._v1_entry()
        v2 = _normalize_broadcast(v1)
        assert v2["schema_version"] == 2
        assert "langs" in v2
        assert "zh-TW" in v2["langs"]
        ld = v2["langs"]["zh-TW"]
        assert ld["narration_text"] == "Good morning."
        assert ld["paragraphs"]["p1_current"] == "Good morning."
        assert ld["metadata"]["narration_source"] == "claude"
        assert ld["audio_urls"]["full_audio_url"] == "/audio/test.mp3"

    def test_v1_preserves_processed_data(self):
        v2 = _normalize_broadcast(self._v1_entry())
        assert v2["processed_data"]["current"]["AT"] == 25
        assert v2["raw_data"] == {"current": {}}

    def test_v2_passes_through(self):
        v2_input = {
            "schema_version": 2,
            "generated_at": "2026-03-15T06:15:00+08:00",
            "langs": {"en": {"narration_text": "Hi"}},
        }
        result = _normalize_broadcast(v2_input)
        assert result is v2_input  # same object, no copy

    def test_none_returns_none(self):
        assert _normalize_broadcast(None) is None

    def test_empty_returns_empty(self):
        assert _normalize_broadcast({}) == {}


class TestGetLangData:
    """Verify get_lang_data extracts the right language sub-dict."""

    def test_exact_match(self):
        bc = {"langs": {"en": {"narration_text": "Hi"}, "zh-TW": {"narration_text": "你好"}}}
        assert get_lang_data(bc, "en")["narration_text"] == "Hi"
        assert get_lang_data(bc, "zh-TW")["narration_text"] == "你好"

    def test_fallback_to_any(self):
        bc = {"langs": {"zh-TW": {"narration_text": "你好"}}}
        ld = get_lang_data(bc, "en")
        assert ld["narration_text"] == "你好"

    def test_empty_broadcast(self):
        assert get_lang_data({}, "en") == {}
        assert get_lang_data(None, "en") == {}
