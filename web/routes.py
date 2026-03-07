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

from datetime import datetime, timezone


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
        "current": _slice_current(current_data, aqi_realtime, solar),
        "overview": _slice_overview(forecast_segs, aqi_forecast, transitions, outdoor_index, forecast_7day),
        "lifestyle": _slice_lifestyle(current_data, commute, climate, paragraphs, processed, summaries, outdoor_index, lang=lang),
        "narration": _slice_narration(paragraphs, meta),
    }


# ── View Slices ──────────────────────────────────────────────────────────────

def _slice_current(current: dict, aqi_realtime: dict | None = None, solar: dict | None = None) -> dict:
    """Current View: Real-time conditions with 5-level insights."""
    aqi_realtime = aqi_realtime or {}
    return {
        "temp": current.get("AT"),
        "obs_time": current.get("obs_time"),
        "location": current.get("station_name"),
        "weather_code": current.get("Wx"),
        "weather_text": current.get("Wx_text"),
        "ground_state": current.get("ground_state", "Dry"),
        "ground_level": current.get("ground_level", 1),

        # 5-Level Metrics
        "hum": {
            "val": current.get("RH"),
            "text": current.get("hum_text", "Normal"),
            "level": current.get("hum_level", 3)
        },
        "wind": {
            "val": current.get("WDSD"),
            "text": current.get("wind_text", "Calm"),
            "level": current.get("wind_level", 1),
            "dir": current.get("wind_dir_text")
        },
        "aqi": {
            "val": current.get("aqi"),
            "text": current.get("aqi_status", "Good"),
            "level": current.get("aqi_level", 1),
            "pm25": aqi_realtime.get("pm25"),
            "pm10": aqi_realtime.get("pm10"),
        },
        "vis": {
            "val": current.get("visibility"),
            "text": current.get("vis_text", "Good"),
            "level": current.get("vis_level", 1)
        },
        "uv": {
            "val": current.get("UVI"),
            "text": current.get("uv_text", "Low"),
            "level": current.get("uv_level", 1)
        },
        "pres": {
            "val": current.get("PRES"),
            "text": current.get("pres_text", "Normal"),
            "level": current.get("pres_level", 3)
        },
        "solar": solar,
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

    return {
        "timeline": timeline_list,
        "weekly_timeline": forecast_7day[:16],
        "aqi_forecast": {
            **aqi_forecast,
        },
        "transitions": transitions,
    }


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
        
    rain_gear_text = summaries.get("rain_gear")
    if not rain_gear_text:
        rain_gear_text = ("不需準備雨具。" if not rain_recent else "請記得攜帶雨具。") if is_zh else ("No precipitation gear expected." if not rain_recent else "Carry an umbrella.")

    # 2. Commute (v6: p2_garden_commute contains garden + commute)
    commute_text = summaries.get("commute") or paragraphs.get("p2_garden_commute")
    if not commute_text:
        am = commute.get("morning", {}).get("hazards", [])
        pm = commute.get("evening", {}).get("hazards", [])
        if am:
            commute_text = (f"早上注意：{am[0]}。") if is_zh else (f"Morning alert: {am[0]}.")
        elif pm:
            commute_text = (f"傍晚注意：{pm[0]}。") if is_zh else (f"Evening alert: {pm[0]}.")
        else:
            commute_text = "交通狀況良好。" if is_zh else "Traffic conditions look normal."

    # 3. HVAC (v6: p4_meal_climate contains meals + climate control)
    hvac_text = summaries.get("hvac") or paragraphs.get("p4_meal_climate")
    if not hvac_text:
        hvac_mode = climate.get("mode", "Off")
        dehumidifier = climate.get("dehumidifier")
        ac_mode = climate.get("ac_mode")
        windows = climate.get("windows")
        aqi_val = current.get("aqi", 0)

        if is_zh:
            ac_suffix = "（乾燥模式）" if ac_mode == "dry" else ""
            mode_zh = {"Off": "關閉", "fan": "電風扇", "cooling": f"冷氣{ac_suffix}",
                       "heating": "暖氣", "dehumidify": "除濕機"}.get(hvac_mode, hvac_mode)
            hvac_parts = [f"建議：{mode_zh}。"]
            if dehumidifier in ("strongly_recommended", "recommended"):
                hvac_parts.append("建議開啟除濕機。")
            elif dehumidifier == "consider":
                hvac_parts.append("視情況考慮開除濕機。")
            if windows == "open":
                hvac_parts.append("適合開窗通風。")
            elif windows == "close":
                hvac_parts.append("建議關閉窗戶。")
            elif not dehumidifier and not windows and int(aqi_val or 0) > 100:
                hvac_parts.append("建議開啟空氣清淨機。")
        else:
            ac_suffix = " (dry mode)" if ac_mode == "dry" else ""
            mode_en = {"Off": "off", "fan": "fan only", "cooling": f"AC{ac_suffix}",
                       "heating": "heating", "dehumidify": "dehumidifier"}.get(hvac_mode, hvac_mode)
            hvac_parts = [f"System: {mode_en}."]
            if dehumidifier in ("strongly_recommended", "recommended"):
                hvac_parts.append("Dehumidifier recommended.")
            elif dehumidifier == "consider":
                hvac_parts.append("Consider the dehumidifier.")
            if windows == "open":
                hvac_parts.append("Open windows to ventilate.")
            elif windows == "close":
                hvac_parts.append("Keep windows closed.")
            elif not dehumidifier and not windows and int(aqi_val or 0) > 100:
                hvac_parts.append("Air purifier recommended.")
        hvac_text = " ".join(hvac_parts)

    # 4. Meals (v6: p4_meal_climate)
    meals_text = summaries.get("meals") or paragraphs.get("p4_meal_climate")
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

    # 5. Garden (v6: first sentence of p2_garden_commute) & Outdoor (v6: p3_outdoor)
    garden_text = summaries.get("garden")
    outdoor_text = summaries.get("outdoor") or paragraphs.get("p3_outdoor")

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

    # Meal mood category
    meal_mood = processed.get("meal_mood", {}).get("mood")

    # Air quality forecast card
    aqi_forecast = processed.get("aqi_forecast", {})
    air_quality_text = summaries.get("air_quality", "")
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

    # Direct MOENV warnings: surface when AQI is elevated (>= 100)
    aqi_num = aqi_forecast.get("aqi")
    if isinstance(aqi_num, (int, float)) and aqi_num >= 100:
        for w in aqi_forecast.get("warnings", []):
            _alert.append({"type": "Air", "level": "WARNING", "msg": w})

    # Peak AQI window from hourly forecast
    hourly_aqi = aqi_forecast.get("hourly", [])
    peak_window = _compute_aqi_peak_window(hourly_aqi)

    return {
        "wardrobe": {
            "text": wardrobe_text,
            "feels_like": at,
            "rain_gear_text": rain_gear_text,
        },
        "commute": {
            "text": commute_text,
            "hazards": commute.get("morning", {}).get("hazards", []) + commute.get("evening", {}).get("hazards", [])
        },
        "air_quality": {
            "text": air_quality_text or ("空氣品質資料暫不可用。" if is_zh else "Air quality data unavailable."),
            "aqi": aqi_forecast.get("aqi"),
            "status": aqi_forecast.get("status", ""),
            "peak_window": peak_window,
        },
        "hvac": {
            "text": hvac_text,
            "mode": climate.get("mode", "Off")
        },
        "meals": {
            "text": meals_text,
            "mood": meal_mood,
        },
        "garden": {
            "text": garden_text,
        },
        "outdoor": {
            "text": outdoor_text,
            "score": outdoor_index.get("score"),
            "grade": outdoor_index.get("grade"),
            "label": outdoor_index.get("label"),
            "top_activity": outdoor_index.get("top_activity"),
            "activity_scores": outdoor_index.get("activity_scores", {}),
            "parkinsons_safe": outdoor_index.get("parkinsons_safe", True),
            "best_window": outdoor_index.get("best_window"),
        },
        "alert": _alert,
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
            {"key": "p1", "title": "Current & Outlook",    "text": paragraphs.get("p1_conditions", "")},
            {"key": "p2", "title": "Garden & Commute",     "text": paragraphs.get("p2_garden_commute", "")},
            {"key": "p3", "title": "Outdoor with Dad",     "text": paragraphs.get("p3_outdoor", "")},
            {"key": "p4", "title": "Meals & Climate",      "text": paragraphs.get("p4_meal_climate", "")},
            {"key": "p5", "title": "Forecast",             "text": paragraphs.get("p5_forecast", "")},
            {"key": "p6", "title": "Yesterday's Accuracy", "text": paragraphs.get("p6_accuracy", "")},
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
