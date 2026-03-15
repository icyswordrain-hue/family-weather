# Family Weather Dashboard — API & Infrastructure Cost Estimate

*Last updated: 2026-03-15*

## Pipeline Overview

Each pipeline run makes these external calls in sequence:

```
Cloud Scheduler (cron) → Cloud Run → Modal /refresh endpoint
  ├─ CWA API ×6       (free — government open data)
  ├─ MOENV API ×2      (free — government open data)
  ├─ Claude Sonnet 4.6 ×2  (narration: zh-TW + en)
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
| Claude Sonnet 4.6 | 2 | 0–2 | 0–2 | ~4 |
| Google Cloud TTS | 2 | 0 | 0 | 2 |
| GCS operations | 5 | 0–5 | 0–5 | ~10 |
| Chat (Haiku 4.5) | user-driven | — | — | ~3 (est.) |

---

## Cost Breakdown

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

## Total Cost Summary

| Period | Claude Narration | Claude Chat | TTS | Modal | GCS | **Grand Total** |
|--------|-----------------|-------------|-----|-------|-----|----------------|
| **Weekly** | $0.48 | $0.02 | $0.09 | $0.06 | $0.00 | **$0.65** |
| **Monthly** | $2.05 | $0.10 | $0.40 | $0.25 | $0.01 | **$2.81** |
| **Yearly** | $24.97 | $1.28 | $4.82 | $3.00 | $0.12 | **$34.19** |

---

## Available Gemini Models (from API)

Models confirmed available via the project's Gemini API key (as of 2026-03-15):

| Model ID | Input limit | Output limit | Notes |
|----------|-----------|-------------|-------|
| `gemini-2.5-pro` | 1M | 65K | Highest quality, expensive |
| `gemini-2.5-flash` | 1M | 65K | Best quality/cost ratio, supports thinking budgets |
| `gemini-2.5-flash-lite` | 1M | 65K | Cheapest, no thinking |
| `gemini-2.0-flash` | 1M | 8K | Previous gen, no thinking |
| `gemini-2.0-flash-lite` | 1M | 8K | Previous gen budget option |

All models have a **free tier of 500 RPD** (requests per day). This project uses ~4 calls/day — well within the free tier for any model.

---

## Sonnet 4.6 vs Gemini 2.5 Flash (Thinking Low) — Comparison

### Pricing (paid tier)

| | Claude Sonnet 4.6 | Gemini 2.5 Flash | Gemini 2.5 Flash-Lite |
|---|---|---|---|
| **Input** | $3.00/MTok | $0.30/MTok | $0.10/MTok |
| **Output** (incl. thinking) | $15.00/MTok | $2.50/MTok | $0.40/MTok |
| **Input multiplier vs Sonnet** | 1× | **10× cheaper** | **30× cheaper** |
| **Output multiplier vs Sonnet** | 1× | **6× cheaper** | **37× cheaper** |
| **Free tier** | None | 500 RPD | 500 RPD |

### Thinking budget impact

Gemini 2.5 Flash supports adjustable thinking budgets (0–24,576 tokens). Thinking tokens are billed as output tokens at $2.50/MTok.

| Thinking budget | Est. thinking tokens/call | Added output cost/call | Effect on narration |
|----------------|--------------------------|----------------------|-------------------|
| **Off** (0) | 0 | $0.000 | Fastest, no internal reasoning |
| **Low** (~1,024) | ~500–1,024 | ~$0.003 | Slight structure improvement |
| **Medium** (~8,192) | ~2,000–4,000 | ~$0.010 | Better metadata JSON accuracy |
| **High** (~24,576) | ~4,000–8,000 | ~$0.020 | Overkill for creative writing |

For the narration task (creative prose + structured metadata JSON), **thinking "low" or "off"** is sufficient. The task doesn't require deep reasoning — it's mostly creative writing with a structured output format.

### Quality comparison (for narration use case)

| Dimension | Claude Sonnet 4.6 | Gemini 2.5 Flash (thinking low) |
|-----------|-------------------|--------------------------------|
| **Creative prose quality** | Excellent — nuanced, varied phrasing, natural family tone | Good — competent but may be more formulaic |
| **Structured JSON output** | Reliable metadata extraction | Reliable with thinking; may need prompt tuning without |
| **Instruction following** | Strong adherence to v7 prompt format | Strong; thinking budget helps with complex format |
| **Multilingual (zh-TW/en)** | High quality in both languages | Good; Mandarin may need prompt adjustment |
| **Coding benchmarks** | 79.6% SWE-bench | 78% SWE-bench (comparable) |
| **Speed** | ~5–15s per call | ~2–5s per call (faster) |
| **Consistency** | Very consistent output format | Slightly more variable without thinking |

**Bottom line:** For structured weather narration, Gemini 2.5 Flash with thinking "low" produces adequate quality at a fraction of the cost. The main trade-off is in prose style — Sonnet's narration reads more naturally as a "family weather briefing." This is subjective and best evaluated by A/B testing.

### Monthly cost comparison (narration only, ~4 calls/day)

| Provider & Model | Input cost | Output cost | **Monthly total** | vs Current |
|-----------------|-----------|------------|-----------------|-----------|
| **Claude Sonnet 4.6** (current) | $0.43 | $1.62 | **$2.05** | — |
| **Gemini 2.5 Flash** (free tier) | $0.00 | $0.00 | **$0.00** | −$2.05 |
| Gemini 2.5 Flash (paid, thinking off) | $0.04 | $0.27 | **$0.31** | −$1.74 |
| Gemini 2.5 Flash (paid, thinking low) | $0.04 | $0.39 | **$0.43** | −$1.62 |
| **Gemini 2.5 Flash-Lite** (free tier) | $0.00 | $0.00 | **$0.00** | −$2.05 |
| Gemini 2.5 Flash-Lite (paid) | $0.01 | $0.04 | **$0.05** | −$2.00 |
| **Claude Haiku 4.5** | $0.12 | $0.43 | **$0.55** | −$1.50 |

### Grand total with each provider

| Scenario | Narration | Chat | TTS | Modal | GCS | **Grand Total/yr** |
|----------|----------|------|-----|-------|-----|--------------------|
| **Current** (Sonnet 4.6) | $24.97 | $1.28 | $4.82 | $3.00 | $0.12 | **$34.19** |
| **Gemini 2.5 Flash** (free tier) | $0.00 | $1.28 | $4.82 | $3.00 | $0.12 | **$9.22** |
| Gemini Flash (paid, thinking low) | $5.16 | $1.28 | $4.82 | $3.00 | $0.12 | **$14.38** |
| **Gemini Flash-Lite** (free tier) | $0.00 | $1.28 | $4.82 | $3.00 | $0.12 | **$9.22** |
| **Claude Haiku 4.5** | $6.60 | $1.28 | $4.82 | $3.00 | $0.12 | **$15.82** |

### Implementation

The code already supports switching via a single env var:
```
NARRATION_PROVIDER=GEMINI
GEMINI_PRO_MODEL=gemini-2.5-flash      # primary (replaces gemini-2.5-pro)
GEMINI_FLASH_MODEL=gemini-2.5-flash-lite  # fallback
```

To enable thinking budget, `gemini_client.py` would need a small code change to pass `thinking_config` in `GenerateContentConfig`. Currently not wired up.

---

## Other Minor Savings (not worth the complexity)
- **Edge TTS instead of Google Cloud TTS:** Saves $0.40/month, but Edge TTS is blocked from Modal datacenter IPs — would require architectural changes.
- **Reduce to 2 scheduled runs/day:** Saves ~$0.30/month but loses midday weather updates.
- **Skip narration reuse more aggressively:** Already implemented via the conditions-unchanged check.
