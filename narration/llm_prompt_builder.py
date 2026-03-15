"""
prompt_builder.py — v7
Builds the Claude/Gemini prompt from pre-processed weather data.

Paragraph structure (v7):
  P1  Conditions & Alerts (always) — current weather, wardrobe, heads-up, cardiac, Ménière's (no AQI)
  P2  Garden & Commute (always) — gardening tip + both commute legs
  P3  Outdoor & Meal (always) — outdoor activity + one dish
  P4  HVAC & Air Quality (always) — climate control + AQI/window guidance
  P5  Forecast & Accuracy (always) — 24h forecast + accuracy review (last 3 days)

Changes from v6:
  - 6 paragraphs → 5
  - AQI status removed from P1; moved to new P4
  - P3 (outdoor) + P4 (meal) merged into new P3 (outdoor & meal)
  - Old P5 (forecast) + P6 (accuracy) merged into new P5
  - Accuracy extended to last 3 days (was yesterday only), capped at 1 sentence
  - Total word count reduced: 320–350 → 245–270 words (EN)
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT — v7
# ─────────────────────────────────────────────────────────────────────────────

_V7_LANG_CONFIG = {
    "en": {
        "role": "You are a warm, concise broadcaster for a family near Shulin/Banqiao, Taiwan. Use ONLY the provided JSON weather data; never invent numbers. Output a plain-text script for a TTS engine.",
        "lang_rules": "- English only. Use pinyin for Chinese terms (e.g., \"niu rou mian\"). Zero Chinese characters.",
        "word_count": "225–250 words",
        "format_rule": "- Plain text only. No markdown, headers, bullets, or code blocks.",
        "p3_dish_note": "Write the dish name in pinyin.",
        "p3_location_note": "name the time (e.g., \"mid-morning\") and the location (pinyin).",
        "meta_intro": "Output exact separator ---METADATA--- then a single JSON:",
        "meta_examples": {
            "wardrobe": "1-sentence wardrobe advice based on apparent temperature",
            "wardrobe_tagline": "≤8 words imperative covering wardrobe + rain gear. e.g. 'Light jacket; bring an umbrella.'",
            "rain_gear_text": "1 sentence — whether to carry umbrella, raincoat, or boots",
            "commute_am": "1-sentence morning commute summary",
            "commute_pm": "1-sentence evening commute summary",
            "commute_tagline": "≤8 words key commute condition. e.g. 'Rain delays — allow extra 15 min.'",
            "meal": "single dish name in pinyin, or null if P3 meal section was skipped",
            "meals_text": "1 sentence meal suggestion matching the weather mood",
            "meals_tagline": "≤8 words food + weather mood. e.g. 'Hot soup weather — try beef noodles.'",
            "outdoor": "1-sentence Dad outing summary, or null if P3 was skipped",
            "outdoor_tagline": "≤8 words activity + best time. e.g. 'Great for photography — head out before noon.'",
            "garden": "3-5 word gardening tip topic for history tracking",
            "garden_text": "2 sentences — garden tasks and soil or plant care advice",
            "garden_tagline": "≤8 words garden task. e.g. 'Skip watering — rain does the job.'",
            "climate": "1-sentence climate control summary, or null if skipped",
            "hvac_tagline": "≤8 words climate action. e.g. 'Run AC on dry mode today.'",
            "air_quality_summary": "1 sentence AQI advisory for tomorrow (Good: reassure; Moderate: name pollutant + sensitive groups; Unhealthy: limit outdoor exposure)",
            "air_quality_tagline": "≤8 words air status. e.g. 'Clean air — no precautions needed.'",
            "alert_text": "1-2 sentences health risks (cardiac, Ménière's) and commute hazards. Empty string if nothing to flag. Do NOT include air quality.",
            "alert_level": "INFO or WARNING or CRITICAL. CRITICAL = cardiac/Ménière's; WARNING = safety heads-up; INFO = mild note. Leave alert_text empty for uneventful days.",
            "forecast_oneliner": "the bottom-line takeaway from P5",
            "accuracy_grade": "spot on / close / off / first broadcast",
        },
    },
    "zh-TW": {
        "role": "你是一個親切、簡潔的家庭廣播員，服務台灣樹林/板橋交界處的一家人。只使用提供的 JSON 天氣數據，絕對不要自行填補數字。輸出為 TTS 引擎使用的純文字廣播稿。",
        "lang_rules": "- 使用繁體中文。地名與菜餚直接用中文（如「牛肉麵」）。",
        "word_count": "305–335 字",
        "format_rule": "- 純文字格式。不使用標題、粗體、斜體、項目符號或程式碼區塊。\n- ---METADATA--- 之後的 JSON 物件鍵名與英文值須保持英文。",
        "p3_dish_note": "以中文寫出菜名。",
        "p3_location_note": "指定出門時段並以拼音標註地點名稱。",
        "meta_intro": "輸出 ---METADATA--- 後接 JSON（鍵名保持英文，值用繁體中文）：",
        "meta_examples": {
            "wardrobe": "1句話穿著建議",
            "wardrobe_tagline": "≤8字命令式，涵蓋穿著與雨具。例如：「輕薄外套，記得帶傘。」",
            "rain_gear_text": "1句話——是否需要雨傘、雨衣或雨靴",
            "commute_am": "1句話早上通勤摘要",
            "commute_pm": "1句話傍晚通勤摘要",
            "commute_tagline": "≤8字通勤關鍵狀況。例如：「雨天延誤，多留15分鐘。」",
            "meal": "單一菜名，若跳過則為 null",
            "meals_text": "1句話符合天氣心情的餐食建議",
            "meals_tagline": "≤8字餐食推薦。例如：「適合來碗熱牛肉麵。」",
            "outdoor": "1句話爸爸外出摘要，若跳過 P3 則為 null",
            "outdoor_tagline": "≤8字活動＋最佳時段。例如：「適合攝影，午前出發最佳。」",
            "garden": "3-5 字的花園主題用以歷史追蹤",
            "garden_text": "2句話——花園工作和土壤或植物護理建議",
            "garden_tagline": "≤8字花園任務。例如：「今天有雨，免澆水。」",
            "climate": "1句話空調摘要，若跳過則為 null",
            "hvac_tagline": "≤8字空調行動。例如：「開除濕模式即可。」",
            "air_quality_summary": "1句話明日 AQI 建議（良好：令人放心；普通：指出主要污染物；不健康：建議減少戶外活動）",
            "air_quality_tagline": "≤8字明日空氣狀況。例如：「空氣清新，無需防護。」",
            "alert_text": "1-2句話健康風險（心臟、梅尼爾氏症）及通勤危險摘要。不含空氣品質。若無事項則留空字串。",
            "alert_level": "INFO 或 WARNING 或 CRITICAL。CRITICAL=心臟或梅尼爾氏症；WARNING=安全提示；INFO=輕微注意。",
            "forecast_oneliner": "字串",
            "accuracy_grade": "字串",
        },
    },
}


def _build_v7_prompt(lang: str) -> str:
    """Assemble the v7 system prompt from the shared template + language config."""
    cfg = _V7_LANG_CONFIG.get(lang, _V7_LANG_CONFIG["en"])
    ex = cfg["meta_examples"]

    return f"""{cfg["role"]}

