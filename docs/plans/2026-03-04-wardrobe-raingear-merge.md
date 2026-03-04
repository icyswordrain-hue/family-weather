# Wardrobe + Rain Gear Card Merge

**Date:** 2026-03-04  
**Status:** Implemented

## Problem

The lifestyle view rendered two adjacent cards — **Rain Gear** (☂️) and **Wardrobe** (🧥) — that together answer a single user question: *"What do I wear/carry when I leave the house?"* This created visual redundancy and wasted grid real estate.

## Decision: Option A — Sub-line merge at the slice layer

Collapse both cards into one `🧥 Wardrobe` card. The rain-gear sentence becomes a `☂️` sub-line below the main wardrobe text.

```
🧥  Wardrobe
    A light jacket should do — feels around 24°.     (main text)
    Feels like 24°                                    (ls-sub: feels_like)
    ☂️ No rain gear needed today.                     (ls-sub: rain_gear)
```

### Why this approach
- **No LLM prompt change needed** — both fields still produced separately; merge happens at `_slice_lifestyle`.
- **Rain-gear stays visually distinct** — the ☂️ prefix keeps it scannable; it doesn't get buried.
- **Fallback narrator unchanged** — `_build_fallback_cards` still emits separate `wardrobe` and `rain_gear` keys.
- **Fewer cards** — lifestyle grid is one row shorter.

## Files Changed

### `web/routes.py` — `_slice_lifestyle`
- `rain_gear_text` folded into `wardrobe` dict as `wardrobe.rain_gear_text`.
- Top-level `"rain_gear"` key removed from return value.

### `web/static/app.js` — `renderLifestyleView`
- Standalone `// 2. Rain Gear` card block removed.
- `wardrobe.rain_gear_text` rendered as a `☂️` sub-line inside the wardrobe card.

## No changes required
- `narration/fallback_narrator.py` — emits both keys, slice layer handles the merge.
- `narration/llm_prompt_builder.py` — keeps `wardrobe` and `rain_gear` as separate schema fields.
- Tests — narration tests target `---CARDS---` output, which still has both keys.
