/**
 * app.js — Family Weather Dashboard frontend logic (v4 — Revamp).
 *
 * Views:
 *  1. Current: Big gauges (Temp, Hum, Wind, AQI)
 *  2. Overview: Timeline, Trend Chart, Alerts
 *  3. Lifestyle: Wardrobe, Commute, Outdoor, Meals, HVAC
 *  4. Narration: Full text script
 *
 * Features:
 *  - Dynamic Right Panel (Context-aware)
 *  - Mobile "Info" Drawer
 */

'use strict';

// ── Global Error Handler (Top Level) ───────────────────────────────────────
function remoteLog(type, msg) {
  fetch('/debug/log', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type, msg, ts: new Date().toISOString() })
  }).catch(() => { });
}

window.onerror = function (msg, url, lineNo, columnNo, error) {
  const logList = document.getElementById('rp-log-list');
  if (logList) {
    const div = document.createElement('div');
    div.className = 'log-entry error';
    const span = document.createElement('span');
    span.className = 'log-msg';
    span.textContent = `Runtime Error: ${msg}`;
    div.appendChild(span);
    logList.appendChild(div);
  }
  remoteLog('error', `${msg} at ${url}:${lineNo}`);
  console.error("Global Error:", msg, error);
  return false;
};

remoteLog('info', 'app.js loaded');
console.log("App.js Loaded");

// ── State ──────────────────────────────────────────────────────────────────
let broadcastData = null;
let currentView = 'lifestyle'; // 'lifestyle' | 'narration' | 'dashboard'
let tempChart = null;
let loadingInterval = null;
const LOADING_MSGS = [
  "Connecting to CWA Banqiao Station...",
  "Retrieving Township Forecasts...",
  "Checking MOENV Air Quality...",
  "Processing V5 Logic...",
  "Generating Narration...",
  "Synthesizing Audio...",
  "Finalizing..."
];

const ICONS = {
  'sunny': '☀️', 'Sunny/Clear': '☀️', '1': '☀️',
  'partly-cloudy': '⛅', 'Mixed Clouds': '⛅', '2': '⛅', '3': '⛅',
  'cloudy': '☁️', 'Overcast': '☁️', '4': '☁️', '5': '☁️', '6': '☁️', '7': '☁️',
  'rainy': '🌧️', '8': '🌧️', '9': '🌧️', '10': '🌧️', '11': '🌧️', '12': '🌧️', '13': '🌧️',
  '14': '🌧️', '15': '🌧️', '16': '🌧️', '17': '🌧️', '18': '🌧️', '19': '🌧️', '20': '🌧️'
};

// ── Boot ───────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  window.app = {
    fetchBroadcast,
    triggerRefresh
  };

  // Show first log entry immediately
  addLog("System Boot: Initiating connection...");

  initSidebarNav();
  initMobileDrawer();
  initRefreshButton();
  updateClock();
  setInterval(updateClock, 1000);

  fetchBroadcast();
});

// ── API fetch ──────────────────────────────────────────────────────────────
async function fetchBroadcast() {
  showLoading();
  addLog("System Boot: Fetching latest broadcast...");
  try {
    const res = await fetch('/api/broadcast');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    broadcastData = await res.json();
    if (broadcastData.error) throw new Error(broadcastData.error);
    addLog("Data received successfully.");
    render(broadcastData);
    showContent();
  } catch (err) {
    addLog(`Error: ${err.message || 'Unknown error'}`);
    showError(err.message || 'Unknown error');
  }
}

// ── Render Dispatch ────────────────────────────────────────────────────────
function render(data) {
  const slices = data.slices || {};

  // Render all views (they are hidden/shown via CSS class)
  renderCurrentView(slices.current);
  renderOverviewView(slices.overview);
  renderLifestyleView(slices.lifestyle);
  renderNarrationView(slices.narration, data.audio_urls);

  // Footer / Meta
  const ts = data.generated_at || '';
  if (ts) {
    let dateStr = ts;
    try {
      dateStr = new Date(ts).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' });
    } catch (e) {
      console.warn("Timezone zh-TW/Taipei not supported, falling back to default.", e);
      dateStr = new Date(ts).toLocaleString();
    }
    const msg = `Last updated: ${dateStr}`;
    setText('rp-last-updated', msg);
  }
}

