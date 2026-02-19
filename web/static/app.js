/**
 * app.js — Family Weather Dashboard frontend logic (v3 — Srawana layout).
 *
 * Responsibilities:
 *  - Fetch broadcast JSON from /api/broadcast
 *  - Render per-profile cards (Me, Spouse, Dad, Kids)
 *  - Render overview metric cards, right panel, weekly temp chart
 *  - Handle sidebar profile switching
 *  - Audio player with progress tracking & speed control
 *  - Raw data toggle (Me view)
 *  - Live clock in right panel
 */

'use strict';

// ── State ──────────────────────────────────────────────────────────────────
let broadcastData = null;
let currentProfile = 'me';
let audioSrc = { me: null, spouse: null, dad: null, kids: null };
let tempChart = null;

// Weather icon emoji map
const ICONS = {
  'sunny': '☀️',
  'partly-cloudy': '⛅',
  'cloudy': '☁️',
  'rainy': '🌧️',
};

// ── Boot ───────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  window.app = { fetchBroadcast, triggerRefresh };
  initSidebarNav();
  initRefreshButton();
  initAudioPlayer();
  initClock();
  updateTopbarDate();
  fetchBroadcast();
});

// ── Clock ──────────────────────────────────────────────────────────────────
function initClock() {
  updateClock();
  setInterval(updateClock, 1000);
}

function updateClock() {
  const el = document.getElementById('rpTime');
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit', hour12: true, timeZone: 'Asia/Taipei'
  });
}

function updateTopbarDate() {
  const now = new Date();
  const month = document.getElementById('topbarMonth');
  const date = document.getElementById('topbarDate');
  if (month) month.textContent = now.toLocaleDateString('en-US', { month: 'long', year: 'numeric', timeZone: 'Asia/Taipei' });
  if (date) date.textContent = now.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric', timeZone: 'Asia/Taipei' });
}

// ── API fetch ──────────────────────────────────────────────────────────────
async function fetchBroadcast() {
  showLoading();
  try {
    const res = await fetch('/api/broadcast');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    broadcastData = await res.json();
    if (broadcastData.error) throw new Error(broadcastData.error);
    render(broadcastData);
    showContent();
  } catch (err) {
    showError(err.message || 'Unknown error');
  }
}

// ── Refresh ────────────────────────────────────────────────────────────────
function initRefreshButton() {
  const btn = document.getElementById('refreshBtn');
  if (btn) btn.addEventListener('click', triggerRefresh);
}

