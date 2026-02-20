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
    div.innerHTML = `<span class="log-msg">Runtime Error: ${msg}</span>`;
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
let currentView = 'dashboard'; // 'dashboard' | 'lifestyle' | 'narration'
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

  // Initial Right Panel update
  updateRightPanel(currentView, slices.context);

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

  // Gauge Cards (Restructured)
  renderGauge('gauge-ground', data.ground_state, 'Ground', '', `lvl-${data.ground_level}`);
  renderGauge('gauge-wind', data.wind.text, 'Wind', `${data.wind.val} m/s ${data.wind.dir}`, `lvl-${data.wind.level}`);
  renderGauge('gauge-hum', data.hum.text, 'Humidity', data.hum.val + '%', `lvl-${data.hum.level}`);
  renderGauge('gauge-aqi', data.aqi.text, 'Air Quality', `AQI ${data.aqi.val}`, `lvl-${data.aqi.level}`);
  renderGauge('gauge-uv', data.uv.text, 'UV Index', `Index ${data.uv.val || 0}`, `lvl-${data.uv.level}`);
  renderGauge('gauge-pres', data.pres.text, 'Pressure', `${Math.round(data.pres.val)} hPa`, `lvl-${data.pres.level}`);
  renderGauge('gauge-vis', data.vis.text, 'Visibility', `${data.vis.val != null ? data.vis.val + ' km' : '—'}`, `lvl-${data.vis.level}`);
}

function renderGauge(id, mainVal, label, subVal = '', valueClass = '') {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = `
    <div class="gauge-label">${label}</div>
    <div class="gauge-value ${valueClass}">${mainVal}</div>
    ${subVal ? `<div class="gauge-sub">${subVal}</div>` : ''}
  `;
}

// ── View 2: Overview ───────────────────────────────────────────────────────
function renderOverviewView(data) {
  if (!data) return;

  // Alerts (Unified Grouping)
  const alertContainer = document.getElementById('ov-alerts');
  alertContainer.innerHTML = '';

  if (data.alerts) {
    const alerts = data.alerts;
    const items = [];

    // 1. Cardiac Risk
    if (alerts.cardiac && alerts.cardiac.triggered) {
      items.push({
        type: 'health',
        icon: '❤️',
        title: 'Cardiac Alert',
        text: alerts.cardiac.reason,
        guidance: 'Keep warm and avoid sudden cold exposure.'
      });
    }

    // 2. Ménière's Alert
    if (alerts.menieres && alerts.menieres.triggered) {
      items.push({
        type: 'health',
        icon: '🦻',
        title: 'Ménière\'s Alert',
        text: alerts.menieres.reason,
        guidance: 'Watch for vertigo or ear fullness; stay hydrated.'
      });
    }

    // 3. Narrative Heads Up
    if (alerts.heads_up) {
      items.push({
        type: 'narrative',
        icon: '📢',
        title: 'Heads Up',
        text: alerts.heads_up
      });
    }

    if (items.length > 0) {
      const wrapper = document.createElement('div');
      wrapper.className = 'unified-alerts';
      if (items.some(i => i.type === 'health')) {
        wrapper.classList.add('has-health');
      }

      const group = document.createElement('div');
      group.className = 'alert-group';

      items.forEach(item => {
        const div = document.createElement('div');
        div.className = `alert-item ${item.type}`;
        div.innerHTML = `
          <div class="alert-icon">${item.icon}</div>
          <div class="alert-content">
            <div class="alert-title">${item.title}</div>
            <div class="alert-text">${item.text}</div>
            ${item.guidance ? `<div class="alert-guidance">${item.guidance}</div>` : ''}
          </div>
        `;
        group.appendChild(div);
      });

      wrapper.appendChild(group);
      alertContainer.appendChild(wrapper);
    }
  }

  // Timeline (Dynamic Order)
  const timelineGrid = document.getElementById('ov-timeline');
  timelineGrid.innerHTML = '';
  const timeline = data.timeline || [];

  timeline.forEach(seg => {
    const slotName = seg.display_name || 'Forecast';
    const card = document.createElement('div');
    card.className = 'time-card';
    card.innerHTML = `
      <div class="tc-header">${slotName}</div>
      <div class="tc-icon">${ICONS[seg.cloud_cover] || ICONS[seg.Wx] || '☁️'}</div>
      <div class="tc-temp">${Math.round(seg.AT)}°</div>
      <div class="tc-details">
         <div class="tc-row">
           <span class="tc-label">Rain</span>
           <span class="tc-val lvl-${seg.precip_level || 1}">${seg.precip_text}</span>
         </div>
         <div class="tc-row">
           <span class="tc-label">Wind</span>
           <span class="tc-val lvl-${seg.wind_level || 1}">${seg.wind_text}</span>
         </div>
      </div>
    `;
    timelineGrid.appendChild(card);
  });

  // Trend Chart removed
}

