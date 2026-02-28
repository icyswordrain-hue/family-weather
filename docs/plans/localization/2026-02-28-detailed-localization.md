# Detailed UI Localization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Translate the remaining unlocalized UI elements (Morning/Afternoon slots, condition change cards) and improve Chinese typography to match the clean English layout.

**Architecture:** We will add two new dictionaries to the `TRANSLATIONS` object in `app.js` (`slots` and `transitions`) and apply them to the programmatic rendering in `renderOverviewView`. We will also update `index.html` and `style.css` to import and use `Noto Sans TC` as the primary fallback font for Chinese characters, which perfectly complements the existing `Inter` font.

**Tech Stack:** JavaScript, CSS, HTML

---

### Task 1: Add Translation Dictionaries to app.js

**Files:**
- Modify: `web/static/app.js`

**Step 1: Add `slots` and `transitions` to `TRANSLATIONS['zh-TW']`**

Around line 245, inside the `zh-TW` translation object, add:

```javascript
    slots: {
      'Morning': '早上',
      'Afternoon': '下午',
      'Evening': '傍晚',
      'Overnight': '深夜',
      'Forecast': '預報'
    },
    transitions: {
      'Sunny': '晴朗',
      'Cloudy': '多雲',
      'Rain expected': '預期降雨',
      'More rain': '降雨增加',
      'Less rain': '降雨減少',
      'Humid': '變潮濕',
      'Dry air': '變乾燥',
      'Windier': '風力增強',
      'Calmer': '風力減弱',
      'change': '變化'
    }
```

**Step 2: Commit**

```bash
git add web/static/app.js
git commit -m "feat(i18n): add slot and transition translation dictionaries"
```

---

### Task 2: Apply Translations to Timeline Rendering

**Files:**
- Modify: `web/static/app.js`

**Step 1: Localize the slot name in `renderOverviewView`**

Around line 383, change how `slotName` is defined for the UI:

```javascript
// Replace:
// const slotName = seg.display_name || 'Forecast';
// header.textContent = slotName;

// With:
const origSlotName = seg.display_name || 'Forecast';
const slotName = origSlotName;
header.textContent = (T.slots && T.slots[origSlotName]) ? T.slots[origSlotName] : origSlotName;
```

**Step 2: Localize the transition cards in `renderOverviewView`**

Around line 428, in the `transition.breaches` loop, wrap all pushed strings using a helper inline:

```javascript
// Add a quick helper inside the transition block:
const locTrans = (txt) => (T.transitions && T.transitions[txt]) ? T.transitions[txt] : txt;

// Update the pushes:
          if (b.metric === 'CloudCover') {
            let label = b.to;
            if (label === 'Sunny/Clear') label = 'Sunny';
            if (label === 'Mixed Clouds') label = 'Cloudy';
            parts.push(locTrans(label));
          } else if (b.metric === 'AT') {
            parts.push(`${b.delta > 0 ? '+' : ''}${Math.round(b.delta)}°`);
          } else if (b.metric === 'PoP6h') {
            const intensity = ["Dry", "Very Unlikely", "Unlikely", "Possible", "Likely", "Very Likely"];
            const fIdx = intensity.indexOf(b.from), tIdx = intensity.indexOf(b.to);
            if (tIdx > fIdx) parts.push(locTrans(tIdx >= 3 ? 'Rain expected' : 'More rain'));
            else if (tIdx < fIdx) parts.push(locTrans('Less rain'));
          } else if (b.metric === 'RH') {
            parts.push(locTrans(b.delta > 0 ? 'Humid' : 'Dry air'));
          } else if (b.metric === 'WS') {
            const bf = ["Calm", "Light air", "Light breeze", "Gentle breeze", "Moderate breeze", "Fresh breeze", "Strong breeze"];
            const fIdx = bf.indexOf(b.from), tIdx = bf.indexOf(b.to);
            if (tIdx > fIdx) parts.push(locTrans('Windier'));
            else if (tIdx < fIdx) parts.push(locTrans('Calmer'));
          }
```

And around line 452:
```javascript
// Change:
// t.textContent = `→ ${parts.length ? parts.join(' · ') : 'change'}`;
// To:
t.textContent = `→ ${parts.length ? parts.join(' · ') : locTrans('change')}`;
```

**Step 3: Commit**

```bash
git add web/static/app.js
git commit -m "fix(i18n): apply localization to timeline slots and transitions"
```

---

### Task 3: Improve Chinese Typography

**Files:**
- Modify: `web/templates/index.html`
- Modify: `web/static/style.css`

**Step 1: Import Noto Sans TC in `index.html`**

In `web/templates/index.html` within the `<head>`, add the Google Fonts link for Noto Sans TC alongside the current fonts:

```html
  <!-- Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;700&family=Inter:wght@400;500;600;700;800&family=ZCOOL+XiaoWei&family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
```

**Step 2: Update CSS font variables**

In `web/static/style.css` around line 50, update `--font`:

```css
  --font: 'Inter', 'Noto Sans TC', system-ui, -apple-system, sans-serif;
```

*(This prioritizes Inter for English/Numbers, and falls back perfectly to Noto Sans TC for Chinese text, which shares similar geometric proportions to Inter).*

**Step 3: Commit**

```bash
git add web/templates/index.html web/static/style.css
git commit -m "style: add Noto Sans TC font for consistent Chinese typography"
```
