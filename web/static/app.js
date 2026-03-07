/**
 * app.js — Canopy / 厝邊天氣 frontend logic (v4 — Revamp).
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
    span.textContent = `${(window._T_runtime_error || 'Runtime Error: ')}${msg}`;
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
let LOADING_MSGS = []; // Populated by applyLanguage

const CACHE_KEY = 'weather_broadcast_cache';
const CACHE_MAX_AGE_MS = 24 * 60 * 60 * 1000; // 24 hours

// ── Weather text localisation map (CWA API → English) ──────────────────────
const WEATHER_TEXT_EN = {
  '晴': 'Sunny',
  '晴時多雲': 'Partly Cloudy',
  '多雲時晴': 'Mostly Sunny',
  '多雲': 'Cloudy',
  '陰': 'Overcast',
  '陰時多雲': 'Mostly Cloudy',
  '多雲時陰': 'Mostly Cloudy',
  '短暫雨': 'Brief Rain',
  '短暫陣雨': 'Brief Showers',
  '陣雨': 'Showers',
  '雨': 'Rain',
  '大雨': 'Heavy Rain',
  '豪雨': 'Torrential Rain',
  '短暫雷陣雨': 'Brief Thunderstorms',
  '雷陣雨': 'Thunderstorms',
  '有霧': 'Foggy',
  '霧': 'Fog',
  '有靄': 'Hazy',
};

function localiseWeatherText(text) {
  if (getLang() === 'en') return WEATHER_TEXT_EN[text] || text;
  return text;
}

const LOCATION_EN = {
  // ── CWA Station names (as returned by StationName field) ──────────────
  '桃改臺北': 'Shulin Station',   // 72AI40 — home station
  '桃改台北': 'Shulin Station',   // alternate romanisation
  '板橋': 'Banqiao Station',  // C0AJ80 — work station
  '新北': 'Xindian Stn.',     // 466881 — synoptic fallback
  '樹林': 'Shulin Station',   // 72AI40 auto name
  // ── Township district names (from forecast location names) ────────────
  '樹林區': 'Shulin',
  '板橋區': 'Banqiao',
  '三峽區': 'Sanxia',
  '三重': 'Sanchong',
  '中和': 'Zhonghe',
  '永和': 'Yonghe',
  '新莊': 'Xinzhuang',
  '土城': 'Tucheng',
  '蘆洲': 'Luzhou',
  '鶯歌': 'Yingge',
  '淡水': 'Tamsui',
  '汐止': 'Xizhi',
  '瑞芳': 'Ruifang',
  '深坑': 'Shenkeng',
  '石碇': 'Shiding',
  '坪林': 'Pinglin',
  '烏來': 'Wulai',
  '八里': 'Bali',
  '林口': 'Linkou',
  '五股': 'Wugu',
  '泰山': 'Taishan',
};

function localiseLocation(name) {
  if (getLang() === 'en') return LOCATION_EN[name] || name;
  // zh-TW: map raw station names to friendly district labels
  const ZH_STATION = {
    '桃改臺北': '樹林站',
    '桃改台北': '樹林站',
    '樹林': '樹林站',
    '板橋': '板橋站',
    '新北': '新店站',
  };
  return ZH_STATION[name] || name;
}

function localiseMetric(text) {
  if (!text) return '';
  return (T.metrics && T.metrics[text]) ? T.metrics[text] : text;
}

function localisePrecipText(text) {
  if (!text) return '—';
  if (getLang() !== 'zh-TW') return text;
  if (text === 'All clear') return '不會降雨';
  if (text === 'Stay in') return '建議待室內';
  const m = text.match(/^~(\d+)\s*min$/);
  if (m) return `約 ${m[1]} 分鐘`;
  return text;
}

const IMG = (name, alt) =>
  `<img src="/static/brand-icons/${name}.webp" class="brand-icon" alt="${alt}" />`;

const ICONS = {
  'sunny': IMG('sunny', 'Sunny'), 'Sunny/Clear': IMG('sunny', 'Sunny'), '1': IMG('sunny', 'Sunny'),
  'partly-cloudy': IMG('partly-cloudy', 'Partly Cloudy'), 'Mixed Clouds': IMG('partly-cloudy', 'Partly Cloudy'),
  '2': IMG('partly-cloudy', 'Partly Cloudy'), '3': IMG('partly-cloudy', 'Partly Cloudy'),
  'cloudy': IMG('cloudy', 'Cloudy'), 'Overcast': IMG('cloudy', 'Cloudy'),
  '4': IMG('cloudy', 'Cloudy'), '5': IMG('cloudy', 'Cloudy'), '6': IMG('cloudy', 'Cloudy'), '7': IMG('cloudy', 'Cloudy'),
  'rainy': IMG('rainy', 'Rainy'),
  '8': IMG('rainy', 'Rainy'), '9': IMG('rainy', 'Rainy'), '10': IMG('rainy', 'Rainy'),
  '11': IMG('rainy', 'Rainy'), '12': IMG('rainy', 'Rainy'), '13': IMG('rainy', 'Rainy'),
  '14': IMG('rainy', 'Rainy'), '15': IMG('rainy', 'Rainy'), '16': IMG('rainy', 'Rainy'),
  '17': IMG('rainy', 'Rainy'), '18': IMG('rainy', 'Rainy'), '19': IMG('rainy', 'Rainy'), '20': IMG('rainy', 'Rainy'),
};

// ── Translations ───────────────────────────────────────────────────────────
const TRANSLATIONS = {
  en: {
    loading: 'Fetching forecast…',
    error_prefix: 'Error: ',
    last_updated: 'updated: ',
    ground: 'Ground',
    wind: 'Wind',
    humidity: 'Humidity',
    air_quality: 'Air Quality',
    uv: 'UV Index',
    pressure: 'Pressure',
    feels_like: 'Feels like',
    rain: 'Rain',
    outdoor: 'Outdoor',
    days: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
    night: 'Night', day: 'Day',
    cloudCover: { Sunny: 'Sunny', Fair: 'Fair', 'Mixed Clouds': 'Cloudy', Overcast: 'Overcast', Rain: 'Rain', Unknown: '—' },
    cardiac_title: 'Cardiac Alert',
    cardiac_guidance: 'Keep warm and avoid sudden cold exposure.',
    menieres_title: "Ménière's Alert",
    menieres_guidance: 'Watch for vertigo or ear fullness; stay hydrated.',
    heads_up_title: 'Heads Up',
    aqi_title: "Tomorrow's Air Quality",
    wardrobe: 'Wardrobe',
    rain_gear: 'Rain Gear',
    commute: 'Commute',
    garden: 'Garden Health',
    outdoor_act: 'Outdoor Activities',
    meals: 'Meals',
    hvac: 'HVAC Advice',
    outdoor_aqi_warn: '⚠ Outdoor score reduced — AQI ',
    best_label: 'Best',
    top_label: 'Top',
    boot: 'System Boot: Initiating connection…',
    data_ok: 'Data received successfully.',
    render: 'Pipeline success. Rendering…',
    step1: 'Connecting to CWA Shulin Station…',
    step2: 'Retrieving Township Forecasts…',
    step3: 'Checking MOENV Air Quality…',
    step4: 'Processing Logic…',
    step5: 'Generating Narration…',
    step6: 'Synthesizing Audio…',
    step7: 'Finalizing…',
    // Static panel labels
    nav_section: 'Views',
    nav_lifestyle: 'Lifestyle',
    nav_dashboard: 'Canopy',
    h1_lifestyle: 'Lifestyle',
    h1_dashboard: 'Canopy',
    h2_24h: '24-Hour Forecast',
    h2_7day: '7-Day Forecast',
    lang_label: 'Language',
    theme_label: 'Theme',
    system_controls: 'System Controls',
    refresh_btn: 'Refresh',
    tab_narration: 'Narration',
    tab_settings: 'Settings',
    log_requesting: 'Requesting narration via: ',
    log_title: 'System Log',
    log_step_prefix: 'Step: ',
    log_runtime_error: 'Runtime Error: ',
  },
  'zh-TW': {
    loading: '正在獲取天氣…',
    error_prefix: '錯誤：',
    last_updated: '更新：',
    ground: '地面狀況',
    wind: '風速',
    humidity: '濕度',
    air_quality: '空氣品質',
    uv: '紫外線',
    pressure: '氣壓',
    feels_like: '體感溫度',
    rain: '降雨',
    outdoor: '戶外',
    days: ['日', '一', '二', '三', '四', '五', '六'],
    night: '晚', day: '早',
    cloudCover: { Sunny: '晴', Fair: '晴多雲', 'Mixed Clouds': '多雲', Overcast: '陰', Rain: '雨', Unknown: '—' },
    cardiac_title: '心臟警示',
    cardiac_guidance: '請保持溫暖，避免突然暴露於冷空氣中。',
    menieres_title: '梅尼爾氏症警示',
    menieres_guidance: '注意眩暈或耳鳴；多補充水分。',
    heads_up_title: '注意事項',
    aqi_title: '明日空氣品質',
    wardrobe: '穿搭建議',
    rain_gear: '雨具準備',
    commute: '通勤狀況',
    garden: '花園照護',
    outdoor_act: '戶外活動',
    meals: '餐食建議',
    hvac: '空調建議',
    outdoor_aqi_warn: '⚠ 戶外指數降低 — AQI ',
    best_label: '最佳時段',
    top_label: '推薦活動',
    boot: '系統啟動：初始化連線…',
    data_ok: '資料接收成功。',
    render: '管道成功，正在渲染…',
    step1: '連線至 CWA 樹林站…',
    step2: '取得鄉鎮預報…',
    step3: '查詢 MOENV 空氣品質…',
    step4: '處理天氣邏輯…',
    step5: '生成廣播稿…',
    step6: '合成語音…',
    step7: '最終處理中…',
    // Static panel labels
    nav_section: '功能',
    nav_lifestyle: '生活建議',
    nav_dashboard: '厝邊天氣',
    h1_lifestyle: '生活建議',
    h1_dashboard: '厝邊天氣',
    h2_24h: '24 小時預報',
    h2_7day: '七日預報',
    lang_label: 'Language',
    theme_label: '外觀主題',
    system_controls: '系統控制',
    refresh_btn: '重新整理',
    tab_narration: '解說',
    tab_settings: '設定',
    log_requesting: '請求廣播（提供者）：',
    log_title: '系統記錄',
    log_step_prefix: '步驟：',
    log_runtime_error: '執行錯誤：',
    metrics: {
      'Near Saturated': '接近飽和', 'Clammy': '悶濕',
      'Very Dry': '極度乾燥', 'Dry': '乾燥', 'Comfortable': '舒適', 'Muggy': '悶熱', 'Humid': '潮濕', 'Very Humid': '極度潮濕', 'Oppressive': '令人窒息',
      'Calm': '無風', 'Light air': '軟風', 'Light breeze': '輕風', 'Gentle breeze': '微風', 'Moderate breeze': '和風', 'Fresh breeze': '清風', 'Strong breeze': '強風', 'Near gale': '疾風', 'Gale': '大風', 'Strong gale': '烈風', 'Storm': '狂風', 'Violent storm': '暴風', 'Hurricane force': '颶風',
      'Good': '良好', 'Moderate': '普通', 'Unhealthy for Sensitive Groups': '對敏感族群不健康', 'Unhealthy': '不健康', 'Very Unhealthy': '非常不健康', 'Hazardous': '危害',
      'Go out': '適合外出', 'Good to go': '可以出門', 'Manageable': '勉強可行', 'Think twice': '建議斟酌', 'Stay in': '建議待室內',
      'Low': '低', 'High': '高', 'Very High': '極高', 'Extreme': '極端',
      'Safe': '安全', 'Wear Sunscreen': '需擦防曬', 'Seek Shade': '請避曬',
      'Unsettled': '不穩定', 'Normal': '正常', 'Stable': '穩定',
      'Very Poor': '極差', 'Poor': '差', 'Fair': '尚可', 'Excellent': '極佳',
      'Very Unlikely': '極不可能', 'Unlikely': '不太可能', 'Possible': '有可能', 'Likely': '很有可能', 'Very Likely': '極有可能', 'Unknown': '未知'
    },
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
  },
};


// Active translation map — updated by applyLanguage()
let T = TRANSLATIONS['zh-TW'];

// ── Cache helpers ───────────────────────────────────────────────────────────
function saveBroadcastCache(data) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ ts: new Date().toISOString(), data }));
  } catch (e) { /* private browsing — fail silently */ }
}

