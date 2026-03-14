"""catalog_manager.py — Catalogue rotation with bench system for meals and locations.

Tracks suggestion frequency per item. On regen cycles, retires the most-suggested
items to a bench (cooloff = N cycles) and inserts LLM-generated replacements into
the live catalogs. Benched items whose cooloff has expired become eligible again.
"""

import json
import logging
import math
import os
from datetime import datetime
from typing import Any

from config import (
    LOCAL_DATA_DIR,
    RUN_MODE,
    ROTATION_PERCENT,
    BENCH_COOLOFF_CYCLES,
)

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.dirname(__file__)
_MEALS_PATH = os.path.join(_DATA_DIR, "meals.json")
_LOCATIONS_PATH = os.path.join(_DATA_DIR, "locations.json")

# Mood key mapping: regen JSON uses snake_case for meals, display names for locations
_MEAL_MOOD_MAP = {
    "hot_humid": "Hot & Humid",
    "warm_pleasant": "Warm & Pleasant",
    "cool_damp": "Cool & Damp",
    "cold": "Cold",
}
_MEAL_MOOD_REVERSE = {v: k for k, v in _MEAL_MOOD_MAP.items()}

# Location moods match between regen JSON and catalog
_LOCATION_MOODS = ["Nice", "Warm", "Cloudy & Breezy", "Stay In"]


# ── Persistence helpers ──────────────────────────────────────────────────────

def _stats_path() -> str:
    return os.path.join(LOCAL_DATA_DIR, "catalog_stats.json")


def _bench_path() -> str:
    return os.path.join(LOCAL_DATA_DIR, "catalog_bench.json")


def _load_json(path: str, default: Any = None) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else {}


def _save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _save_json_cloud(blob_path: str, data: Any) -> None:
    """Save JSON to GCS (CLOUD mode)."""
    import config
    from google.cloud import storage
    blob = storage.Client().bucket(config.GCS_BUCKET_NAME).blob(blob_path)
    blob.upload_from_string(
        json.dumps(data, ensure_ascii=False, indent=2),
        content_type="application/json",
    )


# ── Stats ────────────────────────────────────────────────────────────────────

def load_catalog_stats() -> dict:
    """Load or initialize catalog_stats.json."""
    default = {"meals": {}, "locations": {}, "current_cycle": 0, "updated_at": ""}
    if RUN_MODE == "CLOUD":
        try:
            import config
            from google.cloud import storage
            blob = storage.Client().bucket(config.GCS_BUCKET_NAME).blob("data/catalog_stats.json")
            return json.loads(blob.download_as_text(encoding="utf-8"))
        except Exception:
            return default
    return _load_json(_stats_path(), default)


def save_catalog_stats(stats: dict) -> None:
    stats["updated_at"] = datetime.now().isoformat()
    if RUN_MODE == "CLOUD":
        _save_json_cloud("data/catalog_stats.json", stats)
    else:
        _save_json(_stats_path(), stats)


def load_bench() -> dict:
    """Load or initialize catalog_bench.json."""
    default = {"meals": [], "locations": []}
    if RUN_MODE == "CLOUD":
        try:
            import config
            from google.cloud import storage
            blob = storage.Client().bucket(config.GCS_BUCKET_NAME).blob("data/catalog_bench.json")
            return json.loads(blob.download_as_text(encoding="utf-8"))
        except Exception:
            return default
    return _load_json(_bench_path(), default)


def save_bench(bench: dict) -> None:
    if RUN_MODE == "CLOUD":
        _save_json_cloud("data/catalog_bench.json", bench)
    else:
        _save_json(_bench_path(), bench)


# ── Suggestion tracking ─────────────────────────────────────────────────────

def record_suggestion(meal_name: str | None, location_name: str | None, activity_name: str | None = None) -> None:
    """Increment suggest_count for the given meal, location, and/or activity."""
    stats = load_catalog_stats()
    today = datetime.now().strftime("%Y-%m-%d")

    if meal_name:
        entry = stats["meals"].setdefault(meal_name, {"suggest_count": 0, "added_cycle": stats["current_cycle"], "last_suggested": ""})
        entry["suggest_count"] = entry.get("suggest_count", 0) + 1
        entry["last_suggested"] = today

    if location_name:
        entry = stats["locations"].setdefault(location_name, {"suggest_count": 0, "added_cycle": stats["current_cycle"], "last_suggested": ""})
        entry["suggest_count"] = entry.get("suggest_count", 0) + 1
        entry["last_suggested"] = today

    if activity_name:
        activities = stats.setdefault("activities", {})
        entry = activities.setdefault(activity_name, {"suggest_count": 0, "last_suggested": ""})
        entry["suggest_count"] = entry.get("suggest_count", 0) + 1
        entry["last_suggested"] = today

    save_catalog_stats(stats)


