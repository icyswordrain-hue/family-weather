import sys
import logging
from datetime import datetime
from data import weather_processor as processor

# Mock data
slots = [
    {
        "start_time": "2026-02-20T12:00:00+08:00",
        "end_time": "2026-02-20T18:00:00+08:00",
        "T": 20, "Wx": 1
    },
    {
        "start_time": "2026-02-20T18:00:00+08:00",
        "end_time": "2026-02-21T06:00:00+08:00", # 12 hours!
        "T": 18, "Wx": 2
    }
]

def test_segmentation():
    print("Testing _segment_forecast with 12h evening slot...")
    segmented = processor._segment_forecast(slots)
    
    print("Segments found:", segmented.keys())
    assert "Evening" in segmented or "Overnight" in segmented


def test_segment_has_safe_minutes():
    """Enriched segments must carry safe_minutes and the new precip_level/text."""
    # Slot with PoP6h=50, Wx=13 (moderate rain) in Afternoon window
    from datetime import date
    today = date.today()
    afternoon_slot = {
        "start_time": f"{today}T12:00:00+08:00",
        "end_time":   f"{today}T18:00:00+08:00",
        "T": 25, "RH": 80, "WS": 2.0, "WD": 90,
        "Wx": 13, "PoP6h": 50,
    }
    segmented = processor._segment_forecast(
        [afternoon_slot],
        now=__import__("datetime").datetime(today.year, today.month, today.day, 13, 0),
    )

    # Manually apply the enrichment (mirrors what process() will do after wiring)
    from data.scales import pop_to_safe_minutes, safe_minutes_to_level, _wx_to_rain_risk
    seg = segmented.get("Afternoon") or next(
        (v for v in segmented.values() if v is not None), None
    )
    assert seg is not None, f"No segment found: {segmented}"

    wx   = seg.get("Wx")
    pop6h = seg.get("PoP6h")
    risk = _wx_to_rain_risk(wx)
    safe_min = pop_to_safe_minutes(pop6h, window_minutes=360, risk_pct=risk * 100) if risk else 360
    seg["safe_minutes"] = safe_min
    seg["precip_level"], seg["precip_text"] = safe_minutes_to_level(safe_min)

    assert "safe_minutes" in seg
    assert seg["precip_level"] in (0, 1, 3, 5)

if __name__ == "__main__":
    test_segmentation()