function loadCachedBroadcast() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const cached = JSON.parse(raw);
    if (!cached?.data || !cached?.ts) return null;
    if (Date.now() - new Date(cached.ts).getTime() > CACHE_MAX_AGE_MS) {
      localStorage.removeItem(CACHE_KEY);
      return null;
    }
    return cached; // { ts, data }
  } catch (e) { return null; }
}

function showStaleIndicator() {
  const el = document.getElementById('optimistic-loading');
  if (el) el.classList.remove('hidden');
}

function hideStaleIndicator() {
  const el = document.getElementById('optimistic-loading');
  if (el) el.classList.add('hidden');
}

// ── Boot ───────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  window.app = {
    fetchBroadcast,
    triggerRefresh
  };

  // Language must be applied first so T.boot is correct
  initSidebarControls();
  initSystemTheme();
  addLog(T.boot);

  initNav();
  initPlayerBar();
  initPlayerSheet();
  initSheetSettings();
  initRefreshButton();
  updateClock();
  setInterval(updateClock, 1000);

  const cached = loadCachedBroadcast();
  if (cached) {
    broadcastData = cached.data;
    render(broadcastData);
    showContent();
    showStaleIndicator();
    fetchBroadcast(true);
  } else {
    fetchBroadcast(false);
  }
});

