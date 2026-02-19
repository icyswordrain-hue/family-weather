# Weather Broadcast Skill

**Project:** Family Weather Dashboard
**Location:** Shulin/Banqiao border (24.9955° N, 121.4279° E)

## What this skill does

Generates a daily spoken weather broadcast for the family dashboard. It:

1. Fetches real-time weather from CWA Banqiao station (O-A0003-001)
2. Fetches township forecasts for Sanxia District (F-D0047-071)
3. Fetches AQI from MOENV Tucheng station
4. Processes data per the v4 prompt rules
5. Generates narration via Gemini 2.5 Flash
6. Synthesizes audio via Cloud TTS Chirp 3 HD (cmn-TW)
7. Saves broadcast to GCS and updates conversation history

## Trigger

POST `/api/refresh` — called by Cloud Scheduler at 05:30, 11:30, 17:30 Asia/Taipei.

## Key files

- `data/fetch_cwa.py` — CWA API client (current + forecast)
- `data/fetch_moenv.py` — MOENV AQI client
- `data/processor.py` — All v4 data processing rules
- `narration/prompt_builder.py` — Gemini prompt construction
- `narration/gemini_client.py` — Vertex AI call
- `narration/tts_client.py` — Cloud TTS + GCS upload
- `history/conversation.py` — Conversation history persistence
- `web/slices.py` — Per-profile data slices

## Secrets required

Set in Google Secret Manager and injected into Cloud Run:

- `CWA_API_KEY` — from opendata.cwa.gov.tw
- `MOENV_API_KEY` — from data.moenv.gov.tw
- `GCP_PROJECT_ID` — your GCP project
- `GCS_BUCKET_NAME` — defaults to `family-weather-dashboard`

## Deployment (Antigravity prompt)

```
Deploy this Flask application to Google Cloud Run in the asia-east1 region
(Taiwan). Use a Dockerfile. Set the following environment variables from
Secret Manager: CWA_API_KEY, MOENV_API_KEY. Enable the Cloud TTS API,
Vertex AI API, and Cloud Scheduler. Create a Cloud Storage bucket named
"family-weather-dashboard" in the same region. Set up three Cloud Scheduler
jobs to POST to /api/refresh at 05:30, 11:30, and 17:30 Asia/Taipei time.
```
