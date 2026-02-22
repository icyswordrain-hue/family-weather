# Weather Broadcast Skill

**Project:** Family Weather Dashboard
**Location:** Shulin/Banqiao border (24.9955° N, 121.4279° E)

## What this skill does

Generates a daily spoken weather broadcast for the family dashboard. It:

1. Fetches real-time weather from CWA Banqiao station (Manual 466881, Dataset O-A0003-001)
2. Fetches township forecasts for Sanxia and Banqiao (F-D0047-071)
3. Fetches AQI from MOENV Tucheng station (realtime + forecast)
4. Processes data per the **v6** design spec (pressure drops, AT proxy, low deviation detection)
5. Generates narration via Gemini or Claude (v6 persona and paragraph specs)
6. Synthesizes audio via Edge TTS (cmn-TW)
7. Saves broadcast to local history and optionally GCS

## Trigger

POST `/api/refresh` — called by Cloud Scheduler at 05:30, 11:30, 17:30 Asia/Taipei.

## Key files

- `data/fetch_cwa.py` — CWA API client (current observations + township forecasts)
- `data/fetch_moenv.py` — MOENV AQI client (realtime + zone forecast)
- `data/processor.py` — **v6 processing rules** (Ménière's 4-trigger, Cardiac, 50km pull)
- `narration/prompt_builder.py` — **v6 prompt construction** and response parsing
- `narration/claude_client.py` — Claude API integration (primary narration provider)
- `narration/gemini_client.py` — Gemini API integration (fallback narration provider)
- `narration/template_narrator.py` — Template-based narration (no LLM, for testing)
- `narration/summarizer.py` — History summariser for prompt context
- `narration/tts_client.py` — Edge TTS / Google Cloud TTS integration
- `history/conversation.py` — Persistence with 14-day regen detection

## Secrets required

Set in Google Secret Manager and injected into Cloud Run:

- `CWA_API_KEY` — from opendata.cwa.gov.tw
- `MOENV_API_KEY` — from data.moenv.gov.tw
- `ANTHROPIC_API_KEY` — for Claude narration (primary)
- `GEMINI_API_KEY` — for Gemini narration (fallback)
- `GCP_PROJECT_ID` — your GCP project
- `GCS_BUCKET_NAME` — defaults to `family-weather-dashboard`

## Workflows & Superpowers

Use these integrated skills for a systematic development cycle:

1. **Bug Fixing**: Use [systematic-debugging](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/.agent/skills/systematic-debugging/SKILL.md) to trace data issues (e.g., CWA API changes) to the root cause before fixing.
2. **Feature Iteration**: Use [test-driven-development](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/.agent/skills/test-driven-development/SKILL.md) for new processing logic or alert thresholds (Red-Green-Refactor).
3. **Pre-Flight Check**: Always use [verification-before-completion](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/.agent/skills/verification-before-completion/SKILL.md) before claiming a task is done or updated.
4. **Planning**: Use [writing-plans](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/.agent/skills/writing-plans/SKILL.md) for major version bumps (v7+) or architecture changes.

## Special rules (v6)

- **Ménière's Triggers** (any triggers alert; 2+ or typhoon → high severity):
  1. Pressure drop ≥ 10 hPa in 24h → typhoon-level (high)
  2. Pressure drop ≥ 6 hPa in 24h → moderate
  3. Absolute pressure < 1005 hPa → low pressure
  4. RH ≥ 90% in 2+ segments → sustained high humidity
- **Narration Provider**: Default `CLAUDE` (`claude-sonnet-4-6` primary, `claude-haiku-4-5-20251001` fallback). Set `NARRATION_PROVIDER=GEMINI` or `TEMPLATE` to switch.
- **Gemini Models**: `gemini-3.1-pro-preview` (pro), `gemini-1.5-flash` (flash fallback).
- **Meal Logic**: ONE single dish suggested per broadcast.
- **Location Pool**: 50km radius with 14-day refresh cycle.
- **Refresh**: 05:30, 11:30, 17:30 Asia/Taipei.
