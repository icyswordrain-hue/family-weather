# Family Weather Dashboard — API & Infrastructure Cost Estimate

*Last updated: 2026-03-15*

## Pipeline Overview

Each pipeline run makes these external calls in sequence:

```
Cloud Scheduler (cron) → Cloud Run → Modal /refresh endpoint
  ├─ CWA API ×6       (free — government open data)
  ├─ MOENV API ×2      (free — government open data)
  ├─ LLM narration ×2  (Claude or Gemini, per provider toggle)
  ├─ Google Cloud TTS ×2   (morning slot only)
  └─ GCS writes ×3-5       (save broadcast, upload audio)
```

**Scheduled runs:** 3×/day (06:15, 11:15, 17:15 CST)

- **Morning:** always runs full pipeline + TTS
- **Midday & Evening:** fetch current obs first, skip full pipeline if conditions haven't changed (temp ±3°C, rain status, dew point ±3°C). On stable-weather days, both skip entirely.

**Realistic daily call volume** (assuming ~50% midday/evening skip rate):

| Service | Morning | Midday (avg) | Evening (avg) | Daily Total |
|---------|---------|-------------|---------------|-------------|
| CWA API | 6 | 3–6 | 3–6 | ~12 |
| MOENV API | 2 | 1–2 | 1–2 | ~4 |
| LLM narration | 2 | 0–2 | 0–2 | ~4 |
| Google Cloud TTS | 2 | 0 | 0 | 2 |
| GCS operations | 5 | 0–5 | 0–5 | ~10 |
| Chat (Haiku 4.5) | user-driven | — | — | ~3 (est.) |

---

## Cost Breakdown (Claude provider — current default)

### 1. Claude API — Narration (dominant cost)

**Model:** `claude-sonnet-4-6` ($3/MTok input, $15/MTok output)
**Per call:** ~1,200 input tokens (650 system + ~550 user/history/weather), ~900 output tokens (narration + metadata JSON)
**Daily:** ~4 calls

| Period | Input tokens | Output tokens | Input cost | Output cost | **Total** |
|--------|-------------|--------------|------------|-------------|-----------|
| Weekly | 33,600 | 25,200 | $0.10 | $0.38 | **$0.48** |
| Monthly | 144,000 | 108,000 | $0.43 | $1.62 | **$2.05** |
| Yearly | 1,752,000 | 1,314,000 | $5.26 | $19.71 | **$24.97** |

### 2. Claude API — Chat (Haiku 4.5)

**Model:** `claude-haiku-4-5-20251001` ($0.80/MTok input, $4/MTok output)
**Per call:** ~700 input tokens, ~150 output tokens, max 300
**Assume:** ~3 chat messages/day

| Period | Cost |
|--------|------|
| Weekly | **$0.02** |
| Monthly | **$0.10** |
| Yearly | **$1.28** |

### 3. Google Cloud TTS (Standard voices)

**Voices:** `en-GB-Standard-C` + `cmn-TW-Standard-A` → **$4/1M characters**
**Per morning:** ~2,500 chars (English ~450 words) + ~800 chars (Chinese) = ~3,300 chars
**Morning only** — midday/evening skip TTS

| Period | Characters | **Cost** |
|--------|-----------|---------|
| Weekly | 23,100 | **$0.09** |
| Monthly | 99,000 | **$0.40** |
| Yearly | 1,204,500 | **$4.82** |

### 4. Modal (serverless compute)

**Container:** Default CPU/memory (no GPU), Python 3.12

- Full pipeline run: ~60–90s (avg 75s)
- Skipped midday/evening: ~10s (condition check only)
- Broadcast reads: <1s each, ~15/day
- Health checks: <0.1s, continuous

Approximate cost at Modal's rates (~$0.000048/vCPU-s + ~$0.000003/GiB-s):

| Period | **Cost** |
|--------|---------|
| Weekly | **$0.06** |
| Monthly | **$0.25** |
| Yearly | **$3.00** |

### 5. Google Cloud Storage

