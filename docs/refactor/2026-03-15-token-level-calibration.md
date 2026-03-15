# Token Level Calibration — Narration Max Tokens

**Date:** 2026-03-15
**Status:** Applied

## Problem

Narrations were getting truncated, especially during regen cycles. The `max_tokens` settings (1600 normal, 2000 regen for both providers) were set by estimation rather than empirical measurement.

## Test Methodology

Created `dev-tools/test_token_levels.py` — a diagnostic script that:
1. Fetches live weather data and builds a real zh-TW prompt (normal + regen)
2. Calls both Claude (claude-sonnet-4-6) and Gemini (gemini-3-flash-preview) at 3 token levels: **1600, 2200, 2800**
3. No thinking tokens for either provider
4. Reports: stop reason, tokens used, metadata validity, regen presence, narration char count

Total: 12 API calls (2 providers × 3 levels × 2 modes).

## Test Results

### Normal (no regen)

```
Provider   Mode    MaxTok   Used Stop              Meta Regen Chars   Time
claude     normal    1600   1375 end_turn            Y     -   540  30.2s
claude     normal    2200   1380 end_turn            Y     -   561  31.4s
claude     normal    2800   1452 end_turn            Y     -   587  32.1s
gemini     normal    1600    861 FINISHREASON.STOP   Y     -   529   7.6s
gemini     normal    2200    820 FINISHREASON.STOP   Y     -   485   6.5s
gemini     normal    2800    851 FINISHREASON.STOP   Y     -   504   7.3s
```

### Regen (regenerate_meal_lists=True)

```
Provider   Mode    MaxTok   Used Stop              Meta Regen Chars   Time
claude     regen     1600   1600 max_tokens          Y     Y   571  35.0s
claude     regen     2200   2200 max_tokens          Y     Y   547  50.5s
claude     regen     2800   2800 max_tokens          Y     Y   576  60.4s
gemini     regen     1600   1531 FINISHREASON.STOP   Y     Y   516  11.7s
gemini     regen     2200   1567 FINISHREASON.STOP   Y     Y   591  11.5s
gemini     regen     2800   1578 FINISHREASON.STOP   Y     Y   512  11.7s
```

## Key Findings

1. **Gemini normal** peaks at ~861 tokens — well under 1600. The previous 1600 was ~86% wasted headroom.
2. **Claude normal** peaks at ~1452 tokens — fits in 1600 with ~10% headroom.
3. **Claude regen fills any budget given** — it hit max_tokens at 1600, 2200, AND 2800. It generates more meal/location entries to fill the available space. The `---METADATA---` block always completes first (parseable), but the `---REGEN---` JSON gets truncated.
4. **Gemini regen** completes cleanly at ~1531–1578 tokens, even at 1600 cap.

## Config Changes (config.py)

| Setting                  | Before | After  | Rationale                                        |
|--------------------------|--------|--------|--------------------------------------------------|
| `GEMINI_MAX_TOKENS`      | 1600   | **1100** | Peak 861, ~28% headroom                         |
| `GEMINI_MAX_TOKENS_REGEN`| 2000   | 2000   | No change — peak 1578 fits                       |
| `CLAUDE_MAX_TOKENS`      | 1600   | 1600   | No change — peak 1452 fits with ~10% headroom    |
| `CLAUDE_MAX_TOKENS_REGEN`| 2000   | **4096** | Claude fills any budget; needs generous cap for complete regen JSON |
