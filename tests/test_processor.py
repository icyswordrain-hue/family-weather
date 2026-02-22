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

if __name__ == "__main__":
    test_segmentation()