RULES:
{cfg["lang_rules"]}
{cfg["format_rule"]}
- Total length: {cfg["word_count"]}. Tight and direct. Every sentence must carry information.

STYLE:
- Lead with the point: Every paragraph opens with the most important takeaway.
- No wind-ups: Never open a paragraph with atmosphere-setting sentences. The first word of each paragraph should be a fact or action.
- Sensation first: Say "sticky and warm" rather than "humidity 72%." Use the provided beaufort_desc and precip_text. One precise number per paragraph maximum.
- Transition narration: Describe shifts as physical movement ("clouds will thicken through the afternoon") rather than data diffs.
- Life-anchored time: Use "before you leave at seven" or "around lunch" instead of "06:00–12:00."
- Yesterday comparison: Include one brief comparison (e.g., "warmer than yesterday") using history. Skip if no history.
- Hard limit: Every paragraph must be 4 sentences or fewer.

STRUCTURE:

P1 — Current Conditions & Alerts (4 sentences max):
Open with heads_ups[] alerts (or "Smooth sailing" if empty). State apparent temperature, humidity sensation, wind (e.g., "gentle breeze out of the north"), clouds, ground wetness, and visibility. Do NOT mention AQI here — that belongs in P4.
Weave in Cardiac (if cardiac_alert) and Ménière's (if menieres_alert) naturally. Focus on physical sensations and practical advice (e.g., "keep Dad's room warm" or "take it slow today").
Close with wardrobe. State explicitly if rain gear (umbrella or raincoat) is needed.