// ── View 1: Dashboard (Merged Current + Overview) ──────────────────────────
function renderCurrentView(data) {
  if (!data) return;
  setText('cur-temp', Math.round(data.temp) + '°');
  setText('cur-weather-text', data.weather_text || '—');
  setText('cur-icon', ICONS[data.weather_code] || ICONS[data.weather_text] || '🌤️');
  setText('rp-location', data.location || '—');

  // Gauge Cards (Restructured)
  renderGauge('gauge-ground', data.ground_state, 'Ground', '', `lvl-${data.ground_level}`);
  renderGauge('gauge-wind', data.wind.text, 'Wind', `${data.wind.val} m/s ${data.wind.dir || '—'}`, `lvl-${data.wind.level}`);
  renderGauge('gauge-hum', data.hum.text, 'Humidity', data.hum.val + '%', `lvl-${data.hum.level}`);
  renderGauge('gauge-aqi', data.aqi.text, 'Air Quality', `AQI ${data.aqi.val}`, `lvl-${data.aqi.level}`);
  renderGauge('gauge-uv', data.uv.text, 'UV Index', `Index ${data.uv.val || 0}`, `lvl-${data.uv.level}`);
  renderGauge('gauge-pres', data.pres.text, 'Pressure', `${Math.round(data.pres.val)} hPa`, `lvl-${data.pres.level}`);
}

function renderGauge(id, mainVal, label, subVal = '', valueClass = '') {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = '';
  const l = document.createElement('div');
  l.className = 'gauge-label';
  l.textContent = label;

  const v = document.createElement('div');
  v.className = `gauge-value ${valueClass}`;
  v.textContent = mainVal;

  el.appendChild(l);
  el.appendChild(v);

  if (subVal) {
    const s = document.createElement('div');
    s.className = 'gauge-sub';
    s.textContent = subVal;
    el.appendChild(s);
  }
}

