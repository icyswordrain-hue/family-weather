from data.location_loader import OUTDOOR_LOCATIONS

def test_loads_all_moods():
    assert set(OUTDOOR_LOCATIONS.keys()) == {"Nice", "Warm", "Cloudy & Breezy", "Stay In"}

def test_each_mood_has_locations():
    for mood, locs in OUTDOOR_LOCATIONS.items():
        assert len(locs) > 0, f"Mood '{mood}' has no locations"

def test_location_has_required_fields():
    for mood, locs in OUTDOOR_LOCATIONS.items():
        for loc in locs:
            assert "name" in loc
            assert "activity" in loc
            assert "surface" in loc