async function triggerRefresh() {
  const btn = document.getElementById('refreshBtn');
  if (btn) { btn.classList.add('spinning'); btn.disabled = true; }
  showLoading();
  try {
    const res = await fetch('/api/refresh', { method: 'POST' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    broadcastData = data;
    render(broadcastData);
    showContent();
    document.getElementById('audioPlayer').load();
  } catch (err) {
    showError(err.message || 'Refresh failed');
  } finally {
    if (btn) { btn.classList.remove('spinning'); btn.disabled = false; }
  }
}

// ── Render ─────────────────────────────────────────────────────────────────
function render(data) {
  const slices = data.slices || {};
  const proc = data.processed_data || {};

  renderOverviewCards(proc);
  renderRightPanel(proc, slices);
  renderWeeklyChart(proc, slices);

  renderMe(slices.me, data);
  renderSpouse(slices.spouse);
  renderDad(slices.dad);
  renderKids(slices.kids, data.audio_urls);

  // Audio URLs
  const urls = data.audio_urls || {};
  audioSrc.me = urls.full_audio_url || null;
  audioSrc.spouse = urls.full_audio_url || null;
  audioSrc.dad = urls.full_audio_url || null;
  audioSrc.kids = urls.kids_audio_url || null;

  // Footer timestamp
  const ts = data.generated_at || '';
  if (ts) {
    document.getElementById('generatedAt').textContent =
      'Generated: ' + new Date(ts).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' });
  }
}

// ── Overview Cards ─────────────────────────────────────────────────────────
function renderOverviewCards(proc) {
  const cur = proc.current || {};

  // Wind Speed
  const wdsd = cur.WDSD;
  setText('ov-wind-val', wdsd != null ? `${wdsd} m/s` : '—');
  clearDelta('ov-wind-delta');

  // Rain Chance — pull from first available forecast segment
  const segs = proc.forecast_segments || {};
  const firstSeg = segs.Morning || segs.Afternoon || segs.Evening || segs.Night || null;
  const rainPct = firstSeg && firstSeg.pop != null ? firstSeg.pop : null;
  setText('ov-rain-val', rainPct != null ? `${rainPct}%` : '—');
  clearDelta('ov-rain-delta');

  // Pressure — not in data, show AQI as substitute with note
  const aqi = cur.aqi;
  setText('ov-pressure-val', aqi != null ? `AQI ${aqi}` : '—');
  const aqiStatus = cur.aqi_status || '';
  setDelta('ov-pressure-delta', aqiStatus, null);

  // UV Index — placeholder (not in API data yet)
  setText('ov-uv-val', '—');
  clearDelta('ov-uv-delta');
}

// ── Right Panel ────────────────────────────────────────────────────────────
function renderRightPanel(proc, slices) {
  const cur = proc.current || {};

  // Location from station name
  const stationName = cur.station_name || '—';
  setText('rpCity', stationName);
  setText('rpRegion', 'Taiwan');

  // Weather icon & temp
  const dadSlice = (slices.dad && slices.dad.cards) || [];
  const condCard = dadSlice.find(c => c.id === 'conditions');
  const iconKey = condCard ? (condCard.icon || 'cloudy') : 'cloudy';
  setText('rpWeatherIcon', ICONS[iconKey] || '⛅');

  const temp = cur.AT ?? null;
  setText('rpTemp', temp != null ? `${temp}° C` : '—');

  const wx = cur.Wx || cur.beaufort_desc || '—';
  setText('rpCondition', wx);

  // Hourly rain bars — build from forecast segments
  const segs = proc.forecast_segments || {};
  const segMap = [
    { label: 'Morning', key: 'Morning' },
    { label: 'Afternoon', key: 'Afternoon' },
    { label: 'Evening', key: 'Evening' },
    { label: 'Night', key: 'Night' },
  ];

  const bars = document.getElementById('rpRainBars');
  if (bars) {
    bars.innerHTML = '';
    const available = segMap.filter(s => segs[s.key] && segs[s.key].pop != null);
    const toShow = available.length ? available : segMap;

    toShow.forEach(s => {
      const seg = segs[s.key] || {};
      const pct = seg.pop != null ? seg.pop : null;
      const row = document.createElement('div');
      row.className = 'rp-rain-row';
      row.innerHTML = `
        <span class="rp-rain-label">${s.label.slice(0, 3)}</span>
        <div class="rp-bar-track">
          <div class="rp-bar-fill" style="width:${pct != null ? pct : 0}%"></div>
        </div>
        <span class="rp-rain-pct">${pct != null ? pct + '%' : '—'}</span>
      `;
      bars.appendChild(row);
    });
  }

  // Sunrise & Sunset — compute from Taiwan location (fixed approximations)
  const now = new Date();
  const twDate = now.toLocaleDateString('en-US', { timeZone: 'Asia/Taipei' });
  // Use approximate times for New Taipei
  const sunrise = new Date(`${twDate} 05:55 GMT+0800`);
  const sunset = new Date(`${twDate} 18:00 GMT+0800`);

  setText('rpSunrise', sunrise.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true, timeZone: 'Asia/Taipei' }));
  setText('rpSunset', sunset.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true, timeZone: 'Asia/Taipei' }));
  setText('rpSunLocation', stationName);

  const diffRise = Math.round((now - sunrise) / 60000);
  const diffSet = Math.round((sunset - now) / 60000);

  setText('rpSunriseAgo', diffRise > 0 ? `${fmtMinutes(diffRise)} ago` : 'soon');
  setText('rpSunsetIn', diffSet > 0 ? `in ${fmtMinutes(diffSet)}` : 'passed');
}

function fmtMinutes(mins) {
  if (mins < 60) return `${mins}m`;
  return `${Math.floor(mins / 60)}h ${mins % 60}m`;
}

