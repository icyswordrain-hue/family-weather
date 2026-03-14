"""tests/test_narration_skip.py — Tests for condition-change narration skip + v2 schema migration."""
import pytest
from app import _conditions_changed
from history.conversation import _normalize_broadcast, get_lang_data


class TestConditionsChanged:
    """Verify _conditions_changed detects meaningful weather shifts."""

    def _base_current(self):
        return {"AT": 25.0, "RH": 70.0, "RAIN": 0.0}

    def test_identical_conditions_not_changed(self):
        c = self._base_current()
        m = {"AT": 25.0, "RH": 70.0, "RAIN": 0.0, "dew_point": 19.3}
        changed, reasons = _conditions_changed(c, m)
        assert not changed
        assert reasons == []

    def test_small_temp_shift_not_changed(self):
        """2°C shift is below the 3°C threshold."""
        c = self._base_current()
        c["AT"] = 27.0
        m = {"AT": 25.0, "RH": 70.0, "RAIN": 0.0, "dew_point": 19.3}
        changed, reasons = _conditions_changed(c, m)
        assert not changed

    def test_large_temp_shift_changed(self):
        """4°C shift exceeds the 3°C threshold."""
        c = self._base_current()
        c["AT"] = 29.0
        m = {"AT": 25.0, "RH": 70.0, "RAIN": 0.0, "dew_point": 19.3}
        changed, reasons = _conditions_changed(c, m)
        assert changed
        assert any("temp" in r for r in reasons)

    def test_rain_onset_changed(self):
        c = self._base_current()
        c["RAIN"] = 2.5
        m = {"AT": 25.0, "RH": 70.0, "RAIN": 0.0, "dew_point": 19.3}
        changed, reasons = _conditions_changed(c, m)
        assert changed
        assert any("rain" in r for r in reasons)

    def test_rain_stopping_changed(self):
        c = self._base_current()
        c["RAIN"] = 0.0
        m = {"AT": 25.0, "RH": 70.0, "RAIN": 3.0, "dew_point": 19.3}
        changed, reasons = _conditions_changed(c, m)
        assert changed

    def test_dew_point_shift_changed(self):
        """Large humidity shift causes dew point to cross 3°C threshold."""
        c = {"AT": 25.0, "RH": 95.0, "RAIN": 0.0}  # dew_point ~24.3
        m = {"AT": 25.0, "RH": 70.0, "RAIN": 0.0, "dew_point": 19.3}
        changed, reasons = _conditions_changed(c, m)
        assert changed
        assert any("dew" in r for r in reasons)

    def test_missing_fields_not_changed(self):
        """Missing AT/RH should not crash, and should not flag a change."""
        c = {}
        m = {}
        changed, reasons = _conditions_changed(c, m)
        assert not changed

    def test_multiple_reasons(self):
        """Temp + rain both changing returns multiple reasons."""
        c = {"AT": 30.0, "RH": 70.0, "RAIN": 5.0}
        m = {"AT": 25.0, "RH": 70.0, "RAIN": 0.0, "dew_point": 19.3}
        changed, reasons = _conditions_changed(c, m)
        assert changed
        assert len(reasons) >= 2


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
