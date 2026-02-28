# LLM Prompt — Fluff Reduction & Word Budget Enforcement

**Date:** 2026-02-28
**Status:** Implemented

## Problem

The English broadcast was running ~520 words despite the system prompt saying "300–500 words." Several style rules actively encouraged extra sentences:

- **"One-sentence takeaway"** — instructed the LLM to append a closing sentence to any paragraph already 3+ sentences long, compounding length on the paragraphs that were already longest.
- **P5 "narrate as a story"** — caused the forecast paragraph to enumerate every 6-hour window (~133 words), the single biggest offender.
- **P6 "1-3 sentences"** — gave too much latitude; accuracy verdicts consistently ran to ~59 words.
- **No per-paragraph sentence cap** — word-count targets in isolation are easy for LLMs to ignore.

## Changes

**File:** `narration/llm_prompt_builder.py`

### RULES — word target tightened

```
Before: Total length: 300–500 words. Concise, conversational, no verbal filler.
After:  Total length: 320–350 words. Tight and direct. Every sentence must carry information.
```

### STYLE — three rule changes

| Before | After |
|---|---|
| `One-sentence takeaway: End paragraphs longer than three sentences with a punchy closing line.` | Removed |
| *(no cap)* | `Hard limit: Every paragraph must be 4 sentences or fewer.` |
| *(no wind-up rule)* | `No wind-ups: Never open a paragraph with atmosphere-setting sentences. The first word of each paragraph should be a fact or action.` |

### P5 — Forecast paragraph tightened

```
Before: A one-sentence narrative frame ("tale of two halves") followed by a sensory baseline.
        Narrate the next 24 hours as a story. Focus on transitions; keep stable stretches brief.
        Close with a bottom-line takeaway.

After:  One opening sentence naming the overall pattern. Cover only the 1–2 key transitions —
        skip stable stretches entirely. Close with one bottom-line sentence. Maximum 5 sentences total.
```

### P6 — Accuracy paragraph tightened

```
Before: Compare yesterday's P5 to today's actuals. Verdict: spot on, close, or missed. 1-3 sentences.
After:  One sentence: verdict (spot on / close / off) plus the single biggest difference or confirmation.
        Maximum 2 sentences.
```

### ZH prompt — calibrated separately

Chinese characters are ~1.5–2× more information-dense than English words and Mandarin TTS speaks faster in chars/min. A naïve 320–350 字 target would produce ~1.5 min audio vs ~2.2 min for the EN equivalent.

```
Before: 總長度：300–500 字
After:  總長度：420–460 字
```

All other style changes (4-sentence hard limit, no wind-ups, P5/P6 tightening) are mirrored in the ZH prompt.

## Expected Outcome

| | Before | After |
|---|---|---|
| EN word count | ~520 words | ~320–350 words |
| EN raw audio | ~3.5 min | ~2.2–2.4 min |
| ZH character count | ~500+ 字 | ~420–460 字 |
| P5 forecast | ~133 words | ~70–80 words |
| P6 accuracy | ~59 words | ~30–35 words |

## What is NOT changed

- 6-paragraph structure (P1–P6) preserved
- All weather intelligence: health alerts, commute, Dad outdoor, meals, climate control, forecast, accuracy
- METADATA / CARDS / REGEN separators and parsing — untouched
- Sensation-first, life-anchored time, pinyin style rules — kept
