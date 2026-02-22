"""
helpers.py — Shared data processing helpers.
"""

__all__ = ["safe_float", "safe_int"]


def safe_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


# Backward-compat aliases for callers still using the private names
_safe_float = safe_float
_safe_int = safe_int