# ── Stale identification ────────────────────────────────────────────────────

def identify_stale_items(
    catalog: list[dict],
    stats_section: dict,
    mood: str,
    rotation_pct: float = ROTATION_PERCENT,
) -> list[dict]:
    """Return the most-suggested items in a mood category, up to rotation_pct of the pool.

    Args:
        catalog: Full catalog list (meals or locations)
        stats_section: The stats["meals"] or stats["locations"] dict
        mood: Mood string matching the catalog's moods field
        rotation_pct: Fraction of mood-pool items to retire

    Returns:
        List of catalog items to retire, sorted by suggest_count desc.
    """
    mood_items = [item for item in catalog if mood in item.get("moods", [])]
    if not mood_items:
        return []

    quota = max(1, math.floor(len(mood_items) * rotation_pct))

    # Sort by suggest_count descending; items never suggested sort last
    def _sort_key(item: dict) -> int:
        name = item.get("name", "")
        return stats_section.get(name, {}).get("suggest_count", 0)

    ranked = sorted(mood_items, key=_sort_key, reverse=True)
    # Only retire items that have actually been suggested at least once
    stale = [item for item in ranked[:quota] if _sort_key(item) > 0]
    return stale


# ── Bench management ────────────────────────────────────────────────────────

def get_bench_summary() -> dict[str, list[str]]:
    """Return benched item names grouped by type, for LLM prompt context."""
    bench = load_bench()
    return {
        "meals": [entry["item"]["name"] for entry in bench.get("meals", []) if "item" in entry],
        "locations": [entry["item"]["name"] for entry in bench.get("locations", []) if "item" in entry],
    }


def get_returning_items(bench: dict, current_cycle: int) -> dict[str, list[dict]]:
    """Find benched items whose cooloff has expired."""
    returning: dict[str, list[dict]] = {"meals": [], "locations": []}
    for cat_type in ("meals", "locations"):
        for entry in bench.get(cat_type, []):
            benched_at = entry.get("benched_at_cycle", 0)
            cooloff = entry.get("cooloff_cycles", BENCH_COOLOFF_CYCLES)
            if current_cycle - benched_at >= cooloff:
                returning[cat_type].append(entry)
    return returning


# ── Catalogue rotation ──────────────────────────────────────────────────────