P2 — Garden & Commute (4 sentences max):
Start with a gardening tip based on history (or seasonal if no history). Pivot to the commute (Sanxia/Shulin). Cover AT, precip_text, wind, and hazards. Combine morning and evening legs into one summary.

P3 — Outdoor & Meal (4 sentences max):
Recommend an outdoor activity for Dad (or indoor if weather is poor). Choose ONE location from top_locations that best fits today's weather — use its notes (shade, surface, terrain) to explain why it suits the conditions; {cfg["p3_location_note"]}
Choose ONE dish from top_meals_detail that best matches today's weather mood — reference its description or tags to explain how it complements the weather (e.g., "cooling jelly clears the heat" or "hearty noodle soup warms you up"). {cfg["p3_dish_note"]}

P4 — HVAC & Air Quality (2 sentences max):
One sentence: plain advice on AC/heater/dehumidifier mode (e.g., "dehumidify for six hours this afternoon").
One sentence: AQI advisory and window guidance (AQI level, main pollutant if moderate or above, open/close windows).

P5 — Forecast & Accuracy (4 sentences max):
Forecast (up to 3 sentences): One opening sentence naming the overall pattern. The `transitions` array in the data flags segments where significant change occurs (is_transition: true) — use the first such entry as your 1 key transition; skip stable stretches. Close with one bottom-line sentence.
Accuracy (1 sentence): Compare yesterday's forecast to actual. If 3 days of history available, note trend (e.g., "2 of 3 days close"). Use grades: spot on / close / off.

