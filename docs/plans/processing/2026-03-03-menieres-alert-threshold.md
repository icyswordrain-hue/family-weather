# Ménière's Alert Threshold — 2026-03-03

## Problem

`_detect_menieres_alert` was setting `triggered=True` for three conditions:
- Static low pressure (PRES < 1005 hPa) — **moderate** severity
- High humidity (RH > 85%) — **moderate** severity
- Rapid pressure change (|Δ| > 8 hPa) — **high** severity

The LLM receives the full `processed_data` JSON including `menieres_alert`. With
`triggered: true` present even for moderate conditions, the model would mention
Ménière's in P1 and rate the alert card `WARNING` or `CRITICAL`. This caused
false positives on many days with normal, stable (but slightly low) pressure.

`_compute_heads_ups` already correctly gated on `severity == "high"`, but the LLM
path bypassed that gate entirely.

## Change

### `data/health_alerts.py` — `_detect_menieres_alert`

- Static low pressure and high humidity: `triggered` stays `False`, severity and
  reasons are still recorded for observability.
- Rapid pressure change (±>8 hPa, rise or drop): `triggered = True`,
  `severity = "high"` — unchanged, this is the only true alert trigger.
- `_compute_heads_ups` guard simplified: the redundant `severity == "high"` check
  removed since `triggered` is now itself the high-severity gate.

### `narration/fallback_narrator.py` — `_build_fallback_metadata`

- `menieres_triggered` now checks `menieres.get("triggered")` directly instead of
  `severity in ("high", "moderate")`. Aligns history metadata with the new
  contract: only rapid pressure changes are recorded as a Ménière's alert event.

## Result

| Condition | Before | After |
|---|---|---|
| PRES < 1005 hPa (stable) | `triggered=True, severity=moderate` | `triggered=False, severity=moderate` |
| RH > 85% | `triggered=True, severity=moderate` | `triggered=False, severity=moderate` |
| Rapid ±8 hPa change | `triggered=True, severity=high` | unchanged |
| LLM sees `triggered:true` | moderate + high | high only |
| Flash alert generated | moderate + high | high only |
| History `menieres_alert:true` | moderate + high | high only |
