---
date: "2026-03-11"
title: "Remove Parkinson's Phrasing and Logic"
status: "Implemented"
---

# Remove Parkinson's Phrasing and Logic

## Context

Dad does not have Parkinson's. The codebase had accumulated Parkinson's-specific
assumptions across four layers: the LLM prompt schema (wasted tokens on a useless
field), the fallback narrator (injected incorrect conditional sentences), the
frontend data slice (exposed a misleading flag), and test fixtures (stale ghost
data that misrepresents the schema). This change removes all of it and replaces
any outdoor-safety framing with generic terrain/accessibility language.

## Files Changed

### `narration/fallback_narrator.py`
- Removed `parkinsons` property read from `_loc` in the P3 (Outdoor & Meal) block.
- Removed the conditional sentences that appended "Parkinson's friendly" /
  "Manageable for Parkinson's" to outdoor card text.
- Replaced with neutral "with Dad" framing (e.g., "Stick to flat, familiar routes
  if heading out with Dad").

### `web/routes.py`
- Dropped `parkinsons_safe` from the `outdoor` dict returned by `_slice_lifestyle()`.

### `narration/llm_prompt_builder.py`
- Removed `"parkinsons": "good|ok|avoid"` from the location schema in the REGEN
  system instruction.
- Rewrote the P3 outdoor instruction to focus on terrain difficulty, shade,
  seating, and general accessibility — no mention of any medical condition.

### `data/locations.json`
- Stripped `"parkinsons"` field from all location entries (~184 entries).
- Each entry now uses: `name`, `activity`, `surface`, `lat`, `lng`, `notes`.

### `tests/test_location_loader.py`
- `test_location_has_required_fields` now asserts on `"surface"` instead of the
  deleted `"parkinsons"` field.

### `tests/test_fallback_narrator.py`
- Stripped `parkinsons_safe` from the `outdoor_index` fixture.
- Stripped `parkinsons` from the `location_rec.top_locations[0]` fixture; replaced
  with `"surface": "paved"` to match the live location schema.

## Verification

```bash
# Confirm zero remaining references across Python source and JSON
grep -r "parkinsons" narration/ web/ data/ tests/ --include="*.py" --include="*.json"
# Expected: only tests/test_fallback_narrator.py lines 21-22 (until fixture is fixed)

# Run the test suite
pytest tests/ -q
# Expected: all pass
```

After the fixture is fixed, the grep should return no output.