// ── View 2: Overview ───────────────────────────────────────────────────────
function renderOverviewView(data) {
  if (!data) return;

  // Alerts (Unified Grouping)
  const alertContainer = document.getElementById('ov-alerts');
  if (alertContainer) {
    alertContainer.innerHTML = '';
    if (data.alerts) {
      const items = [];
      if (data.alerts.cardiac && data.alerts.cardiac.triggered) {
        items.push({ type: 'health', icon: '❤️', title: 'Cardiac Alert', text: data.alerts.cardiac.reason, guidance: 'Keep warm and avoid sudden cold exposure.' });
      }
      if (data.alerts.menieres && data.alerts.menieres.triggered) {
        items.push({ type: 'health', icon: '🦻', title: 'Ménière\'s Alert', text: data.alerts.menieres.reason, guidance: 'Watch for vertigo or ear fullness; stay hydrated.' });
      }
      if (data.alerts.heads_up) {
        items.push({ type: 'narrative', icon: '📢', title: 'Heads Up', text: data.alerts.heads_up });
      }

      if (items.length > 0) {
        const wrapper = document.createElement('div');
        wrapper.className = 'unified-alerts' + (items.some(i => i.type === 'health') ? ' has-health' : '');
        const group = document.createElement('div');
        group.className = 'alert-group';

        items.forEach(item => {
          const div = document.createElement('div');
          div.className = `alert-item ${item.type}`;
          const icon = document.createElement('div');
          icon.className = 'alert-icon';
          icon.textContent = item.icon;
          const content = document.createElement('div');
          content.className = 'alert-content';
          const title = document.createElement('div');
          title.className = 'alert-title';
          title.textContent = item.title;
          const text = document.createElement('div');
          text.className = 'alert-text';
          text.textContent = item.text;
          content.appendChild(title);
          content.appendChild(text);
          if (item.guidance) {
            const g = document.createElement('div');
            g.className = 'alert-guidance';
            g.textContent = item.guidance;
            content.appendChild(g);
          }
          div.appendChild(icon);
          div.appendChild(content);
          group.appendChild(div);
        });
        wrapper.appendChild(group);
        alertContainer.appendChild(wrapper);
      }
    }
  }

  // Timeline
  const timelineGrid = document.getElementById('ov-timeline');
  if (timelineGrid) {
    timelineGrid.innerHTML = '';
    const transitionMap = {};
    (data.transitions || []).forEach(t => { if (t.is_transition && t.from_segment) transitionMap[t.from_segment] = t; });

    (data.timeline || []).forEach((seg, idx) => {
      const slotName = seg.display_name || 'Forecast';
      const card = document.createElement('div');
      card.className = 'time-card';
      const header = document.createElement('div');
      header.className = 'tc-header';
      header.textContent = slotName;
      const icon = document.createElement('div');
      icon.className = 'tc-icon';
      icon.textContent = ICONS[seg.cloud_cover] || ICONS[seg.Wx] || '☁️';
      const temp = document.createElement('div');
      temp.className = 'tc-temp';
      temp.textContent = `${Math.round(seg.AT ?? seg.T ?? 0)}°`;
      const details = document.createElement('div');
      details.className = 'tc-details';

      const addRow = (label, val, lvl) => {
        const row = document.createElement('div');
        row.className = 'tc-row';
        const l = document.createElement('span');
        l.className = 'tc-label';
        l.textContent = label;
        const v = document.createElement('span');
        v.className = `tc-val lvl-${lvl}`;
        v.textContent = val;
        row.appendChild(l);
        row.appendChild(v);
        details.appendChild(row);
      };
      addRow('Rain', seg.precip_text || '—', seg.precip_level || 1);
      addRow('Wind', seg.wind_text || '—', seg.wind_level || 1);
      if (seg.outdoor_grade) {
        addRow('Outdoor', `${seg.outdoor_grade} · ${seg.outdoor_score}`, `grade-${seg.outdoor_grade}`);
      }
      card.appendChild(header);
      card.appendChild(icon);
      card.appendChild(temp);
      card.appendChild(details);

      const nextSeg = data.timeline[idx + 1];
      const transition = nextSeg ? transitionMap[slotName] : null;
      if (transition && transition.is_transition) {
        const parts = [];
        (transition.breaches || []).forEach(b => {
          if (b.metric === 'CloudCover') {
            let label = b.to;
            if (label === 'Sunny/Clear') label = 'Sunny';
            if (label === 'Mixed Clouds') label = 'Cloudy';
            parts.push(label);
          } else if (b.metric === 'AT') {
            parts.push(`${b.delta > 0 ? '+' : ''}${Math.round(b.delta)}°`);
          } else if (b.metric === 'PoP6h') {
            const intensity = ["Dry", "Very Unlikely", "Unlikely", "Possible", "Likely", "Very Likely"];
            const fIdx = intensity.indexOf(b.from), tIdx = intensity.indexOf(b.to);
            if (tIdx > fIdx) parts.push(tIdx >= 3 ? 'Rain expected' : 'More rain');
            else if (tIdx < fIdx) parts.push('Less rain');
          } else if (b.metric === 'RH') {
            parts.push(b.delta > 0 ? 'Humid' : 'Dry air');
          } else if (b.metric === 'WS') {
            const bf = ["Calm", "Light air", "Light breeze", "Gentle breeze", "Moderate breeze", "Fresh breeze", "Strong breeze"];
            const fIdx = bf.indexOf(b.from), tIdx = bf.indexOf(b.to);
            if (tIdx > fIdx) parts.push('Windier');
            else if (tIdx < fIdx) parts.push('Calmer');
          }
        });
        const t = document.createElement('div');
        t.className = 'tc-transition';
        t.textContent = `→ ${parts.length ? parts.join(' · ') : 'change'}`;
        card.appendChild(t);
      }
      timelineGrid.appendChild(card);
    });
  }

  // 7-Day Timeline
  const weeklyTimelineEl = document.getElementById('ov-weekly-timeline');
  if (weeklyTimelineEl && data.weekly_timeline) {
    weeklyTimelineEl.innerHTML = '';
    data.weekly_timeline.forEach(item => {
      let dt;
      try { dt = new Date(item.start_time.replace('+08:00', '')); } catch (e) { dt = new Date(); }
      const hours = dt.getHours();
      const isNight = (hours >= 18 || hours < 6);
      const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      const displayTime = `${days[dt.getDay()]} ${isNight ? 'Night' : 'Day'}`;

      const card = document.createElement('div');
      card.className = 'time-card';
      const header = document.createElement('div');
      header.className = 'tc-header';
      header.textContent = displayTime;
      const icon = document.createElement('div');
      icon.className = 'tc-icon';
      icon.textContent = ICONS[item.cloud_cover] || ICONS[item.Wx] || '☁️';
      const temp = document.createElement('div');
      temp.className = 'tc-temp' + (item.AT >= 30 ? ' text-hot' : item.AT <= 15 ? ' text-cold' : '');
      temp.textContent = `${Math.round(item.AT ?? 0)}°`;
      const details = document.createElement('div');
      details.className = 'tc-details';
      const row = document.createElement('div');
      row.className = 'tc-row';
      const l = document.createElement('span');
      l.className = 'tc-label';
      l.textContent = 'Rain';
      const v = document.createElement('span');
      v.className = 'tc-val lvl-' + (item.PoP12h >= 40 ? '3' : '1');
      v.textContent = (item.PoP12h ?? '--') + '%';
      row.appendChild(l);
      row.appendChild(v);
      details.appendChild(row);
      card.appendChild(header);
      card.appendChild(icon);
      card.appendChild(temp);
      card.appendChild(details);
      weeklyTimelineEl.appendChild(card);
    });
  }

  // AQI Forecast
  const aqiFcEl = document.getElementById('ov-aqi-forecast');
  if (aqiFcEl && data.aqi_forecast && (data.aqi_forecast.status || data.aqi_forecast.content)) {
    const aqi = data.aqi_forecast;
    aqiFcEl.className = 'aqi-forecast-block';
    aqiFcEl.innerHTML = '';
    const icon = document.createElement('div');
    icon.className = 'aqi-fc-icon';
    icon.textContent = '🌫️';
    const body = document.createElement('div');
    body.className = 'aqi-fc-body';
    const header = document.createElement('div');
    header.className = 'aqi-fc-header';
    const title = document.createElement('span');
    title.className = 'aqi-fc-title';
    title.textContent = "Tomorrow's Air Quality";
    const date = document.createElement('span');
    date.className = 'aqi-fc-date';
    date.textContent = (aqi.forecast_date ? ` (${aqi.forecast_date})` : '') + (aqi.aqi ? ` · AQI ${aqi.aqi}` : '');
    header.appendChild(title);
    header.appendChild(date);
    const status = document.createElement('div');
    status.className = 'aqi-fc-status';
    status.textContent = translateAQIText(aqi.status);
    body.appendChild(header);
    body.appendChild(status);
    if (aqi.summary_en || aqi.content) {
      const content = document.createElement('div');
      content.className = 'aqi-fc-content';
      content.textContent = aqi.summary_en || aqi.content;
      body.appendChild(content);
    }
    aqiFcEl.appendChild(icon);
    aqiFcEl.appendChild(body);
  }
}

