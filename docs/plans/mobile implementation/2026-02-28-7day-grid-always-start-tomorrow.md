# 7-Day Grid: Always Start from Tomorrow

> **Date:** 2026-02-28
> **Status:** Implemented
> **Follows:** `2026-02-28-force-day-top-7day-view.md`

---

## The Problem

The previous fix (`ef6194a`) correctly dropped "Tonight" when the first period in `weekly_timeline` was a night slot, making the grid start from "Tomorrow Day". However, it only handled the case where the broadcast was generated at **nighttime**.

If a broadcast were ever generated during **daytime**, `weekly_timeline[0]` would be "Today Day" (06:00), not "Tonight". The `firstIsNight` check would return `false`, so neither slot would be dropped — "Today Day" would appear in column 1 of the top row, and "Tonight" in column 1 of the bottom row. This breaks the "always start from tomorrow" contract and creates an asymmetric user experience depending on when the broadcast was generated.

Additionally, the padding loop only handled the case where `nightItems` was shorter than `dayItems`. In the daytime-first scenario after dropping both "Today Day" and "Tonight", `dayItems` could end up shorter, leaving the grid misaligned.

---

## Data Confirmed

Inspecting `local_data/history.json`: the CWA F-D0047-071 API always returns **14 periods starting from Tonight** for nightly broadcasts, giving 7 day slots (Tomorrow → Day+7) and 7 night slots (Tonight → Night+6). After dropping Tonight: 7 Day + 6 Night + 1 null placeholder = the correct 7-column grid.

The daytime-first scenario is an edge case but requires guarding for robustness.

---

## Approach

Extend the existing drop logic with an `else if` branch:

- **Nighttime first** (`firstIsNight = true`): drop `nightItems[0]` (Tonight) — unchanged from `ef6194a`
- **Daytime first** (`firstIsNight = false`): drop both `dayItems[0]` (Today Day) AND `nightItems[0]` (Tonight), so the grid still starts cleanly from Tomorrow Day

Add a second symmetrical padding loop to handle `dayItems` being shorter after the daytime drop.

Bump the `weekly_timeline` slice cap from `[:14]` to `[:16]` in `routes.py` to provide a data buffer in case the CWA API returns extra periods when a daytime broadcast is generated.

---

## Implementation Details

### `web/static/app.js`

```js
const firstIsNight = data.weekly_timeline.length > 0 && isNightSlot(data.weekly_timeline[0]);
if (firstIsNight) {
  // Normal case: broadcast generated at night. First slot is "Tonight".
  // Drop it so the top row begins with Tomorrow Day.
  nightItems.shift();
} else if (dayItems.length > 0) {
  // Edge case: broadcast generated during daytime. First slot is "Today Day".
  // Drop both Today Day and Tonight so the grid still starts from Tomorrow.
  dayItems.shift();   // Remove Today Day
  nightItems.shift(); // Remove Tonight (first night item)
}

// Pad whichever array is shorter so both rows have equal column count.
while (nightItems.length < dayItems.length) nightItems.push(null);
while (dayItems.length < nightItems.length) dayItems.push(null);
```

### `web/routes.py`

```python
"weekly_timeline": forecast_7day[:16],  # was [:14]
```

Extra 2-slot buffer ensures a daytime-first dataset can still surface 7 complete future day slots if the API provides them.

---

## Result

| Scenario | Top row | Bottom row |
|---|---|---|
| Nighttime broadcast (common) | Tomorrow → Day+7 (7 real) | Tomorrow Night → Night+6 (6 real) + null |
| Daytime broadcast (edge case) | Tomorrow → Day+6 (6 real) + null | Tomorrow Night → Night+6 (6 real) + null |
| Daytime + `[:16]` cap (if API provides extra period) | Tomorrow → Day+7 (7 real) | Tomorrow Night → Night+6 (6 real) + null |

The grid always reads left-to-right as "tomorrow through the next 7 days" with no current-day bleed-through.