---METADATA---
{cfg["meta_intro"]}
{{
  "wardrobe": "{ex['wardrobe']}",
  "wardrobe_tagline": "{ex['wardrobe_tagline']}",
  "rain_gear": true or false,
  "rain_gear_text": "{ex['rain_gear_text']}",
  "commute_am": "{ex['commute_am']}",
  "commute_pm": "{ex['commute_pm']}",
  "commute_tagline": "{ex['commute_tagline']}",
  "meal": "{ex['meal']}",
  "meals_text": "{ex['meals_text']}",
  "meals_tagline": "{ex['meals_tagline']}",
  "outdoor": "{ex['outdoor']}",
  "outdoor_tagline": "{ex['outdoor_tagline']}",
  "garden": "{ex['garden']}",
  "garden_text": "{ex['garden_text']}",
  "garden_tagline": "{ex['garden_tagline']}",
  "climate": "{ex['climate']}",
  "hvac_tagline": "{ex['hvac_tagline']}",
  "air_quality_summary": "{ex['air_quality_summary']}",
  "air_quality_tagline": "{ex['air_quality_tagline']}",
  "alert_text": "{ex['alert_text']}",
  "alert_level": "{ex['alert_level']}",
  "cardiac_alert": true or false,
  "menieres_alert": true or false,
  "forecast_oneliner": "{ex['forecast_oneliner']}",
  "accuracy_grade": "{ex['accuracy_grade']}"
}}
"""


# Keep backward-compatible names for any code that references them directly
V7_SYSTEM_PROMPT = _build_v7_prompt("en")
V7_SYSTEM_PROMPT_EN = V7_SYSTEM_PROMPT
V7_SYSTEM_PROMPT_ZH = _build_v7_prompt("zh-TW")

# ─────────────────────────────────────────────────────────────────────────────
# REGEN INSTRUCTION — appended every 14 days
# ─────────────────────────────────────────────────────────────────────────────

def build_regen_instruction(processed_data: dict) -> str:
    """Build dynamic regen instruction with stale/bench context for smarter LLM replacement."""
    try:
        from data.catalog_manager import (
            load_catalog_stats,
            identify_stale_items,
            get_bench_summary,
        )
        from data.catalog_manager import _MEAL_MOOD_MAP, _LOCATION_MOODS

        stats = load_catalog_stats()
        bench_summary = get_bench_summary()

        # Load current catalogs to identify what will be retired
        meals_catalog = json.load(open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "meals.json"), encoding="utf-8"))
        locations_catalog = json.load(open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "locations.json"), encoding="utf-8"))

        retiring_meals: dict[str, list[str]] = {}
        for regen_key, display_mood in _MEAL_MOOD_MAP.items():
            stale = identify_stale_items(meals_catalog, stats.get("meals", {}), display_mood)
            if stale:
                retiring_meals[regen_key] = [item["name"] for item in stale]

        retiring_locations: dict[str, list[str]] = {}
        for mood in _LOCATION_MOODS:
            stale = identify_stale_items(locations_catalog, stats.get("locations", {}), mood)
            if stale:
                retiring_locations[mood] = [item["name"] for item in stale]

        retiring_section = ""
        if retiring_meals or retiring_locations:
            retiring_section += "\nItems being RETIRED this cycle (generate replacements for these):\n"
            if retiring_meals:
                retiring_section += f"  Meals: {json.dumps(retiring_meals, ensure_ascii=False)}\n"
            if retiring_locations:
                retiring_section += f"  Locations: {json.dumps(retiring_locations, ensure_ascii=False)}\n"

        bench_section = ""
        if bench_summary.get("meals") or bench_summary.get("locations"):
            bench_section += "\nItems currently BENCHED (do NOT regenerate these — they will return later):\n"
            if bench_summary["meals"]:
                bench_section += f"  Meals: {', '.join(bench_summary['meals'])}\n"
            if bench_summary["locations"]:
                bench_section += f"  Locations: {', '.join(bench_summary['locations'])}\n"

        # Calculate target counts based on what's being retired
        meal_targets = {k: len(v) for k, v in retiring_meals.items()} if retiring_meals else {}
        loc_targets = {k: len(v) for k, v in retiring_locations.items()} if retiring_locations else {}
        target_note = ""
        if meal_targets:
            target_note += f"\nTarget replacement counts per mood — Meals: {json.dumps(meal_targets)}"
        if loc_targets:
            target_note += f"\nTarget replacement counts per mood — Locations: {json.dumps(loc_targets)}"

    except Exception:
        retiring_section = ""
        bench_section = ""
        target_note = ""

    return f"""

SPECIAL TASK — Database Refresh (catalogue rotation):
After the ---METADATA--- JSON, add a separator ---REGEN--- on its own line, then output a single JSON object with two keys:

{{
  "meals": {{
    "hot_humid": ["dish1 pinyin", "dish2 pinyin", ...],
    "warm_pleasant": ["dish1 pinyin", ...],
    "cool_damp": ["dish1 pinyin", ...],
    "cold": ["dish1 pinyin", ...]
  }},
  "locations": {{
    "Nice": [{{"name":"...","activity":"...","surface":"...","lat":0.0,"lng":0.0,"notes":"..."}}],
    "Warm": [...],
    "Cloudy & Breezy": [...],
    "Stay In": [...]
  }}
}}
{retiring_section}{bench_section}{target_note}
Meals: Generate replacements for retired items. Pinyin only, no Chinese characters. Mix home-cooked staples, night market classics, and regional specialties. No dish repeated across categories.

