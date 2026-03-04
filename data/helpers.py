"""
helpers.py — Shared data processing helpers.
"""

__all__ = ["safe_float", "safe_int"]


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
