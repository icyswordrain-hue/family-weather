"""
template_narrator.py — Builds a plain-text weather broadcast from processed data
without using any LLM. The text is suitable for direct input into Cloud TTS.
"""

from __future__ import annotations

from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def build_narration(processed: dict, date_str: str | None = None) -> str:
    """
    Generate a simple, readable English weather broadcast from processed data.

    Args:
        processed: Output of data.processor.process()
        date_str:  ISO date (YYYY-MM-DD), defaults to today.

    Returns:
        Plain-text string suitable for Cloud TTS.
    """
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    lines: list[str] = []

    # ── Current conditions ────────────────────────────────────────────────────
    current = processed.get("current", {})
    if current:
        temp = current.get("AT")
        humidity = current.get("RH")
        wind = current.get("beaufort_desc", "")
        rain = current.get("RAIN", 0)

        parts = [f"Feels like {temp:.0f}C right now." if temp is not None else ""]
        if humidity is not None:
            parts.append(f"Humidity {humidity:.0f}%.")
        if wind and wind != "Unknown":
            parts.append(f"Wind: {wind}.")
        if rain is not None and float(rain) > 0:
            parts.append(f"Rainfall in past 2 hours: {rain} mm.")
        lines.append(" ".join(p for p in parts if p))

    # ── AQI ───────────────────────────────────────────────────────────────────
    aqi_realtime = processed.get("aqi_realtime", {})
    if aqi_realtime:
        aqi_val = aqi_realtime.get("aqi")
        category = aqi_realtime.get("status") or aqi_realtime.get("aqi_category", "")
        if aqi_val:
            lines.append(f"Tucheng Air Quality: AQI {aqi_val}, {category}.")

    # ── Commute ───────────────────────────────────────────────────────────────
    commute = processed.get("commute", {})
    morning = commute.get("morning", {})
    evening = commute.get("evening", {})
    if morning:
        precip = morning.get("precip_text", "")
        temp_m = morning.get("AT")
        s = "Morning commute"
        if temp_m is not None:
            s += f", feels like {temp_m:.0f}C"
        if precip:
            s += f", rain chance {precip}"
        s += "."
        lines.append(s)
    if evening:
        precip = evening.get("precip_text", "")
        temp_e = evening.get("AT")
        s = "Evening commute"
        if temp_e is not None:
            s += f", feels like {temp_e:.0f}C"
        if precip:
            s += f", rain chance {precip}"
        s += "."
        lines.append(s)

    # ── Today's forecast summary ──────────────────────────────────────────────
    # processor.py returns "forecast_segments" as a dict keyed by segment name
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
    for t in notable[:2]:  # max 2 alerts
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

    # ── Meal suggestion ───────────────────────────────────────────────────────
    meal = processed.get("meal_mood", {})
    mood = meal.get("mood", "")
    suggestions = meal.get("all_suggestions", []) or meal.get("top_suggestions", [])
    if mood and mood != "Warm & Pleasant" and suggestions:
        dish = suggestions[0] if suggestions else ""
        lines.append(f"Weather mood: {mood}. Suggested meal: {dish}.")

    # ── Climate control ───────────────────────────────────────────────────────
    climate = processed.get("climate_control", {})
    mode = climate.get("mode", "")
    if mode in ("cooling", "heating", "dehumidify"):
        mode_map = {"cooling": "AC cooling", "heating": "Heating", "dehumidify": "Dehumidifier"}
        notes = climate.get("notes", [])
        reason = notes[0] if notes else ""
        msg = f"Suggestion: use {mode_map[mode]} indoors"
        if climate.get("set_temp"):
            msg += f" at {climate['set_temp']}"
        if reason:
            msg += f" - {reason}"
        lines.append(msg + ".")

    # ── Cardiac alert ─────────────────────────────────────────────────────────
    cardiac = processed.get("cardiac_alert")
    if cardiac and isinstance(cardiac, dict):
        reason = cardiac.get("reason", "")
        if reason:
            lines.append(f"Health alert: {reason}")
    elif cardiac and isinstance(cardiac, str):
        lines.append(f"Health alert: {cardiac}")

    # ── AQI Forecast ──────────────────────────────────────────────────────────
    aqi_forecast = processed.get("aqi_forecast", {})
    if aqi_forecast:
        fc_aqi = aqi_forecast.get("aqi")
        fc_status = aqi_forecast.get("status", "")
        if fc_aqi:
            lines.append(f"AQI Forecast: {fc_aqi}, {fc_status}.")

    if not lines:
        lines.append(f"{date_str} weather data unavailable, please try again later.")

    return "\n\n".join(lines)
