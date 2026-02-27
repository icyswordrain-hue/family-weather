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
  '板橋': 'Banqiao',
  '新北': 'New Taipei',
  '三重': 'Sanchong',
  '中和': 'Zhonghe',
  '永和': 'Yonghe',
  '新莊': 'Xinzhuang',
  '土城': 'Tucheng',
  '蘆洲': 'Luzhou',
  '樹林': 'Shulin',
  '鶯歌': 'Yingge',
  '三峽': 'Sanxia',
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
  return name;
}

function localiseMetric(text) {
  if (!text) return '';
  return (T.metrics && T.metrics[text]) ? T.metrics[text] : text;
}

const ICONS = {
  'sunny': '☀️', 'Sunny/Clear': '☀️', '1': '☀️',
  'partly-cloudy': '⛅', 'Mixed Clouds': '⛅', '2': '⛅', '3': '⛅',
  'cloudy': '☁️', 'Overcast': '☁️', '4': '☁️', '5': '☁️', '6': '☁️', '7': '☁️',
  'rainy': '🌧️', '8': '🌧️', '9': '🌧️', '10': '🌧️', '11': '🌧️', '12': '🌧️', '13': '🌧️',
  '14': '🌧️', '15': '🌧️', '16': '🌧️', '17': '🌧️', '18': '🌧️', '19': '🌧️', '20': '🌧️'
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
    best_label: 'Best',
    top_label: 'Top',
    boot: 'System Boot: Initiating connection…',
    data_ok: 'Data received successfully.',
    render: 'Pipeline success. Rendering…',
    step1: 'Connecting to CWA Banqiao Station…',
    step2: 'Retrieving Township Forecasts…',
    step3: 'Checking MOENV Air Quality…',
    step4: 'Processing V5 Logic…',
    step5: 'Generating Narration…',
    step6: 'Synthesizing Audio…',
    step7: 'Finalizing…',
    // Static panel labels
    nav_section: 'Views',
    nav_lifestyle: 'Lifestyle',
    nav_dashboard: 'Dashboard',
    h1_lifestyle: 'Lifestyle Guide',
    h1_dashboard: 'Weather Dashboard',
    h2_24h: '24-Hour Forecast',
    h2_7day: '7-Day Forecast',
    lang_label: 'Language',
    provider_label: 'Provider',
    system_controls: 'System Controls',
    refresh_btn: 'Refresh',
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
    best_label: '最佳時段',
    top_label: '推薦活動',
    boot: '系統啟動：初始化連線…',
    data_ok: '資料接收成功。',
    render: '管道成功，正在渲染…',
    step1: '連線至 CWA 板橋站…',
    step2: '取得鄉鎮預報…',
    step3: '查詢 MOENV 空氣品質…',
    step4: '處理 V5 邏輯…',
    step5: '生成廣播稿…',
    step6: '合成語音…',
    step7: '最終處理中…',
    // Static panel labels
    nav_section: '功能',
    nav_lifestyle: '生活建議',
    nav_dashboard: '天氣總覽',
    h1_lifestyle: '生活指南',
    h1_dashboard: '天氣儀表板',
    h2_24h: '24 小時預報',
    h2_7day: '七日預報',
    lang_label: 'Language',
    provider_label: 'Provider',
    system_controls: '系統控制',
    refresh_btn: '重新整理',
    log_requesting: '請求廣播（提供者）：',
    log_title: '系統記錄',
    log_step_prefix: '步驟：',
    log_runtime_error: '執行錯誤：',
    metrics: {
      'Very Dry': '極度乾燥', 'Dry': '乾燥', 'Comfortable': '舒適', 'Muggy': '悶熱', 'Humid': '潮濕', 'Very Humid': '極度潮濕', 'Oppressive': '令人窒息',
      'Calm': '無風', 'Light air': '軟風', 'Light breeze': '輕風', 'Gentle breeze': '微風', 'Moderate breeze': '和風', 'Fresh breeze': '清風', 'Strong breeze': '強風', 'Near gale': '疾風', 'Gale': '大風', 'Strong gale': '烈風', 'Storm': '狂風', 'Violent storm': '暴風', 'Hurricane force': '颶風',
      'Good': '良好', 'Moderate': '普通', 'Unhealthy for Sensitive Groups': '對敏感族群不健康', 'Unhealthy': '不健康', 'Very Unhealthy': '非常不健康', 'Hazardous': '危害',
      'Low': '低', 'High': '高', 'Very High': '極高', 'Extreme': '極端',
      'Unsettled': '不穩定', 'Normal': '正常', 'Stable': '穩定',
      'Very Poor': '極差', 'Poor': '差', 'Fair': '尚可', 'Excellent': '極佳',
      'Very Unlikely': '極不可能', 'Unlikely': '不太可能', 'Possible': '有可能', 'Likely': '很有可能', 'Very Likely': '極有可能', 'Unknown': '未知'
    },
  },
};