def rotate_catalog(regen_data: dict) -> dict:
    """Rotate stale items out of live catalogs and insert LLM replacements.

    Args:
        regen_data: Parsed ---REGEN--- JSON from LLM with "meals" and "locations" keys.

    Returns:
        Summary dict with counts of items retired, added, and returned from bench.
    """
    stats = load_catalog_stats()
    bench = load_bench()
    current_cycle = stats.get("current_cycle", 0)

    meals_catalog = _load_json(_MEALS_PATH, [])
    locations_catalog = _load_json(_LOCATIONS_PATH, [])

    summary = {"meals_retired": 0, "meals_added": 0, "locations_retired": 0, "locations_added": 0, "meals_returned": 0, "locations_returned": 0}

    # ── 1. Rotate meals ──────────────────────────────────────────────────
    regen_meals = regen_data.get("meals", {})
    for regen_key, display_mood in _MEAL_MOOD_MAP.items():
        new_names = regen_meals.get(regen_key, [])
        if not new_names:
            continue

        stale = identify_stale_items(meals_catalog, stats.get("meals", {}), display_mood)

        # Move stale → bench
        stale_names = set()
        for item in stale:
            stale_names.add(item["name"])
            bench["meals"].append({
                "item": item,
                "benched_at_cycle": current_cycle,
                "cooloff_cycles": BENCH_COOLOFF_CYCLES,
                "lifetime_suggests": stats.get("meals", {}).get(item["name"], {}).get("suggest_count", 0),
            })
            # Remove from stats
            stats.get("meals", {}).pop(item["name"], None)
        summary["meals_retired"] += len(stale_names)

        # Remove stale from catalog
        meals_catalog = [m for m in meals_catalog if m["name"] not in stale_names]

        # Insert new items (LLM gives pinyin strings for meals)
        for name in new_names:
            if isinstance(name, str):
                new_item = {
                    "name": name,
                    "moods": [display_mood],
                    "description": "",
                    "tags": [],
                }
                meals_catalog.append(new_item)
                stats.setdefault("meals", {})[name] = {
                    "suggest_count": 0,
                    "added_cycle": current_cycle,
                    "last_suggested": "",
                }
                summary["meals_added"] += 1

    # ── 2. Rotate locations ──────────────────────────────────────────────
    regen_locations = regen_data.get("locations", {})
    for mood in _LOCATION_MOODS:
        new_locs = regen_locations.get(mood, [])
        if not new_locs:
            continue

        stale = identify_stale_items(locations_catalog, stats.get("locations", {}), mood)

        stale_names = set()
        for item in stale:
            stale_names.add(item["name"])
            bench["locations"].append({
                "item": item,
                "benched_at_cycle": current_cycle,
                "cooloff_cycles": BENCH_COOLOFF_CYCLES,
                "lifetime_suggests": stats.get("locations", {}).get(item["name"], {}).get("suggest_count", 0),
            })
            stats.get("locations", {}).pop(item["name"], None)
        summary["locations_retired"] += len(stale_names)

        locations_catalog = [loc for loc in locations_catalog if loc["name"] not in stale_names]

        for loc in new_locs:
            if isinstance(loc, dict) and loc.get("name"):
                loc.setdefault("moods", [mood])
                if mood not in loc["moods"]:
                    loc["moods"].append(mood)
                locations_catalog.append(loc)
                stats.setdefault("locations", {})[loc["name"]] = {
                    "suggest_count": 0,
                    "added_cycle": current_cycle,
                    "last_suggested": "",
                }
                summary["locations_added"] += 1

    # ── 3. Return items from bench whose cooloff expired ─────────────────
    returning = get_returning_items(bench, current_cycle)

    for item_entry in returning["meals"]:
        item = item_entry["item"]
        # Only return if not already in catalog (name collision with new items)
        existing_names = {m["name"] for m in meals_catalog}
        if item["name"] not in existing_names:
            meals_catalog.append(item)
            stats.setdefault("meals", {})[item["name"]] = {
                "suggest_count": 0,
                "added_cycle": current_cycle,
                "last_suggested": "",
            }
            summary["meals_returned"] += 1

    for item_entry in returning["locations"]:
        item = item_entry["item"]
        existing_names = {loc["name"] for loc in locations_catalog}
        if item["name"] not in existing_names:
            locations_catalog.append(item)
            stats.setdefault("locations", {})[item["name"]] = {
                "suggest_count": 0,
                "added_cycle": current_cycle,
                "last_suggested": "",
            }
            summary["locations_returned"] += 1

    # Remove returned items from bench
    returned_meal_names = {e["item"]["name"] for e in returning["meals"]}
    returned_loc_names = {e["item"]["name"] for e in returning["locations"]}
    bench["meals"] = [e for e in bench["meals"] if e["item"]["name"] not in returned_meal_names]
    bench["locations"] = [e for e in bench["locations"] if e["item"]["name"] not in returned_loc_names]

    # ── 4. Increment cycle and persist ───────────────────────────────────
    stats["current_cycle"] = current_cycle + 1

    _save_json(_MEALS_PATH, meals_catalog)
    _save_json(_LOCATIONS_PATH, locations_catalog)
    save_catalog_stats(stats)
    save_bench(bench)

    # Reload the in-memory OUTDOOR_LOCATIONS list used by outdoor_scoring
    try:
        from data.location_loader import load_outdoor_locations
        import data.location_loader as _ll
        _ll.OUTDOOR_LOCATIONS = load_outdoor_locations()
    except Exception:
        pass

    # Reload the in-memory _ALL_MEALS list used by meal_classifier
    try:
        import data.meal_classifier as _mc
        _mc._ALL_MEALS = []  # Force reload on next call
    except Exception:
        pass

    logger.info(
        "Catalog rotation complete: %d meals retired, %d added, %d returned; "
        "%d locations retired, %d added, %d returned (cycle %d)",
        summary["meals_retired"], summary["meals_added"], summary["meals_returned"],
        summary["locations_retired"], summary["locations_added"], summary["locations_returned"],
        current_cycle + 1,
    )
    return summary
