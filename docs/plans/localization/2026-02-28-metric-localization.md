# Metric Localization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Localize the common English metric levels (Humidity, Wind, UV, AQI, Precipitation, etc.) output by the backend into traditional Chinese on the frontend.

**Architecture:** The CWA API and MOENV API both return raw numerical values or native text. The `data/scales.py` backend module categorizes these numbers into English qualitative labels (e.g., "Comfortable", "Gentle breeze", "Likely"). Because the global cache stores data in this intermediate English format, localization must happen in the frontend view layer (`app.js`), similar to how `localiseWeatherText()` works.

**Tech Stack:** JavaScript (Vanilla)

---

### Task 1: Add Metric Translation Dictionary

**Files:**
- Modify: `c:\Users\User\.gemini\antigravity\scratch\family-weather\web\static\app.js`

**Step 1: Add `metrics` object to `TRANSLATIONS['zh-TW']`**

Inside `TRANSLATIONS['zh-TW']` (around line 176), add a comprehensive `metrics` mapping for the outputs of `data/scales.py`:

```javascript
    // Inside TRANSLATIONS['zh-TW']
    metrics: {
      // Humidity
      'Very Dry': '極度乾燥', 'Dry': '乾燥', 'Comfortable': '舒適', 'Muggy': '悶熱', 'Humid': '潮濕', 'Very Humid': '極度潮濕', 'Oppressive': '令人窒息',
      // Wind (Beaufort)
      'Calm': '無風', 'Light air': '軟風', 'Light breeze': '輕風', 'Gentle breeze': '微風', 'Moderate breeze': '和風', 'Fresh breeze': '清風', 'Strong breeze': '強風', 'Near gale': '疾風', 'Gale': '大風', 'Strong gale': '烈風', 'Storm': '狂風', 'Violent storm': '暴風', 'Hurricane force': '颶風',
      // AQI
      'Good': '良好', 'Moderate': '普通', 'Unhealthy for Sensitive Groups': '對敏感族群不健康', 'Unhealthy': '不健康', 'Very Unhealthy': '非常不健康', 'Hazardous': '危害',
      // Shared / UV / Pressure
      'Low': '低', 'High': '高', 'Very High': '極高', 'Extreme': '極端',
      'Unsettled': '不穩定', 'Normal': '正常', 'Stable': '穩定',
      // Visibility
      'Very Poor': '極差', 'Poor': '差', 'Fair': '尚可', 'Excellent': '極佳',
      // Precipitation
      'Very Unlikely': '極不可能', 'Unlikely': '不太可能', 'Possible': '有可能', 'Likely': '很有可能', 'Very Likely': '極有可能', 'Unknown': '未知'
    },
```

*(Note: We don't need to add this to `en` since we can just fall back to the raw English string).*

**Step 2: Add `localiseMetric` helper function**

Around line 108 (near `localiseLocation` and `localiseWeatherText`), add:

```javascript
function localiseMetric(text) {
  if (!text) return '';
  return (T.metrics && T.metrics[text]) ? T.metrics[text] : text;
}
```

**Step 3: Commit**

```bash
git add web/static/app.js
git commit -m "feat(i18n): add metric translation dictionary and helper"
```

---

### Task 2: Apply `localiseMetric` to the Current View (Gauges)

**Files:**
- Modify: `c:\Users\User\.gemini\antigravity\scratch\family-weather\web\static\app.js`

**Step 1: Update gauge text assignments in `renderCurrentView`**

Inside `renderCurrentView(current)`, wrap the text assignments using `localiseMetric`:

```javascript
// Look for these lines and update them (around line 348):
document.getElementById('hum-text').textContent = localiseMetric(current.hum.text);
document.getElementById('wind-text').textContent = localiseMetric(current.wind.text);
document.getElementById('aqi-text').textContent = localiseMetric(current.aqi.text);
document.getElementById('vis-text').textContent = localiseMetric(current.vis.text);
document.getElementById('uv-text').textContent = localiseMetric(current.uv.text);
document.getElementById('pres-text').textContent = localiseMetric(current.pres.text);
```

**Step 2: Dry Run or Check via Browser**

- Verify that when `lang=zh-TW`, gauges show text like "舒適" instead of "Comfortable".
- Verify that when `lang=en`, gauges fall back to "Comfortable".

**Step 3: Commit**

```bash
git add web/static/app.js
git commit -m "fix(i18n): apply localiseMetric to current view gauges"
```

---

### Task 3: Apply `localiseMetric` to the Overview View (Timelines)

**Files:**
- Modify: `c:\Users\User\.gemini\antigravity\scratch\family-weather\web\static\app.js`

**Step 1: Update precipitation text in `renderOverviewView`**

Inside `renderOverviewView(data)` (around line 433 and 459), wrap the `precip_text` outputs.

For the 24-hour timeline (`#timeline-grid`):
```javascript
// Change:
// <div class="val precip-val lv${item.precip_level}">${item.precip_text}</div>
// To:
<div class="val precip-val lv${item.precip_level}">${localiseMetric(item.precip_text)}</div>
```

For the 7-day timeline (`#weekly-grid`):
```javascript
// Change:
// <div class="val precip-val lv${item.precip_level}">${item.precip_text}</div>
// To:
<div class="val precip-val lv${item.precip_level}">${localiseMetric(item.precip_text)}</div>
```

**Step 2: Commit**

```bash
git add web/static/app.js
git commit -m "fix(i18n): apply localiseMetric to timeline precipitation text"
```
