"""tests/test_catalog_manager.py — Unit tests for data/catalog_manager.py"""

import json
import os
import pytest
from unittest.mock import patch

# Patch config before importing catalog_manager
os.environ.setdefault("RUN_MODE", "LOCAL")


@pytest.fixture(autouse=True)
def _temp_data_dir(tmp_path, monkeypatch):
    """Redirect all catalog_manager file I/O to a temp directory."""
    monkeypatch.setattr("data.catalog_manager.LOCAL_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("data.catalog_manager.RUN_MODE", "LOCAL")

    # Create minimal meals.json and locations.json in the data dir
    meals = [
        {"name": "meal_A", "moods": ["Hot & Humid"], "description": "", "tags": []},
        {"name": "meal_B", "moods": ["Hot & Humid"], "description": "", "tags": []},
        {"name": "meal_C", "moods": ["Hot & Humid"], "description": "", "tags": []},
        {"name": "meal_D", "moods": ["Warm & Pleasant"], "description": "", "tags": []},
        {"name": "meal_E", "moods": ["Warm & Pleasant"], "description": "", "tags": []},
    ]
    locations = [
        {"name": "loc_A", "moods": ["Nice"], "activity": "walk", "surface": "paved", "lat": 25.0, "lng": 121.4, "notes": ""},
        {"name": "loc_B", "moods": ["Nice"], "activity": "hike", "surface": "dirt", "lat": 25.0, "lng": 121.4, "notes": ""},
        {"name": "loc_C", "moods": ["Nice"], "activity": "cycle", "surface": "paved", "lat": 25.0, "lng": 121.4, "notes": ""},
        {"name": "loc_D", "moods": ["Warm"], "activity": "swim", "surface": "paved", "lat": 25.0, "lng": 121.4, "notes": ""},
    ]

    data_dir = os.path.dirname(os.path.dirname(__file__))
    meals_path = os.path.join(data_dir, "data", "meals.json")
    locs_path = os.path.join(data_dir, "data", "locations.json")

    # Save originals and restore after test
    meals_backup = open(meals_path, "r", encoding="utf-8").read()
    locs_backup = open(locs_path, "r", encoding="utf-8").read()

    with open(meals_path, "w", encoding="utf-8") as f:
        json.dump(meals, f)
    with open(locs_path, "w", encoding="utf-8") as f:
        json.dump(locations, f)

    yield

    with open(meals_path, "w", encoding="utf-8") as f:
        f.write(meals_backup)
    with open(locs_path, "w", encoding="utf-8") as f:
        f.write(locs_backup)


from data.catalog_manager import (
    record_suggestion,
    load_catalog_stats,
    save_catalog_stats,
    identify_stale_items,
    load_bench,
    rotate_catalog,
    get_bench_summary,
    get_returning_items,
)


# ── record_suggestion ────────────────────────────────────────────────────────

class TestRecordSuggestion:
    def test_increments_meal_count(self):
        record_suggestion("meal_A", None)
        stats = load_catalog_stats()
        assert stats["meals"]["meal_A"]["suggest_count"] == 1

        record_suggestion("meal_A", None)
        stats = load_catalog_stats()
        assert stats["meals"]["meal_A"]["suggest_count"] == 2

    def test_increments_location_count(self):
        record_suggestion(None, "loc_A")
        stats = load_catalog_stats()
        assert stats["locations"]["loc_A"]["suggest_count"] == 1

    def test_both_meal_and_location(self):
        record_suggestion("meal_B", "loc_B")
        stats = load_catalog_stats()
        assert stats["meals"]["meal_B"]["suggest_count"] == 1
        assert stats["locations"]["loc_B"]["suggest_count"] == 1

    def test_increments_activity_count(self):
        record_suggestion(None, None, "hiking")
        stats = load_catalog_stats()
        assert stats["activities"]["hiking"]["suggest_count"] == 1

        record_suggestion(None, None, "hiking")
        stats = load_catalog_stats()
        assert stats["activities"]["hiking"]["suggest_count"] == 2

    def test_all_three(self):
        record_suggestion("meal_A", "loc_A", "cycling")
        stats = load_catalog_stats()
        assert stats["meals"]["meal_A"]["suggest_count"] == 1
        assert stats["locations"]["loc_A"]["suggest_count"] == 1
        assert stats["activities"]["cycling"]["suggest_count"] == 1

    def test_noop_with_none(self):
        record_suggestion(None, None)
        stats = load_catalog_stats()
        assert stats["meals"] == {}
        assert stats["locations"] == {}


# ── identify_stale_items ─────────────────────────────────────────────────────

class TestIdentifyStaleItems:
    def test_returns_most_suggested(self):
        catalog = [
            {"name": "meal_A", "moods": ["Hot & Humid"]},
            {"name": "meal_B", "moods": ["Hot & Humid"]},
            {"name": "meal_C", "moods": ["Hot & Humid"]},
        ]
        stats_section = {
            "meal_A": {"suggest_count": 10},
            "meal_B": {"suggest_count": 5},
            "meal_C": {"suggest_count": 1},
        }
        stale = identify_stale_items(catalog, stats_section, "Hot & Humid", rotation_pct=0.35)
        # 35% of 3 = floor(1.05) = 1
        assert len(stale) == 1
        assert stale[0]["name"] == "meal_A"

    def test_skips_never_suggested(self):
        catalog = [
            {"name": "meal_A", "moods": ["Hot & Humid"]},
            {"name": "meal_B", "moods": ["Hot & Humid"]},
        ]
        stats_section = {
            "meal_A": {"suggest_count": 0},
            "meal_B": {"suggest_count": 0},
        }
        stale = identify_stale_items(catalog, stats_section, "Hot & Humid", rotation_pct=0.5)
        assert stale == []

    def test_empty_mood(self):
        stale = identify_stale_items([], {}, "Cold", rotation_pct=0.35)
        assert stale == []


# ── rotate_catalog ───────────────────────────────────────────────────────────

class TestRotateCatalog:
    @patch("data.location_loader.load_outdoor_locations")
    def test_basic_rotation(self, _mock):
        # Seed suggestion stats so some items are stale
        stats = load_catalog_stats()
        stats["meals"] = {
            "meal_A": {"suggest_count": 15, "added_cycle": 0, "last_suggested": "2026-03-01"},
            "meal_B": {"suggest_count": 2, "added_cycle": 0, "last_suggested": "2026-03-10"},
            "meal_C": {"suggest_count": 1, "added_cycle": 0, "last_suggested": "2026-03-12"},
        }
        stats["locations"] = {
            "loc_A": {"suggest_count": 12, "added_cycle": 0, "last_suggested": "2026-03-01"},
            "loc_B": {"suggest_count": 3, "added_cycle": 0, "last_suggested": "2026-03-10"},
            "loc_C": {"suggest_count": 1, "added_cycle": 0, "last_suggested": "2026-03-12"},
        }
        save_catalog_stats(stats)

        regen_data = {
            "meals": {
                "hot_humid": ["new_dish_X"],
            },
            "locations": {
                "Nice": [{"name": "New Park Y", "activity": "walk", "surface": "paved", "lat": 25.0, "lng": 121.4, "notes": "test"}],
            },
        }

        summary = rotate_catalog(regen_data)

        assert summary["meals_retired"] >= 1
        assert summary["meals_added"] == 1
        assert summary["locations_retired"] >= 1
        assert summary["locations_added"] == 1

        # Verify bench has the retired items
        bench = load_bench()
        benched_meal_names = [e["item"]["name"] for e in bench["meals"]]
        assert "meal_A" in benched_meal_names  # highest suggest_count

        benched_loc_names = [e["item"]["name"] for e in bench["locations"]]
        assert "loc_A" in benched_loc_names

        # Verify stats reset for new items
        stats = load_catalog_stats()
        assert stats["meals"]["new_dish_X"]["suggest_count"] == 0
        assert stats["locations"]["New Park Y"]["suggest_count"] == 0
        assert stats["current_cycle"] == 1

    @patch("data.location_loader.load_outdoor_locations")
    def test_bench_cooloff_return(self, _mock):
        # Pre-populate bench with an item benched 3 cycles ago
        bench = load_bench()
        bench["meals"].append({
            "item": {"name": "old_favorite", "moods": ["Cold"], "description": "", "tags": []},
            "benched_at_cycle": 0,
            "cooloff_cycles": 2,
            "lifetime_suggests": 20,
        })
        from data.catalog_manager import save_bench
        save_bench(bench)

        # Set current cycle to 2 (cooloff expired)
        stats = load_catalog_stats()
        stats["current_cycle"] = 2
        save_catalog_stats(stats)

        regen_data = {"meals": {}, "locations": {}}
        summary = rotate_catalog(regen_data)

        assert summary["meals_returned"] == 1

        # Item should be back in the catalog
        import data.catalog_manager as cm
        catalog = cm._load_json(cm._MEALS_PATH, [])
        names = [m["name"] for m in catalog]
        assert "old_favorite" in names

        # Item should be removed from bench
        bench = load_bench()
        benched_names = [e["item"]["name"] for e in bench["meals"]]
        assert "old_favorite" not in benched_names


# ── get_bench_summary ────────────────────────────────────────────────────────

class TestBenchSummary:
    def test_empty_bench(self):
        summary = get_bench_summary()
        assert summary == {"meals": [], "locations": []}

    def test_populated_bench(self):
        from data.catalog_manager import save_bench
        bench = {
            "meals": [{"item": {"name": "benched_dish"}, "benched_at_cycle": 0, "cooloff_cycles": 2, "lifetime_suggests": 5}],
            "locations": [{"item": {"name": "benched_park"}, "benched_at_cycle": 0, "cooloff_cycles": 2, "lifetime_suggests": 3}],
        }
        save_bench(bench)
        summary = get_bench_summary()
        assert "benched_dish" in summary["meals"]
        assert "benched_park" in summary["locations"]


# ── get_returning_items ──────────────────────────────────────────────────────

class TestReturningItems:
    def test_cooloff_not_expired(self):
        bench = {
            "meals": [{"item": {"name": "x"}, "benched_at_cycle": 3, "cooloff_cycles": 2}],
            "locations": [],
        }
        returning = get_returning_items(bench, current_cycle=4)
        assert returning["meals"] == []

    def test_cooloff_expired(self):
        bench = {
            "meals": [{"item": {"name": "x"}, "benched_at_cycle": 1, "cooloff_cycles": 2}],
            "locations": [],
        }
        returning = get_returning_items(bench, current_cycle=3)
        assert len(returning["meals"]) == 1
        assert returning["meals"][0]["item"]["name"] == "x"
