"""tests/test_narration_skip.py — Tests for condition-change narration skip logic."""
import pytest
from app import _conditions_changed


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
