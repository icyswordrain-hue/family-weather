"""
narration/fallback_narrator.py — Builds a plain-text weather broadcast from processed data
without using any LLM. Appends ---METADATA--- and ---CARDS--- sections so the output
is parseable by parse_narration_response(), matching the LLM response format.
"""

from __future__ import annotations

import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def build_narration(
    processed: dict,
    date_str: str | None = None,
    history: list[dict] | None = None,
    lang: str = "en",
) -> str:
    """
    Generate a structured weather broadcast from processed data.

    Appends ---METADATA--- and ---CARDS--- JSON sections so that
    parse_narration_response() can populate lifestyle card summaries,
    matching the LLM output format.

    Args:
        processed: Output of data.processor.process()
        date_str:  ISO date (YYYY-MM-DD), defaults to today.
        history:   Conversation history list (for garden continuity).
        lang:      "en" or "zh-TW".

    Returns:
        Plain-text string with ---METADATA--- and ---CARDS--- appended.
    """
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    lines: list[str] = []

    # ── P1: Heads-Up & Current conditions ─────────────────────────────────────
    heads_ups = processed.get("heads_ups", [])
    if heads_ups:
        lines.append("Heads up! " + " ".join(heads_ups))

    current = processed.get("current", {})
    if current:
        temp = current.get("AT")
        humidity = current.get("RH")
        wind = current.get("beaufort_desc", "")
        wind_dir = current.get("wind_dir_text", "")
        rain = current.get("RAIN", 0)

        parts = [f"Feels like {temp:.0f}C right now." if temp is not None else ""]
        if humidity is not None:
            parts.append(f"Humidity {humidity:.0f}%.")
        if wind and wind != "Unknown":
            wind_str = f"{wind} from the {wind_dir}" if wind_dir and wind_dir != "Unknown" else wind
            parts.append(f"Wind: {wind_str}.")
        if rain is not None and float(rain or 0) > 0:
            parts.append(f"Rainfall in past hour: {rain} mm — ground is wet.")
        lines.append(" ".join(p for p in parts if p))

    # ── AQI ───────────────────────────────────────────────────────────────────
    aqi_realtime = processed.get("aqi_realtime", {})
    if aqi_realtime:
        aqi_val = aqi_realtime.get("aqi")
        category = aqi_realtime.get("status") or aqi_realtime.get("aqi_category", "")
        if aqi_val:
            lines.append(f"Tucheng Air Quality: AQI {aqi_val}, {category}.")

    # ── P2: Commute ───────────────────────────────────────────────────────────
    commute = processed.get("commute", {})
    morning = commute.get("morning", {})
    evening = commute.get("evening", {})
    commute_parts = []

    def _fmt_commute(label: str, leg: dict) -> str:
        s = label
        t = leg.get("AT")
        if t is not None:
            s += f", feels like {t:.0f}C"
        precip = leg.get("precip_text", "")
        if precip:
            s += f", rain chance {precip}"
        w = leg.get("beaufort_desc", "")
        wd = leg.get("wind_dir_text", "")
        if w and w != "Unknown":
            w_str = f"{w} from the {wd}" if wd and wd != "Unknown" else w
            s += f", {w_str}"
        vis = leg.get("visibility")
        if vis is not None:
            try:
                vis_km = float(vis)
                if vis_km < 5.0:
                    s += f", visibility {vis_km:.1f}km"
            except (ValueError, TypeError):
                pass
        hazards = leg.get("hazards", [])
        if hazards:
            s += f". Watch out: {hazards[0]}"
        return s + "."

    if morning:
        commute_parts.append(_fmt_commute("Morning commute", morning))
    if evening:
        commute_parts.append(_fmt_commute("Evening commute", evening))
    if commute_parts:
        lines.append(" ".join(commute_parts))

    # ── P3: Outdoor ───────────────────────────────────────────────────────────
    location_rec = processed.get("location_rec", {})
    top_locations = location_rec.get("top_locations", [])
    if top_locations:
        loc = top_locations[0]
        loc_name = loc.get("name", "")
        activity = loc.get("activity", "")
        notes = loc.get("notes", "")
        parkinsons = loc.get("parkinsons", "")
        parts = [f"Today's outdoor pick: {loc_name}."]
        if activity:
            parts.append(f"Activity: {activity}.")
        if parkinsons == "good":
            parts.append("Parkinson's friendly — flat, accessible terrain.")
        elif parkinsons == "ok":
            parts.append("Manageable for Parkinson's with a cane or companion.")
        if notes:
            parts.append(notes)
        lines.append(" ".join(parts))
    else:
        outdoor_mood = location_rec.get("mood", "")
        if outdoor_mood:
            lines.append(f"Outdoor conditions: {outdoor_mood}. Consider indoor activities today.")

    # ── P6: Today's forecast summary ──────────────────────────────────────────
    forecast_segments = processed.get("forecast_segments", {})
    transitions = processed.get("transitions", [])

    segment_order = ["Morning", "Afternoon", "Evening"]
    seg_summaries = []
    for seg_name in segment_order:
        seg = forecast_segments.get(seg_name)
        if not seg:
            continue
        t = seg.get("AT")
        precip = seg.get("precip_text", "")
        cloud = seg.get("cloud_cover", "")
        s = seg_name
        if t is not None:
            s += f" feels like {t:.0f}C"
        if cloud and cloud != "Unknown":
            s += f", {cloud}"
        if precip and precip != "Unknown":
            s += f", rain {precip}"
        seg_summaries.append(s)

    if seg_summaries:
        lines.append("Today's weather: " + "; ".join(seg_summaries) + ".")

    # ── Notable transitions ───────────────────────────────────────────────────
    notable: list[dict] = [t for t in transitions if t.get("is_transition")]
    for t in notable[:2]:
        from_seg = t.get("from_segment", "")
        to_seg = t.get("to_segment", "")
        breaches = t.get("breaches", [])
        if breaches:
            breach_descs = []
            for b in breaches:
                metric = b.get("metric", "")
                if metric == "AT":
                    breach_descs.append(f"temp {b.get('from', '?')}C -> {b.get('to', '?')}C")
                elif metric == "PoP6h":
                    breach_descs.append(f"rain {b.get('from', '?')} -> {b.get('to', '?')}")
                elif metric == "WS":
                    breach_descs.append(f"wind {b.get('from', '?')} -> {b.get('to', '?')}")
                elif metric == "CloudCover":
                    breach_descs.append(f"sky {b.get('from', '?')} -> {b.get('to', '?')}")
                else:
                    breach_descs.append(f"{metric} change")
            lines.append(f"Weather shift {from_seg} to {to_seg}: {', '.join(breach_descs)}.")

    # ── P4: Meal suggestion ───────────────────────────────────────────────────
    meal = processed.get("meal_mood", {})
    mood = meal.get("mood", "")
    suggestions = meal.get("top_suggestions", []) or meal.get("all_suggestions", [])
    if mood and mood != "Warm & Pleasant" and suggestions:
        lines.append(f"Weather mood: {mood}. " + " / ".join(suggestions) + ".")

    # ── P5: Climate control ───────────────────────────────────────────────────
    climate = processed.get("climate_control", {})
    mode = climate.get("mode", "")
    cardiac = processed.get("cardiac_alert")
    est_hours = climate.get("estimated_hours", 0)

    p5_skip = mode in ("fan", "none", None, "") and not cardiac

    if not p5_skip:
        if mode == "heating_optional":
            msg = "Layering indoors recommended"
            if est_hours:
                msg += f" — space heater briefly in morning or evening, roughly {est_hours} hours"
            lines.append(msg + ".")
        elif mode in ("cooling", "heating", "dehumidify"):
            mode_map = {"cooling": "AC cooling", "heating": "Heating", "dehumidify": "Dehumidifier"}
            notes = climate.get("notes", [])
            reason = notes[0] if notes else ""
            msg = f"Suggestion: use {mode_map[mode]} indoors"
            if climate.get("set_temp"):
                msg += f" at {climate['set_temp']}"
            if est_hours:
                msg += f", estimated ~{est_hours} hours"
            if reason:
                msg += f" — {reason}"
            lines.append(msg + ".")
        if cardiac and isinstance(cardiac, dict):
            reason = cardiac.get("reason", "")
            if reason:
                lines.append(f"Health alert: {reason}")
        elif cardiac and isinstance(cardiac, str):
            lines.append(f"Health alert: {cardiac}")
    else:
        lines.append("Comfortable conditions today — no AC or heating needed, open the windows.")

    # ── Accountability ─────────────────────────────────────────────────────────
    lines.append("Forecast accuracy: no previous forecast available for comparison in template mode.")

    # ── AQI Forecast ──────────────────────────────────────────────────────────
    aqi_forecast = processed.get("aqi_forecast", {})
    if aqi_forecast:
        fc_aqi = aqi_forecast.get("aqi")
        fc_status = aqi_forecast.get("status", "")
        if fc_aqi:
            lines.append(f"AQI Forecast: {fc_aqi}, {fc_status}.")

    if not lines:
        lines.append(f"{date_str} weather data unavailable, please try again later.")

    narration_text = "\n\n".join(lines)

    # ── Structured sections (matches LLM output format) ───────────────────────
    metadata = _build_fallback_metadata(processed, history)
    cards = _build_fallback_cards(processed, history, lang)

    return (
        narration_text
        + "\n\n---METADATA---\n"
        + json.dumps(metadata, ensure_ascii=False)
        + "\n\n---CARDS---\n"
        + json.dumps(cards, ensure_ascii=False)
    )


