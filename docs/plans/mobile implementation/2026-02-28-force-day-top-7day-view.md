# 7-Day Forecast Layout Restructure

> **Date:** 2026-02-28
> **Status:** Implemented
> **Commits:** `ef6194a`, `cfea7c8`

---

## The Problem

The 7-Day forecast in `app.js` was rendering Day and Night slots strictly based on whatever segment came back first from the CWA API. If the API was queried at night time, the "Tonight" (Night) slot would arrive first. Because the UI was naively appending cards to a CSS grid based on first-in, first-out sequence, the top row of the 7-day grid would become "Night" cards, while the bottom row would become "Day" cards.

This made the grid harder to parse, as users expect "Daytime" logic (sun icons, higher temperatures) to occupy the primary visual tier (the top row).

---

## Approach & Decision

To correctly force Daytime into the top row:

1. **Option A (Chosen): Drop "Tonight" and Pad End.** When the first slot is a Night slot, we discard it from the 7-day view entirely (as "Tonight" is already well-represented in the immediately preceding 24-hour timeline). This allows the 7-day grid to snap to "Tomorrow Day" as the first top-left item. To maintain the 14-item CSS grid shape, a dashed placeholder `div` is appended to the bottom-right (Day 7 Night).
2. **Option B (Discarded): Pad Front.** Padding the top-left index with a placeholder (representing the past "Today Daytime") successfully pushes "Tonight" to the bottom row, but it wastes valuable screen real-estate at the start of the user's reading flow with a crossed-out/hollow box.

## Implementation Details

### `web/static/app.js` 
Modified `renderOverviewView()` logic to filter the `data.weekly_timeline` array:

```js
const firstIsNight = data.weekly_timeline.length > 0 && isNightSlot(data.weekly_timeline[0]);
if (firstIsNight) {
  nightItems.shift(); // Drop "Tonight"
}

// Balance array lengths so dayItems dictates column count
while (nightItems.length < dayItems.length) {
  nightItems.push(null); // Add missing placeholder to the end of nightItems
}
```

The rendering loop was updated to check for `null` and return a `.wk-placeholder` card element containing an em-dash `"—"`.

**Chart.js Sparkline Synchronization:**
The temperature sparkline was originally reading directly off the `data.weekly_timeline` array, which meant it was drawing the dropped "Tonight" node out-of-sync with the DOM cards beneath it. It was rewritten to build its data arrays directly off the `dayItems[i]` and `nightItems[i]` DOM loop, yielding a perfectly aligned Chart rendering with a `spanGap` jumping over the missing Day 7 Night dot.

### `web/static/style.css`
A new `.wk-placeholder` class was appended with reduced opacity and a dashed border.

```css
.wk-placeholder {
  background: var(--surface);
  border-radius: 10px;
  padding: 8px 6px;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  min-height: 0;
  border: 1px dashed var(--muted);
  opacity: 0.5;
}
```

Cache buster `?v=18` was deployed across templates to flush browser layouts.
