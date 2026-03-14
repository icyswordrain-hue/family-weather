"""location_loader.py — Loads OUTDOOR_LOCATIONS flat list from the canonical JSON data file."""
import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "locations.json")


def load_outdoor_locations() -> list[dict]:
    with open(_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


OUTDOOR_LOCATIONS: list[dict] = load_outdoor_locations()
