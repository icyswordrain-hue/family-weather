# Scale Colour Audit — Changelog

**Date:** 2026-03-04  
**Scope:** `data/scales.py`, `web/static/app.js`, `tests/test_scales.py`

---

## What changed

### 1. AQI — compressed to 3-stop (1 / 3 / 5)

Old 5-level mapping was too granular for a glanceable gauge. Replaced with a clear **Good / Moderate / Danger** signal.

| AQI | Level | Colour |
|---|---|---|
| < 60 | 1 | 🟢 Green |
| 60–119 | 3 | 🟡 Yellow |
| ≥ 120 | 5 | 🔴 Red |

- `_aqi_to_level()` in `scales.py` — new thresholds, `< 60` / `< 120`
- `aqiToLevel()` in `app.js` — mirrored; `isNaN` fallback corrected from `1` → `0` (unknown → grey, not falsely green)
- 6 AQI tests updated to pin boundary edges (59, 60, 119, 120)

---

### 2. UV — redesigned to 4-level with action-oriented labels

Old scale had 5 abstract levels (`Low / Moderate / High / Very High / Extreme`). Levels 3 and 4 triggered identical advice. Replaced with 4 action-oriented levels using CSS slots **1 / 2 / 4 / 5** (skipping yellow to preserve a clear visual jump between sunscreen and shade zones).

| UV Index | Level | Label | Action |
|---|---|---|---|
| ≤ 3 | 1 | Safe | No action |
| 4–7 | 2 | Wear Sunscreen | SPF required |
| 8–10 | 4 | Seek Shade | Limit exposure |
| ≥ 11 | 5 | Extreme | Avoid outdoors |

- `UV_SCALE` in `scales.py` — 4-entry table
- zh-TW translations added to `app.js` metrics map: `Safe → 安全`, `Wear Sunscreen → 需擦防曬`, `Seek Shade → 請避曬`
- 7 UV tests replaced; each boundary edge (3/4, 7/8, 10/11) pinned

---

## What was NOT changed

- Wind, pressure, humidity (dew-gap), visibility scales — all kept at 5 levels (each step has distinct actionable meaning)
- Precip scale (`PRECIP_SCALE_5`) — see `docs/plans/2026-03-04-poisson-safe-outing.md` for planned replacement
- Frontend gauge wiring — gauges consume `level` fields emitted by backend; no JS logic changes beyond `aqiToLevel()` sync fix