// ── Weekly Chart ────────────────────────────────────────────────────────────
function renderWeeklyChart(proc, slices) {
  const segs = proc.forecast_segments || {};
  const stationName = (proc.current || {}).station_name || '—';
  setText('chartLocationText', stationName);

  // Build temperature data from segments or use illustrative placeholders
  const labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4'];
  // Use current temp + simulated weekly trend
  const baseTemp = (proc.current || {}).AT ?? 20;
  const dataPoints = [
    Math.round(baseTemp - 3 + Math.random() * 2),
    Math.round(baseTemp - 1 + Math.random() * 2),
    Math.round(baseTemp + 1 + Math.random() * 2),  // peak — current week
    Math.round(baseTemp + 0 + Math.random() * 3),
  ];

  const ctx = document.getElementById('tempChart');
  if (!ctx) return;

  if (tempChart) { tempChart.destroy(); }

  // Generate smooth gradient
  const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 160);
  gradient.addColorStop(0, 'rgba(44, 92, 230, 0.18)');
  gradient.addColorStop(1, 'rgba(44, 92, 230, 0.00)');

  tempChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Temperature (°C)',
        data: dataPoints,
        borderColor: '#2b5ce6',
        backgroundColor: gradient,
        borderWidth: 2.5,
        pointRadius: dataPoints.map((_, i) => i === 2 ? 7 : 3),
        pointBackgroundColor: dataPoints.map((_, i) => i === 2 ? '#2b5ce6' : '#fff'),
        pointBorderColor: '#2b5ce6',
        pointBorderWidth: 2,
        tension: 0.45,
        fill: true,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.raw}° C`,
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#7a8ca0', font: { size: 11, family: 'Inter' } },
          border: { display: false },
        },
        y: {
          grid: {
            color: '#e8ecf3',
            drawTicks: false,
          },
          ticks: {
            color: '#7a8ca0',
            font: { size: 11, family: 'Inter' },
            callback: v => v + '°',
            maxTicksLimit: 5,
          },
          border: { display: false },
        }
      }
    }
  });
}

// ── Me (Full View) ─────────────────────────────────────────────────────────
function renderMe(slice, fullData) {
  const grid = document.getElementById('cards-me');
  grid.innerHTML = '';
  if (!slice) return;

  slice.cards.forEach(card => {
    if (card.omit_if_empty && !card.text) return;
    const wide = ['forecast', 'accuracy'].includes(card.id);
    grid.appendChild(makeCard(card.title, card.text, { wide }));
  });

  document.getElementById('rawData').textContent =
    JSON.stringify(fullData, null, 2);
}

// ── Spouse ─────────────────────────────────────────────────────────────────
function renderSpouse(slice) {
  const grid = document.getElementById('cards-spouse');
  grid.innerHTML = '';
  if (!slice) return;

  slice.cards.forEach(card => {
    if (card.omit_if_empty && !card.text) return;
    grid.appendChild(makeCard(card.title, card.text));
  });

  const hazards = slice.commute_hazards || {};
  const allHazards = [...(hazards.morning || []), ...(hazards.evening || [])];
  if (allHazards.length > 0) {
    const el2 = makeCard('⚠️ Driving Hazards', allHazards.join('\n'), { warn: true });
    grid.insertBefore(el2, grid.firstChild);
  }
}

// ── Dad ────────────────────────────────────────────────────────────────────
function renderDad(slice) {
  const grid = document.getElementById('cards-dad');
  grid.innerHTML = '';
  if (!slice) return;

  slice.cards.forEach(card => {
    const cardEl = makeCard(card.title, card.text, { cardiac: card.cardiac_warning });

    if (card.id === 'conditions') {
      const icon = ICONS[card.icon] || '🌤️';
      const iconEl = document.createElement('div');
      iconEl.style.cssText = 'font-size:2.5rem;margin-bottom:8px;';
      iconEl.textContent = icon;
      cardEl.insertBefore(iconEl, cardEl.querySelector('.card-text'));

      if (card.aqi != null) {
        const badge = document.createElement('div');
        badge.className = 'aqi-badge ' + aqiClass(card.aqi);
        badge.textContent = `AQI ${card.aqi}${card.aqi_status ? ' — ' + card.aqi_status : ''}`;
        cardEl.appendChild(badge);
      }
    }
    grid.appendChild(cardEl);
  });
}

// ── Kids ───────────────────────────────────────────────────────────────────
function renderKids(slice, audioUrls) {
  const container = document.getElementById('kids-content');
  container.innerHTML = '';
  if (!slice) return;

  const iconWrap = el('div', 'kids-icon-wrap');
  iconWrap.textContent = ICONS[slice.icon] || '🌤️';
  iconWrap.title = 'Tap to hear the weather!';
  iconWrap.addEventListener('click', () => {
    const src = (audioUrls || {}).kids_audio_url;
    if (src) playAudio(src);
  });

  const feels = el('p', 'kids-feels', slice.feels_like || '');
  const wardrobe = el('p', 'kids-wardrobe', slice.wardrobe || '');
  const fact = el('p', 'kids-fun-fact', slice.fun_fact || '');

  container.append(iconWrap, feels, wardrobe, fact);
}

// ── Card factory ───────────────────────────────────────────────────────────
function makeCard(title, text, opts = {}) {
  const card = document.createElement('div');
  let cls = 'card';
  if (opts.wide) cls += ' card-wide';
  if (opts.cardiac) cls += ' cardiac';
  if (opts.warn) cls += ' cardiac';
  card.className = cls;
  card.append(el('h2', 'card-title', title), el('p', 'card-text', text));
  return card;
}

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text) e.textContent = text;
  return e;
}

function aqiClass(aqi) {
  if (aqi <= 50) return 'aqi-good';
  if (aqi <= 100) return 'aqi-moderate';
  return 'aqi-poor';
}

function setText(id, val) {
  const el2 = document.getElementById(id);
  if (el2) el2.textContent = val;
}

function setDelta(id, val, direction) {
  const el2 = document.getElementById(id);
  if (!el2) return;
  el2.textContent = val || '';
  el2.className = 'ov-delta' + (direction === 'up' ? ' up' : direction === 'down' ? ' down' : '');
}

function clearDelta(id) {
  const el2 = document.getElementById(id);
  if (el2) { el2.textContent = ''; el2.className = 'ov-delta'; }
}

// ── Sidebar Nav / Profile Switcher ─────────────────────────────────────────
function initSidebarNav() {
  document.querySelectorAll('.nav-item[data-profile]').forEach(btn => {
    btn.addEventListener('click', () => switchProfile(btn.dataset.profile));
  });
}

function switchProfile(profile) {
  currentProfile = profile;

  document.querySelectorAll('.nav-item[data-profile]').forEach(btn => {
    const isActive = btn.dataset.profile === profile;
    btn.classList.toggle('active', isActive);
    btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
  });

  document.querySelectorAll('.profile-view').forEach(view => {
    view.classList.toggle('active', view.id === `view-${profile}`);
  });

  const src = audioSrc[profile];
  if (src) {
    const player = document.getElementById('audioPlayer');
    if (player.src !== src) {
      player.src = src;
      player.load();
      resetAudioUI();
    }
  }

  document.body.classList.toggle('dad-mode', profile === 'dad');
}

// ── Audio Player ───────────────────────────────────────────────────────────
function initAudioPlayer() {
  const player = document.getElementById('audioPlayer');
  const playBtn = document.getElementById('playBtn');
  const progress = document.getElementById('audioProgress');
  const timeEl = document.getElementById('audioTime');
  const progWrap = document.querySelector('.audio-progress-wrap');

  playBtn.addEventListener('click', () => {
    if (!player.src && audioSrc[currentProfile]) player.src = audioSrc[currentProfile];
    if (player.paused) { player.play().catch(() => { }); }
    else { player.pause(); }
  });

  player.addEventListener('play', () => {
    playBtn.querySelector('.play-icon').textContent = '⏸';
    playBtn.querySelector('.play-label').textContent = 'Pause';
  });

  player.addEventListener('pause', () => {
    playBtn.querySelector('.play-icon').textContent = '▶';
    playBtn.querySelector('.play-label').textContent = 'Play Broadcast';
  });

  player.addEventListener('timeupdate', () => {
    if (!player.duration) return;
    const pct = (player.currentTime / player.duration) * 100;
    progress.style.width = pct + '%';
    timeEl.textContent = fmtTime(player.currentTime);
  });

  player.addEventListener('ended', resetAudioUI);

  progWrap.addEventListener('click', e => {
    if (!player.duration) return;
    const rect = progWrap.getBoundingClientRect();
    player.currentTime = ((e.clientX - rect.left) / rect.width) * player.duration;
  });

  document.querySelectorAll('.speed-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      player.playbackRate = parseFloat(btn.dataset.speed);
      document.querySelectorAll('.speed-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });
}

function playAudio(src) {
  const player = document.getElementById('audioPlayer');
  player.src = src;
  player.play().catch(() => { });
}

function resetAudioUI() {
  document.querySelector('.play-icon').textContent = '▶';
  document.querySelector('.play-label').textContent = 'Play Broadcast';
  document.getElementById('audioProgress').style.width = '0%';
  document.getElementById('audioTime').textContent = '0:00';
}

function fmtTime(secs) {
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

// ── Raw Data Toggle ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('rawToggleBtn');
  const raw = document.getElementById('rawData');
  if (btn && raw) {
    btn.addEventListener('click', () => {
      const showing = !raw.classList.contains('hidden');
      raw.classList.toggle('hidden', showing);
      btn.textContent = showing ? 'Show Raw Data' : 'Hide Raw Data';
    });
  }
});

// ── UI State Helpers ───────────────────────────────────────────────────────
function showLoading() {
  document.getElementById('loadingScreen').classList.remove('hidden');
  document.getElementById('errorScreen').classList.add('hidden');
  document.getElementById('mainContent').classList.add('hidden');
}

function showContent() {
  document.getElementById('loadingScreen').classList.add('hidden');
  document.getElementById('errorScreen').classList.add('hidden');
  document.getElementById('mainContent').classList.remove('hidden');

  const src = audioSrc[currentProfile];
  if (src) document.getElementById('audioPlayer').src = src;
}

function showError(msg) {
  document.getElementById('loadingScreen').classList.add('hidden');
  document.getElementById('mainContent').classList.add('hidden');
  document.getElementById('errorScreen').classList.remove('hidden');
  document.getElementById('errorMsg').textContent = msg;
}