function translateAQIText(status) {
  if (!status) return '';
  const map = {
    '良好': 'Good',
    '普通': 'Moderate',
    '對敏感族群不健康': 'Unhealthy for Sensitive Groups',
    '不健康': 'Unhealthy',
    '非常不健康': 'Very Unhealthy',
    '危害': 'Hazardous'
  };
  return map[status] || status;
}

// ── View 3: Lifestyle ──────────────────────────────────────────────────────
function renderLifestyleView(data) {
  if (!data) return;
  const grid = document.getElementById('lifestyle-grid');
  if (!grid) return;
  grid.innerHTML = '';

  const add = (icon, title, text, extraNodes = []) => {
    const card = document.createElement('div');
    card.className = 'ls-card';
    const ic = document.createElement('div');
    ic.className = 'ls-icon';
    ic.textContent = icon;
    const content = document.createElement('div');
    content.className = 'ls-content';
    const t = document.createElement('div');
    t.className = 'ls-title';
    t.textContent = title;
    const txt = document.createElement('div');
    txt.className = 'ls-text';
    txt.textContent = text;
    content.appendChild(t);
    content.appendChild(txt);
    extraNodes.forEach(n => content.appendChild(n));
    card.appendChild(ic);
    card.appendChild(content);
    grid.appendChild(card);
  };

  const mkBadge = (cls, text) => {
    const s = document.createElement('span');
    s.className = 'ls-badge ' + cls;
    s.textContent = text;
    return s;
  };
  const mkSub = (text) => {
    const d = document.createElement('div');
    d.className = 'ls-sub';
    d.textContent = text;
    return d;
  };

  // 1. Wardrobe
  if (data.wardrobe) {
    const extras = [];
    if (data.wardrobe.feels_like != null) extras.push(mkSub(`Feels like ${Math.round(data.wardrobe.feels_like)}°`));
    add('🧥', 'Wardrobe', data.wardrobe.text, extras);
  }
  // 2. Rain Gear
  if (data.rain_gear) add('☂️', 'Rain Gear', data.rain_gear.text);
  // 3. Commute
  if (data.commute) {
    const extras = [];
    if (data.commute.hazards && data.commute.hazards.length > 0) {
      const ul = document.createElement('ul');
      ul.className = 'ls-hazards';
      data.commute.hazards.forEach(h => {
        const li = document.createElement('li');
        li.textContent = h;
        ul.appendChild(li);
      });
      extras.push(ul);
    }
    add('🚗', 'Commute', data.commute.text, extras);
  }
  // 4. Garden Health
  if (data.garden && data.garden.text) add('🌱', 'Garden Health', data.garden.text);
  // 5. Outdoor Activities
  if (data.outdoor && data.outdoor.text) {
    const extras = [];
    if (data.outdoor.grade) extras.push(mkBadge(`oi-grade-${data.outdoor.grade}`, `Grade ${data.outdoor.grade} · ${data.outdoor.label || ''}`));
    if (data.outdoor.top_activity) extras.push(mkSub(`Best: ${data.outdoor.best_window || ''} · Top: ${data.outdoor.top_activity}`));
    add('🌳', 'Outdoor Activities', data.outdoor.text, extras);
  }
  // 6. Meals
  if (data.meals && data.meals.text) {
    const extras = [];
    if (data.meals.mood) extras.push(mkBadge('mood-badge', data.meals.mood));
    add('🍱', 'Meals', data.meals.text, extras);
  }
  // 7. HVAC Advice
  if (data.hvac) {
    const extras = [];
    if (data.hvac.mode) extras.push(mkBadge(`hvac-${data.hvac.mode.toLowerCase()}`, data.hvac.mode));
    add('🌡️', 'HVAC Advice', data.hvac.text, extras);
  }
}

