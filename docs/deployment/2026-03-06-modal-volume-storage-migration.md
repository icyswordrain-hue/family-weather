# Storage Migration: GCS → Modal Volume
_2026-03-06_

---

## Decision Summary

Broadcast history (`history/conversation.json`) and TTS audio files were moved from Google Cloud Storage to the Modal persistent volume (`family-weather-data` at `/data`). GCS was abandoned as a runtime dependency for the pipeline after multiple independent failure modes proved it too fragile to rely on inside Modal containers.

---

## Why GCS Kept Failing

This was not a single bug. Every time one GCS failure was fixed, a different one surfaced. The pattern over multiple troubleshooting sessions:

### Round 1 — Missing GCP credentials in Modal (2026-03-01)

Modal containers have no GCP credentials by default. Every `storage.Client()` call silently raised `google.auth.exceptions.DefaultCredentialsError` inside the `except Exception` blocks in `history/conversation.py` and `narration/tts_client.py`. The pipeline appeared to complete — logs said "Saved conversation history" — but no data was ever written to GCS. The `try/except` swallowed the error.

**Fix attempted:** Created a dedicated service account (`modal-pipeline@...`), stored its JSON key in GCP Secret Manager as `GCS_BUCKET_NAME`, synced to Modal secrets, added `_bootstrap_gcp_credentials()` to decode and inject `GOOGLE_APPLICATION_CREDENTIALS` at container start.

### Round 2 — Quoted bucket name in Secret Manager (2026-03-06)

After GCP credentials were in place, GCS calls started reaching the API but immediately failed:
```
ValueError: Bucket names must start and end with a number or letter.
```
The value stored in GCP Secret Manager was `"family-weather-dashboard"` — with surrounding double-quote characters. The sync script (`sync_secrets_to_modal.py`) stripped whitespace but not the quotes, so Modal received a literal `"` as the first character of the bucket name.

The error was again swallowed silently. From the outside, the pipeline looked healthy: Cloud Scheduler fired, Modal ran, logs showed no errors at the Cloud Run layer. Only `modal logs family-weather-engine` revealed the root cause.

**Fix attempted:** Re-stored the secret without quotes using `echo -n ... | gcloud secrets versions add`.

### Round 3 — `broadcast()` endpoint missing `RUN_MODE=MODAL`

Even after history writes started working in `refresh()`, the `/api/broadcast` Modal endpoint was still reading from GCS. The `refresh()` function explicitly force-sets `os.environ["RUN_MODE"] = "MODAL"` before importing app code, but `broadcast()` never did. If the Modal secrets contained `RUN_MODE=CLOUD` (which they do — injected from an earlier config), `broadcast()` would call `get_today_broadcast()` → `_load_history_map()` → GCS, ignoring the data just written to the volume by `refresh()`.

**Fix attempted:** Added the same `os.environ["RUN_MODE"] = "MODAL"` line to `broadcast()`.

### Why this was unsustainable

Each fix required:
- Updating GCP Secret Manager
- Running `sync_secrets_to_modal.py`
- Redeploying Modal (`modal deploy`)
- Triggering a test run
- Waiting for the pipeline to complete
- Checking `modal logs` to see if the next failure surfaced

The failure feedback loop was 5–10 minutes per cycle. Errors were swallowed silently. There was no local way to reproduce Modal credential conditions. GCS added an entire external service — with its own auth layer, IAM roles, bucket naming rules, and network round-trips — to a write path that just needed to persist a JSON file.

---

## The Fix: Modal Volume for Everything

The Modal volume (`family-weather-data`) is already mounted at `/data` in all three endpoints. It is always available, always writable, requires no credentials, and is committed to disk by the `volume.commit()` call in `refresh()`'s `finally` block. `station_history.jsonl` has lived there from the start with zero failures.

The local-file helpers `_load_history_map_local()` and `_save_history_local()` already existed in `history/conversation.py` and worked correctly. The only change needed was to route `RUN_MODE=MODAL` through them instead of GCS.

Audio files follow the same logic: write to `/data/audio/{date}/{slot}_{lang}_{hash}.mp3`, serve back via a new Cloud Run → Modal proxy route rather than a public GCS URL.

---

## Architecture After Migration

```
Modal volume /data/                          (persistent across invocations)
  ├── station_history.jsonl                  unchanged
  ├── history.json                           was: GCS history/conversation.json
  └── audio/
        └── {date}/
              └── {slot}_{lang}_{hash}.mp3  was: GCS audio/{date}/...

Browser audio playback:
  GET /api/audio/{date}/{slot}_{lang}_{hash}.mp3
    └── Cloud Run (RUN_MODE=CLOUD): proxy → Modal audio endpoint → /data/audio/...
    └── LOCAL: Flask send_file from local_data/audio/...
```

GCS is no longer accessed at pipeline runtime. Existing GCS objects become stale and can be deleted at any time — they are not read after this change.

---

## Files Changed

| File | Change |
|------|--------|
| `history/conversation.py` | `_load_history_map()` and `save_day()` route `RUN_MODE in ("LOCAL","MODAL")` to local file helpers instead of GCS |
| `narration/tts_client.py` | `synthesise_with_cache()`: new MODAL branch writes to `/data/audio/`, returns `/api/audio/...` URL; CLOUD branch unchanged |
| `backend/modal_app.py` | `broadcast()` force-sets `RUN_MODE=MODAL`; new `audio(filename)` endpoint serves MP3 bytes from volume |
| `app.py` | New `GET /api/audio/<path:filename>` route: proxies to Modal in CLOUD mode, serves from filesystem in LOCAL mode |
| `.github/workflows/deploy.yml` | `MODAL_AUDIO_URL` env var added to Cloud Run deploy step |

---

## Operational Notes

**History file path:** `/data/history.json` on the Modal volume (same as `LOCAL_DATA_DIR/history.json` in local dev).

**Audio file path:** `/data/audio/{date}/{slot}_{lang}_{hash}.mp3`. The cache key is an MD5 of the narration text — same text always produces the same filename, so re-running the same slot does not produce duplicate files.

**Volume commit:** `volume.commit()` is called in `refresh()`'s `finally` block. This persists both the history write and the audio write in one operation at the end of the pipeline. The `audio()` and `broadcast()` endpoints are read-only and do not need to commit.

**GCS is still used for:** `regen.json` (meal/location regeneration cache), which is accessed from `app.py` at container startup via `_restore_regen_from_gcs()`. This was not changed — regen data is written infrequently and is non-critical if lost.

**Local dev:** Unchanged. `RUN_MODE=LOCAL` was already using the local file system. The new MODAL branches are unreachable in local dev.

---

## Troubleshooting After This Change

If `/api/broadcast` returns 404 after a scheduled run:

1. Check Modal logs for pipeline errors:
   ```
   modal logs family-weather-engine
   ```
2. Verify the volume has data — look for a `volume.commit()` log line or run:
   ```
   modal shell family-weather-engine
   # inside: ls /data/
   ```
3. Confirm `RUN_MODE=MODAL` is set inside the container (should always be force-set now).

There are no GCS credentials to check, no bucket name to verify, no IAM role to audit.
