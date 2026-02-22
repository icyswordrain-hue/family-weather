"""
tests/test_helpers.py — Unit tests for data.helpers module.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from data.helpers import safe_float, safe_int, _safe_float, _safe_int


class TestSafeFloat:
    def test_integer_string(self):
        assert safe_float("20") == 20.0

    def test_float_string(self):
        assert safe_float("3.14") == pytest.approx(3.14)

    def test_negative_string(self):
        assert safe_float("-99") == -99.0

    def test_numeric_int(self):
        assert safe_float(5) == 5.0

    def test_none_returns_none(self):
        assert safe_float(None) is None

    def test_empty_string_returns_none(self):
        assert safe_float("") is None

    def test_non_numeric_string_returns_none(self):
        assert safe_float("abc") is None

    def test_range_string_returns_none(self):
        # "51-100" is not a valid float
        assert safe_float("51-100") is None

    def test_inf_string(self):
        assert safe_float("inf") == float("inf")


class TestSafeInt:
    def test_integer_string(self):
        assert safe_int("7") == 7

    def test_float_string_truncates(self):
        assert safe_int("3.9") == 3

    def test_negative_string(self):
        assert safe_int("-99") == -99

    def test_numeric_float(self):
        assert safe_int(1.7) == 1

    def test_none_returns_none(self):
        assert safe_int(None) is None

    def test_empty_string_returns_none(self):
        assert safe_int("") is None

    def test_non_numeric_string_returns_none(self):
        assert safe_int("abc") is None


class TestBackwardCompatAliases:
    """Ensure legacy _safe_float/_safe_int aliases still work."""

    def test_safe_float_alias(self):
        assert _safe_float("1.5") == 1.5
        assert _safe_float(None) is None

    def test_safe_int_alias(self):
        assert _safe_int("3") == 3
        assert _safe_int(None) is None
