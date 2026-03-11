# Overnight Icons Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Generate clear evening/overnight weather assets and dynamically link them in the frontend so "sunny" doesn't appear at night.

**Architecture:** 
The application currently uses a static `ICONS` mapping which does not account for time-of-day variations (e.g., showing a sun icon at 3 AM). 
1. We will use the Nano Banana Pro image generation tool to create two new icons: `clear-night.png` and `partly-cloudy-night.png`. (We will save them as png/webp similar to existing icons in `web/static/brand-icons/`).
2. We will update `web/static/app.js` to replace direct `ICONS[key]` lookups with a dynamic helper `getWeatherIcon(key, alt, isNight)`. This helper will return the night-specific icon if `isNight` is true and the condition is clear or partly cloudy.

**Tech Stack:** JavaScript, Nano Banana Pro (Image Generation)

---

### Task 1: Generate Night Assets

**Files:**
- Create: `web/static/brand-icons/clear-night.png`
- Create: `web/static/brand-icons/partly-cloudy-night.png`

**Step 1: Generate clear night icon**
Use the `nano-banana-pro` image generation skill or generation tool to create a clear night sky icon (e.g., a stylized crescent moon with stars) that matches the existing 3D/glassmorphic brand style.

**Step 2: Generate partly cloudy night icon**
Generate a partly cloudy night icon (e.g., a crescent moon partially obscured by a soft cloud). 

### Task 2: Modify Frontend Icon Logic

**Files:**
- Modify: `web/static/app.js`

**Step 1: Update the Icon Lookup Logic**
In `app.js`, add a helper function after the `ICONS` definition:

```javascript
function getWeatherIcon(weatherKey, alt, isNight) {
  if (isNight) {
    if (['sunny', 'Sunny/Clear', '1', 'Sunny'].includes(weatherKey)) {
      return `<img src="/static/brand-icons/clear-night.png" class="brand-icon" alt="${alt}" />`;
    }
    if (['partly-cloudy', 'Mixed Clouds', '2', '3'].includes(weatherKey)) {
      return `<img src="/static/brand-icons/partly-cloudy-night.png" class="brand-icon" alt="${alt}" />`;
    }
  }
  return ICONS[weatherKey] || IMG('cloudy', 'Cloudy');
}
```

**Step 2: Apply to renderCurrentView**

Modify the current view icon mapping to determine if it is currently night time.

```javascript
  const h = new Date().getHours();
  const isCurrentNight = (h >= 18 || h < 6);
  document.getElementById('cur-icon').innerHTML = getWeatherIcon(data.weather_code || data.weather_text, localiseWeatherText(data.weather_text || '\u2014'), isCurrentNight);
```

**Step 3: Apply to renderOverviewView Contexts**

In `app.js` `renderOverviewView`, modify the `iconEl.innerHTML` rendering in the timeline:
```javascript
      iconEl.innerHTML = getWeatherIcon(seg.cloud_cover || seg.Wx, 'Weather', isNight);
```

And in the 7-day timeline `isNightSlot`, modify the night icon rendering:
```javascript
      const nightIconEl = document.createElement('div');
      nightIconEl.className = 'wk-icon';
      nightIconEl.innerHTML = nightItem
        ? getWeatherIcon(nightItem.cloud_cover || nightItem.Wx, 'Weather', true)
        : IMG('cloudy', 'Cloudy');
```

**Step 4: Verify UI**
Launch the local server (`.\run_local.ps1`) and observe the current forecast dashboard. Verify that nighttime slots in the timeline showcase the newly generated icons.

**Step 5: Commit**
```bash
git add web/static/brand-icons/clear-night.png web/static/brand-icons/partly-cloudy-night.png web/static/app.js
git commit -m "feat: add night weather icons for evening/overnight slots"
```
