"""tests/test_health_alerts.py — Unit tests for data/health_alerts.py"""
from data.health_alerts import _cardiac_alert, _detect_menieres_alert, _compute_heads_ups

# ── Fixtures ──────────────────────────────────────────────────────────────────

COLD_WET_MORNING = {
    "Morning": {"AT": 8.0, "RH": 85.0, "WS": 5.0, "PoP6h": 65.0, "Wx": 10},
    "Afternoon": {"AT": 13.0, "RH": 75.0, "WS": 3.0, "PoP6h": 40.0, "Wx": 6},
}

MILD_MORNING = {
    "Morning": {"AT": 22.0, "RH": 65.0, "WS": 2.0, "PoP6h": 10.0, "Wx": 2},
    "Afternoon": {"AT": 27.0, "RH": 60.0, "WS": 2.0, "PoP6h": 5.0, "Wx": 1},
}

EXTREME_COLD_MORNING = {
    "Morning": {"AT": 5.0, "RH": 70.0, "WS": 2.0, "PoP6h": 10.0, "Wx": 1},
}

# ── Cardiac Alert ─────────────────────────────────────────────────────────────

def test_cardiac_triggers_cold_wet():
    alert = _cardiac_alert(COLD_WET_MORNING)
    assert alert["triggered"] is True
    assert len(alert["reasons"]) > 0

def test_cardiac_no_trigger_mild():
    alert = _cardiac_alert(MILD_MORNING)
    assert alert["triggered"] is False

def test_cardiac_triggers_extreme_cold():
    alert = _cardiac_alert(EXTREME_COLD_MORNING)
    assert alert["triggered"] is True

def test_cardiac_type():
    alert = _cardiac_alert(MILD_MORNING)
    assert alert["type"] == "Cardiac"

def test_cardiac_no_morning_segment():
    alert = _cardiac_alert({})
    assert alert["triggered"] is False

# ── Menieres Alert ────────────────────────────────────────────────────────────

def test_menieres_returns_dict():
    alert = _detect_menieres_alert({"PRES": 1005}, [])
    assert "triggered" in alert
    assert "type" in alert

def test_menieres_low_pressure_sets_moderate_severity():
    # Low pressure alone is moderate risk — does NOT trigger alert
    alert = _detect_menieres_alert({"PRES": 1000}, [])
    assert alert["triggered"] is False
    assert alert["severity"] == "moderate"

def test_menieres_no_trigger_normal():
    alert = _detect_menieres_alert({"PRES": 1015, "RH": 70}, [])
    assert alert["triggered"] is False

def test_menieres_high_humidity_sets_moderate_severity():
    # High humidity alone is moderate risk — does NOT trigger alert
    alert = _detect_menieres_alert({"PRES": 1015, "RH": 90}, [])
    assert alert["triggered"] is False
    assert alert["severity"] == "moderate"

def test_menieres_triggers_rapid_drop():
    # pressure_change_24h needs >= 2 records with top-level PRES key; delta = -10 hPa
    history = [{"PRES": 1015}, {"PRES": 1005}]
    alert = _detect_menieres_alert({"PRES": 1005}, history)
    assert alert["triggered"] is True
    assert alert["severity"] == "high"

# ── Heads Ups ─────────────────────────────────────────────────────────────────

def test_compute_heads_ups_returns_list():
    result = _compute_heads_ups(
        MILD_MORNING, {}, {}, {"realtime": {"aqi": 40}},
        {"triggered": False}, {"triggered": False}
    )
    assert isinstance(result, list)

def test_compute_heads_ups_cardiac_critical():
    result = _compute_heads_ups(
        COLD_WET_MORNING, {}, {}, {"realtime": {"aqi": 40}},
        {"triggered": True, "reasons": ["Cold & Wet"]}, {"triggered": False}
    )
    assert any(a.get("level") == "CRITICAL" for a in result)
