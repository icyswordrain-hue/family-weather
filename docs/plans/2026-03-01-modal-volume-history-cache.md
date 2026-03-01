# Modal: Station History Cache, History Fix, Morning TTS

Three related gaps in the Modal execution path, implemented 2026-03-01.

---

## What was changed and why

### 1. Station observation history (`config.py`, `data/fetch_cwa.py`)

`fetch_current_conditions()` previously returned a snapshot and discarded it. A new append-only JSONL file (`station_history.jsonl`) now captures every fetch in `LOCAL_DATA_DIR` (resolves to `/data` on the Modal Volume). Records include a `fetched_at` timestamp alongside the CWA `obs_time` so consumers can distinguish fetch latency from observation age. The file is pruned to a rolling 7-day window (`STATION_HISTORY_DAYS`) on every write. Both the JSONL write and the `volume.commit()` are non-fatal — a disk or commit failure logs a warning and does not break the fetch.

**Bugs fixed in the original draft:**
- `volume.commit()` guard was `in ("CLOUD", "MODAL")` — CLOUD mode has no Modal Volume. Fixed to `== "MODAL"`.
- JSONL write sat inside the function's outer `try/except`, so a disk error would surface as `RuntimeError("Failed to fetch CWA current conditions")`. Moved to its own guarded block.
- `RUN_MODE` was re-read via `os.environ.get()` instead of using the module-level constant.
- No pruning — file would grow unbounded.
- No `fetched_at` field.

### 2. LLM history context in Modal (`history/conversation.py`)

`_load_history_map()` was reading from the local volume file for MODAL mode (`if RUN_MODE in ["LOCAL", "MODAL"]`), but `save_day()` writes to GCS for all non-LOCAL modes. The local file was never written, so every Modal run started with zero conversation history. One-line fix: treat MODAL like CLOUD for reads (`if RUN_MODE == "LOCAL"`), so both reads and writes go through GCS. `get_today_broadcast()` benefits from the same fix.

### 3. Morning TTS pre-generation (`app.py`)

All three daily Cloud Scheduler refreshes (06:15 morning, 11:15 midday, 17:15 evening) deferred TTS to on-demand in CLOUD/MODAL modes. The morning slot runs before the household wakes up, making it the appropriate time to pay the synthesis cost upfront. The eager-TTS condition was widened from `RUN_MODE == "LOCAL"` to `RUN_MODE == "LOCAL" or (RUN_MODE == "MODAL" and slot == "morning")`. `synthesise_with_cache` already handles MODAL mode (GCS cache-check → edge_tts → GCS upload → returns public URL); it just wasn't being called. Midday and evening remain deferred.

---

## Files changed

| File | Change |
|------|--------|
| `config.py` | Add `from pathlib import Path`; add `STATION_HISTORY_PATH`, `STATION_HISTORY_DAYS` after `LOCAL_DATA_DIR` |
| `data/fetch_cwa.py` | Add `RUN_MODE`, `STATION_HISTORY_PATH`, `STATION_HISTORY_DAYS` to imports; add `_prune_station_history()` helper; replace bare `return {…}` with `record` + guarded JSONL write + `volume.commit()` |
| `history/conversation.py` | `_load_history_map()` line 72: `if RUN_MODE in ["LOCAL", "MODAL"]:` → `if RUN_MODE == "LOCAL":` |
| `app.py` | TTS condition: `if RUN_MODE == "LOCAL"` → `if RUN_MODE == "LOCAL" or (RUN_MODE == "MODAL" and slot == "morning")` |
| `backend/modal_app.py` | No changes — volume already mounted at `/data` on `refresh()` and `broadcast()` |

---

## Notes for future readers

- Any Modal function that *reads* `station_history.jsonl` from a different invocation than the one that wrote it must call `volume.reload()` at function entry.
- `STATION_HISTORY_PATH` and `STATION_HISTORY_DAYS` are overridable via environment variables.
- The `station_history.jsonl` file is the only data currently written to the Modal Volume; all other pipeline outputs (history, audio) go to GCS.