// ── View 4: Narration ──────────────────────────────────────────────────────
function renderNarrationView(data, audioUrls) {
  if (!data) return;

  // Text Script
  const container = document.getElementById('narration-text');
  container.innerHTML = '';
  (data.paragraphs || []).forEach(p => {
    if (!p.text) return;
    const block = document.createElement('div');
    block.className = 'narration-block';
    const pEl = document.createElement('p');
    pEl.textContent = p.text;
    pEl.style.whiteSpace = 'pre-line';
    block.appendChild(pEl);
    container.appendChild(block);
  });

  // Source Badge
  const badge = document.getElementById('narration-meta');
  if (badge && data.meta) {
    badge.textContent = `${data.meta.source}(${data.meta.model})`;
    let badgeClass = 'source-template';
    const s = data.meta.source.toLowerCase();
    if (s.includes('gemini')) badgeClass = 'source-gemini';
    if (s.includes('claude')) badgeClass = 'source-claude';
    badge.className = 'narration-badge ' + badgeClass;
  }

  // Audio Player
  const player = document.getElementById('audio-player-native');
  if (player && audioUrls && audioUrls.full_audio_url) {
    player.src = audioUrls.full_audio_url;
  }
}

// ── Sidebar & Navigation ───────────────────────────────────────────────────
function initSidebarNav() {
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
      const view = btn.dataset.view;
      if (view) switchView(view);
    });
  });
}