def _build_fallback_metadata(processed: dict, history: list[dict] | None) -> dict:
    """Build the ---METADATA--- JSON for history tracking."""
    current = processed.get("current", {})
    commute = processed.get("commute", {})
    meal_mood_data = processed.get("meal_mood", {})
    climate = processed.get("climate_control", {})
    cardiac = processed.get("cardiac_alert")
    menieres = processed.get("menieres_alert")
    forecast_segs = processed.get("forecast_segments", {})

    at = current.get("AT")
    rain_gear_bool = any(
        "likely" in (seg.get("precip_text") or "").lower()
        for seg in forecast_segs.values()
    )

    morning = commute.get("morning", {})
    evening = commute.get("evening", {})
    commute_am = f"feels like {morning['AT']:.0f}°" if morning.get("AT") else "clear"
    commute_pm = f"feels like {evening['AT']:.0f}°" if evening.get("AT") else "clear"

    suggestions = meal_mood_data.get("top_suggestions", []) or meal_mood_data.get("all_suggestions", [])
    meal = suggestions[0] if suggestions else None

    # Garden topic: yesterday's from history, else seasonal
    yesterday_garden = None
    if history:
        for day in reversed(history):
            g = day.get("metadata", {}).get("garden")
            if g:
                yesterday_garden = g
                break
    month = datetime.now().month
    _seasonal = {
        1: "winter protection", 2: "pre-spring check", 3: "spring planting",
        4: "spring planting", 5: "watering check", 6: "heat protection",
        7: "heat protection", 8: "heat protection", 9: "autumn pruning",
        10: "autumn pruning", 11: "frost prep", 12: "winter protection",
    }
    garden_topic = yesterday_garden or _seasonal.get(month, "soil check")

    mode = climate.get("mode", "")
    climate_str = f"{mode} mode" if mode and mode not in ("Off", "fan", "none", "") else None

    cardiac_triggered = bool(cardiac and isinstance(cardiac, dict) and cardiac.get("triggered"))
    menieres_triggered = bool(
        menieres and isinstance(menieres, dict) and menieres.get("severity") in ("high", "moderate")
    )

    morning_seg = forecast_segs.get("Morning", {})
    afternoon_seg = forecast_segs.get("Afternoon", {})
    m_at = morning_seg.get("AT")
    a_at = afternoon_seg.get("AT")
    oneliner = (
        f"Morning starts around {m_at:.0f}°, afternoon at {a_at:.0f}°."
        if m_at and a_at
        else "Check conditions throughout the day."
    )

    return {
        "wardrobe": f"feels like {at:.0f}°" if at is not None else "check conditions",
        "rain_gear": rain_gear_bool,
        "commute_am": commute_am,
        "commute_pm": commute_pm,
        "meal": meal,
        "outdoor": None,
        "garden": garden_topic,
        "climate": climate_str,
        "cardiac_alert": cardiac_triggered,
        "menieres_alert": menieres_triggered,
        "forecast_oneliner": oneliner,
        "accuracy_grade": "first broadcast",
    }


