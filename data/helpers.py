"""
helpers.py — Shared data processing helpers.
"""

import math

__all__ = ["safe_float", "safe_int", "_dew_point", "_apparent_temp", "_saturation_label"]


# CWA API returns -99 / -999 for instruments that are not installed or not
# reporting.  Treat both as "missing" (None) rather than letting -99.0 slip
# through into threshold checks (e.g. UV ≥ 8 = Very High would never fire).
_CWA_MISSING = {-99.0, -999.0}


def safe_float(value) -> float | None:
    try:
        v = float(value)
        return None if v in _CWA_MISSING else v
    except (TypeError, ValueError):
        return None


def safe_int(value) -> int | None:
    try:
        v = float(value)
        if v in _CWA_MISSING:
            return None
        return int(v)
    except (TypeError, ValueError):
        return None


# Backward-compat aliases for callers still using the private names
_safe_float = safe_float
_safe_int = safe_int


def _dew_point(temp_c: float, rh: float) -> float:
    """Magnus formula dew point. Accurate to ±0.35°C."""
    a, b = 17.27, 237.7
    gamma = (a * temp_c / (b + temp_c)) + math.log(rh / 100)
    return round((b * gamma) / (a - gamma), 1)


def _apparent_temp(temp_c: float, rh: float, wind_ms: float) -> float:
    """Australian BOM apparent temperature formula."""
    e = (rh / 100) * 6.105 * math.exp((17.27 * temp_c) / (237.7 + temp_c))
    return round(temp_c + (0.33 * e) - (0.70 * wind_ms) - 4.00, 1)


def _saturation_label(dew_gap: float) -> str:
    if dew_gap < 2:  return "near_saturated"
    if dew_gap < 5:  return "clammy"
    if dew_gap < 10: return "humid"
    if dew_gap < 15: return "comfortable"
    return "dry"
