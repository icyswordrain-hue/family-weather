from datetime import datetime
from data.weather_processor import _segment_forecast

SLOTS = [
    {"start_time": "2026-02-22T06:00:00+08:00", "end_time": "2026-02-22T12:00:00+08:00",
     "AT": 18.0, "RH": 65.0, "WS": 2.0, "WD": 90.0, "PoP6h": 10.0, "Wx": 1},
    {"start_time": "2026-02-22T12:00:00+08:00", "end_time": "2026-02-22T18:00:00+08:00",
     "AT": 24.0, "RH": 55.0, "WS": 3.0, "WD": 180.0, "PoP6h": 20.0, "Wx": 2},
]

def test_segmentation_morning_anchor():
    # 9 AM local time on Sunday, Feb 22
    now = datetime(2026, 2, 22, 9, 0, 0)
    result = _segment_forecast(SLOTS, now=now)
    assert "Morning" in result
    assert result["Morning"] is not None
    assert result["Morning"]["start_time"] == "2026-02-22T06:00:00+08:00"

def test_segmentation_afternoon_anchor():
    # 2 PM local time
    now = datetime(2026, 2, 22, 14, 0, 0)
    result = _segment_forecast(SLOTS, now=now)
    assert "Afternoon" in result
    assert result["Afternoon"] is not None
    assert result["Afternoon"]["start_time"] == "2026-02-22T12:00:00+08:00"

def test_segmentation_evening_anchor():
    # 7 PM local time
    now = datetime(2026, 2, 22, 19, 0, 0)
    result = _segment_forecast(SLOTS, now=now)
    assert "Evening" in result
    # In this case, 7 PM is in the "Evening" segment (18-24)
    # The slot 12-18 does NOT cover it, so it should find a later slot or be None
    # With only 2 slots (0-12, 12-18), it should be None
    assert result["Evening"] is None