def _build_fallback_cards(processed: dict, history: list[dict] | None, lang: str) -> dict:
    """Build the ---CARDS--- JSON matching the LLM CARDS structure."""
    is_zh = lang == "zh-TW"
    current = processed.get("current", {})
    commute = processed.get("commute", {})
    morning = commute.get("morning", {})
    evening = commute.get("evening", {})
    climate = processed.get("climate_control", {})
    meal_mood_data = processed.get("meal_mood", {})
    heads_ups = processed.get("heads_ups", [])
    cardiac = processed.get("cardiac_alert")
    menieres = processed.get("menieres_alert")
    outdoor_index = processed.get("outdoor_index", {})
    location_rec = processed.get("location_rec", {})
    top_locations = location_rec.get("top_locations", [])
    recent_locations = processed.get("recent_locations", [])
    forecast_segments = processed.get("forecast_segments", {})

    at = current.get("AT")
    rain_recent = float(current.get("RAIN") or 0) > 0

    # ── Wardrobe (1 sentence) ─────────────────────────────────────────────────
    if is_zh:
        if at is None:
            wardrobe = "出門前請確認天氣狀況，適當穿著。"
        elif at >= 30:
            wardrobe = "天氣炎熱，選擇清涼透氣的輕薄衣物。"
        elif at >= 25:
            wardrobe = f"體感 {at:.0f} 度，輕便穿著即可。"
        elif at >= 18:
            wardrobe = f"體感 {at:.0f} 度，薄外套或長袖就夠了。"
        elif at >= 12:
            wardrobe = "天氣偏涼，建議穿上外套並採用分層穿搭。"
        else:
            wardrobe = "天氣寒冷，請做好保暖，多添幾件衣物。"
    else:
        if at is None:
            wardrobe = "Check conditions before heading out and dress accordingly."
        elif at >= 30:
            wardrobe = "Light, breathable clothing is the call — it's going to feel hot."
        elif at >= 25:
            wardrobe = f"Light layers are all you need — feels like {at:.0f}° out there."
        elif at >= 18:
            wardrobe = f"A light jacket or long sleeves should do — feels around {at:.0f}°."
        elif at >= 12:
            wardrobe = "A proper jacket and layering recommended for the cooler conditions."
        else:
            wardrobe = "Bundle up — it's cold outside, layer up well."

    # ── Rain Gear (1 sentence) ────────────────────────────────────────────────
    any_rain_likely = any(
        "likely" in (seg.get("precip_text") or "").lower()
        for seg in forecast_segments.values()
    )
    commute_rain = any(
        "likely" in (leg.get("precip_text") or "").lower()
        for leg in (morning, evening)
    )
    if is_zh:
        if any_rain_likely or commute_rain:
            rain_gear = "今天降雨機率偏高，建議帶傘出門。"
        elif rain_recent:
            rain_gear = "地面已濕，備把折疊傘以防萬一。"
        else:
            rain_gear = "今天不需要雨具。"
    else:
        if any_rain_likely or commute_rain:
            rain_gear = "Rain is likely at some point today — bring an umbrella."
        elif rain_recent:
            rain_gear = "The ground is already wet — tuck a compact umbrella in your bag just in case."
        else:
            rain_gear = "No rain gear needed today."

    # ── Commute (2 sentences) ─────────────────────────────────────────────────
    def _commute_sent(leg: dict, label_en: str, label_zh: str, default_en: str, default_zh: str) -> str:
        if not leg:
            return default_zh if is_zh else default_en
        t = leg.get("AT")
        precip = leg.get("precip_text", "")
        hazards = leg.get("hazards", [])
        if is_zh:
            s = label_zh
            if t is not None:
                s += f"體感 {t:.0f} 度"
            if precip:
                s += f"，降雨{precip}"
            if hazards:
                s += f"，注意：{hazards[0]}"
            return s + "。"
        else:
            s = label_en
            if t is not None:
                s += f" feels like {t:.0f}°"
            if precip:
                s += f", rain {precip}"
            if hazards:
                s += f" — {hazards[0]}"
            return s + "."

    am_sent = _commute_sent(morning, "Morning commute:", "早上通勤：", "Morning commute looks clear.", "早上路況正常。")
    pm_sent = _commute_sent(evening, "Evening commute:", "傍晚返家：", "Evening commute looks clear.", "傍晚路況正常。")
    commute_text = f"{am_sent} {pm_sent}"

    # ── Meals (2 sentences) ───────────────────────────────────────────────────
    mood = meal_mood_data.get("mood", "")
    suggestions = meal_mood_data.get("top_suggestions", []) or meal_mood_data.get("all_suggestions", [])
    if suggestions:
        dish = suggestions[0]
        if is_zh:
            meals = f"今天的天氣氛圍{mood}，推薦來一碗{dish}。這道料理很適合這種天氣，暖胃又對味。"
        else:
            meals = f"The {mood.lower()} weather calls for {dish} today. It's exactly the kind of meal that fits the mood."
    else:
        meals = "今天沒有特別推薦的餐點。" if is_zh else "No specific meal recommendation for today."

    # ── HVAC (2 sentences) ────────────────────────────────────────────────────
    mode = climate.get("mode", "Off")
    est_hours = climate.get("estimated_hours", 0)
    set_temp = climate.get("set_temp")
    notes = climate.get("notes", [])
    if is_zh:
        mode_zh = {
            "Off": "關閉", "fan": "電風扇", "cooling": "冷氣",
            "heating": "暖氣", "dehumidify": "除濕機", "heating_optional": "暖氣（選用）",
        }.get(mode, mode)
        if mode in ("cooling", "heating", "dehumidify"):
            hvac_s1 = f"建議開啟{mode_zh}。"
            hvac_s2 = (
                f"設定 {set_temp}，預計使用約 {est_hours} 小時。" if set_temp and est_hours
                else (notes[0] if notes else "請依個人舒適度調整。")
            )
        elif mode == "heating_optional":
            hvac_s1 = "今天可以考慮短暫使用暖氣或電暖器。"
            hvac_s2 = f"大約 {est_hours} 小時即可，其餘時間多穿一件即可。" if est_hours else "依需求斟酌使用即可。"
        else:
            hvac_s1 = "今天天氣舒適，不需要開冷暖氣。"
            hvac_s2 = "可以開窗通風，享受自然空氣。"
    else:
        if mode in ("cooling", "heating", "dehumidify"):
            mode_en = {"cooling": "AC cooling", "heating": "heating", "dehumidify": "the dehumidifier"}.get(mode, mode)
            hvac_s1 = f"Run {mode_en} today for comfort."
            hvac_s2 = (
                f"Set to {set_temp}, roughly {est_hours} hours should do it." if set_temp and est_hours
                else (notes[0] if notes else "Adjust to personal comfort.")
            )
        elif mode == "heating_optional":
            hvac_s1 = "A brief burst of heat in the morning or evening wouldn't hurt."
            hvac_s2 = f"About {est_hours} hours should be plenty — otherwise just layer up." if est_hours else "Otherwise layering up indoors is fine."
        else:
            hvac_s1 = "Comfortable today — no AC or heating required."
            hvac_s2 = "Open the windows and let some fresh air in."
    hvac_text = f"{hvac_s1} {hvac_s2}"

    # ── Garden (2 sentences) ──────────────────────────────────────────────────
    yesterday_garden = None
    if history:
        for day in reversed(history):
            g = day.get("metadata", {}).get("garden")
            if g:
                yesterday_garden = g
                break
    month = datetime.now().month
    if is_zh:
        if yesterday_garden:
            garden_s1 = f"延續昨天的{yesterday_garden}，今天可以進一步照料一下。"
        elif rain_recent:
            garden_s1 = "昨夜有雨，今天適合檢查排水狀況，避免積水。"
        else:
            garden_s1 = "今天是照料花園的好時機，記得檢查土壤濕度。"
        seasonal_zh = {
            3: "春季適合播種或移植盆栽，把握春雨的滋潤。",
            4: "春季適合播種或移植盆栽，把握春雨的滋潤。",
            5: "注意澆水頻率，避免土壤過乾。",
            6: "夏季注意早晚澆水，避免正午暴曬導致植物缺水。",
            7: "夏季注意早晚澆水，避免正午暴曬導致植物缺水。",
            8: "夏季注意早晚澆水，避免正午暴曬導致植物缺水。",
            9: "秋季適合修剪和施肥，為植物準備越冬。",
            10: "秋季適合修剪和施肥，為植物準備越冬。",
            11: "注意霜害防護，為耐寒力弱的植物做好保暖。",
            12: "冬季減少澆水頻率，注意防寒保溫。",
            1: "冬季減少澆水頻率，注意防寒保溫。",
            2: "開春在即，可以開始準備播種所需的土壤和器具。",
        }
        garden_s2 = seasonal_zh.get(month, "注意土壤濕度和植物狀況。")
    else:
        if yesterday_garden:
            garden_s1 = f"Following up on yesterday's {yesterday_garden} — a good day to check in on how things are developing."
        elif rain_recent:
            garden_s1 = "After last night's rain, check drainage and avoid overwatering today."
        else:
            garden_s1 = "Good day to give the garden some attention — check soil moisture before watering."
        seasonal_en = {
            3: "Spring is a good time for sowing or transplanting — make the most of the seasonal moisture.",
            4: "Spring is a good time for sowing or transplanting — make the most of the seasonal moisture.",
            5: "Keep an eye on watering frequency as the warmer days arrive.",
            6: "Water in the early morning or evening to avoid midday heat stress on your plants.",
            7: "Water in the early morning or evening to avoid midday heat stress on your plants.",
            8: "Water in the early morning or evening to avoid midday heat stress on your plants.",
            9: "Autumn is ideal for pruning and fertilising to prepare plants for the cooler months ahead.",
            10: "Autumn is ideal for pruning and fertilising to prepare plants for the cooler months ahead.",
            11: "Watch for frost and protect any cold-sensitive plants overnight.",
            12: "Reduce watering frequency in winter and keep tender plants protected from cold snaps.",
            1: "Reduce watering frequency in winter and keep tender plants protected from cold snaps.",
            2: "Spring is just around the corner — start preparing soil and seed trays.",
        }
        garden_s2 = seasonal_en.get(month, "Check soil conditions and adjust care as needed.")
    garden_text = f"{garden_s1} {garden_s2}"

    # ── Outdoor (2 sentences) ─────────────────────────────────────────────────
    grade = outdoor_index.get("grade", "")
    best_window = outdoor_index.get("best_window", "")
    parkinsons_safe = outdoor_index.get("parkinsons_safe", True)
    top_activity = outdoor_index.get("top_activity", "")
    pick = next((l for l in top_locations if l.get("name") not in recent_locations), top_locations[0] if top_locations else None)

    if is_zh:
        if grade in ("A", "B"):
            verdict = "今天非常適合帶爸爸出門活動。"
        elif grade == "C":
            verdict = "今天戶外條件尚可，短暫外出問題不大。"
        elif grade in ("D", "F"):
            verdict = "今天戶外條件較差，建議在家進行室內活動。"
        else:
            verdict = "今天戶外條件一般，出門請注意天氣變化。"
        if pick:
            loc_name = pick.get("name", "")
            activity = pick.get("activity", top_activity or "散步")
            pk_note = "地形平坦，適合帕金森氏症患者。" if parkinsons_safe else "請有人陪同出行，注意步道狀況。"
            window_note = f"最佳時段：{best_window}。" if best_window else ""
            outdoor_s2 = f"推薦前往{loc_name}進行{activity}，{pk_note}{window_note}"
        elif best_window:
            outdoor_s2 = f"最佳外出時段為{best_window}，注意帕金森氏症患者的安全。"
        else:
            outdoor_s2 = "外出時請以安全為優先，選擇平坦易行的路線。"
    else:
        if grade in ("A", "B"):
            verdict = "Today is a great day to get Dad outside for some fresh air."
        elif grade == "C":
            verdict = "Outdoor conditions are manageable today — a short outing should be fine."
        elif grade in ("D", "F"):
            verdict = "Not a great day for outdoor activity — better to keep it indoors today."
        else:
            verdict = "Outdoor conditions are average today — use your judgement before heading out."
        if pick:
            loc_name = pick.get("name", "")
            activity = pick.get("activity", top_activity or "walking")
            pk_note = "flat, accessible terrain — Parkinson's friendly." if parkinsons_safe else "go with a companion and watch the terrain."
            window_note = f" Best window: {best_window}." if best_window else ""
            outdoor_s2 = f"{loc_name} is a good pick for {activity} — {pk_note}{window_note}"
        elif best_window:
            outdoor_s2 = f"If heading out, {best_window} is the best window — keep it short and safe."
        else:
            outdoor_s2 = "Stick to flat, familiar routes if heading out, and take it easy."
    outdoor_text = f"{verdict} {outdoor_s2}"

    # ── Alert ─────────────────────────────────────────────────────────────────
    cardiac_triggered = bool(cardiac and isinstance(cardiac, dict) and cardiac.get("triggered"))
    menieres_high = bool(menieres and isinstance(menieres, dict) and menieres.get("severity") == "high")
    if cardiac_triggered:
        alert_text = cardiac.get("reason", "Cardiac risk — keep Dad warm and avoid sudden cold exposure.")
        alert_level = "CRITICAL"
    elif menieres_high:
        alert_text = "Ménière's risk today — take it slow and keep medication accessible."
        alert_level = "CRITICAL"
    elif heads_ups:
        alert_text = " ".join(heads_ups[:2])
        alert_level = "WARNING"
    else:
        alert_text = "今天一切正常。" if is_zh else "All clear today."
        alert_level = "INFO"

    return {
        "wardrobe": wardrobe,
        "rain_gear": rain_gear,
        "commute": commute_text,
        "meals": meals,
        "hvac": hvac_text,
        "garden": garden_text,
        "outdoor": outdoor_text,
        "alert": {"text": alert_text, "level": alert_level},
    }
