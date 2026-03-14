# Catalogue Rotation with Bench System + Activity Dedup

**Date:** 2026-03-14

## Problem

The meal and location catalogues (`meals.json`, `locations.json`) were static — the same ~100 items cycled forever. The LLM-generated regen output (every 30 days) was saved to `regen.json` but never merged back into the live catalogues. Dedup only prevented repeats within a 3-day window, and activities had no dedup at all (`activity_suggested` existed in the history schema but was never populated).

## Solution

### 1. Expanded dedup window (3 → 7 days)

`_extract_recent_meals()` and `_extract_recent_locations()` now default to `days=7`, configurable via `DEDUP_WINDOW_DAYS` env var. This prevents the same dish or location from being recommended twice within a week.

### 2. Catalogue rotation with bench

A new module `data/catalog_manager.py` manages the lifecycle of catalogue items:

**Suggestion tracking** — Every broadcast records which meal, location, and activity was suggested. Frequency data is persisted in `catalog_stats.json`:

```json
{
  "meals": { "涼麵 (liáng miàn)": { "suggest_count": 12, "last_suggested": "2026-03-14" } },
  "locations": { "Shulin Sports Park": { "suggest_count": 8, "last_suggested": "2026-03-10" } },
  "activities": { "hiking": { "suggest_count": 5, "last_suggested": "2026-03-13" } },
  "current_cycle": 3
}
```

**Stale identification** — On each regen cycle, `identify_stale_items()` ranks items by `suggest_count` within each mood category and retires the top ~35% (`ROTATION_PERCENT`).

**Bench system** — Retired items move to `catalog_bench.json` with a 2-cycle cooloff (`BENCH_COOLOFF_CYCLES`). After 60 days on the bench, items become eligible to return to the live catalogue. This prevents permanent loss of proven favourites.

**Rotation flow:**

```
Every 30 days (regen cycle):
  1. Identify stale items (top 35% by suggest_count per mood)
  2. LLM prompt includes: retiring items + benched items (to avoid duplicates)
  3. LLM generates replacements (via Opus 4.6)
  4. rotate_catalog():
     a. Move stale → bench (cooloff = 2 cycles)
     b. Insert new items into meals.json / locations.json
     c. Return bench items whose cooloff expired
     d. Reset stats for new items
  5. Persist all files
```

### 3. Dynamic regen prompt

`REGEN_INSTRUCTION` was a static string. It is now `build_regen_instruction()`, a function that dynamically includes:

- Which items are being retired (so the LLM generates thematically complementary replacements)
- Which items are on the bench (so the LLM doesn't regenerate duplicates)
- Target replacement counts per mood category

### 4. Activity dedup (lightweight, Path A)

The 16 scored activity types remain a fixed set in `OUTDOOR_WEIGHTS_BY_ACTIVITY`. No activity catalogue was created. Instead:

- `_extract_recent_activities()` pulls `activity_suggested` from the last 7 days of history
- The prompt builder now skips recently-suggested activities when picking the top activity hint, falling back to the next-best scorer
- `metadata["activity_suggested"]` is now populated on every broadcast (was a schema placeholder)
- Activity frequency is tracked in `catalog_stats.json` alongside meals and locations

## Config

| Variable | Default | Purpose |
| --- | --- | --- |
| `DEDUP_WINDOW_DAYS` | 7 | Days of history checked for repeat suggestions |
| `ROTATION_PERCENT` | 0.35 | Fraction of items per mood to retire each regen |
| `BENCH_COOLOFF_CYCLES` | 2 | Regen cycles before benched items can return |

## Files Changed

| File | Change |
| --- | --- |
| `data/catalog_manager.py` | **New** — rotation logic, stats tracking, bench management |
| `data/meal_classifier.py` | Default dedup window 3 → 7 |
| `data/outdoor_scoring.py` | Default dedup window 3 → 7; new `_extract_recent_activities()` |
| `data/weather_processor.py` | Uses `DEDUP_WINDOW_DAYS` from config; passes `recent_activities` to processed data |
| `narration/llm_prompt_builder.py` | `REGEN_INSTRUCTION` → `build_regen_instruction()`; activity dedup in top-activity hint; strips `recent_activities` from LLM input |
| `app.py` | Wires `record_suggestion()` after broadcast; wires `rotate_catalog()` after regen; populates `activity_suggested` in metadata |
| `config.py` | Adds `ROTATION_PERCENT`, `BENCH_COOLOFF_CYCLES`, `DEDUP_WINDOW_DAYS` |
| `tests/test_catalog_manager.py` | **New** — 15 tests covering stats, stale ID, rotation, bench, returning |
| `tests/test_outdoor_scoring.py` | 4 new tests for `_extract_recent_activities()` |