Locations: Generate replacements for retired items, all within 50km of 24.9955°N 121.4279°E (Shulin/Banqiao border). Include parks, trails, riverside paths, cultural sites, temples, museums, and indoor venues as appropriate. Each entry needs: name (pinyin), suggested activity, surface type (paved/gravel/dirt/indoor), approximate lat/lng, and brief notes on terrain difficulty, shade availability, seating, and general accessibility.
"""


def _slim_for_llm(processed_data: dict) -> dict:
    """Strip fields the LLM never references to reduce input tokens.

    Removes:
    - aqi_forecast.content/hourly → replaced with peak_aqi summary
    - recent_meals, recent_locations — filtering done upstream
    - meal_mood.all_suggestions/all_meals_detail — LLM uses top_* only
    - location_rec.all_locations — LLM uses top_locations only
    - forecast_7day — LLM uses forecast_segments + transitions
    - outdoor_index.activities — distilled to HINTS top_activity
    processed_data itself is never mutated.
    """
    slim = {**processed_data}

    # ── AQI forecast: keep summary, drop verbose content/hourly ──
    if "aqi_forecast" in slim:
        af: dict[str, Any] = dict(slim["aqi_forecast"])
        af.pop("content", None)
        af.pop("forecast_date", None)
        hourly = af.pop("hourly", [])
        if hourly:
            peak = max(hourly, key=lambda h: h.get("aqi") or 0)
            af["peak_aqi"] = {
                "aqi": peak.get("aqi"),
                "hour": (peak.get("forecast_time") or "")[:13],
            }
        slim["aqi_forecast"] = af

    # ── Drop upstream-filtered lists (LLM never uses these) ──
    slim.pop("recent_meals", None)
    slim.pop("recent_locations", None)
    slim.pop("recent_activities", None)

    # ── Meal mood: keep only top_suggestions + top_meals_detail ──
    if "meal_mood" in slim:
        mm = dict(slim["meal_mood"])
        mm.pop("all_suggestions", None)
        mm.pop("all_meals_detail", None)
        slim["meal_mood"] = mm

    # ── Location rec: keep only top_locations ──
    if "location_rec" in slim:
        lr = dict(slim["location_rec"])
        lr.pop("all_locations", None)
        slim["location_rec"] = lr

    # ── 7-day forecast: frontend-only, LLM uses segments + transitions ──
    slim.pop("forecast_7day", None)

    # ── Outdoor index: drop full activities dict (distilled to HINTS) ──
    if "outdoor_index" in slim:
        oi = dict(slim["outdoor_index"])
        oi.pop("activities", None)
        slim["outdoor_index"] = oi

    return slim


def build_prompt(
    processed_data: dict,
    history: list[dict],
    today_date: str | None = None,
) -> list[dict]:
    """
    Build the message list for Claude/Gemini narration.

    Returns list of message dicts:
      [{"role": "user", "parts": [{"text": "..."}]}]
    """
    today = today_date or datetime.now().strftime("%Y-%m-%d")

    history_text = _format_history(history)
    data_text = json.dumps(_slim_for_llm(processed_data), ensure_ascii=False, indent=2)

    regen_note = build_regen_instruction(processed_data) if processed_data.get("regenerate_meal_lists") else ""

    _acts = processed_data.get("outdoor_index", {}).get("activities", {})
    _recent_acts = set(processed_data.get("recent_activities", []))
    if _acts:
        # Rank activities by score descending, skip recently suggested ones
        _ranked = sorted(_acts.items(), key=lambda kv: kv[1]["score"], reverse=True)
        _fresh = [(k, v) for k, v in _ranked if k not in _recent_acts]
        if _fresh:
            _top_k, _top_v = _fresh[0]
            top_activity = "photography" if ("photography" in [k for k, _ in _fresh[:3]] and _fresh[0][1]["score"] >= 80 and "photography" not in _recent_acts) else _top_k
        else:
            # All activities recently used — fall back to raw top scorer
            top_activity = _ranked[0][0]
    else:
        top_activity = "unknown"
    outdoor_grade = processed_data.get("outdoor_index", {}).get("overall_grade", "unknown")

    climate_ctrl = processed_data.get("climate_control", {})
    climate_mode = climate_ctrl.get("mode", "Off")
    climate_reason = (climate_ctrl.get("dew_reasons") or [""])[0]
    _ac_mode = climate_ctrl.get("ac_mode")
    _dehumidifier = climate_ctrl.get("dehumidifier")
    _windows = climate_ctrl.get("windows")
    climate_hint_parts = [climate_mode]
    if climate_reason:
        climate_hint_parts.append(f"({climate_reason})")
    if _ac_mode:
        climate_hint_parts.append(f"[{_ac_mode} mode]")
    if _dehumidifier and _dehumidifier not in (None, "None"):
        climate_hint_parts.append(f"dehumidifier: {_dehumidifier}")
    if _windows:
        climate_hint_parts.append(f"windows: {_windows}")
    climate_hint = " ".join(climate_hint_parts)

    am_hazards = processed_data.get("commute", {}).get("morning", {}).get("hazards", [])
    pm_hazards = processed_data.get("commute", {}).get("evening", {}).get("hazards", [])
    commute_hints = f"Morning hazards: {', '.join(am_hazards) or 'none'}; Evening hazards: {', '.join(pm_hazards) or 'none'}"

    user_message = f"""Date: {today}

