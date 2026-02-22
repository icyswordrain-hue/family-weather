"""location_loader.py — Loads OUTDOOR_LOCATIONS from the canonical JSON data file."""
import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "locations.json")

def load_outdoor_locations() -> dict[str, list[dict]]:
    with open(_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

OUTDOOR_LOCATIONS = load_outdoor_locations()