// ── API fetch ──────────────────────────────────────────────────────────────
async function fetchBroadcast(silent = false) {
  if (!silent) showLoading();
  const btn = document.getElementById('refresh-btn');
  if (btn) btn.classList.add('loading');

  try {
    const url = new URL('/api/broadcast', window.location.origin);
    if (typeof getLang === 'function') url.searchParams.set('lang', getLang());
    const res = await fetch(url.toString());
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    broadcastData = await res.json();
    if (broadcastData.error) throw new Error(broadcastData.error);
    addLog(T.data_ok);
    render(broadcastData);
    saveBroadcastCache(broadcastData);
    showContent(); // also hides #optimistic-loading
  } catch (err) {
    addLog(`${T.error_prefix}${err.message || 'Unknown error'}`);
    if (!silent) {
      showError(err.message || 'Unknown error');
    } else {
      hideStaleIndicator();
    }
  } finally {
    if (btn) btn.classList.remove('loading');
  }
}

// ── Render Dispatch ────────────────────────────────────────────────────────
function render(data) {
  const slices = data.slices || {};

  // Render all views (they are hidden/shown via CSS class)
  renderCurrentView(slices.current);
  renderOverviewView(slices.overview);
  renderLifestyleView(slices.lifestyle);

  // Wire player bar — always called so transcript renders even without audio
  {
    const narrationSlice = data.slices && data.slices.narration;
    const paragraphs = narrationSlice ? (narrationSlice.paragraphs || []) : [];
    const meta = narrationSlice ? (narrationSlice.meta || {}) : {};
    const audioUrl = data.audio_urls && data.audio_urls.full_audio_url || null;
    if (window._playerBarSetAudio) {
      window._playerBarSetAudio(audioUrl, paragraphs, meta);
    }
  }

  // Footer / Meta
  const ts = data.generated_at || '';
  if (ts) {
    const d = new Date(ts);
    const m = d.getMonth() + 1;  // no leading zero
    const dd = String(d.getDate()).padStart(2, '0');
    const hh = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    setText('rp-last-updated', `${T.last_updated}${m}/${dd} ${hh}:${min}`);
  }
}

// ── View 1: Dashboard (Merged Current + Overview) ──────────────────────────
function renderCurrentView(data) {
  if (!data) return;
  setText('cur-temp', Math.round(data.temp) + '\u00b0');
  setText('cur-weather-text', localiseWeatherText(data.weather_text || '\u2014'));
  document.getElementById('cur-icon').innerHTML = ICONS[data.weather_code] || ICONS[data.weather_text] || IMG('partly-cloudy', 'Weather');
  setText('rp-location', localiseLocation(data.location || '\u2014'));
  const mobileLoc = document.getElementById('mobile-location');
  if (mobileLoc) mobileLoc.textContent = localiseLocation(data.location || '\u2014');

  // Gauge Cards
  renderGauge('gauge-ground', localiseMetric(data.ground_state), T.ground, '', `lvl-${data.ground_level}`);
  renderGauge('gauge-wind', localiseMetric(data.wind.text), T.wind, `${data.wind.val} m/s ${data.wind.dir || '\u2014'}`, `lvl-${data.wind.level}`);
  renderGauge('gauge-hum', localiseMetric(data.hum.text), T.humidity, data.hum.val + '%', `lvl-${data.hum.level}`, IMG('canopy-moisture', 'Humidity'));
  const aqiSub = data.aqi.pm25 != null ? `AQI ${data.aqi.val} \u00b7 PM2.5 ${data.aqi.pm25}` : `AQI ${data.aqi.val}`;
  renderGauge('gauge-aqi', localiseMetric(data.aqi.text), T.air_quality, aqiSub, `lvl-${data.aqi.level}`);
  renderGauge('gauge-uv', localiseMetric(data.uv.text), T.uv, `Index ${data.uv.val || 0}`, `lvl-${data.uv.level}`, IMG('uv-warning', 'UV'));
  renderGauge('gauge-pres', localiseMetric(data.pres.text), T.pressure, `${Math.round(data.pres.val)} hPa`, `lvl-${data.pres.level}`, IMG('pressure-drop', 'Pressure'));

  // Outdoor score trigger card (side stack)
  if (data.outdoor && data.outdoor.grade) {
    renderGauge('gauge-outdoor', localiseMetric(data.outdoor.label || ''), T.outdoor_act, '', `oi-grade-${data.outdoor.grade}`, IMG('outdoor', 'Outdoor'));
  } else {
    const oel = document.getElementById('gauge-outdoor');
    if (oel) oel.innerHTML = '';
  }

  // Wire expand/collapse toggle on outdoor trigger (idempotent — safe across re-renders)
  const outdoorTrigger = document.getElementById('gauge-outdoor');
  const gaugesPanel = document.getElementById('gauges-expand');
  if (outdoorTrigger && gaugesPanel && !outdoorTrigger._expandWired) {
    outdoorTrigger._expandWired = true;
    const toggle = () => {
      const expanded = outdoorTrigger.getAttribute('aria-expanded') === 'true';
      outdoorTrigger.setAttribute('aria-expanded', String(!expanded));
      gaugesPanel.setAttribute('aria-hidden', String(expanded));
      gaugesPanel.classList.toggle('gauges-collapsed', expanded);
    };
    outdoorTrigger.addEventListener('click', toggle);
    outdoorTrigger.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
    });
  }

  // Solar times
  const solar = data.solar;
  const solarRow = document.getElementById('solar-row');
  if (solar && solarRow) {
    document.getElementById('solar-sunrise').innerHTML = IMG('sunrise', 'Sunrise') + ' ' + solar.sunrise;
    document.getElementById('solar-sunset').innerHTML = IMG('sunset', 'Sunset') + ' ' + solar.sunset;
    solarRow.style.display = '';
  } else if (solarRow) {
    solarRow.style.display = 'none';
  }
}