- **Storage:** <10 MB total (history JSON + 30-day audio retention) → ~$0.00
- **Operations:** <1,000 writes + <5,000 reads/month → ~$0.01
- **Egress:** Audio downloads ~60 MB/month → free (same-region)

| Period | **Cost** |
|--------|---------|
| Monthly | **$0.01** |
| Yearly | **$0.12** |

### 6. Cloud Run

Well within free tier (2M requests, 360K vCPU-seconds/month). Actual usage: ~100 requests/day.

| Period | **Cost** |
|--------|---------|
| Monthly | **$0.00** |
| Yearly | **$0.00** |

### 7. Cloud Scheduler

Free tier: 3 jobs. This project uses exactly 3 jobs.

| Period | **Cost** |
|--------|---------|
| Monthly | **$0.00** |

### 8. CWA & MOENV APIs

Government open data — free.

---

## Total Cost Summary (Claude provider)

| Period | Claude Narration | Claude Chat | TTS | Modal | GCS | **Grand Total** |
|--------|-----------------|-------------|-----|-------|-----|----------------|
| **Weekly** | $0.48 | $0.02 | $0.09 | $0.06 | $0.00 | **$0.65** |
| **Monthly** | $2.05 | $0.10 | $0.40 | $0.25 | $0.01 | **$2.81** |
| **Yearly** | $24.97 | $1.28 | $4.82 | $3.00 | $0.12 | **$34.19** |

---

## Available Gemini Models (from API)

Models confirmed available via the project's Gemini API key (**Paid tier 1**, as of 2026-03-15):

### Stable models

| Model ID | Input limit | Output limit | Input $/MTok | Output $/MTok | Notes |
|----------|-----------|-------------|-------------|--------------|-------|
| `gemini-2.5-pro` | 1M | 65K | $1.25 | $10.00 | High quality, supports thinking |
| `gemini-2.5-flash` | 1M | 65K | $0.30 | $2.50 | Good quality/cost, supports thinking |
| `gemini-2.5-flash-lite` | 1M | 65K | $0.10 | $0.40 | Cheapest stable model |
| `gemini-2.0-flash` | 1M | 8K | — | — | Previous gen |
| `gemini-2.0-flash-lite` | 1M | 8K | — | — | Previous gen |

### Preview models (Gemini 3.x)

| Model ID | Input limit | Output limit | Input $/MTok | Output $/MTok | Notes |
|----------|-----------|-------------|-------------|--------------|-------|
| `gemini-3-flash-preview` | 1M | 65K | $0.50 | $3.00 | Sonnet 4.6 quality match |
| `gemini-3.1-flash-lite-preview` | 1M | 65K | $0.25 | $1.50 | Fast + cheap, supports thinking |
| `gemini-3.1-pro-preview` | 1M | 65K | $2.00 | $12.00 | Highest quality |
| `gemini-3-pro-preview` | 1M | 65K | — | — | Previous 3.x gen |

**Note:** This key is on **Paid tier 1** — all requests are billed at the rates above. The "free tier" (500 RPD, no billing) requires a separate project without billing enabled.

---

## Sonnet 4.6 vs Gemini 3 Flash — Comparison

### Why Gemini 3 Flash?

