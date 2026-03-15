"""
slices.py — Extracts view-specific data slices from the full broadcast.

Views:
  current   — Real-time metrics (Big Gauges)
  overview  — Timeline, Trend Chart, Alerts
  lifestyle — Wardrobe, Commute, Outdoor, Meals, HVAC
  narration — Full text script
  context   — Dynamic Right Panel data (Rain Text, Location)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

# ── Localisation maps ────────────────────────────────────────────────────────
# Moved from app.js to allow backend slices to serve pre-localised text.

_WEATHER_TEXT_EN = {
    '晴': 'Sunny', '晴時多雲': 'Partly Cloudy', '多雲時晴': 'Mostly Sunny',
    '多雲': 'Cloudy', '陰': 'Overcast', '陰時多雲': 'Mostly Cloudy',
    '多雲時陰': 'Mostly Cloudy', '短暫雨': 'Brief Rain', '短暫陣雨': 'Brief Showers',
    '陣雨': 'Showers', '雨': 'Rain', '大雨': 'Heavy Rain', '豪雨': 'Torrential Rain',
    '短暫雷陣雨': 'Brief Thunderstorms', '雷陣雨': 'Thunderstorms',
    '有霧': 'Foggy', '霧': 'Fog', '有靄': 'Hazy',
}

_LOCATION_EN = {
    '桃改臺北': 'Shulin Station', '桃改台北': 'Shulin Station',
    '板橋': 'Banqiao Station', '新北': 'Xindian Stn.',
    '樹林': 'Shulin Station',
    '樹林區': 'Shulin', '板橋區': 'Banqiao', '三峽區': 'Sanxia',
    '三重': 'Sanchong', '中和': 'Zhonghe', '永和': 'Yonghe',
    '新莊': 'Xinzhuang', '土城': 'Tucheng', '蘆洲': 'Luzhou',
    '鶯歌': 'Yingge', '淡水': 'Tamsui', '汐止': 'Xizhi',
    '瑞芳': 'Ruifang', '深坑': 'Shenkeng', '石碇': 'Shiding',
    '坪林': 'Pinglin', '烏來': 'Wulai', '八里': 'Bali',
    '林口': 'Linkou', '五股': 'Wugu', '泰山': 'Taishan',
}

_LOCATION_ZH = {
    '桃改臺北': '樹林站', '桃改台北': '樹林站', '樹林': '樹林站',
    '板橋': '板橋站', '新北': '新店站',
}

_METRIC_ZH = {
    # Humidity / dew gap
    'Near Saturated': '接近飽和', 'Clammy': '悶濕',
    'Very Dry': '極度乾燥', 'Dry': '乾燥', 'Comfortable': '舒適',
    'Muggy': '悶熱', 'Humid': '潮濕', 'Very Humid': '極度潮濕', 'Oppressive': '令人窒息',
    # Wind (Beaufort)
    'Calm': '無風', 'Light air': '軟風', 'Light breeze': '輕風',
    'Gentle breeze': '微風', 'Moderate breeze': '和風', 'Fresh breeze': '清風',
    'Strong breeze': '強風', 'Near gale': '疾風', 'Gale': '大風',
    'Strong gale': '烈風', 'Storm': '狂風', 'Violent storm': '暴風', 'Hurricane force': '颶風',
    # AQI status
    'Good': '良好', 'Moderate': '普通',
    'Unhealthy for Sensitive Groups': '對敏感族群不健康',
    'Unhealthy': '不健康', 'Very Unhealthy': '非常不健康', 'Hazardous': '危害',
    # Outdoor grades
    'Go out': '適合外出', 'Good to go': '可以出門', 'Manageable': '勉強可行',
    'Think twice': '建議斟酌', 'Stay in': '建議待室內',
    # UV
    'Low': '低', 'High': '高', 'Very High': '極高', 'Extreme': '極端',
    'Safe': '安全', 'Wear Sunscreen': '需擦防曬', 'Seek Shade': '請避曬',
    # Pressure
    'Unsettled': '不穩定', 'Normal': '正常', 'Stable': '穩定',
    # Visibility
    'Very Poor': '極差', 'Poor': '差', 'Fair': '尚可', 'Excellent': '極佳',
    # Precipitation likelihood
    'Very Unlikely': '極不可能', 'Unlikely': '不太可能', 'Possible': '有可能',
    'Likely': '很有可能', 'Very Likely': '極有可能', 'Unknown': '未知',
    # Ground state
    'Wet': '潮濕地面',
    # Meal moods
    'Hot & Humid': '炎熱潮濕', 'Warm & Pleasant': '溫暖舒適',
    'Cool & Damp': '涼爽潮濕', 'Cold': '寒冷',
    # HVAC modes
    'Off': '無需空調', 'fan': '電風扇', 'cooling': '冷氣',
    'heating': '暖氣', 'heating_optional': '可選暖氣', 'dehumidify': '除濕',
}

_SLOT_ZH = {
    'Morning': '早上', 'Afternoon': '下午',
    'Evening': '晚上', 'Overnight': '深夜', 'Forecast': '預報',
}

_TRANSITION_ZH = {
    'Sunny': '晴朗', 'Cloudy': '多雲',
    'Rain expected': '預期降雨', 'More rain': '降雨增加', 'Less rain': '降雨減少',
    'Near Saturated': '近飽和', 'Clammy': '悶熱', 'Humid': '潮濕',
    'Comfortable': '舒適', 'Dry': '乾燥',
    'Windier': '風力增強', 'Calmer': '風力減弱',
    'Shorter outdoor window': '戶外時間縮短',
    'Rain likely — plan indoors': '可能下雨—建議室內活動',
    'Outdoor window closing': '戶外時段結束',
    'change': '變化',
}

_BEAUFORT_ORDER = [
    "Calm", "Light air", "Light breeze", "Gentle breeze",
    "Moderate breeze", "Fresh breeze", "Strong breeze",
    "Near gale", "Gale", "Strong gale", "Storm",
    "Violent storm", "Hurricane force",
]


def _loc_metric(text: str | None, lang: str) -> str:
    if not text:
        return ''
    if lang == 'zh-TW':
        return _METRIC_ZH.get(text, text)
    return text


def _loc_weather(text: str | None, lang: str) -> str:
    if not text:
        return ''
    if lang == 'en':
        return _WEATHER_TEXT_EN.get(text, text)
    return text


def _loc_location(name: str | None, lang: str) -> str:
    if not name:
        return ''
    if lang == 'en':
        return _LOCATION_EN.get(name, name)
    return _LOCATION_ZH.get(name, name)


def _loc_precip(text: str | None, lang: str) -> str:
    if not text:
        return '—'
    if lang != 'zh-TW':
        return text
    if text == 'All clear':
        return '不會降雨'
    if text == 'Stay in':
        return '建議待室內'
    m = re.match(r'^~(\d+)\s*min$', text)
    if m:
        return f'約 {m.group(1)} 分鐘'
    return text


def _loc_slot(name: str, lang: str) -> str:
    if lang == 'zh-TW':
        return _SLOT_ZH.get(name, name)
    return name


def _loc_transition(text: str, lang: str) -> str:
    if lang == 'zh-TW':
        return _TRANSITION_ZH.get(text, text)
    return text


def _truncate_tagline(text: str, max_words: int = 8) -> str:
    """Truncate text to at most max_words for use as a card tagline."""
    if not text:
        return ""
    if any('\u4e00' <= c <= '\u9fff' for c in text[:5]):
        return text[:16].rstrip("，。、；") + ("" if len(text) <= 16 else "")
    words = text.split()
    if len(words) <= max_words:
        return text.rstrip(".")
    return " ".join(words[:max_words]).rstrip(".,;—") + "."


def _compute_aqi_peak_window(hourly: list[dict]) -> str | None:
    """Return a human-readable peak-AQI window string from hourly AQI data.

    If any hour hits AQI >= 100, returns the contiguous bad window, e.g. "11:00–16:00".
    Otherwise returns the single worst hour, e.g. "Peak at 14:00 (AQI 85)".
    Returns None when hourly data is absent.
    """
    if not hourly:
        return None
    bad = []
    for h in hourly:
        aqi = h.get("aqi")
        ft = h.get("forecast_time", "")
        if aqi is None or not ft:
            continue
        try:
            dt = datetime.fromisoformat(str(ft).replace("Z", "+00:00"))
            if aqi >= 100:
                bad.append((dt, aqi))
        except ValueError:
            continue
    if bad:
        bad.sort(key=lambda x: x[0])
        start = bad[0][0].strftime("%H:%M")
        end_dt = bad[-1][0]
        # Advance end by 1 hour to show the close of the window
        end = f"{end_dt.hour + 1:02d}:00" if end_dt.hour < 23 else "24:00"
        return f"{start}–{end}"
    # No bad hours — show peak hour
    try:
        best = max(hourly, key=lambda h: h.get("aqi") or 0)
        aqi_val = best.get("aqi")
        ft = best.get("forecast_time", "")
        if aqi_val and ft:
            dt = datetime.fromisoformat(str(ft).replace("Z", "+00:00"))
            return f"Peak at {dt.strftime('%H:%M')} (AQI {aqi_val})"
    except (ValueError, TypeError):
        pass
    return None


def _match_aqi_to_segment(seg_start: str, hourly: list[dict]) -> int | None:
    """Return the AQI value whose forecast_time is closest to seg_start."""
    if not hourly or not seg_start:
        return None
    try:
        seg_dt = datetime.fromisoformat(str(seg_start).replace("Z", "+00:00"))
        seg_ts = seg_dt.timestamp()
    except ValueError:
        return None
    best_aqi, best_diff = None, float("inf")
    for h in hourly:
        ft = h.get("forecast_time", "")
        aqi = h.get("aqi")
        if not ft or aqi is None:
            continue
        try:
            h_dt = datetime.fromisoformat(str(ft).replace("Z", "+00:00"))
            diff = abs(h_dt.timestamp() - seg_ts)
            if diff < best_diff:
                best_diff, best_aqi = diff, aqi
        except ValueError:
            continue
    return best_aqi


def build_slices(broadcast: dict, lang: str = "en") -> dict:
    """
    Build per-view data slices from a broadcast record.

    Args:
        broadcast: Dict with at minimum 'paragraphs', 'metadata', 'processed_data'.
        lang: Language parameter, defaults to 'en'.

    Returns:
        Dict with keys 'current', 'overview', 'lifestyle', 'narration', 'context'.
    """
    paragraphs = broadcast.get("paragraphs", {})
    processed = broadcast.get("processed_data", {})
    summaries = broadcast.get("summaries", {})

    current_data = processed.get("current", {})
    forecast_segs = processed.get("forecast_segments", {})
    forecast_7day = processed.get("forecast_7day", [])
    climate = processed.get("climate_control", {})
    commute = processed.get("commute", {})
    aqi_realtime = processed.get("aqi_realtime", {})
    aqi_forecast = processed.get("aqi_forecast", {})
    transitions = processed.get("transitions", [])

    meta = broadcast.get("metadata", {})
    outdoor_index = processed.get("outdoor_index", {})

    solar = processed.get("solar")

    return {
        "current": _slice_current(current_data, aqi_realtime, solar, outdoor_index, lang=lang),
        "overview": _slice_overview(forecast_segs, aqi_forecast, transitions, outdoor_index, forecast_7day, lang=lang),
        "lifestyle": _slice_lifestyle(current_data, commute, climate, paragraphs, processed, summaries, outdoor_index, lang=lang),
        "narration": _slice_narration(paragraphs, meta),
    }


# ── View Slices ──────────────────────────────────────────────────────────────

def _slice_current(current: dict, aqi_realtime: dict | None = None, solar: dict | None = None, outdoor: dict | None = None, lang: str = "en") -> dict:
    """Current View: Real-time conditions with 5-level insights."""
    aqi_realtime = aqi_realtime or {}
    outdoor = outdoor or {}
    return {
        "temp": current.get("AT"),
        "obs_time": current.get("obs_time"),
        "location": _loc_location(current.get("station_name"), lang),
        "weather_code": current.get("Wx"),
        "weather_text": _loc_weather(current.get("Wx_text"), lang),
        "cloud_cover": current.get("cloud_cover"),  # stays English — used as icon key
        "ground_state": _loc_metric(current.get("ground_state", "Dry"), lang),
        "ground_level": current.get("ground_level", 1),

        # 5-Level Metrics
        "hum": {
            "val": current.get("RH"),
            "text": _loc_metric(current.get("hum_text", "Normal"), lang),
            "level": current.get("hum_level", 3)
        },
        "wind": {
            "val": current.get("WDSD"),
            "text": _loc_metric(current.get("wind_text", "Calm"), lang),
            "level": current.get("wind_level", 1),
            "dir": current.get("wind_dir_text")
        },
        "aqi": {
            "val": current.get("aqi"),
            "text": _loc_metric(current.get("aqi_status", "Good"), lang),
            "level": current.get("aqi_level", 1),
            "pm25": aqi_realtime.get("pm25"),
            "pm10": aqi_realtime.get("pm10"),
        },
        "vis": {
            "val": current.get("visibility"),
            "text": _loc_metric(current.get("vis_text", "Good"), lang),
            "level": current.get("vis_level", 1)
        },
        "uv": {
            "val": current.get("UVI"),
            "text": _loc_metric(current.get("uv_text", "Low"), lang),
            "level": current.get("uv_level", 1)
        },
        "pres": {
            "val": current.get("PRES"),
            "text": _loc_metric(current.get("pres_text", "Normal"), lang),
            "level": current.get("pres_level", 3)
        },
        "solar": solar,
        "dew_point": current.get("dew_point_c"),
        "dew_gap": current.get("dew_gap_c"),
        "outdoor": {
            "score": outdoor.get("overall_score"),
            "grade": outdoor.get("overall_grade"),
            "label": _loc_metric(outdoor.get("overall_label"), lang),
        },
    }


def _slice_overview(
    segments: dict,
    aqi_forecast: dict | None = None,
    transitions: list | None = None,
    outdoor_index: dict | None = None,
    forecast_7day: list | None = None,
) -> dict:
    """Overview View: Timeline, AQI Forecast, Transitions."""
    aqi_forecast = aqi_forecast or {}
    transitions = transitions or []
    outdoor_index = outdoor_index or {}
    forecast_7day = forecast_7day or []

    hourly_aqi = aqi_forecast.get("hourly", [])

    timeline_list = []
    for name, seg in segments.items():
        if seg:
            seg_copy = dict(seg)
            seg_copy["display_name"] = name
            seg_grade_data = outdoor_index.get("segments", {}).get(name, {})
            seg_copy["outdoor_score"] = seg_grade_data.get("score")
            seg_copy["outdoor_grade"] = seg_grade_data.get("grade")
            seg_copy["outdoor_label"] = seg_grade_data.get("label")
            seg_copy["aqi"] = _match_aqi_to_segment(seg.get("start_time"), hourly_aqi)
            timeline_list.append(seg_copy)

    timeline_list.sort(key=lambda x: x["start_time"])

    at_mins = [s["MinAT"] if s.get("MinAT") is not None else s.get("AT") for s in timeline_list]
    at_maxs = [s["MaxAT"] if s.get("MaxAT") is not None else s.get("AT") for s in timeline_list]
    at_mins = [v for v in at_mins if v is not None]
    at_maxs = [v for v in at_maxs if v is not None]
    timeline_temp_range = {
        "min": min(at_mins) if at_mins else None,
        "max": max(at_maxs) if at_maxs else None,
    }

    return {
        "timeline": timeline_list,
        "timeline_temp_range": timeline_temp_range,
        "weekly_timeline": forecast_7day[:16],
        "aqi_forecast": {
            **aqi_forecast,
        },
        "transitions": transitions,
    }


# ---------------------------------------------------------------------------
# Alert redundancy / deduplication helpers
# ---------------------------------------------------------------------------

_ALERT_SEVERITY = {"CRITICAL": 3, "WARNING": 2, "INFO": 1}

# Keywords used to classify a "General" LLM alert into its real category.
# Checked case-insensitively against the alert message.
_AIR_CLASSIFY_KEYWORDS    = ("aqi", "air quality", "pm2.5", "pm10", "空氣", "ozone", "particulate")
_HEALTH_CLASSIFY_KEYWORDS = ("cardiac", "ménière", "menieres", "meniere", "pressure drop", "pressure rise", "心臟", "梅尼爾")
_COMMUTE_CLASSIFY_KEYWORDS = ("commute", "traffic", "road", "通勤", "路況", "drive", "driving")


def _classify_alert_type(alert: dict) -> str:
    """Return the effective category of an alert, reclassifying 'General' by keyword."""
    if alert.get("type", "General") != "General":
        return alert["type"]
    msg_low = alert.get("msg", "").lower()
    for kw in _AIR_CLASSIFY_KEYWORDS:
        if kw in msg_low:
            return "Air"
    for kw in _HEALTH_CLASSIFY_KEYWORDS:
        if kw in msg_low:
            return "Health"
    for kw in _COMMUTE_CLASSIFY_KEYWORDS:
        if kw in msg_low:
            return "Commute"
    return "General"


def _dedup_alerts(alerts: list[dict]) -> list[dict]:
    """Deduplicate alerts by effective type, keeping the highest-severity entry per type.

    Prevents the same category (e.g. Air quality) from appearing twice when both
    the LLM summary path and a direct-injection path (e.g. MOENV warnings) fire
    for the same condition on the same broadcast.
    """
    best: dict[str, dict] = {}
    for a in alerts:
        key = _classify_alert_type(a)
        prev = best.get(key)
        if prev is None:
            best[key] = a
        else:
            if _ALERT_SEVERITY.get(a.get("level", "INFO"), 0) > _ALERT_SEVERITY.get(prev.get("level", "INFO"), 0):
                best[key] = a
            # On equal severity, prefer a more-specific type (not "General")
            elif (a.get("type") != "General" and prev.get("type") == "General"
                  and _ALERT_SEVERITY.get(a.get("level", "INFO"), 0) == _ALERT_SEVERITY.get(prev.get("level", "INFO"), 0)):
                best[key] = a
    return list(best.values())


def _slice_lifestyle(current: dict, commute: dict, climate: dict, paragraphs: dict, processed: dict, summaries: dict | None = None, outdoor_index: dict | None = None, lang: str = "en") -> dict:
    """Lifestyle View: Wardrobe, Rain Gear, Commute, Outdoor, Meals, HVAC."""
    if not isinstance(summaries, dict):
        summaries = {}
    if not isinstance(climate, dict):
        climate = {"mode": "Off"}
    
    is_zh = lang == "zh-TW"

    # 1. Wardrobe & Rain Gear
    at = current.get("AT")
    rain_recent = (current.get("RAIN") or 0) > 0

    wardrobe_text = summaries.get("wardrobe")
    if not wardrobe_text:
        wardrobe_text = _wardrobe_tip(at, lang=lang)
    wardrobe_tagline = summaries.get("wardrobe_tagline", "")

    rain_gear_text = summaries.get("rain_gear")
    if not rain_gear_text:
        rain_gear_text = ("不需準備雨具。" if not rain_recent else "請記得攜帶雨具。") if is_zh else ("No precipitation gear expected." if not rain_recent else "Carry an umbrella.")

    # 2. Commute (v7: p2_garden_commute contains garden + commute)
    commute_text = summaries.get("commute")
    commute_tagline = summaries.get("commute_tagline", "")
    if not commute_text:
        am = commute.get("morning", {}).get("hazards", [])
        pm = commute.get("evening", {}).get("hazards", [])
        if am:
            commute_text = (f"早上注意：{am[0]}。") if is_zh else (f"Morning alert: {am[0]}.")
        elif pm:
            commute_text = (f"傍晚注意：{pm[0]}。") if is_zh else (f"Evening alert: {pm[0]}.")
        else:
            commute_text = "交通狀況良好。" if is_zh else "Traffic conditions look normal."

    # 3. HVAC (v7: p4_hvac_air)
    hvac_text = summaries.get("hvac")
    hvac_tagline = summaries.get("hvac_tagline", "")
    if not hvac_text:
        hvac_mode = climate.get("mode", "Off")
        dehumidifier = climate.get("dehumidifier")
        ac_mode = climate.get("ac_mode")
        windows = climate.get("windows")
        aqi_val = current.get("aqi", 0)

        dew_reason = (climate.get("dew_reasons") or [""])[0]
        if is_zh:
            ac_suffix = "（乾燥模式）" if ac_mode == "dry" else "（冷氣模式）" if hvac_mode == "cooling" else ""
            action_zh = {
                "Off": "今天不需要開空調。",
                "fan": "開電風扇即可。",
                "cooling": f"請開冷氣{ac_suffix}。",
                "heating": "請開暖氣。",
                "heating_optional": "視需要可開暖氣。",
                "dehumidify": "請開除濕機。",
            }.get(hvac_mode, f"建議設為{hvac_mode}模式。")
            if dew_reason:
                action_zh = action_zh.rstrip("。") + f"——{dew_reason}。"
            hvac_parts = [action_zh]
            if dehumidifier in ("strongly_recommended", "recommended"):
                hvac_parts.append("建議同時開啟除濕機。")
            elif dehumidifier == "consider":
                hvac_parts.append("視情況考慮開除濕機。")
            if windows == "open":
                hvac_parts.append("適合開窗通風。")
            elif windows == "close":
                hvac_parts.append("建議關閉窗戶。")
        else:
            ac_mode_label = "dry" if ac_mode == "dry" else "cool"
            action_en = {
                "Off": "No HVAC needed today.",
                "fan": "Use the fan only.",
                "cooling": f"Run the AC in {ac_mode_label} mode.",
                "heating": "Turn on the heater.",
                "heating_optional": "Heating is optional today.",
                "dehumidify": "Run the dehumidifier.",
            }.get(hvac_mode, f"Set HVAC to {hvac_mode}.")
            if dew_reason:
                action_en = action_en.rstrip(".") + f" — {dew_reason}."
            hvac_parts = [action_en]
            if dehumidifier in ("strongly_recommended", "recommended"):
                hvac_parts.append("Also run the dehumidifier.")
            elif dehumidifier == "consider":
                hvac_parts.append("Consider running the dehumidifier too.")
            if windows == "open":
                hvac_parts.append("Open windows to ventilate.")
            elif windows == "close":
                hvac_parts.append("Keep windows closed.")
        hvac_text = " ".join(hvac_parts)

    # 4. Meals (v7: p3_outdoor_meal)
    meals_text = summaries.get("meals")
    meals_tagline = summaries.get("meals_tagline", "")
    if not meals_text:
        meal_mood_data = processed.get("meal_mood", {})
        meal_suggestions = meal_mood_data.get("top_suggestions", []) or meal_mood_data.get("all_suggestions", [])
        if meal_suggestions:
            if is_zh:
                meals_text = f"推薦餐點：{', '.join(meal_suggestions[:2])}。"
            else:
                meals_text = f"Suggested: {', '.join(meal_suggestions[:2])}."
        else:
            meals_text = "無特別推薦。" if is_zh else "No specific suggestions."

    # 5. Garden (v7: first sentence of p2_garden_commute) & Outdoor (v7: p3_outdoor_meal)
    garden_text = summaries.get("garden")
    garden_tagline = summaries.get("garden_tagline", "")
    outdoor_text = summaries.get("outdoor") or paragraphs.get("p3_outdoor")
    outdoor_tagline = summaries.get("outdoor_tagline", "")

    if not garden_text:
        p2 = paragraphs.get("p2_garden_commute", "")
        if p2:
            parts = p2.split("。" if is_zh else ". ", 1)
            garden_text = parts[0] + ("。" if is_zh else ".")
        else:
            garden_text = "記得檢查土壤濕度。" if is_zh else "Check soil moisture."

    # Outdoor text only
    if not outdoor_text:
        outdoor_text = "是個適合散步的好日子。" if is_zh else "Good day for a walk."

    outdoor_index = outdoor_index or {}

    # Derive best_window and top_activity, preferring broadcast-time pinned values
    # so the insight row stays consistent with the LLM card text.
    _segs = outdoor_index.get("segments", {})
    _computed_bw = max(_segs, key=lambda k: _segs[k]["score"]) if _segs else None
    best_window = summaries.get("_best_window") or _computed_bw
    _acts = outdoor_index.get("activities", {})
    if _acts:
        _max_score = max(v["score"] for v in _acts.values())
        _tied = [k for k, v in _acts.items() if v["score"] == _max_score]
        _computed_ta = "photography" if ("photography" in _tied and _max_score >= 80) else _tied[0]
    else:
        _computed_ta = None
    top_activity = summaries.get("_top_activity") or _computed_ta

    # Meal mood category
    meal_mood = processed.get("meal_mood", {}).get("mood")

    # Air quality forecast card
    aqi_forecast = processed.get("aqi_forecast", {})
    air_quality_text = summaries.get("air_quality", "")
    air_quality_tagline = summaries.get("air_quality_tagline", "")
    if not air_quality_text:
        lang_key = "summary_zh" if is_zh else "summary_en"
        air_quality_text = aqi_forecast.get(lang_key) or aqi_forecast.get("content", "")

    # Alert card: sourced from LLM ---CARDS--- alert field
    alert_summary = summaries.get("alert", {})
    if isinstance(alert_summary, dict):
        alert_text = alert_summary.get("text", "")
        alert_level = alert_summary.get("level", "INFO")
        _alert = [{"level": alert_level, "type": "General", "msg": alert_text}] if alert_text else []
    else:
        _alert = []

    # Direct MOENV warnings: surface only when AQI is genuinely hazardous (>= 150,
    # "Unhealthy for Everyone") AND the content text contains explicit advisory language.
    # Threshold 100 ("Sensitive Groups") fires too frequently on ordinary days; the
    # content field is a general daily narrative that is always non-empty, so without
    # the keyword gate it surfaces generic weather synopses as WARNING-level alerts.
    _AIR_ALERT_KEYWORDS = ("不良", "不健康", "有害", "建議減少", "建議室內", "避免戶外")
    aqi_num = aqi_forecast.get("aqi")
    if isinstance(aqi_num, (int, float)) and aqi_num >= 150:
        for w in aqi_forecast.get("warnings", []):
            if any(kw in w for kw in _AIR_ALERT_KEYWORDS):
                _alert.append({"type": "Air", "level": "WARNING", "msg": w})

    # Peak AQI window from hourly forecast
    hourly_aqi = aqi_forecast.get("hourly", [])
    peak_window = _compute_aqi_peak_window(hourly_aqi)

    # Action tip: air purifier / close windows based on AQI severity
    aqi_num_raw = aqi_forecast.get("aqi")
    aqi_num = int(aqi_num_raw) if isinstance(aqi_num_raw, (int, float)) else 0
    if aqi_num >= 150:
        purifier_advice = "關閉窗戶並開啟空氣清淨機。" if is_zh else "Close windows and run the air purifier."
    elif aqi_num >= 100:
        purifier_advice = "建議關窗，可考慮開啟空氣清淨機。" if is_zh else "Consider closing windows and running the air purifier."
    elif aqi_num >= 51:
        purifier_advice = "敏感族群可考慮開啟空氣清淨機。" if is_zh else "Sensitive groups: consider running the air purifier indoors."
    else:
        purifier_advice = None

    # Fallback taglines: truncate card text when LLM didn't provide taglines
    if not wardrobe_tagline and wardrobe_text:
        wardrobe_tagline = _truncate_tagline(wardrobe_text)
    if not commute_tagline and commute_text:
        commute_tagline = _truncate_tagline(commute_text)
    if not hvac_tagline and hvac_text:
        hvac_tagline = _truncate_tagline(hvac_text)
    if not meals_tagline and meals_text:
        meals_tagline = _truncate_tagline(meals_text)
    if not garden_tagline and garden_text:
        garden_tagline = _truncate_tagline(garden_text)
    if not outdoor_tagline and outdoor_text:
        outdoor_tagline = _truncate_tagline(outdoor_text)
    if not air_quality_tagline and air_quality_text:
        air_quality_tagline = _truncate_tagline(air_quality_text)

    return {
        "wardrobe": {
            "text": wardrobe_text,
            "tagline": wardrobe_tagline,
            "feels_like": at,
            "rain_gear_text": rain_gear_text,
        },
        "commute": {
            "text": commute_text,
            "tagline": commute_tagline,
            "hazards": commute.get("morning", {}).get("hazards", []) + commute.get("evening", {}).get("hazards", [])
        },
        "air_quality": {
            "text": air_quality_text or ("空氣品質資料暫不可用。" if is_zh else "Air quality data unavailable."),
            "tagline": air_quality_tagline,
            "aqi": aqi_forecast.get("aqi"),
            "status": aqi_forecast.get("status", ""),
            "peak_window": peak_window,
            "pm25": processed.get("current", {}).get("pm25"),
            "pm10": processed.get("current", {}).get("pm10"),
            "purifier_advice": purifier_advice,
        },
        "hvac": {
            "text": hvac_text,
            "tagline": hvac_tagline,
            "mode": climate.get("mode", "Off")
        },
        "meals": {
            "text": meals_text,
            "tagline": meals_tagline,
            "mood": meal_mood,
        },
        "garden": {
            "text": garden_text,
            "tagline": garden_tagline,
        },
        "outdoor": {
            "text": outdoor_text,
            "tagline": outdoor_tagline,
            "score": outdoor_index.get("overall_score"),
            "grade": outdoor_index.get("overall_grade"),
            "label": outdoor_index.get("overall_label"),
            "top_activity": top_activity,
            "activity_scores": outdoor_index.get("activities", {}),
            "best_window": best_window,
        },
        "alert": _dedup_alerts(_alert),
    }


def _slice_narration(paragraphs: dict, metadata: dict) -> dict:
    """Narration View: Full text and metadata."""

    # Determined source/model from metadata (saved in main.py)
    source = metadata.get("narration_source", "template").title() # "Gemini", "Claude", "Template"
    model = metadata.get("narration_model", "Unknown")

    # Fallback legacy logic if missing
    if source == "Template" and "gemini" in metadata.get("llm_model", "").lower():
        source = "Gemini"

    # Paragraph section titles — use language-neutral keys.
    # The frontend TRANSLATIONS object maps these to the display language.
    # For the narration view the section titles are rendered from the paragraph
    # keys, so we embed a `key` field alongside `text` to allow the frontend
    # to translate if desired, while `title` stays in a neutral readable form.
    return {
        "paragraphs": [
            {"key": "p1", "title": "Current & Outlook",   "text": paragraphs.get("p1_conditions", "")},
            {"key": "p2", "title": "Garden & Commute",    "text": paragraphs.get("p2_garden_commute", "")},
            {"key": "p3", "title": "Outdoor & Meal",      "text": paragraphs.get("p3_outdoor_meal", "")},
            {"key": "p4", "title": "HVAC & Air Quality",  "text": paragraphs.get("p4_hvac_air", "")},
            {"key": "p5", "title": "Forecast & Accuracy", "text": paragraphs.get("p5_forecast_accuracy", "")},
        ],
        "meta": {
            "model": model,
            "source": source,
        }
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _wardrobe_tip(at: float | None, lang: str = "en") -> str:
    """Generate simple wardrobe advice."""
    is_zh = lang == "zh-TW"
    parts = []

    if at is None:
        return "請查看預報。" if is_zh else "Check forecast."
        
    if at < 15:
        parts.append("建議穿著厚外套及保暖衣物" if is_zh else "Heavy coat & layers")
    elif at < 20:
        parts.append("建議穿著輕薄外套或毛衣" if is_zh else "Light jacket or sweater")
    elif at < 26:
        parts.append("舒適/短袖" if is_zh else "Comfortable / T-shirt")
    else:
        parts.append("輕薄衣物及防曬" if is_zh else "Light clothing & sunscreen")
        
    return " · ".join(parts) if is_zh else " + ".join(parts)
