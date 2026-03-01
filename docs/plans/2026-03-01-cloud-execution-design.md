# Cloud Execution & Smart Pipeline Design

## Goal
Transition the Family Weather Dashboard to run on the cloud (Modal + Google Cloud Storage) while maintaining full local functionality. Introduce cost-saving measures via GCS TTS audio caching and smart midday pipeline execution.

## Core Architecture
When `RUN_MODE=CLOUD`, the Flask application acts as a lightweight proxy and UI server (e.g., hosted on Google Cloud Run). The heavy lifting (data fetching, LLM narration, TTS synthesis) runs on Modal's serverless infrastructure.

## Key Components & Changes

### 1. Audio Storage and Serving (TTS)
**Problem:** Currently, Modal saves TTS audio to its internal `/data` volume, making it inaccessible to the Flask frontend.
**Solution:**
- **Cloud Mode (`RUN_MODE=CLOUD` | `RUN_MODE=MODAL`):** Modal will upload all generated TTS audio (Google Cloud TTS or Edge TTS) directly to Google Cloud Storage (GCS) and return the public or signed GCS URLs in the payload.
- **Local Mode (`RUN_MODE=LOCAL`):** The pipeline saves audio to the local file system (`local_data/`) and returns `/local_assets/...` URLs, exactly as it does now.
- **Update:** `tts_client.py` will be modified to support GCS uploads for Edge TTS when in cloud mode.

### 2. Aggressive TTS Caching
**Goal:** Avoid re-rendering TTS audio if the script hasn't changed meaningfully.
**Solution:**
- Implement a hashing mechanism for the narration text.
- Before calling the TTS provider, the pipeline generates a hash of the cleaned narration text.
- It checks GCS (in Cloud mode) or local storage (in Local mode) if an audio file matching `[date]_[hash].mp3` exists.
- If it exists, skip TTS synthesis and return the URL of the cached audio.
- If not, synthesize, upload as `[date]_[hash].mp3`, and return the URL.

### 3. Smart Midday Pipeline Run
**Goal:** Reduce pipeline executions from 3/day to 2/day on stable weather days by skipping the midday run if conditions haven't changed.
**Solution (Approach C):**
- The skip logic will live inside the Flask `app.py` `/api/refresh` endpoint.
- When `/api/refresh` is triggered, Flask classifies the current time slot (morning, midday, evening).
- If the slot is **midday**:
  1. Flask performs a lightweight fetch of current conditions (`fetch_cwa.fetch_current_conditions()`).
  2. Flask loads the morning broadcast from history (GCS or local).
  3. A new helper function `_conditions_changed_since_morning(current, cached_morning)` compares key signals:
     - Temperature swing >= 3°C
     - Rain status change
     - Alert state changes
     - AQI category boundary cross
     - Outdoor score label change
  4. If NO changes are detected, Flask aborts the Modal refresh call, logs the skip, and returns the morning broadcast to the frontend.
- If it's morning/evening, or midday *did* change, Flask proxies the request to Modal to execute the full `.refresh()` pipeline.

### 4. Database Regeneration (Regen) Syncing
**Problem:** `regen.json` is generated on Modal but needs to be accessible. Currently, `app.py` writes it to `LOCAL_DATA_DIR`.
**Solution:**
- The `regen` data is already included in the broadcast JSON payload returned by Modal.
- The Flask app receives this payload from the Modal proxy stream.
- When Flask receives the `regen` payload, it can persist it locally (or to GCS, depending on where the history module writes it).
- Currently, `app.py` line 278 handles writing `regen.json`. This logic works fine as long as Flask persists it to wherever it needs it (e.g., GCS in cloud mode, or local in local mode). We will update `app.py` to ensure `regen.json` is saved to GCS when in `CLOUD` mode, rather than just `LOCAL_DATA_DIR`.

## Required File Modifications

1. **`narration/tts_client.py`**:
   - Update `_generate_edge_audio` to upload to GCS when in Cloud/Modal mode, instead of forcing `_save_local_audio`.
   - Implement TTS caching based on a hash of the narration text. Download/check existence before synthesizing.

2. **`app.py`**:
   - Implement the `_conditions_changed_since_morning` logic.
   - Update the `/api/refresh` route to incorporate the time-slot classification and the conditional skip logic for midday runs.
   - Update regen data persisting to save to GCS in `CLOUD` mode.

3. **`backend/pipeline.py` or new helper file**:
   - Add the actual `_conditions_changed_since_morning` function.

4. **`config.py`**:
   - Ensure GCS bucket names and paths are clearly defined for audio caching.

## Trade-offs
- **TTS Caching vs. Storage Cost:** We trade API compute cost for marginally higher GCS storage cost. Since it's just audio files, storage cost is negligible.
- **Midday Skip:** We rely on the Flask app to do a lightweight CWA fetch. This adds a tiny bit of compute to the Flask proxy, but the API call is fast and free.
