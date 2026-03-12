# Fix: broadcast() volume.reload() — chat returns "No broadcast available" after pipeline

**Date:** 2026-03-13
**File changed:** `backend/modal_app.py`

## Problem

After a successful pipeline run, sending a chat message immediately returned:

> No broadcast available for 2026-03-13

The system log showed the pipeline completing normally ("Pipeline success.", "Saving broadcast to history..."), but the chat endpoint still couldn't find the data.

## Root cause

`refresh()` writes history to the Modal Volume then calls `volume.commit()`. The `broadcast()` function runs in a **separate Modal container** (possibly a warm/reused one). Without `volume.reload()`, that container reads a **stale mount** — it never sees the data committed by `refresh()`. So `get_today_broadcast()` returns `None` → 404 → Cloud Run's `_get_broadcast_for_chat()` treats it as a missing broadcast.

The call chain:
```
/api/chat (Cloud Run)
  → _get_broadcast_for_chat()
    → no _broadcast_cache entry
    → GET MODAL_BROADCAST_URL
      → broadcast() Modal endpoint
        → volume still stale (no reload)
        → get_today_broadcast() → None
        → {"error": "No broadcast found"} 404
  → returns None → "No broadcast available"
```

## Fix

One line added to `broadcast()` in `modal_app.py`, after `sys.path.insert` and before the history import:

```python
volume.reload()  # pick up data committed by refresh()
```

## Gotcha for future reference

Any Modal endpoint that reads from a volume written by a **different** function invocation must call `volume.reload()` first. A warm container's volume mount is frozen at container-start time; `volume.commit()` in another container does not push updates automatically.