Gemini 3 Flash is the quality-matched Gemini alternative to Sonnet 4.6. It scores 78% on SWE-bench (vs Sonnet's 79.6%), leads on GPQA science reasoning (90.4%), and is 3× faster at 5–6× lower cost.

### Pricing (Paid tier 1)

| | Claude Sonnet 4.6 | Gemini 3 Flash | Gemini 2.5 Flash |
|---|---|---|---|
| **Input** | $3.00/MTok | $0.50/MTok | $0.30/MTok |
| **Output** | $15.00/MTok | $3.00/MTok | $2.50/MTok |
| **vs Sonnet (input)** | 1× | **6× cheaper** | **10× cheaper** |
| **vs Sonnet (output)** | 1× | **5× cheaper** | **6× cheaper** |

### Quality comparison (for narration use case)

| Dimension | Claude Sonnet 4.6 | Gemini 3 Flash |
|-----------|-------------------|----------------|
| **Creative prose quality** | Excellent — nuanced, natural family tone | Strong — comparable quality, slightly different style |
| **Structured JSON output** | Reliable | Reliable |
| **Instruction following** | Strong adherence to v7 prompt format | Strong — matches Sonnet on complex formats |
| **Multilingual (zh-TW/en)** | High quality in both | Good; may need prompt tuning for zh-TW |
| **SWE-bench (coding)** | 79.6% | 78% |
| **GPQA (science)** | — | 90.4% |
| **Speed** | ~5–15s per call | ~2–5s per call (3× faster) |

### Model mapping (mirrors Claude primary/fallback pattern)

```
Claude:  Sonnet 4.6            → Haiku 4.5           (quality → cheap)
Gemini:  3 Flash (preview)     → 2.5 Flash           (quality → cheap)
```

### Monthly cost comparison (narration only, ~4 calls/day, Paid tier 1)

| Provider & Model | Input cost | Output cost | **Monthly total** | vs Sonnet |
|-----------------|-----------|------------|-----------------|-----------|
| **Claude Sonnet 4.6** (current) | $0.43 | $1.62 | **$2.05** | — |
| **Gemini 3 Flash** (preview) | $0.07 | $0.32 | **$0.39** | −$1.66 |
| Gemini 2.5 Flash | $0.04 | $0.27 | **$0.31** | −$1.74 |
| Gemini 2.5 Flash-Lite | $0.01 | $0.04 | **$0.05** | −$2.00 |
| **Claude Haiku 4.5** | $0.12 | $0.43 | **$0.55** | −$1.50 |

### Grand total with each provider (annual)

| Scenario | Narration | Chat | TTS | Modal | GCS | **Grand Total/yr** |
|----------|----------|------|-----|-------|-----|--------------------|
| **Current** (Sonnet 4.6) | $24.97 | $1.28 | $4.82 | $3.00 | $0.12 | **$34.19** |
| **Gemini 3 Flash** | $4.75 | $1.28 | $4.82 | $3.00 | $0.12 | **$13.97** |
| Gemini 2.5 Flash | $3.77 | $1.28 | $4.82 | $3.00 | $0.12 | **$12.99** |
| **Claude Haiku 4.5** | $6.60 | $1.28 | $4.82 | $3.00 | $0.12 | **$15.82** |

### Implementation

Provider is selectable via the settings toggle in the player sheet UI. The backend reads the `provider` parameter from the refresh request body.

Default model mapping (overridable via env vars):

```bash
# Claude (default)
CLAUDE_MODEL=claude-sonnet-4-6              # primary
CLAUDE_FALLBACK_MODEL=claude-haiku-4-5-20251001  # fallback

# Gemini
GEMINI_PRO_MODEL=gemini-3-flash-preview     # primary
GEMINI_FLASH_MODEL=gemini-2.5-flash         # fallback
```

### Why not consolidate Claude and Gemini clients?

The two clients (`narration/claude_client.py`, `narration/gemini_client.py`) use fundamentally different SDKs (`anthropic` vs `google.genai`) with incompatible message formats, response parsing, and client lifecycle patterns. Merging them would create a leaky abstraction. The current structure — separate files with the same `generate_narration()` signature, orchestrated by `backend/pipeline.py` — is the right level of abstraction.

**API key gotcha:** Both clients must read their API key from `os.environ` at call time (not module import time) because Modal injects secrets after module import. Claude does this via `_get_client()` (lazy singleton); Gemini does it inline at each `genai.Client()` creation.

---

## Other Minor Savings (not worth the complexity)

- **Edge TTS instead of Google Cloud TTS:** Saves $0.40/month, but Edge TTS is blocked from Modal datacenter IPs — would require architectural changes.
- **Reduce to 2 scheduled runs/day:** Saves ~$0.30/month but loses midday weather updates.
- **Skip narration reuse more aggressively:** Already implemented via the conditions-unchanged check.
