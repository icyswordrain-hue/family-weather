# Cost Optimization — March 2026

## Context

Audited the full pipeline (Cloud Run, Modal, GCS, Claude, Gemini, TTS, CWA, MOENV)
to estimate monthly running cost and identify ways to reduce API spend.

## Monthly Cost Estimate

| Service | Role | Est. $/month |
|---------|------|-------------|
| Modal | Pipeline execution (on-demand) | $5–15 |
| Cloud Run | Flask proxy (scale-to-zero, 512 MiB, max 2) | $5–20 |
| GCS | Broadcast JSON + MP3 + history | ~$0.50 |
| Cloud TTS | Narration audio synthesis | ~$0.40 |
| Claude Sonnet | Narration (~2–3 calls/day, 1400 max tokens) | $3–5 |
| Claude Opus | Regen meal/location DB (1×/30 days) | ~$0.30 |
| Claude Haiku | Chat (0–50 calls/month, 300 max tokens) | $0.10–0.50 |
| CWA / MOENV | Weather + AQI data (free gov APIs) | $0 |
| Gemini | Configured but inactive | $0 |
| Other (Artifact Registry, Secret Manager) | Infra overhead | ~$0.15 |
| **Total** | | **~$15–42** |

## Existing Cost Controls

- 30-min narration cache (skips LLM on identical conditions)
- Midday skip when weather unchanged from morning
- Same-day narration reuse on stable conditions
- TTS MD5 caching (no re-synthesis for identical text)
- Edge TTS fallback (free)
- Template narrator fallback (no API cost on LLM failure)
- Anthropic ephemeral prompt caching (reduces input tokens)
- Scale-to-zero on both Cloud Run and Modal
- GCS 30-day audio lifecycle policy

## Changes Made

1. **Regen model: Opus → Sonnet** (`CLAUDE_REGEN_MODEL` default `claude-sonnet-4-6`)
   - Opus ($15/$75 per M tokens) is 5× more expensive than Sonnet ($3/$15)
   - Regen produces meal/location JSON — Sonnet handles this adequately
   - Still overridable via env var

2. **Regen cycle: 30 → 60 days** (`REGEN_CYCLE_DAYS` default `60`)
   - Halves regen frequency; 7-day dedup window already prevents stale suggestions
   - Bench cooloff (2 cycles) now means ~120 days before benched items return

## Future Options (not implemented)

| Change | Savings | Notes |
|--------|---------|-------|
| Narration: Sonnet → Haiku | ~75% narration cost | Test quality first |
| TTS: Google → Edge permanently | ~$0.40/mo | `TTS_PROVIDER=EDGE` |
| Cache TTL: 30 min → 2–3 hours | Fewer LLM calls | 1-line change in `backend/cache.py` |
| Max tokens: 1400 → 1000 | ~30% output savings | Verify no truncation |
| Chat turns: 6 → 4 | ~30% chat input | `CHAT_HISTORY_MAX_TURNS=4` |
| Switch to Gemini Flash | Cheaper than Haiku | Test narration quality |
