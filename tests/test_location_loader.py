from data.location_loader import OUTDOOR_LOCATIONS

VALID_MOODS = {"Nice", "Warm", "Cloudy & Breezy", "Stay In"}


def test_loads_as_list():
    assert isinstance(OUTDOOR_LOCATIONS, list)
    assert len(OUTDOOR_LOCATIONS) > 0


def test_has_100_locations():
    assert len(OUTDOOR_LOCATIONS) == 100


def test_location_has_required_fields():
    for loc in OUTDOOR_LOCATIONS:
        assert "name" in loc
        assert "activity" in loc
        assert "surface" in loc
        assert "moods" in loc


def test_all_moods_are_valid():
    for loc in OUTDOOR_LOCATIONS:
        for mood in loc["moods"]:
            assert mood in VALID_MOODS, f"Unknown mood '{mood}' in location '{loc['name']}'"


def test_each_mood_has_locations():
    for mood in VALID_MOODS:
        matching = [loc for loc in OUTDOOR_LOCATIONS if mood in loc.get("moods", [])]
        assert len(matching) > 0, f"Mood '{mood}' has no locations"
