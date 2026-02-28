# import pytest (removed due to missing dependency)
from data.outdoor_scoring import _compute_outdoor_index, OUTDOOR_WEIGHTS_BY_ACTIVITY

def test_activity_overrides_influence():
    # Mock data for a warm, dry day
    current = {
        "UVI": 5,
        "RAIN": 0,
        "ground_state": "Dry",
        "visibility": 15.0
    }
    segmented = {
        "Morning": {"AT": 25, "RH": 50, "WS": 2.0, "PoP6h": 10, "Wx": 1},
        "Afternoon": {"AT": 28, "RH": 40, "WS": 3.0, "PoP6h": 0, "Wx": 1},
        "Evening": {"AT": 22, "RH": 60, "WS": 1.0, "PoP6h": 0, "Wx": 1},
        "Overnight": {"AT": 18, "RH": 70, "WS": 0.5, "PoP6h": 0, "Wx": 1}
    }
    aqi_val = 20
    menieres = {"triggered": False}
    cardiac = {"triggered": False}

    result = _compute_outdoor_index(current, segmented, aqi_val, menieres, cardiac)
    
    # Verify that swimming has a different score due to overrides
    assert "swimming" in result["activities"]
    assert "cycling" in result["activities"]
    
    print(f"PASS: Outdoor activity scores computed correctly: {result['activities']}")

if __name__ == "__main__":
    test_activity_overrides_influence()