function renderGauge(id, mainVal, label, subVal = '', valueClass = '', icon = '') {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = '';

  if (icon) {
    const ic = document.createElement('div');
    ic.className = 'gauge-icon';
    ic.innerHTML = icon;
    el.appendChild(ic);
  }

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

  // Timeline
  const timelineGrid = document.getElementById('ov-timeline');
  if (timelineGrid) {
    timelineGrid.innerHTML = '';
    const transitionMap = {};
    (data.transitions || []).forEach(t => { if (t.is_transition && t.from_segment) transitionMap[t.from_segment] = t; });

    (data.timeline || []).forEach((seg, idx) => {
      const origSlotName = seg.display_name || 'Forecast';
      const slotName = origSlotName;
      const card = document.createElement('div');
      // Determine if it is a night segment for styling
      const isNightSegment = () => {
        try {
          if (!seg.start_time) return false;
          const h = new Date(seg.start_time.replace('+08:00', '')).getHours();
          return h >= 18 || h < 6;
        } catch { return false; }
      };
      card.className = `time-card wk-card ${isNightSegment() ? 'wk-night' : 'wk-day'}`;
      const header = document.createElement('div');
      header.className = 'tc-header';
      header.textContent = (T.slots && T.slots[origSlotName]) ? T.slots[origSlotName] : origSlotName;
      const icon = document.createElement('div');
      icon.className = 'tc-icon';
      icon.innerHTML = ICONS[seg.cloud_cover] || ICONS[seg.Wx] || IMG('cloudy', 'Cloudy');
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

      if (seg.outdoor_grade) {
        const gradeToLvl = { A: 1, B: 2, C: 3, D: 4, F: 5 };
        const outdoorDisplay = localiseMetric(seg.outdoor_label) || seg.outdoor_grade;
        addRow(T.outdoor, outdoorDisplay, gradeToLvl[seg.outdoor_grade] || 0);
      }
      if (seg.aqi != null) {
        addRow('AQI', String(seg.aqi), aqiToLevel(seg.aqi));
      }
      card.appendChild(header);
      card.appendChild(icon);
      card.appendChild(temp);
      card.appendChild(details);

      const col = document.createElement('div');
      col.className = 'tc-col';
      col.appendChild(card);

      const nextSeg = data.timeline[idx + 1];
      const transition = nextSeg ? transitionMap[slotName] : null;
      if (transition && transition.is_transition) {
        const locTrans = (txt) => (T.transitions && T.transitions[txt]) ? T.transitions[txt] : txt;
        const parts = [];
        (transition.breaches || []).forEach(b => {
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
        });
        const t = document.createElement('div');
        t.className = 'tc-transition';
        t.textContent = `→ ${parts.length ? parts.join(' · ') : locTrans('change')}`;
        col.appendChild(t);
      }
      timelineGrid.appendChild(col);
    });
  }

  // 7-Day Timeline
  const weeklyTimelineEl = document.getElementById('ov-weekly-timeline');
  if (weeklyTimelineEl && data.weekly_timeline) {
    weeklyTimelineEl.className = 'weekly-grid';   // swap class
    weeklyTimelineEl.innerHTML = '';

    const isNightSlot = item => {
      try {
        const h = new Date(item.start_time.replace('+08:00', '')).getHours();
        return h >= 18 || h < 6;
      } catch { return false; }
    };

    let dayItems = data.weekly_timeline.filter(i => !isNightSlot(i));
    let nightItems = data.weekly_timeline.filter(i => isNightSlot(i));

    // Always start from "Tomorrow Day" — skip any current-day slots so the grid
    // is a consistent "next 7 days" view regardless of time or broadcast time.
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

    // Normalise both arrays to exactly 7 columns — pad with null, trim if over.
    while (dayItems.length < 7) dayItems.push(null);
    while (nightItems.length < 7) nightItems.push(null);
    dayItems = dayItems.slice(0, 7);
    nightItems = nightItems.slice(0, 7);

    const topItems = dayItems;
    const bottomItems = nightItems;

    // Column header row — day name shown once above both card rows
    const headerEl = document.getElementById('ov-weekly-header');
    if (headerEl) {
      headerEl.innerHTML = '';
      topItems.forEach(item => {
        const hdr = document.createElement('div');
        hdr.className = 'wk-col-header';
        if (item) {
          let dt;
          try { dt = new Date(item.start_time.replace('+08:00', '')); } catch { dt = new Date(); }
          hdr.textContent = T.days[dt.getDay()];
        } else {
          hdr.textContent = '—';
        }
        headerEl.appendChild(hdr);
      });
    }

    [...topItems, ...bottomItems].forEach(item => {
      const card = document.createElement('div');

      // If item is null (placeholder for missing end slot)
      if (!item) {
        card.className = 'wk-card wk-night wk-placeholder';
        const label = document.createElement('div');
        label.className = 'wk-label';
        const span = document.createElement('span');
        span.className = 'wk-day-name';
        span.textContent = '—';
        label.appendChild(span);
        card.appendChild(label);
        weeklyTimelineEl.appendChild(card);
        return;
      }

      let dt;
      try { dt = new Date(item.start_time.replace('+08:00', '')); } catch (e) { dt = new Date(); }
      const isNight = isNightSlot(item);
      const dayLabel = T.days[dt.getDay()];
      const periodLabel = isNight ? T.night : T.day;

      card.className = `wk-card ${isNight ? 'wk-night' : 'wk-day'}`;

      const label = document.createElement('div');
      label.className = 'wk-label';
      const daySpan = document.createElement('span');
      daySpan.className = 'wk-day-name';
      daySpan.textContent = dayLabel;
      label.appendChild(daySpan);

      const icon = document.createElement('div');
      icon.className = 'wk-icon';
      icon.innerHTML = ICONS[item.cloud_cover] || ICONS[item.Wx] || IMG('cloudy', 'Cloudy');

      const cond = document.createElement('div');
      cond.className = 'wk-cond';
      cond.textContent = (T.cloudCover && T.cloudCover[item.cloud_cover]) || item.cloud_cover || '—';

      const temp = document.createElement('div');
      temp.className = 'wk-temp';
      temp.textContent = `${Math.round(item.AT ?? 0)}°`;

      card.appendChild(label);
      card.appendChild(icon);
      card.appendChild(cond);
      card.appendChild(temp);
      weeklyTimelineEl.appendChild(card);
    });

    // 7-Day temperature sparkline (day = amber, night = blue)
    const sparkCanvas = document.getElementById('ov-weekly-sparkline');
    if (sparkCanvas) {
      // Build chart data directly from the rendered columns to guarantee perfect sync
      const sparkLabels = [];
      const sparkDay = [];
      const sparkNight = [];

      for (let i = 0; i < dayItems.length; i++) {
        const dItem = dayItems[i];
        const nItem = nightItems[i];

        let displayDt = null;
        if (dItem) {
          try { displayDt = new Date(dItem.start_time.replace('+08:00', '')); } catch (e) { }
        } else if (nItem) {
          try { displayDt = new Date(nItem.start_time.replace('+08:00', '')); } catch (e) { }
        }

        if (displayDt) {
          sparkLabels.push(T.days[displayDt.getDay()]);
        } else {
          sparkLabels.push('');
        }

        sparkDay.push(dItem ? Math.round(dItem.AT ?? 0) : null);
        sparkNight.push(nItem ? Math.round(nItem.AT ?? 0) : null);
      }

      const allVals = [...sparkDay, ...sparkNight].filter(v => v != null);

      // Snap axis to 5° grid; guarantee at least 3 gridlines (10° window)
      const dataMin = allVals.length ? Math.min(...allVals) : 15;
      const dataMax = allVals.length ? Math.max(...allVals) : 30;
      let axisMin = Math.floor(dataMin / 5) * 5;
      let axisMax = Math.ceil(dataMax / 5) * 5;
      if (axisMax === axisMin) axisMax = axisMin + 10;
      if (axisMax - axisMin < 10) axisMin = axisMax - 10;
      const gridVals = [];
      for (let v = axisMin; v <= axisMax; v += 5) gridVals.push(v);

      // halfCard = (gridWidth - 6 * gap) / 14
      // Setting layout.padding.left = layout.padding.right = halfCard ensures
      // that Chart.js places dot i of 7 exactly over card i's centre column.
      const gridWidth = weeklyTimelineEl.offsetWidth || sparkCanvas.parentElement.offsetWidth || 700;
      const halfCard = Math.max(16, Math.round((gridWidth - 24) / 14));

      // Read theme tokens at render time
      const cs = getComputedStyle(document.documentElement);
      const mutedColor = cs.getPropertyValue('--muted').trim() || '#8fa3c0';
      const surfaceColor = cs.getPropertyValue('--surface').trim() || '#ffffff';

      if (tempChart) { tempChart.destroy(); tempChart = null; }
      tempChart = new Chart(sparkCanvas, {
        type: 'line',
        data: {
          labels: sparkLabels,
          datasets: [
            {
              label: 'Day',
              data: sparkDay,
              borderColor: '#f0932b',
              tension: 0.35,
              pointRadius: 3,
              pointHoverRadius: 5,
              borderWidth: 2,
              spanGaps: true,
              fill: false,
            },
            {
              label: 'Night',
              data: sparkNight,
              borderColor: '#7da4ff',
              tension: 0.35,
              pointRadius: 3,
              pointHoverRadius: 5,
              borderWidth: 2,
              spanGaps: true,
              fill: false,
            },
          ],
        },
        plugins: [
          {
            id: 'sparklineExtras',
            // Fill plot area with surface colour (behind data lines)
            beforeDraw(chart) {
              const { ctx, chartArea } = chart;
              if (!chartArea) return;
              ctx.save();
              ctx.fillStyle = surfaceColor;
              ctx.fillRect(chartArea.left, chartArea.top, chartArea.width, chartArea.height);
              ctx.restore();
            },
            // Draw gridlines behind data lines
            beforeDatasetsDraw(chart) {
              const { ctx, chartArea, scales } = chart;
              if (!chartArea) return;
              ctx.save();
              ctx.strokeStyle = 'rgba(127, 140, 160, 0.25)';
              ctx.lineWidth = 1;
              gridVals.forEach(val => {
                const y = scales.y.getPixelForValue(val);
                ctx.beginPath();
                ctx.moveTo(chartArea.left, y);
                ctx.lineTo(chartArea.right, y);
                ctx.stroke();
              });
              ctx.restore();
            },
            // Draw axis labels in both padding zones (after everything else)
            afterDraw(chart) {
              const { ctx, chartArea, scales } = chart;
              if (!chartArea) return;
              ctx.save();
              ctx.font = `10px 'Fira Code', monospace`;
              ctx.fillStyle = mutedColor;
              ctx.textBaseline = 'middle';
              gridVals.forEach(val => {
                const y = scales.y.getPixelForValue(val);
                const label = `${val}°`;
                ctx.textAlign = 'right';
                ctx.fillText(label, chartArea.left - 22, y);
                ctx.textAlign = 'left';
                ctx.fillText(label, chartArea.right + 22, y);
              });
              ctx.restore();
            },
          },
        ],
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 400 },
          layout: { padding: { left: halfCard + 28, right: halfCard + 28 } },
          plugins: {
            legend: { display: false },
            tooltip: {
              mode: 'index',
              intersect: false,
              callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y}°` },
            },
          },
          scales: {
            x: { display: false },
            y: { display: false, min: axisMin, max: axisMax },
          },
        },
      });
    }
  }

}

function aqiToLevel(val) {
  const n = parseInt(val);
  if (isNaN(n)) return 0;
  if (n <= 50) return 1;
  if (n <= 100) return 2;
  if (n <= 150) return 3;
  if (n <= 200) return 4;
  return 5;
}

function translateAQIText(status) {
  // AQI status is returned in the active language directly — pass through.
  return status || '';
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
    ic.innerHTML = icon;
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

  // 1. Heads Up alert card (top position; only rendered when alerts exist)
  if (data.alert && data.alert.length > 0) {
    const hasCritical = data.alert.some(a => a.level === 'CRITICAL');
    const hasWarning = data.alert.some(a => a.level === 'WARNING');
    const card = document.createElement('div');
    let alertClass = 'ls-card ls-alert-card';
    if (hasCritical) alertClass += ' ls-alert-critical';
    else if (hasWarning) alertClass += ' ls-alert-warning';
    card.className = alertClass;
    const ic = document.createElement('div');
    ic.className = 'ls-icon';
    ic.innerHTML = hasCritical ? IMG('alert', 'Alert') : (hasWarning ? IMG('heads-up', 'Warning') : IMG('all-clear', 'Clear'));
    const content = document.createElement('div');
    content.className = 'ls-content';
    const ttl = document.createElement('div');
    ttl.className = 'ls-title';
    ttl.textContent = T.heads_up_title;
    content.appendChild(ttl);
    const TYPE_ICONS = {
      Health: IMG('heart-flag', 'Health'),
      Commute: IMG('commute', 'Commute'),
      Air: IMG('air-quality', 'Air Quality'),
      General: IMG('general', 'General'),
    };
    data.alert.forEach(item => {
      const row = document.createElement('div');
      row.className = 'ls-alert-item';
      const ico = document.createElement('span');
      ico.className = 'ls-alert-type-icon';
      ico.innerHTML = TYPE_ICONS[item.type] || IMG('general', 'General');
      const msg = document.createElement('span');
      msg.className = 'ls-alert-msg';
      msg.textContent = item.msg;
      const badge = document.createElement('span');
      badge.className = 'ls-badge ls-alert-badge-' + (item.level || 'WARNING').toLowerCase();
      badge.textContent = item.level || 'WARNING';
      row.appendChild(ico);
      row.appendChild(msg);
      row.appendChild(badge);
      content.appendChild(row);
    });
    card.appendChild(ic);
    card.appendChild(content);
    grid.appendChild(card);
  }
  // 2. Wardrobe (includes rain gear as sub-line)
  if (data.wardrobe) {
    const extras = [];
    if (data.wardrobe.feels_like != null) extras.push(mkSub(`${T.feels_like} ${Math.round(data.wardrobe.feels_like)}°`));
    if (data.wardrobe.rain_gear_text) extras.push(mkSub(`☂️ ${data.wardrobe.rain_gear_text}`));
    add(IMG('feels-like', 'Feels Like'), T.wardrobe, data.wardrobe.text, extras);
  }
  // 4. Commute
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
    add(IMG('commute', 'Commute'), T.commute, data.commute.text, extras);
  }
  // 5. Garden Health
  if (data.garden && data.garden.text) add(IMG('garden', 'Garden'), T.garden, data.garden.text);
  // 6. Outdoor Activities
  if (data.outdoor && data.outdoor.text) {
    const extras = [];
    if (data.outdoor.grade) extras.push(mkBadge(`oi-grade-${data.outdoor.grade}`, localiseMetric(data.outdoor.label || '')));
    if (data.outdoor.top_activity) extras.push(mkSub(`${T.best_label}: ${data.outdoor.best_window || ''} · ${T.top_label}: ${data.outdoor.top_activity}`));
    if (data.air_quality && data.air_quality.aqi != null && data.air_quality.aqi > 100) {
      extras.push(mkSub(`${T.outdoor_aqi_warn}${data.air_quality.aqi}`));
    }
    add(IMG('outdoor', 'Outdoor'), T.outdoor_act, data.outdoor.text, extras);
  }
  // 7. Meals
  if (data.meals && data.meals.text) {
    const extras = [];
    if (data.meals.mood) extras.push(mkBadge('mood-badge', data.meals.mood));
    add(IMG('meals', 'Meals'), T.meals, data.meals.text, extras);
  }
  // 8. HVAC Advice
  if (data.hvac) {
    const extras = [];
    if (data.hvac.mode) extras.push(mkBadge(`hvac-${data.hvac.mode.toLowerCase()}`, data.hvac.mode));
    const hvacMode = (data.hvac.mode || '').toLowerCase();
    const hvacIconName =
      hvacMode === 'cooling' ? 'cool-shade' :
        hvacMode === 'dehumidify' ? 'drip-warning' :
          (hvacMode === 'fan' || hvacMode === 'off') ? 'window-advice' :
            'hvac';
    add(IMG(hvacIconName, 'HVAC'), T.hvac, data.hvac.text, extras);
  }
  // 9. Air Quality (tomorrow's forecast) — moved to end
  if (data.air_quality && data.air_quality.text) {
    const extras = [];
    if (data.air_quality.aqi != null) {
      const lvl = aqiToLevel(data.air_quality.aqi);
      const statusText = data.air_quality.status || String(data.air_quality.aqi);
      extras.push(mkBadge(`lvl-${lvl}`, statusText));
    }
    if (data.air_quality.pm25 != null) {
      const pm25Parts = [`PM2.5 ${data.air_quality.pm25}`];
      if (data.air_quality.pm10 != null) pm25Parts.push(`PM10 ${data.air_quality.pm10}`);
      extras.push(mkSub(pm25Parts.join(' · ') + ' µg/m³'));
    }
    if (data.air_quality.peak_window) {
      extras.push(mkSub(`⚠ ${data.air_quality.peak_window}`));
    }
    add(IMG('air-quality', 'Air Quality'), T.air_quality, data.air_quality.text, extras);
  }
}

// ── System Theme ───────────────────────────────────────────────────────────
function initSystemTheme() {
  const mq = window.matchMedia('(prefers-color-scheme: dark)');
  const apply = () => {
    let override = 'light'; // Forced for Phase 1
    localStorage.setItem('theme', override);
    const isDark = override === 'dark';
    document.documentElement.classList.toggle('dark', isDark);
  };
  apply();
  window.setTheme = (val) => {
    localStorage.setItem('theme', val);
    apply();
  };
}

// ── Player Bar ─────────────────────────────────────────────────────────────
function initPlayerBar() {
  const bar = document.getElementById('player-bar');
  const audio = document.getElementById('player-audio');
  const playBtn = document.getElementById('player-play-btn');
  const icon = document.getElementById('player-play-icon');
  const progress = document.getElementById('player-progress-bar');
  const duration = document.getElementById('player-duration');
  const speedBtn = document.getElementById('player-speed-btn');  // desktop only

  if (!bar || !audio) return;

  bar.classList.add('loading');

  // ── Speed control ──────────────────────────────────────────────────────
  const SPEEDS = [1.0, 1.2, 1.5];
  let speed = parseFloat(localStorage.getItem('playerSpeed') || '1.2');
  if (!SPEEDS.includes(speed)) speed = 1.2;

  function applySpeed(s) {
    speed = s;
    audio.playbackRate = s;
    // Update desktop speed button text
    if (speedBtn) speedBtn.textContent = `${s}×`;
    // Update sheet speed pills
    document.querySelectorAll('.ps-speed-pill').forEach(pill => {
      pill.classList.toggle('active', parseFloat(pill.dataset.speed) === s);
    });
    localStorage.setItem('playerSpeed', String(s));
    if (audio.duration) {
      duration.textContent = `${formatTime(audio.currentTime / speed)} / ${formatTime(audio.duration / speed)}`;
      const sheetDur = document.getElementById('ps-duration');
      if (sheetDur) sheetDur.textContent = `${formatTime(audio.currentTime / speed)} / ${formatTime(audio.duration / speed)}`;
    }
  }

  applySpeed(speed);

  // Desktop speed button — cycles through speeds
  if (speedBtn) {
    speedBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const next = SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length];
      applySpeed(next);
    });
  }

  // Sheet speed pills
  document.querySelectorAll('.ps-speed-pill').forEach(pill => {
    pill.addEventListener('click', () => applySpeed(parseFloat(pill.dataset.speed)));
  });

  // ── Playback helpers ───────────────────────────────────────────────────
  function formatTime(s) {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60).toString().padStart(2, '0');
    return `${m}:${sec}`;
  }

  function setPlaying(playing) {
    icon.setAttribute('points', playing
      ? '4,3 8,3 8,17 4,17 M12,3 16,3 16,17 12,17'  // pause bars
      : '5,3 17,10 5,17'                              // play triangle
    );
  }

  audio.addEventListener('play', () => setPlaying(true));
  audio.addEventListener('pause', () => setPlaying(false));
  audio.addEventListener('ended', () => setPlaying(false));

  audio.addEventListener('timeupdate', () => {
    if (!audio.duration) return;
    const pct = `${(audio.currentTime / audio.duration) * 100}%`;
    progress.style.width = pct;
    duration.textContent = `${formatTime(audio.currentTime / speed)} / ${formatTime(audio.duration / speed)}`;
    // Sync sheet controls
    const sheetBar = document.getElementById('ps-progress-bar');
    if (sheetBar) sheetBar.style.width = pct;
    const sheetDur = document.getElementById('ps-duration');
    if (sheetDur) sheetDur.textContent = `${formatTime(audio.currentTime / speed)} / ${formatTime(audio.duration / speed)}`;
  });

  audio.addEventListener('loadedmetadata', () => {
    audio.playbackRate = speed;  // browsers reset playbackRate on src change
    duration.textContent = `0:00 / ${formatTime(audio.duration / speed)}`;
    const sheetDur = document.getElementById('ps-duration');
    if (sheetDur) sheetDur.textContent = `0:00 / ${formatTime(audio.duration / speed)}`;
  });

  playBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    if (audio.paused) audio.play();
    else audio.pause();
  });

  // Sheet progress bar: click to seek
  const sheetProgressWrap = document.getElementById('ps-progress-wrap');
  if (sheetProgressWrap) {
    sheetProgressWrap.addEventListener('click', (e) => {
      if (!audio.duration) return;
      const rect = sheetProgressWrap.getBoundingClientRect();
      const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      audio.currentTime = ratio * audio.duration;
    });
  }

  // Mobile: tap anywhere on bar (not play button) opens sheet
  bar.addEventListener('click', () => {
    if (window.matchMedia('(max-width: 767px)').matches) {
      const sheet = document.getElementById('player-sheet');
      if (sheet && !sheet.classList.contains('open')) {
        document.getElementById('player-sheet-toggle')?.click();
      }
    }
  });

  // On page load — warms Cloud Run instance before user clicks Play
  fetch('/api/warmup').catch(() => { });

  window._playerBarSetAudio = function (audioUrl, paragraphs, meta) {
    const audio = document.getElementById('player-audio');

    if (!audioUrl) {
      const date = broadcastData?.date || '';
      const slot = broadcastData?.slot || 'midday';
      const lang = getLang();
      const script = paragraphs.map(p => p.text).join('\n\n');

      const playBtn = document.getElementById('player-play-btn');

      const newBtn = playBtn.cloneNode(true);
      playBtn.parentNode.replaceChild(newBtn, playBtn);

      newBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (newBtn.classList.contains('fetching')) return;

        if (!audio.src || audio.src === location.href) {
          newBtn.classList.add('fetching');
          try {
            const res = await fetch('/api/tts', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ script, lang, date, slot }),
            });
            const { url } = await res.json();
            audio.src = url;
            audio.play();
          } catch (err) {
            console.error("TTS fetch failed", err);
          } finally {
            newBtn.classList.remove('fetching');
          }
        } else {
          audio.paused ? audio.play() : audio.pause();
        }
      });
    } else {
      audio.src = audioUrl;
    }

    bar.classList.remove('loading');
    audio.playbackRate = speed;  // set early; loadedmetadata will confirm

    const content = document.getElementById('ps-narration-content');
    if (!content) return;

    if (!paragraphs || !paragraphs.length) { content.textContent = ''; return; }

    const source = (meta && meta.source) ? meta.source.toLowerCase() : 'template';
    let html = '';
    paragraphs.forEach(p => {
      if (!p.text) return;
      html += `<div class="ps-para"><h3 class="ps-para-title">${p.title}</h3><p class="ps-para-body">${p.text}</p></div>`;
    });
    if (meta && meta.source) {
      html += `<div class="ps-meta"><span class="narration-badge source-${source}">${meta.source}</span></div>`;
    }
    content.innerHTML = html;
  };
}

// ── Player Sheet ───────────────────────────────────────────────────────────
function initPlayerSheet() {
  const sheet = document.getElementById('player-sheet');
  const backdrop = document.getElementById('player-sheet-backdrop');
  const toggle = document.getElementById('player-sheet-toggle');
  const close = document.getElementById('player-sheet-close');

  if (!sheet || !toggle) return;

  function openSheet() {
    sheet.classList.add('open');
    if (backdrop) backdrop.classList.add('open');
    toggle.classList.add('open');
    sheet.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function closeSheet() {
    sheet.classList.remove('open');
    if (backdrop) backdrop.classList.remove('open');
    toggle.classList.remove('open');
    sheet.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  toggle.addEventListener('click', (e) => {
    e.stopPropagation();
    sheet.classList.contains('open') ? closeSheet() : openSheet();
  });
  if (close) close.addEventListener('click', closeSheet);
  if (backdrop) backdrop.addEventListener('click', closeSheet);

  // ── Tab switching ──────────────────────────────────────────────────────
  document.querySelectorAll('.ps-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;
      document.querySelectorAll('.ps-tab').forEach(t => t.classList.toggle('active', t === tab));
      document.querySelectorAll('.ps-tab-panel').forEach(panel => {
        if (panel.id === `ps-panel-${target}`) {
          panel.removeAttribute('hidden');
        } else {
          panel.setAttribute('hidden', '');
        }
      });
    });
  });
}

// ── Sidebar Controls ───────────────────────────────────────────────────────
function initSidebarControls() {
  // Restore saved language on boot
  const savedLang = localStorage.getItem('lang') || 'zh-TW';
  const radio = document.querySelector(`input[name="language"][value="${savedLang}"]`);
  if (radio) radio.checked = true;
  applyLanguage(savedLang);

  // Language toggles
  document.querySelectorAll('input[name="language"]').forEach(input => {
    input.addEventListener('change', () => {
      const lang = input.value;
      localStorage.setItem('lang', lang);
      applyLanguage(lang);
    });
  });

}

// ── Sheet Settings Controls ─────────────────────────────────────────────────
function initSheetSettings() {
  // Sheet language radios → mirror sidebar radios
  document.querySelectorAll('input[name="language-sheet"]').forEach(radio => {
    radio.addEventListener('change', () => {
      const sidebar = document.querySelector(`input[name="language"][value="${radio.value}"]`);
      if (sidebar) { sidebar.checked = true; sidebar.dispatchEvent(new Event('change', { bubbles: true })); }
    });
  });


  // Sheet refresh → delegate to sidebar refresh button
  const sheetRefresh = document.getElementById('sheet-refresh-btn');
  if (sheetRefresh) {
    sheetRefresh.addEventListener('click', () => {
      document.getElementById('player-sheet-close')?.click();
      document.getElementById('refresh-btn')?.click();
    });
  }

  // Sync sheet radios to current sidebar state on init
  ['language'].forEach(name => {
    const checked = document.querySelector(`input[name="${name}"]:checked`);
    if (checked) {
      const sheetRadio = document.querySelector(`input[name="${name}-sheet"][value="${checked.value}"]`);
      if (sheetRadio) sheetRadio.checked = true;
    }
  });
}

// ── Navigation (desktop + mobile dispatch) ─────────────────────────────────
function initNav() {
  const isMobile = window.matchMedia('(max-width: 767px)').matches;
  if (isMobile) {
    initMobileNav();
  } else {
    initSidebarNav();
  }
}

function initMobileNav() {
  // Mobile: all views visible via CSS (display: block).
  // No tab switching needed. Scroll is handled by the browser.

  // Lift current conditions (+ its section header) above lifestyle so the
  // scroll order is: 1. conditions  2. lifestyle cards  3. timelines / forecast
  const conditions = document.querySelector('.current-conditions-wrapper');
  const dashHeader = document.querySelector('#view-dashboard .section-header-card');
  const lifestyle = document.getElementById('view-lifestyle');
  if (conditions && lifestyle) {
    if (dashHeader) lifestyle.parentNode.insertBefore(dashHeader, lifestyle);
    lifestyle.parentNode.insertBefore(conditions, lifestyle);
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
  const views = ['lifestyle', 'dashboard'];
  const oldIdx = views.indexOf(currentView);
  const newIdx = views.indexOf(viewName);
  const direction = newIdx > oldIdx ? 'slide-in-right' : 'slide-in-left';

  currentView = viewName;

  // Update Nav
  document.querySelectorAll('.nav-item').forEach(b => {
    b.classList.toggle('active', b.dataset.view === viewName);
  });

  document.querySelectorAll('.view-container').forEach(v => {
    v.classList.remove('slide-in-right', 'slide-in-left');
    if (v.id === `view-${viewName}`) {
      v.classList.add('active', direction);
    } else {
      v.classList.remove('active');
    }
  });
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
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false, timeZone: 'Asia/Taipei'
      });
    } catch (e) {
      el.textContent = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    }
  }

  // Analog Hands (Force Taipei Time for Analog too)
  let tNow = now;
  try {
    const taipeiStr = now.toLocaleString('en-US', { timeZone: 'Asia/Taipei' });
    tNow = new Date(taipeiStr);
  } catch (e) { }

  // Mobile digital clock
  const mobileClockEl = document.getElementById('mobile-clock');
  if (mobileClockEl) {
    try {
      mobileClockEl.textContent = now.toLocaleTimeString('en-US', {
        hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Taipei'
      });
    } catch (e) {
      mobileClockEl.textContent =
        `${tNow.getHours().toString().padStart(2, '0')}:${tNow.getMinutes().toString().padStart(2, '0')}`;
    }
  }

  const hourHand = document.getElementById('clock-hour');
  const minuteHand = document.getElementById('clock-minute');
  const secondHand = document.getElementById('clock-second');

  if (hourHand && minuteHand && secondHand) {
    const seconds = tNow.getSeconds();
    const minutes = tNow.getMinutes();
    const hours = tNow.getHours();

    const secondDeg = ((seconds / 60) * 360);
    const minuteDeg = ((minutes / 60) * 360) + ((seconds / 60) * 6);
    const hourDeg = ((hours % 12 + minutes / 60) * 30);

    secondHand.style.transform = `rotate(${secondDeg}deg)`;
    minuteHand.style.transform = `rotate(${minuteDeg}deg)`;
    hourHand.style.transform = `rotate(${hourDeg}deg)`;
  }
}

function showLoading(isRefresh = false) {
  document.getElementById('error-screen').classList.add('hidden');

  if (isRefresh) {
    document.getElementById('main-content').style.opacity = '0.5';
    document.getElementById('main-content').style.pointerEvents = 'none';
    const optLoad = document.getElementById('optimistic-loading');
    if (optLoad) optLoad.classList.remove('hidden');
  } else {
    document.getElementById('loading-screen').classList.remove('hidden');
    document.getElementById('main-content').classList.add('hidden');
  }

  const txt = document.getElementById('loading-text');
  if (txt) txt.textContent = T.loading;
  startLoadingAnimation();
}

function showContent() {
  stopLoadingAnimation();
  document.getElementById('loading-screen').classList.add('hidden');
  document.getElementById('error-screen').classList.add('hidden');

  const main = document.getElementById('main-content');
  main.classList.remove('hidden');
  main.style.opacity = '1';
  main.style.pointerEvents = 'auto';

  const optLoad = document.getElementById('optimistic-loading');
  if (optLoad) optLoad.classList.add('hidden');
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

  showLoading(true);
  startLoadingAnimation();
  addLog(T.boot);

  const provider = 'CLAUDE';

  console.log("DEBUG: Selected provider for refresh:", provider);
  addLog(`${T.log_requesting}${provider}`);

  let gotResult = false;

  try {
    const res = await fetch('/api/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider, lang: getLang() })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          if (!line.trim().startsWith('{')) {
            addLog(`Server: ${line.trim()}`);
            if (line.toLowerCase().includes('error')) {
              showError(line.trim());
              gotResult = true; // treat as terminal
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
            addLog(T.render);
            broadcastData = msg.payload;
            render(broadcastData);
            saveBroadcastCache(broadcastData);
            showContent();
            gotResult = true;
          } else if (msg.type === 'status') {
            _addStatusRow(msg.sources);
          } else if (msg.type === 'error') {
            showError(msg.message || 'Pipeline failed');
            gotResult = true;
          }
        } catch (e) {
          console.error("Stream parse error:", e, "on line:", line);
          if (line.toLowerCase().includes('failed') || line.toLowerCase().includes('error')) {
            showError(line);
            gotResult = true;
          }
        }
      }
    }

    // Stream ended without a result — fetch latest cached broadcast instead of hanging
    if (!gotResult) {
      console.warn("Stream ended without result event — falling back to /api/broadcast");
      addLog("Pipeline stream truncated — loading last available broadcast…");
      try {
        const fallback = await fetch(`/api/broadcast?lang=${getLang()}`);
        if (fallback.ok) {
          broadcastData = await fallback.json();
          render(broadcastData);
          saveBroadcastCache(broadcastData);
          showContent();
        } else {
          showError("Pipeline ended without a result and no cached broadcast available.");
        }
      } catch (fallbackErr) {
        showError("Pipeline ended without a result.");
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
  addLog(`${T.log_step_prefix}${LOADING_MSGS[0]}`);

  if (loadingInterval) clearInterval(loadingInterval);
  loadingInterval = setInterval(() => {
    i = (i + 1) % LOADING_MSGS.length;
    txt.textContent = LOADING_MSGS[i];
    addLog(`${T.log_step_prefix}${LOADING_MSGS[i]}`);
  }, 1200);
}

function stopLoadingAnimation() {
  if (loadingInterval) {
    clearInterval(loadingInterval);
    loadingInterval = null;
  }
}

function _addStatusRow(sources) {
  const list = document.getElementById('rp-log-list');
  if (!list) return;
  const row = document.createElement('div');
  row.className = 'log-entry log-status-row';
  (sources || []).forEach(src => {
    const chip = document.createElement('span');
    chip.className = `log-status-chip log-status-${src.state}`;
    chip.textContent = `${src.name} ${src.detail}`;
    row.appendChild(chip);
  });
  list.appendChild(row);
  list.scrollTop = list.scrollHeight;
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

function getLang() {
  return localStorage.getItem('lang') || 'zh-TW';
}

// No-op consolidated into initSidebarControls
function initLangToggle() { }


function applyLanguage(lang) {
  T = TRANSLATIONS[lang] || TRANSLATIONS['zh-TW'];

  // Update LOADING_MSGS in-place for next animation run
  LOADING_MSGS.splice(0, LOADING_MSGS.length,
    T.step1, T.step2, T.step3, T.step4, T.step5, T.step6, T.step7);

  // Swap all data-i18n elements
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    if (T[key] !== undefined) el.textContent = T[key];
  });

  window._T_runtime_error = T.log_runtime_error;

  // Swap view headings (hardcoded in HTML, no data-i18n — update by element ID)
  setText('view-heading-lifestyle', T.h1_lifestyle);
  setText('view-heading-dashboard', T.h1_dashboard);
  setText('section-heading-24h', T.h2_24h);
  setText('section-heading-7day', T.h2_7day);
  setText('section-heading-aqi', T.aqi_title);

  // Re-render data labels if data is already loaded
  if (broadcastData) render(broadcastData);
}

// ── Chart ──────────────────────────────────────────────────────────────────
// ── Local TTS (Web Speech API) ─────────────────────────────────────────────
function initLocalTTS(text) {
  if (!('speechSynthesis' in window)) return;

  const synth = window.speechSynthesis;

  function speak() {
    synth.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    const lang = document.querySelector('input[name="lang"]:checked')?.value || 'zh-TW';
    utter.lang = lang;
    utter.rate = 0.95;

    const voices = synth.getVoices();
    const matchVoice = voices.find(v => v.lang === lang) ||
      voices.find(v => v.lang.startsWith(lang.split('-')[0]));
    if (matchVoice) utter.voice = matchVoice;

    synth.speak(utter);
  }

  if (synth.getVoices().length > 0) {
    speak();
  } else {
    synth.addEventListener('voiceschanged', speak, { once: true });
  }
}

// getLang() is defined above near initLangToggle — this duplicate is removed.