HISTORY:
{history_text}

DATA:
{data_text}
{regen_note}
HINTS:
- Top outdoor activity by score: {top_activity}
- Outdoor grade: {outdoor_grade}
- HVAC mode to recommend: {climate_hint}
- Commute hazards: {commute_hints}
Generate today's broadcast."""

    return [
        {"role": "user", "parts": [{"text": user_message}]},
    ]


def build_system_prompt(lang: str = 'en') -> str:
    """Return the system prompt for the given language code.
    Supported: 'en' (default), 'zh-TW'. Unknown codes fall back to English.
    """
    if lang == 'zh-TW':
        return V7_SYSTEM_PROMPT_ZH
    return V7_SYSTEM_PROMPT_EN


def parse_narration_response(raw_response: str) -> dict:
    """
    Parse the LLM response into narration text, structured metadata,
    and optionally regenerated meal/location databases.

    Returns:
        {
            "full_text": "...all paragraphs joined...",
            "paragraphs": {
                "p1_conditions": "...",
                "p2_garden_commute": "...",
                "p3_outdoor": "..." or absent,
                "p4_meal_climate": "..." or absent,
                "p5_forecast": "...",
                "p6_accuracy": "..."
            },
            "metadata": {...},
            "regen": {...} or None
        }
    """
    result = {
        "full_text": "",
        "paragraphs": {},
        "metadata": {},
        "cards": {},
        "regen": None,
    }

    # ── Split on ---METADATA--- (case-insensitive, whitespace-tolerant) ──
    _METADATA_SEP = re.compile(r'-{3}\s*METADATA\s*-{3}', re.IGNORECASE)
    parts = _METADATA_SEP.split(raw_response, maxsplit=1)
    narration_text = parts[0].strip()
    result["full_text"] = narration_text

    # ── Parse paragraphs ──────────────────────────────────────────────────
    paragraphs = [p.strip() for p in narration_text.split("\n\n") if p.strip()]
    _assign_paragraphs(paragraphs, result)

    # ── Parse metadata + optional regen ──────────────────────────────────
    if len(parts) > 1:
        remainder = parts[1].strip()

        # Split off ---REGEN--- (if present)
        regen_parts = remainder.split("---REGEN---", 1)
        metadata_text = regen_parts[0].strip()
        regen_text = regen_parts[1].strip() if len(regen_parts) > 1 else ""

        # Handle legacy responses that still contain ---CARDS---
        cards_parts = metadata_text.split("---CARDS---", 1)
        metadata_text = cards_parts[0].strip()

        # Strip markdown code fences that LLMs sometimes wrap around JSON
        metadata_text = re.sub(r'^```(?:json)?\s*\n?', '', metadata_text, flags=re.MULTILINE)
        metadata_text = re.sub(r'\n?```\s*$', '', metadata_text, flags=re.MULTILINE)
        metadata_text = metadata_text.strip()

        try:
            result["metadata"] = json.loads(metadata_text)
        except json.JSONDecodeError as exc:
            logger.warning(
                "Failed to parse ---METADATA--- JSON (error: %s). "
                "This usually means the LLM response was truncated at max_tokens. "
                "Raw text (first 300 chars): %s",
                exc, metadata_text[:300],
            )

        # Derive cards from metadata fields
        meta = result["metadata"]
        result["cards"] = _derive_cards_from_metadata(meta if isinstance(meta, dict) else {})

        if regen_text:
            # Strip markdown code fences from regen text too
            regen_text = re.sub(r'^```(?:json)?\s*\n?', '', regen_text, flags=re.MULTILINE)
            regen_text = re.sub(r'\n?```\s*$', '', regen_text, flags=re.MULTILINE)
            regen_text = regen_text.strip()
            try:
                result["regen"] = json.loads(regen_text)
            except json.JSONDecodeError:
                logger.warning("Failed to parse ---REGEN--- JSON")

    return result


