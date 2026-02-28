# Lifestyle Card Verbosity & Overlap Fix

> **Date:** 2026-02-28
> **Status:** Implemented
> **Commit:** `dade244`

---

## The Problem

Two related issues made the lifestyle cards redundant and noisy:

1. **Wardrobe card mentioned rain gear** — on rainy days, wardrobe text appended "and pack rain gear" / "記得攜帶雨具", duplicating the dedicated rain gear card sitting right next to it. The LLM was also instructed to factor in rain when writing the wardrobe card.

2. **Alert card was hidden when clear** — when nothing was flagged, the fallback produced an empty alert text, causing the card to be invisible entirely. The LLM prompt instructed it to use an empty string. This left the user wondering whether alerts had been checked at all. When the LLM *did* write something for a quiet day, it tended to enumerate absent risks ("no cardiac alert, no weather concerns…") which was verbose and unhelpful.

---

## What Changed

### Wardrobe card — temperature only, no rain

The wardrobe card now covers clothing choice based on apparent temperature. Rain gear belongs on the rain gear card.

- **`narration/fallback_narrator.py`** — Removed the `if rain_recent` blocks that appended rain gear language to wardrobe text in both EN and ZH.
- **`web/routes.py`** — Removed the `if rain:` block in `_wardrobe_tip()` that prepended "Rain gear needed ☔"; also removed the now-unused `rain` parameter from the function signature.
- **`narration/llm_prompt_builder.py`** — Updated the wardrobe card description in both EN and ZH CARDS prompts to explicitly say: *do not mention rain or rain gear — that is covered by the rain_gear card.*

### Alert card — always visible, concise

The alert card now always renders. When nothing is flagged, it shows a brief "All clear today." / "今天一切正常。" rather than disappearing.

- **`narration/fallback_narrator.py`** — Changed the no-alert fallback from `alert_text = ""` to a language-aware short phrase.
- **`narration/llm_prompt_builder.py`** — Updated both EN and ZH alert descriptions: instead of "use empty string if nothing to flag", the LLM is now told to write a single short sentence like "All clear today." and explicitly not to enumerate absent alert types.
- **`web/static/app.js`** — Alert card icon now shows ✅ for INFO-only (all clear), ⚠️ for WARNING, 🚨 for CRITICAL. Previously INFO fell through to ⚠️ which looked alarming on a quiet day.

### Tests

- **`tests/test_fallback_narrator.py`** — Updated `test_no_alert_when_no_heads_ups` to assert `alert["text"] == "All clear today."` instead of `""`. Removed an unused `import json`.

---

## Design Rationale

Each card owns its information. The wardrobe card answers "what do I wear?" — rain gear is a separate concern with its own card. Duplicating the answer wastes space and creates the impression that information might be wrong (which entry do I trust?).

The alert card should always be present so the user can see at a glance that it was checked. A hidden card is ambiguous — was there nothing to flag, or did something go wrong? "All clear today." resolves that ambiguity with one short phrase.
