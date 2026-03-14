"""chat_context.py — Build the system prompt context for the /api/chat endpoint.

Extracts a compact snapshot of today's processed weather data from the broadcast
object so Haiku can answer user questions without re-running the pipeline.
Total injected context: ~600-650 tokens.
"""

from __future__ import annotations

import json


def build_chat_context(broadcast: dict, date: str, lang: str = "en") -> str:
    """
    Build a system prompt string containing today's weather snapshot.

    Args:
        broadcast: Full broadcast dict (from get_today_broadcast or _broadcast_cache).
        date: Date string YYYY-MM-DD.
        lang: 'en' or 'zh-TW'.

    Returns:
        Plain-text system prompt for client.messages.create(system=...).
    """
    pd = broadcast.get("processed_data", {})

    # Handle v2 schema (language-specific fields nested under langs)
    if broadcast.get("schema_version") == 2:
        _langs = broadcast.get("langs", {})
        _ld = _langs.get(lang) or next(iter(_langs.values()), {})
        summaries = _ld.get("summaries", {})
        metadata = _ld.get("metadata", {})
    else:
        summaries = broadcast.get("summaries", {})
        metadata = broadcast.get("metadata", {})

    # ── Current conditions ─────────────────────────────────────────────────
    current = pd.get("current", {})
    current_snap = {
        k: v for k, v in {
            "apparent_temp_c": current.get("AT"),
            "actual_temp_c": current.get("T"),
            "humidity_pct": current.get("RH"),
            "wind_speed_mps": current.get("WDSD"),
            "wind_description": current.get("beaufort_desc") or current.get("wind_text"),
            "aqi": current.get("AQI") or current.get("aqi"),
            "aqi_status": current.get("aqi_status"),
            "pressure_hpa": current.get("PRES"),
            "uv_index": current.get("UVI"),
            "rainfall_mm": current.get("RAIN"),
            "weather": current.get("Wx_text"),
            "ground_state": current.get("ground_state"),
            "dew_point_c": current.get("dew_point"),
            "humidity_label": current.get("saturation_label") or current.get("hum_text"),
        }.items()
        if v is not None
    }

    # ── Forecast segments ──────────────────────────────────────────────────
    _SEG_KEYS = (
        "AT", "MinAT", "MaxAT", "RH", "PoP6h", "Wx",
        "cloud_cover", "start_time", "end_time", "precip_text", "wind_text",
    )
    segments = {
        name: {k: seg[k] for k in _SEG_KEYS if k in seg}
        for name, seg in pd.get("forecast_segments", {}).items()
    }

    # ── 7-day outlook (first 4 days sufficient for planning queries) ───────
    _DAY_KEYS = ("date", "MinAT", "MaxAT", "PoP12h", "Wx")
    outlook = [
        {k: slot[k] for k in _DAY_KEYS if k in slot}
        for slot in pd.get("forecast_7day", [])[:4]
    ]

    # ── Health alerts ──────────────────────────────────────────────────────
    cardiac = pd.get("cardiac_alert", {})
    menieres = pd.get("menieres_alert", {})

    # ── Outdoor index ──────────────────────────────────────────────────────
    outdoor = pd.get("outdoor_index", {})

    lang_line = (
        "請以繁體中文回答，簡潔（1–3句）。"
        if lang == "zh-TW"
        else "Answer in English, concisely (1–3 sentences)."
    )

    def _j(obj: object) -> str:
        return json.dumps(obj, ensure_ascii=False, indent=2)

    lines = [
        "You are Canopy, a helpful weather assistant for a family near Shulin/Banqiao, New Taipei, Taiwan.",
        "Answer questions using ONLY the weather snapshot below. Be concise (1–3 sentences).",
        "If a question cannot be answered from the provided data, say so — do not invent numbers.",
        lang_line,
        "",
        f"Date: {date}",
        "",
        "--- CURRENT CONDITIONS ---",
        _j(current_snap),
        "",
        "--- FORECAST SEGMENTS (36H) ---",
        _j(segments),
        "",
        "--- 7-DAY OUTLOOK (next 4 days) ---",
        _j(outlook),
        "",
        "--- HEALTH ALERTS ---",
        f"Cardiac: triggered={cardiac.get('triggered', False)}, severity={cardiac.get('severity', 'none')}",
        f"Menieres: triggered={menieres.get('triggered', False)}, severity={menieres.get('severity', 'none')}",
        "",
        "--- OUTDOOR INDEX ---",
        f"Grade: {outdoor.get('overall_grade', '?')} | Score: {outdoor.get('overall_score', '?')} | Label: {outdoor.get('overall_label', '?')}",
        "",
        "--- LIFESTYLE SUMMARIES (pre-written) ---",
        _j(summaries),
        "",
        "--- KEY FLAGS ---",
        f"Rain gear needed: {metadata.get('rain_gear', False)}",
        f"Forecast oneliner: {metadata.get('forecast_oneliner', '')}",
    ]

    return "\n".join(lines)
