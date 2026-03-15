from datetime import datetime
from data.weather_processor import _segment_forecast, _parse_dt, SEGMENT_ORDER

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

def test_segmentation_overnight_anchor():
    # 2 AM local time — falls in Overnight segment (0-6)
    now = datetime(2026, 2, 22, 2, 0, 0)
    result = _segment_forecast(SLOTS, now=now)
    assert "Overnight" in result
    # Our fixture only has slots 06-12 and 12-18; overnight (00-06) has no matching slot
    assert result["Overnight"] is None

def test_segmentation_evening_anchor():
    # 7 PM local time
    now = datetime(2026, 2, 22, 19, 0, 0)
    result = _segment_forecast(SLOTS, now=now)
    assert "Evening" in result
    # In this case, 7 PM is in the "Evening" segment (18-24)
    # The slot 12-18 does NOT cover it, so it should find a later slot or be None
    # With only 2 slots (0-12, 12-18), it should be None
    assert result["Evening"] is None


# ── Cross-day location assignment (Sunday evening → Monday weekday) ──────────

_SLOT_DEFAULTS = {"AT": 20.0, "T": 20.0, "RH": 65.0, "WS": 2.0, "WD": 90.0,
                  "PoP6h": 10.0, "Wx": 1}

def _slot(start, **overrides):
    """Point-in-time slot (F-D0047-069 style: start == end)."""
    d = {"start_time": start, "end_time": start, **_SLOT_DEFAULTS}
    d.update(overrides)
    return d

def _assign_locations(home_segs, work_segs):
    """Replicate the location-assignment logic from weather_processor.py L260-286."""
    _LOC_MAP_WEEKDAY = {"Morning": "Banqiao", "Afternoon": "Banqiao",
                         "Evening": "Shulin", "Overnight": "Shulin"}
    segmented = {}
    for seg_name in SEGMENT_ORDER:
        home_seg = home_segs[seg_name]
        work_seg = work_segs[seg_name]
        ref_seg = work_seg or home_seg
        seg_is_weekday = False
        if ref_seg and ref_seg.get("start_time"):
            seg_dt = _parse_dt(ref_seg["start_time"]).replace(tzinfo=None)
            seg_is_weekday = seg_dt.weekday() < 5
        if seg_is_weekday:
            if seg_name in ("Morning", "Afternoon"):
                segmented[seg_name] = work_seg or home_seg
            else:
                segmented[seg_name] = home_seg or work_seg
            if segmented[seg_name]:
                segmented[seg_name]["location"] = _LOC_MAP_WEEKDAY[seg_name]
        else:
            segmented[seg_name] = home_seg
            if segmented[seg_name]:
                segmented[seg_name]["location"] = "Shulin"
    return segmented


def test_sunday_evening_monday_segments_get_banqiao():
    """On Sunday evening, next-day Morning/Afternoon (Monday) should use Banqiao."""
    # Sunday 2026-03-15 20:00.  March 16 is Monday (weekday).
    now = datetime(2026, 3, 15, 20, 0, 0)

    home_slots = [
        _slot("2026-03-15T21:00:00+08:00"),   # Sunday evening
        _slot("2026-03-16T00:00:00+08:00"),   # Monday overnight
        _slot("2026-03-16T03:00:00+08:00"),
        _slot("2026-03-16T06:00:00+08:00"),   # Monday morning
        _slot("2026-03-16T09:00:00+08:00"),
        _slot("2026-03-16T12:00:00+08:00"),   # Monday afternoon
        _slot("2026-03-16T15:00:00+08:00"),
    ]
    work_slots = [
        _slot("2026-03-16T06:00:00+08:00", AT=22.0),  # Monday morning (Banqiao)
        _slot("2026-03-16T09:00:00+08:00", AT=24.0),
        _slot("2026-03-16T12:00:00+08:00", AT=26.0),  # Monday afternoon (Banqiao)
        _slot("2026-03-16T15:00:00+08:00", AT=27.0),
    ]

    home_segs = _segment_forecast(home_slots, now=now)
    work_segs = _segment_forecast(work_slots, now=now)
    segmented = _assign_locations(home_segs, work_segs)

    # Monday Morning/Afternoon → Banqiao (weekday work)
    assert segmented["Morning"] is not None
    assert segmented["Morning"]["location"] == "Banqiao"
    assert segmented["Afternoon"] is not None
    assert segmented["Afternoon"]["location"] == "Banqiao"
    # Sunday Evening → Shulin (weekend)
    assert segmented["Evening"] is not None
    assert segmented["Evening"]["location"] == "Shulin"
    # Monday Overnight → Shulin (home, even on weekday)
    assert segmented["Overnight"] is not None
    assert segmented["Overnight"]["location"] == "Shulin"


def test_friday_evening_saturday_segments_all_shulin():
    """On Friday evening, next-day Morning/Afternoon (Saturday) should all be Shulin."""
    # Friday 2026-03-20 21:00.  March 21 is Saturday.
    now = datetime(2026, 3, 20, 21, 0, 0)

    home_slots = [
        _slot("2026-03-20T21:00:00+08:00"),
        _slot("2026-03-21T00:00:00+08:00"),
        _slot("2026-03-21T03:00:00+08:00"),
        _slot("2026-03-21T06:00:00+08:00"),
        _slot("2026-03-21T09:00:00+08:00"),
        _slot("2026-03-21T12:00:00+08:00"),
        _slot("2026-03-21T15:00:00+08:00"),
    ]
    work_slots = [
        _slot("2026-03-21T06:00:00+08:00", AT=22.0),
        _slot("2026-03-21T09:00:00+08:00", AT=24.0),
        _slot("2026-03-21T12:00:00+08:00", AT=26.0),
        _slot("2026-03-21T15:00:00+08:00", AT=27.0),
    ]

    home_segs = _segment_forecast(home_slots, now=now)
    work_segs = _segment_forecast(work_slots, now=now)
    segmented = _assign_locations(home_segs, work_segs)

    # Saturday — everything should be Shulin
    assert segmented["Morning"]["location"] == "Shulin"
    assert segmented["Afternoon"]["location"] == "Shulin"
    assert segmented["Evening"]["location"] == "Shulin"
    assert segmented["Overnight"]["location"] == "Shulin"