function switchView(viewName) {
  currentView = viewName;

  // Update Nav
  document.querySelectorAll('.nav-item').forEach(b => {
    b.classList.toggle('active', b.dataset.view === viewName);
  });

  document.querySelectorAll('.view-container').forEach(v => {
    v.classList.toggle('active', v.id === `view-${viewName}`);
  });

  // Mobile drawer: close on switch
  closeMobileDrawer();
}

// ── Mobile Drawer ──────────────────────────────────────────────────────────
function initMobileDrawer() {
  const toggle = document.getElementById('drawer-toggle');
  const backdrop = document.getElementById('drawer-backdrop');
  if (toggle) {
    toggle.addEventListener('click', () => {
      document.body.classList.toggle('drawer-open');
    });
  }
  if (backdrop) {
    backdrop.addEventListener('click', closeMobileDrawer);
  }
  // Also close on swipe down? (Maybe later)
}

function closeMobileDrawer() {
  document.body.classList.remove('drawer-open');
}

// ── Helpers ────────────────────────────────────────────────────────────────
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

// ── Clock ──────────────────────────────────────────────────────────────────

function updateClock() {
  const now = new Date();

  // Digital Subtitle
  const el = document.getElementById('rp-time');
  if (el) {
    try {
      el.textContent = now.toLocaleTimeString('en-US', {
        hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Taipei'
      });
    } catch (e) {
      el.textContent = now.toLocaleTimeString('en-US', {
        hour: '2-digit', minute: '2-digit', hour12: false
      });
    }
  }

  // Analog Hands
  const hourHand = document.getElementById('clock-hour');
  const minuteHand = document.getElementById('clock-minute');
  const secondHand = document.getElementById('clock-second');

  if (hourHand && minuteHand && secondHand) {
    const seconds = now.getSeconds();
    const minutes = now.getMinutes();
    const hours = now.getHours();

    const secondDeg = ((seconds / 60) * 360);
    const minuteDeg = ((minutes / 60) * 360) + ((seconds / 60) * 6);
    const hourDeg = ((hours / 12) * 360) + ((minutes / 60) * 30);

    secondHand.style.transform = `rotate(${secondDeg}deg)`;
    minuteHand.style.transform = `rotate(${minuteDeg}deg)`;
    hourHand.style.transform = `rotate(${hourDeg}deg)`;
  }
}

function showLoading() {
  document.getElementById('loading-screen').classList.remove('hidden');
  document.getElementById('error-screen').classList.add('hidden');
  document.getElementById('main-content').classList.add('hidden');
  startLoadingAnimation();
}

function showContent() {
  stopLoadingAnimation();
  document.getElementById('loading-screen').classList.add('hidden');
  document.getElementById('error-screen').classList.add('hidden');
  document.getElementById('main-content').classList.remove('hidden');
}

