/**
 * app.js — Family Weather Dashboard frontend logic.
 *
 * Responsibilities:
 *  - Fetch broadcast JSON from /api/broadcast
 *  - Render per-profile cards (Me, Spouse, Dad, Kids)
 *  - Handle profile switching
 *  - Audio player with progress tracking
 *  - Raw data toggle (Me view)
 */

'use strict';

// ── State ──────────────────────────────────────────────────────────────────
let broadcastData = null;
let currentProfile = 'me';
let audioSrc = { me: null, spouse: null, dad: null, kids: null };

// Weather icon emoji map
const ICONS = {
  'sunny':          '☀️',
  'partly-cloudy':  '⛅',
  'cloudy':         '☁️',
  'rainy':          '🌧️',
};

// ── Boot ───────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  window.app = { fetchBroadcast };
  initProfileSwitcher();
  initAudioPlayer();
  fetchBroadcast();
});

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

// ── Render ─────────────────────────────────────────────────────────────────
function render(data) {
  const slices = data.slices || {};

  renderMe(slices.me, data);
  renderSpouse(slices.spouse);
  renderDad(slices.dad);
  renderKids(slices.kids, data.audio_urls);

  // Store audio URLs keyed by profile
  const urls = data.audio_urls || {};
  audioSrc.me     = urls.full_audio_url || null;
  audioSrc.spouse = urls.full_audio_url || null;
  audioSrc.dad    = urls.full_audio_url || null;
  audioSrc.kids   = urls.kids_audio_url || null;

  // Footer timestamp
  const ts = data.generated_at || '';
  if (ts) {
    document.getElementById('generatedAt').textContent =
      'Generated: ' + new Date(ts).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' });
  }
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

  // Raw data
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

  // Hazard callouts
  const hazards = slice.commute_hazards || {};
  const allHazards = [...(hazards.morning || []), ...(hazards.evening || [])];
  if (allHazards.length > 0) {
    const el = makeCard('⚠️ Driving Hazards', allHazards.join('\n'), { warn: true });
    grid.insertBefore(el, grid.firstChild);
  }
}

// ── Dad ────────────────────────────────────────────────────────────────────
function renderDad(slice) {
  const grid = document.getElementById('cards-dad');
  grid.innerHTML = '';
  if (!slice) return;

  slice.cards.forEach(card => {
    const isCardiac = card.cardiac_warning;
    const cardEl = makeCard(card.title, card.text, { cardiac: isCardiac });

    // Conditions card: add icon + AQI badge
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
  if (opts.wide)    cls += ' card-wide';
  if (opts.cardiac) cls += ' cardiac';
  if (opts.warn)    cls += ' cardiac'; // reuse styling
  card.className = cls;

  const h = el('h2', 'card-title', title);
  const p = el('p', 'card-text', text);
  card.append(h, p);
  return card;
}

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls)  e.className = cls;
  if (text) e.textContent = text;
  return e;
}

function aqiClass(aqi) {
  if (aqi <= 50)  return 'aqi-good';
  if (aqi <= 100) return 'aqi-moderate';
  return 'aqi-poor';
}

// ── Profile Switcher ───────────────────────────────────────────────────────
function initProfileSwitcher() {
  document.querySelectorAll('.profile-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const profile = btn.dataset.profile;
      switchProfile(profile);
    });
  });
}

function switchProfile(profile) {
  currentProfile = profile;

  // Update buttons
  document.querySelectorAll('.profile-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.profile === profile);
    btn.setAttribute('aria-selected', btn.dataset.profile === profile ? 'true' : 'false');
  });

  // Update views
  document.querySelectorAll('.profile-view').forEach(view => {
    view.classList.toggle('active', view.id === `view-${profile}`);
  });

  // Update audio source
  const src = audioSrc[profile];
  if (src) {
    const player = document.getElementById('audioPlayer');
    if (player.src !== src) {
      player.src = src;
      player.load();
      resetAudioUI();
    }
  }

  // Dad view: toggle accessibility class on body
  document.body.classList.toggle('dad-mode', profile === 'dad');
}

// ── Audio Player ───────────────────────────────────────────────────────────
function initAudioPlayer() {
  const player   = document.getElementById('audioPlayer');
  const playBtn  = document.getElementById('playBtn');
  const progress = document.getElementById('audioProgress');
  const timeEl   = document.getElementById('audioTime');
  const progWrap = document.querySelector('.audio-progress-wrap');

  playBtn.addEventListener('click', () => {
    if (!player.src && audioSrc[currentProfile]) {
      player.src = audioSrc[currentProfile];
    }
    if (player.paused) {
      player.play().catch(() => {});
    } else {
      player.pause();
    }
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

  // Seek on click
  progWrap.addEventListener('click', e => {
    if (!player.duration) return;
    const rect = progWrap.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    player.currentTime = ratio * player.duration;
  });
}

function playAudio(src) {
  const player = document.getElementById('audioPlayer');
  player.src = src;
  player.play().catch(() => {});
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

// ── Raw Data Toggle (Me view) ──────────────────────────────────────────────
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

// ── UI state helpers ───────────────────────────────────────────────────────
function showLoading() {
  document.getElementById('loadingScreen').classList.remove('hidden');
  document.getElementById('errorScreen').classList.add('hidden');
  document.getElementById('mainContent').classList.add('hidden');
}

function showContent() {
  document.getElementById('loadingScreen').classList.add('hidden');
  document.getElementById('errorScreen').classList.add('hidden');
  document.getElementById('mainContent').classList.remove('hidden');

  // Set initial audio source
  const src = audioSrc[currentProfile];
  if (src) {
    const player = document.getElementById('audioPlayer');
    player.src = src;
  }
}

function showError(msg) {
  document.getElementById('loadingScreen').classList.add('hidden');
  document.getElementById('mainContent').classList.add('hidden');
  const errScreen = document.getElementById('errorScreen');
  errScreen.classList.remove('hidden');
  document.getElementById('errorMsg').textContent = msg;
}
