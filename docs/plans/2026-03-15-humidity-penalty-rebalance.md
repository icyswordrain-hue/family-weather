# Humidity Penalty Rebalance for Taiwan Climate

## Context

The outdoor scoring system penalized humidity identically regardless of
temperature. For Taiwan residents acclimatized to subtropical conditions:

- **Hot + humid was over-penalized** — The BOM apparent temperature formula
  already inflates AT significantly in humid heat (e.g., 33°C at 80% RH →
  ~38°C AT), then the quadratic comfort penalty and dew_gap penalty stacked
  on top. Typical summer afternoons scored "Stay in" — unreasonable for
  conditions locals navigate daily.

- **Cold + humid was under-penalized** — Taiwan's winter cold (10-16°C) with
  85-95% RH creates penetrating dampness that feels worse than dry cold, but
  the BOM formula's vapor pressure term can actually *raise* AT in cool
  conditions, and the fixed dew_gap penalty didn't scale with cold.

## Changes

### Asymmetric AT comfort curve (`data/outdoor_scoring.py`)

Replaced the symmetric quadratic divisor (2.5) with direction-dependent values:

- **Hot side:** divisor **3.0** — gentler penalty for heat above 22°C
- **Cold side:** divisor **2.0** — steeper penalty for cold below 22°C

| AT   | Old penalty | New penalty |
|------|-------------|-------------|
| 36°C | -75 (cap)   | -65         |
| 32°C | -40         | -33         |
| 27°C | -10         | -8          |
| 22°C | 0           | 0           |
| 17°C | -10         | -12         |
| 12°C | -40         | -50         |
| 8°C  | -75 (cap)   | -75 (cap)   |

### Hot-side dew_gap reduction (`data/outdoor_scoring.py`)

When AT ≥ 28°C, dew_gap penalties (`dew_gap_clammy`, `dew_gap_humid`) are
halved via integer division. This avoids double-counting humidity discomfort
that the BOM AT formula already captures on the hot side.

No cold-side dew_gap amplifier — the steeper cold-side AT curve already
handles that.
