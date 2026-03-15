# Refactor: Merge Force Refresh with Re-Sync Audio

**Date:** 2026-03-15
**Status:** Completed

## Problem

Two separate controls existed for refreshing content:

1. **Force Refresh** (settings panel Auto/Force toggle) — bypassed narration skip guard, forced LLM regeneration. Did NOT regenerate TTS audio outside morning slot.
2. **Re-synthesize Audio** button (settings tab) — regenerated TTS from existing narration via `POST /api/tts`. No LLM call.

Users who force-refreshed at midday got fresh narration but stale audio, requiring a second manual step. The two controls served related but disconnected purposes, creating UX confusion.

## Solution

Merge both into a single action: force refresh now always regenerates TTS audio alongside narration. The standalone re-sync button and `/api/tts` endpoint are removed.

### Morning slot resolution

TTS generation in `_pipeline_steps()` was gated on `slot == "morning"`. The new logic:

```python
if slot == "morning" or force:
    _tts_slot = slot if slot == "morning" else "manual"
    synthesise_with_cache(text, lang, date, _tts_slot)
```

- Normal refreshes: unchanged (TTS only on morning slot)
- Force refreshes: TTS runs on any slot, using `slot="manual"` (the same pattern the removed `/api/tts` endpoint used)

## Files Changed

| File | Change |
|------|--------|
| `app.py` | TTS gating `if slot == "morning"` → `if slot == "morning" or force:`; deleted `/api/tts` endpoint (52 lines) |
| `backend/modal_app.py` | Deleted Modal `tts()` endpoint (49 lines) |
| `web/templates/dashboard.html` | Removed `sheet-tts-btn` button |
| `web/static/app.js` | Removed TTS button click handler + `tts_btn` translation keys |
| `CLAUDE.md` | Removed `/api/tts` from proxy list |
| `tests/test_tts_mode_split.py` | Added `test_force_midday_tts_is_eager` |

## What stays unchanged

- **Audio age badge** (`_updateAudioAgeBadge`) — still useful for non-force refreshes where audio drifts
- **Auto/Force toggle** and `.force-mode` CSS — still needed for narration force bypass
- **Normal (non-force) refresh behavior** — TTS only on morning slot
