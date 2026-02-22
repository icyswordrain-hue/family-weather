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
    # Helper to format a commute leg
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

    # ── P3: Gardening & Parkinson's / Outdoor ─────────────────────────────────
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

    # ── P4: Meal suggestion (conditional — skip if Warm & Pleasant) ──────────
    meal = processed.get("meal_mood", {})
    mood = meal.get("mood", "")
    suggestions = meal.get("top_suggestions", []) or meal.get("all_suggestions", [])
    if mood and mood != "Warm & Pleasant" and suggestions:
        lines.append(f"Weather mood: {mood}. " + " / ".join(suggestions) + ".")

    # ── P5: Climate control & Cardiac (conditional — v4 skip logic) ───────────
    climate = processed.get("climate_control", {})
    mode = climate.get("mode", "")
    cardiac = processed.get("cardiac_alert")
    est_hours = climate.get("estimated_hours", 0)

    # v4 rule: skip P5 if comfortable (fan/none mode) AND no cardiac alert
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

        # Cardiac alert (inside P5)
        if cardiac and isinstance(cardiac, dict):
            reason = cardiac.get("reason", "")
            if reason:
                lines.append(f"Health alert: {reason}")
        elif cardiac and isinstance(cardiac, str):
            lines.append(f"Health alert: {cardiac}")
    else:
        # Fold comfort note into the output (per v4 spec)
        lines.append("Comfortable conditions today — no AC or heating needed, open the windows.")

    # ── P7: Accountability ────────────────────────────────────────────────────
    # Template can't do a full forecast-vs-actual comparison, but we note it
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

    return "\n\n".join(lines)