def _derive_cards_from_metadata(meta: dict | None) -> dict:
    """Build the cards dict from expanded METADATA fields.

    This replaces the former ---CARDS--- LLM output block, deriving
    card text and taglines from metadata instead.
    """
    if not meta:
        return {}

    return {
        "wardrobe": meta.get("wardrobe", ""),
        "wardrobe_tagline": meta.get("wardrobe_tagline", ""),
        "rain_gear": meta.get("rain_gear_text", ""),
        "commute": f"{meta.get('commute_am', '')} {meta.get('commute_pm', '')}".strip(),
        "commute_tagline": meta.get("commute_tagline", ""),
        "meals": meta.get("meals_text", ""),
        "meals_tagline": meta.get("meals_tagline", ""),
        "hvac": meta.get("climate", ""),
        "hvac_tagline": meta.get("hvac_tagline", ""),
        "garden": meta.get("garden_text", ""),
        "garden_tagline": meta.get("garden_tagline", ""),
        "outdoor": meta.get("outdoor", ""),
        "outdoor_tagline": meta.get("outdoor_tagline", ""),
        "air_quality": meta.get("air_quality_summary", ""),
        "air_quality_tagline": meta.get("air_quality_tagline", ""),
        "alert": {
            "text": meta.get("alert_text", ""),
            "level": meta.get("alert_level", "INFO"),
        },
    }


def _assign_paragraphs(paragraphs: list[str], result: dict) -> None:
    """
    Map parsed paragraphs to P1–P5 keys. All 5 are now always present.
    """
    n = len(paragraphs)
    keys = ["p1_conditions", "p2_garden_commute", "p3_outdoor_meal", "p4_hvac_air", "p5_forecast_accuracy"]

    for i, key in enumerate(keys):
        if i < n:
            result["paragraphs"][key] = paragraphs[i]
        else:
            logger.warning("Missing paragraph %s in LLM response", key)


def _format_history(history: list[dict]) -> str:
    """Compact history — only what the LLM needs for continuity and accuracy."""
    if not history:
        return "(First broadcast — no history.)"

    lines = []
    for day in history:
        date = day.get("generated_at", "?")[:10]
        lines.append(f"[{date}]")

        # Prior forecast for P5 accuracy comparison
        # Handle v2 schema (langs dict) and v1 (flat paragraphs)
        if day.get("schema_version") == 2:
            _langs = day.get("langs", {})
            _ld = _langs.get("zh-TW") or next(iter(_langs.values()), {})
            paras = _ld.get("paragraphs", {})
        else:
            paras = day.get("paragraphs", {})
        forecast_key = (
            "p5_forecast_accuracy" if "p5_forecast_accuracy" in paras
            else "p5_forecast" if "p5_forecast" in paras
            else "p6_forecast"
        )
        forecast = paras.get(forecast_key, "")
        if forecast:
            if len(forecast) > 200:
                forecast = forecast[:200] + "..."
            lines.append(f"Forecast: {forecast}")

        # Actual conditions for accuracy
        proc = day.get("processed_data", {})
        current = proc.get("current", {})
        if current:
            lines.append(
                f"Actual: AT={current.get('AT')}°C RH={current.get('RH')}% "
                f"Wind={current.get('beaufort_desc')} AQI={current.get('aqi')}"
            )

        lines.append("")

    return "\n".join(lines)