// Active translation map — updated by applyLanguage()
let T = TRANSLATIONS['zh-TW'];

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

  initSidebarNav();
  initPlayerBar();
  initPlayerSheet();
  initRefreshButton();
  updateClock();
  setInterval(updateClock, 1000);

  fetchBroadcast();
});

// ── API fetch ──────────────────────────────────────────────────────────────
async function fetchBroadcast() {
  showLoading();
  const btn = document.getElementById('refresh-btn');
  if (btn) btn.classList.add('loading');

  try {
    const res = await fetch('/api/broadcast');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    broadcastData = await res.json();
    if (broadcastData.error) throw new Error(broadcastData.error);
    addLog(T.data_ok);
    render(broadcastData);
    showContent();
  } catch (err) {
    addLog(`${T.error_prefix}${err.message || 'Unknown error'}`);
    showError(err.message || 'Unknown error');
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

  // Wire player bar when audio is available
  if (data.audio_urls && data.audio_urls.full_audio_url) {
    const narrationSlice = data.slices && data.slices.narration;
    const title = narrationSlice
      ? (narrationSlice.paragraphs || []).find(p => p.key === 'p1')?.title || 'Morning Briefing'
      : 'Morning Briefing';
    const text = narrationSlice
      ? (narrationSlice.paragraphs || []).map(p => p.text).filter(Boolean).join('\n\n')
      : (data.narration_text || '');
    if (window._playerBarSetAudio) {
      window._playerBarSetAudio(data.audio_urls.full_audio_url, title, text);
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
  setText('cur-temp', Math.round(data.temp) + '°');
  setText('cur-weather-text', localiseWeatherText(data.weather_text || '—'));
  setText('cur-icon', ICONS[data.weather_code] || ICONS[data.weather_text] || '🌤️');
  setText('rp-location', localiseLocation(data.location || '—'));

  // Gauge Cards (Restructured)
  renderGauge('gauge-ground', data.ground_state, T.ground, '', `lvl-${data.ground_level}`);
  renderGauge('gauge-wind', data.wind.text, T.wind, `${data.wind.val} m/s ${data.wind.dir || '—'}`, `lvl-${data.wind.level}`);
  renderGauge('gauge-hum', data.hum.text, T.humidity, data.hum.val + '%', `lvl-${data.hum.level}`);
  renderGauge('gauge-aqi', data.aqi.text, T.air_quality, `AQI ${data.aqi.val}`, `lvl-${data.aqi.level}`);
  renderGauge('gauge-uv', data.uv.text, T.uv, `Index ${data.uv.val || 0}`, `lvl-${data.uv.level}`);
  renderGauge('gauge-pres', data.pres.text, T.pressure, `${Math.round(data.pres.val)} hPa`, `lvl-${data.pres.level}`);
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
      addRow(T.rain, seg.precip_text || '—', seg.precip_level || 1);
      if (seg.outdoor_grade) {
        const gradeToLvl = { A: 1, B: 2, C: 3, D: 4, F: 5 };
        addRow(T.outdoor, seg.outdoor_grade, gradeToLvl[seg.outdoor_grade] || 0);
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

    const dayItems = data.weekly_timeline.filter(i => !isNightSlot(i));
    const nightItems = data.weekly_timeline.filter(i => isNightSlot(i));

    // Top row matches whatever period the first slot belongs to
    const firstIsNight = data.weekly_timeline.length > 0 && isNightSlot(data.weekly_timeline[0]);
    const topItems = firstIsNight ? nightItems : dayItems;
    const bottomItems = firstIsNight ? dayItems : nightItems;

    [...topItems, ...bottomItems].forEach(item => {
      let dt;
      try { dt = new Date(item.start_time.replace('+08:00', '')); } catch (e) { dt = new Date(); }
      const isNight = isNightSlot(item);
      const dayLabel = T.days[dt.getDay()];
      const periodLabel = isNight ? T.night : T.day;

      const card = document.createElement('div');
      card.className = `wk-card ${isNight ? 'wk-night' : 'wk-day'}`;

      const label = document.createElement('div');
      label.className = 'wk-label';
      label.textContent = `${dayLabel} ${periodLabel}`;

      const icon = document.createElement('div');
      icon.className = 'wk-icon';
      icon.textContent = ICONS[item.cloud_cover] || ICONS[item.Wx] || '☁️';

      const temp = document.createElement('div');
      temp.className = 'wk-temp';
      temp.textContent = `${Math.round(item.AT ?? 0)}°`;

      const rain = document.createElement('div');
      rain.className = `wk-rain lvl-${item.precip_level || 1}`;
      rain.textContent = item.precip_text || '—';

      card.appendChild(label);
      card.appendChild(icon);
      card.appendChild(temp);
      card.appendChild(rain);
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
    const date = document.createElement('span');
    date.className = 'aqi-fc-date';
    date.textContent = (aqi.forecast_date ? `${aqi.forecast_date}` : '') + (aqi.aqi ? ` · AQI ${aqi.aqi}` : '');
    header.appendChild(date);
    const status = document.createElement('div');
    status.className = `aqi-fc-status lvl-${aqiToLevel(aqi.aqi)}`;
    status.textContent = translateAQIText(aqi.status);
    body.appendChild(header);
    body.appendChild(status);
    if (aqi.summary_en || aqi.summary_zh || aqi.content) {
      const content = document.createElement('div');
      content.className = 'aqi-fc-content';
      const lang = localStorage.getItem('lang') || 'zh-TW';
      const aqiSummary = lang === 'en' ? aqi.summary_en : aqi.summary_zh;
      content.textContent = aqiSummary || aqi.content || 'N/A';
      body.appendChild(content);
    }
    aqiFcEl.appendChild(icon);
    aqiFcEl.appendChild(body);
  }
}

function aqiToLevel(val) {
  const n = parseInt(val);
  if (isNaN(n)) return 1;
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
    if (data.wardrobe.feels_like != null) extras.push(mkSub(`${T.feels_like} ${Math.round(data.wardrobe.feels_like)}°`));
    add('🧥', T.wardrobe, data.wardrobe.text, extras);
  }
  // 2. Rain Gear
  if (data.rain_gear) add('☂️', T.rain_gear, data.rain_gear.text);
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
    add('🚗', T.commute, data.commute.text, extras);
  }
  // 4. Garden Health
  if (data.garden && data.garden.text) add('🌱', T.garden, data.garden.text);
  // 5. Outdoor Activities
  if (data.outdoor && data.outdoor.text) {
    const extras = [];
    if (data.outdoor.grade) extras.push(mkBadge(`oi-grade-${data.outdoor.grade}`, `Grade ${data.outdoor.grade} · ${data.outdoor.label || ''}`));
    if (data.outdoor.top_activity) extras.push(mkSub(`${T.best_label}: ${data.outdoor.best_window || ''} · ${T.top_label}: ${data.outdoor.top_activity}`));
    add('🌳', T.outdoor_act, data.outdoor.text, extras);
  }
  // 6. Meals
  if (data.meals && data.meals.text) {
    const extras = [];
    if (data.meals.mood) extras.push(mkBadge('mood-badge', data.meals.mood));
    add('🍱', T.meals, data.meals.text, extras);
  }
  // 7. HVAC Advice
  if (data.hvac) {
    const extras = [];
    if (data.hvac.mode) extras.push(mkBadge(`hvac-${data.hvac.mode.toLowerCase()}`, data.hvac.mode));
    add('🌡️', T.hvac, data.hvac.text, extras);
  }

  // 8. Heads Up alert card (structured per-item with level styling)
  if (data.alert && data.alert.length > 0) {
    const hasCritical = data.alert.some(a => a.level === 'CRITICAL');
    const card = document.createElement('div');
    card.className = 'ls-card ls-alert-card ' + (hasCritical ? 'ls-alert-critical' : 'ls-alert-warning');
    const ic = document.createElement('div');
    ic.className = 'ls-icon';
    ic.textContent = hasCritical ? '🚨' : '⚠️';
    const content = document.createElement('div');
    content.className = 'ls-content';
    const ttl = document.createElement('div');
    ttl.className = 'ls-title';
    ttl.textContent = T.heads_up_title;
    content.appendChild(ttl);
    const TYPE_ICONS = { Health: '❤️', Commute: '🚗', Air: '🌫️', General: '📌' };
    data.alert.forEach(item => {
      const row = document.createElement('div');
      row.className = 'ls-alert-item';
      const ico = document.createElement('span');
      ico.className = 'ls-alert-type-icon';
      ico.textContent = TYPE_ICONS[item.type] || '📌';
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
}

// ── System Theme ───────────────────────────────────────────────────────────
function initSystemTheme() {
  const mq = window.matchMedia('(prefers-color-scheme: dark)');
  const apply = (dark) => document.documentElement.classList.toggle('dark', dark);
  apply(mq.matches);
  mq.addEventListener('change', (e) => apply(e.matches));
}

// ── Player Bar ─────────────────────────────────────────────────────────────
function initPlayerBar() {
  const bar = document.getElementById('player-bar');
  const audio = document.getElementById('player-audio');
  const playBtn = document.getElementById('player-play-btn');
  const icon = document.getElementById('player-play-icon');
  const title = document.getElementById('player-title');
  const progress = document.getElementById('player-progress-bar');
  const duration = document.getElementById('player-duration');

  if (!bar || !audio) return;

  bar.classList.add('loading');

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
    progress.style.width = `${(audio.currentTime / audio.duration) * 100}%`;
    duration.textContent = formatTime(audio.currentTime);
  });

  audio.addEventListener('loadedmetadata', () => {
    duration.textContent = formatTime(audio.duration);
  });

  playBtn.addEventListener('click', () => {
    if (audio.paused) audio.play();
    else audio.pause();
  });

  window._playerBarSetAudio = function (audioUrl, narrationTitle, narrationText) {
    bar.classList.remove('loading');
    audio.src = audioUrl;
    if (title) title.textContent = narrationTitle || 'Morning Briefing';
    const body = document.getElementById('player-sheet-body');
    if (body) body.textContent = narrationText || '';
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

  toggle.addEventListener('click', () => {
    sheet.classList.contains('open') ? closeSheet() : openSheet();
  });
  if (close) close.addEventListener('click', closeSheet);
  if (backdrop) backdrop.addEventListener('click', closeSheet);
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

  // Provider toggles
  document.querySelectorAll('input[name="provider"]').forEach(input => {
    input.addEventListener('change', triggerRefresh);
  });
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
  startLoadingAnimation(); // Start fake messages until connection established
  addLog(T.boot);

  // Read selected provider
  const providerInput = document.querySelector('input[name="provider"]:checked');
  const provider = providerInput ? providerInput.value : 'CLAUDE';

  console.log("DEBUG: Selected provider for refresh:", provider);
  addLog(`${T.log_requesting}${provider}`);

  try {
    const res = await fetch('/api/refresh', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        provider,
        lang: getLang()
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
            addLog(T.render);
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