function showError(msg) {
  stopLoadingAnimation();
  console.error(msg);
  const errEl = document.getElementById('error-msg');
  if (errEl) errEl.textContent = msg;
  document.getElementById('loading-screen').classList.add('hidden');
  document.getElementById('error-screen').classList.remove('hidden');
  document.getElementById('main-content').classList.add('hidden');
}

function initRefreshButton() {
  const btn = document.getElementById('refresh-btn');
  if (btn) btn.addEventListener('click', triggerRefresh);
}

async function triggerRefresh() {
  const btn = document.getElementById('refresh-btn');
  if (btn) {
    btn.disabled = true;
    btn.classList.add('spinning');
  }

  showLoading();
  startLoadingAnimation(); // Start fake messages until connection established
  addLog("Initiating connection...");

  // Read selected provider
  const providerInput = document.querySelector('input[name="provider"]:checked');
  const provider = providerInput ? providerInput.value : 'CLAUDE';

  try {
    const res = await fetch('/api/refresh', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        provider
      })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    // Stream reader
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // Keep incomplete line

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          // If the line is not JSON (e.g. raw error string from server), log it and move on
          if (!line.trim().startsWith('{')) {
            addLog(`Server: ${line.trim()}`);
            if (line.toLowerCase().includes('error')) {
              showError(line.trim());
              return;
            }
            continue;
          }

          const msg = JSON.parse(line);
          if (msg.type === 'log') {
            stopLoadingAnimation();
            addLog(msg.message);
            const loadingTxt = document.getElementById('loading-text');
            if (loadingTxt) loadingTxt.textContent = msg.message;
          } else if (msg.type === 'result') {
            addLog("Pipeline success. Rendering...");
            broadcastData = msg.payload;
            render(broadcastData);
            showContent();
            return; // Exit successfully
          } else if (msg.type === 'error') {
            showError(msg.message || 'Pipeline failed');
            return;
          }
        } catch (e) {
          console.error("Stream parse error:", e, "on line:", line);
          // If it's a critical error keyword in a non-JSON line, catch it
          if (line.toLowerCase().includes('failed') || line.toLowerCase().includes('error')) {
            showError(line);
            return;
          }
        }
      }
    }
    // If we reach here without a 'result' or 'error' message but the stream is done
    if (!broadcastData) {
      showError("Pipeline ended without a result.");
    }
  } catch (err) {
    addLog(`Error: ${err.message}`);
    showError(err.message || 'Refresh failed');
  } finally {
    stopLoadingAnimation();
    if (btn) {
      btn.disabled = false;
      btn.classList.remove('spinning');
    }
  }
}


function startLoadingAnimation() {
  const txt = document.getElementById('loading-text');
  if (!txt) return;
  let i = 0;
  txt.textContent = LOADING_MSGS[0];
  addLog(`Step: ${LOADING_MSGS[0]}`);

  if (loadingInterval) clearInterval(loadingInterval);
  loadingInterval = setInterval(() => {
    i = (i + 1) % LOADING_MSGS.length;
    txt.textContent = LOADING_MSGS[i];
    addLog(`Step: ${LOADING_MSGS[i]}`);
  }, 1200);
}

function stopLoadingAnimation() {
  if (loadingInterval) {
    clearInterval(loadingInterval);
    loadingInterval = null;
  }
}

function addLog(msg) {
  const list = document.getElementById('rp-log-list');
  if (!list) return;
  const div = document.createElement('div');
  div.className = 'log-entry';

  let ts = '';
  try {
    ts = new Date().toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  } catch (e) {
    ts = `${now.getHours()}:${now.getMinutes()}:${now.getSeconds()}`;
  }

  const tsSpan = document.createElement('span');
  tsSpan.className = 'log-ts';
  tsSpan.textContent = ts;

  const msgSpan = document.createElement('span');
  msgSpan.className = 'log-msg';
  msgSpan.textContent = msg;

  div.appendChild(tsSpan);
  div.appendChild(msgSpan);
  list.appendChild(div);
  list.scrollTop = list.scrollHeight;
}

// ── Chart ──────────────────────────────────────────────────────────────────
