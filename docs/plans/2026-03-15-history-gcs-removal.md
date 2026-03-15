# Refactor: Remove GCS History Backend, Consolidate on Modal Volume

## Problem

`history/conversation.py` had two storage backends: GCS (for `RUN_MODE=CLOUD`) and
local file (for `LOCAL`/`MODAL`). In practice the GCS path was dead code because:

1. `modal_app.py` sets `RUN_MODE=MODAL` before importing `app.py` / `conversation.py`
2. All Cloud Run routes (`/api/broadcast`, `/api/chat`, `/api/tts`) proxy to Modal endpoints
3. `save_day()` always ran inside Modal containers where `RUN_MODE=MODAL`

The GCS branch added complexity (credential bootstrapping, blob error handling, dual
read/write paths) with no production benefit.

## Changes

### 1. `history/conversation.py` — Remove GCS code path

- Removed imports: `google.cloud.storage`, `google.api_core.exceptions.NotFound`,
  `RUN_MODE`, `GCS_BUCKET_NAME`, `GCS_HISTORY_KEY`
- `_load_history_map()` now delegates directly to `_load_history_map_local()`
- `save_day()` uses `_load_history_map_local()` + `_save_history_local()` unconditionally
- Storage path determined by `LOCAL_DATA_DIR` from config (`local_data/` in LOCAL,
  `/data/` in MODAL — the Modal Volume mount point)

### 2. `config.py` — Remove `GCS_HISTORY_KEY`

Deleted the `GCS_HISTORY_KEY = "history/conversation.json"` constant. Only consumer
was `conversation.py`. `GCS_BUCKET_NAME` remains (used by `tts_client.py`,
`catalog_manager.py`, `app.py` regen).

## Storage Architecture After Change

| RUN_MODE | History path | Persistence |
|----------|-------------|-------------|
| LOCAL | `local_data/history.json` | Disk |
| MODAL | `/data/history.json` | Modal Volume (`volume.commit()` in `modal_app.py`) |

Cloud Run never reads history directly — all reads proxy through Modal's
`broadcast()` endpoint which calls `volume.reload()` then `get_today_broadcast()`.