// ── View 3: Lifestyle ──────────────────────────────────────────────────────
function renderLifestyleView(data) {
  if (!data) return;
  const grid = document.getElementById('lifestyle-grid');
  grid.innerHTML = '';

  // 1. Wardrobe & Rain Gear (Row 1)
  if (data.wardrobe) {
    const feelsLike = data.wardrobe.feels_like != null
      ? `<div class="ls-sub">Feels like ${Math.round(data.wardrobe.feels_like)}°</div>`
      : '';
    grid.appendChild(makeIconCard('🧥', 'Wardrobe', data.wardrobe.text, feelsLike));
  }
  if (data.rain_gear) {
    grid.appendChild(makeIconCard('☂️', 'Rain Gear', data.rain_gear.text));
  }

  // 2. Commute & HVAC (Row 2)
  if (data.commute) {
    const hazards = (data.commute.hazards || []);
    const hazardsHtml = hazards.length > 0
      ? `<ul class="ls-hazards">${hazards.map(h => `<li>${h}</li>`).join('')}</ul>`
      : '';
    grid.appendChild(makeIconCard('🚗', 'Commute', data.commute.text, hazardsHtml));
  }
  if (data.hvac) {
    const mode = data.hvac.mode;
    const modeHtml = mode
      ? `<span class="ls-badge hvac-${mode.toLowerCase()}">${mode}</span>`
      : '';
    grid.appendChild(makeIconCard('🌡️', 'HVAC Advice', data.hvac.text, modeHtml));
  }

  // 3. Meals
  if (data.meals && data.meals.text) {
    const moodHtml = data.meals.mood
      ? `<span class="ls-badge mood-badge">${data.meals.mood}</span>`
      : '';
    grid.appendChild(makeIconCard('🍱', 'Meals', data.meals.text, moodHtml));
  }

  // 4. Garden & Outdoors (WIDE)
  if (data.garden && data.garden.text) {
    const card = makeIconCard('🌱', 'Garden Health', data.garden.text);
    card.classList.add('wide');
    grid.appendChild(card);
  }
  if (data.outdoor && data.outdoor.text) {
    const card = makeIconCard('🌳', 'Outdoor Activities', data.outdoor.text);
    card.classList.add('wide');
    grid.appendChild(card);
  }
}

function makeIconCard(icon, title, text, extra = '') {
  const el = document.createElement('div');
  el.className = 'ls-card';
  el.innerHTML = `
    <div class="ls-icon">${icon}</div>
    <div class="ls-content">
      <div class="ls-title">${title}</div>
      <div class="ls-text">${text}</div>
      ${extra}
    </div>
  `;
  return el;
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
    const htmlText = p.text.replace(/\n/g, '<br>');
    block.innerHTML = `<h3>${p.title}</h3><p>${htmlText}</p>`;
    container.appendChild(block);
  });

  // Source Badge
  const badge = document.getElementById('narration-meta');
  if (badge && data.meta) {
    badge.textContent = `${data.meta.source} (${data.meta.model})`;
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

async function updateRightPanel(view, contextData) {
  const contentEl = document.getElementById('rp-dynamic');
  if (!contentEl || !contextData) return;

  contentEl.innerHTML = ''; // Clear existing content

  // Location update
  setText('rp-location', contextData.location || 'Sanxi, TW');

  // Context Bubble content
  const bubble = document.createElement('div');
  bubble.className = 'context-bubble-inner';
  bubble.innerHTML = `
    <div class="rp-label">Daily Forecast</div>
    <div class="rp-text">${contextData.rain_forecast_text || 'No rain expected today.'}</div>
  `;
  contentEl.appendChild(bubble);

  // Additional context-specific info could go here
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

  // Update Main Views
  document.querySelectorAll('.view-container').forEach(v => {
    v.classList.toggle('active', v.id === `view-${viewName}`);
  });

  // Update Right Panel Context
  if (broadcastData && broadcastData.slices) {
    updateRightPanel(viewName, broadcastData.slices.context);
  }

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

function renderHealthCard(title, reason, guidance) {
  const card = document.createElement('div');
  card.className = 'alert-card alert-health';
  card.innerHTML = `
    <div class="ac-header">${title}</div>
    <div class="ac-reason">${reason}</div>
    <div class="ac-guidance">${guidance}</div>
  `;
  return card;
}

function makeCard(title, text, opts = {}) {
  const card = document.createElement('div');
  card.className = 'card ' + (opts.warn ? 'card-warn' : '') + (opts.wide ? 'card-wide' : '');
  card.innerHTML = `<h3 class="card-title">${title}</h3><div class="card-text">${text}</div>`;
  return card;
}

function aqiClass(aqi) {
  if (aqi <= 50) return 'aqi-good';
  if (aqi <= 100) return 'aqi-moderate';
  return 'aqi-poor';
}

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
      const {
        done,
        value
      } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, {
        stream: true
      });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // Keep incomplete line

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const msg = JSON.parse(line);
          if (msg.type === 'log') {
            stopLoadingAnimation(); // Switch to real logs
            addLog(msg.message);
            const loadingTxt = document.getElementById('loading-text');
            if (loadingTxt) loadingTxt.textContent = msg.message;
          } else if (msg.type === 'result') {
            addLog("Pipeline success. Rendering...");
            broadcastData = msg.payload;
            render(broadcastData);
            showContent();
          } else if (msg.type === 'error') {
            throw new Error(msg.message);
          }
        } catch (e) {
          console.warn("JSON parse error", e, line);
        }
      }
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
    const now = new Date();
    ts = `${now.getHours()}:${now.getMinutes()}:${now.getSeconds()}`;
  }

  div.innerHTML = `<span class="log-ts">${ts}</span><span class="log-msg">${msg}</span>`;
  list.appendChild(div);
  list.scrollTop = list.scrollHeight;
}

// ── Chart ──────────────────────────────────────────────────────────────────
