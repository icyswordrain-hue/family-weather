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

## Significant Cost-Saving Opportunity

### Switch narration to Gemini 2.5 Flash (saves ~$24/year — 73% of total)

The code already supports `NARRATION_PROVIDER=GEMINI` with `gemini-2.5-flash` as the fallback model. Gemini 2.5 Flash has a **free tier of 500 requests/day** — the ~4 calls/day is well under that limit.

| Scenario | Monthly narration cost | Monthly total | Annual total |
|----------|----------------------|---------------|-------------|
| **Current** (Sonnet 4.6) | $2.05 | $2.81 | $34.19 |
| **Gemini 2.5 Flash** (free tier) | $0.00 | $0.76 | $9.22 |
| **Gemini 2.5 Flash** (paid) | $0.07 | $0.83 | $9.96 |
| **Claude Haiku 4.5** | $0.44 | $1.20 | $14.41 |

Even beyond the free tier, Flash pricing ($0.15/MTok input, $0.60/MTok output) is **20× cheaper on input and 25× cheaper on output** than Sonnet 4.6.

**Trade-off:** Narration quality. Sonnet produces more nuanced, natural-sounding family weather briefings. Flash is faster but may be more formulaic. A/B testable by setting `NARRATION_PROVIDER=GEMINI` for a week.

### Other minor savings (not worth the complexity)
- **Edge TTS instead of Google Cloud TTS:** Saves $0.40/month, but Edge TTS is blocked from Modal datacenter IPs — would require architectural changes.
- **Reduce to 2 scheduled runs/day:** Saves ~$0.30/month but loses midday weather updates.
- **Skip narration reuse more aggressively:** Already implemented via the conditions-unchanged check.
