"""
prompt_builder.py — v7
Builds the Claude/Gemini prompt from pre-processed weather data.

Paragraph structure (v7):
  P1  Conditions & Alerts (always) — current weather, wardrobe, heads-up, cardiac, Ménière's (no AQI)
  P2  Garden & Commute (always) — gardening tip + both commute legs
  P3  Outdoor & Meal (always) — outdoor activity (no Parkinson's phrasing) + one dish
  P4  HVAC & Air Quality (always) — climate control + AQI/window guidance
  P5  Forecast & Accuracy (always) — 24h forecast + accuracy review (last 3 days)

Changes from v6:
  - 6 paragraphs → 5
  - AQI status removed from P1; moved to new P4
  - P3 (outdoor) + P4 (meal) merged into new P3 (outdoor & meal)
  - Parkinson's-specific phrasing removed from P3/outdoor card
  - Old P5 (forecast) + P6 (accuracy) merged into new P5
  - Accuracy extended to last 3 days (was yesterday only), capped at 1 sentence
  - Total word count reduced: 320–350 → 270–300 words (EN)
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT — v7
# ─────────────────────────────────────────────────────────────────────────────

V7_SYSTEM_PROMPT = """\
You are a warm, concise broadcaster for a family near Shulin/Banqiao, Taiwan. Use ONLY the provided JSON weather data; never invent numbers. Output a plain-text script for a TTS engine.

RULES:
- English only. Use pinyin for Chinese terms (e.g., "niu rou mian"). Zero Chinese characters.
- Plain text only. No markdown, headers, bullets, or code blocks.
- Total length: 250–280 words. Tight and direct. Every sentence must carry information.

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
Recommend an outdoor activity for Dad (or indoor if weather is poor). Choose ONE location from top_locations that best fits today's weather — use its notes (shade, surface, terrain) to explain why it suits the conditions; name the time (e.g., "mid-morning") and the location (pinyin).
Choose ONE dish from top_meals_detail that best matches today's weather mood — reference its description or tags to explain how it complements the weather (e.g., "cooling jelly clears the heat" or "hearty noodle soup warms you up"). Write the dish name in pinyin.

P4 — HVAC & Air Quality (2 sentences max):
One sentence: plain advice on AC/heater/dehumidifier mode (e.g., "dehumidify for six hours this afternoon").
One sentence: AQI advisory and window guidance (AQI level, main pollutant if moderate or above, open/close windows).

P5 — Forecast & Accuracy (4 sentences max):
Forecast (up to 3 sentences): One opening sentence naming the overall pattern. The `transitions` array in the data flags segments where significant change occurs (is_transition: true) — use the first such entry as your 1 key transition; skip stable stretches. Close with one bottom-line sentence.
Accuracy (1 sentence): Compare yesterday's forecast to actual. If 3 days of history available, note trend (e.g., "2 of 3 days close"). Use grades: spot on / close / off.

---METADATA---
Output exact separator ---METADATA--- then a single JSON:
{
  "wardrobe": "1-sentence wardrobe advice based on apparent temperature",
  "wardrobe_tagline": "≤8 words imperative covering wardrobe + rain gear. e.g. 'Light jacket; bring an umbrella.'",
  "rain_gear": true or false,
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
  "cardiac_alert": true or false,
  "menieres_alert": true or false,
  "forecast_oneliner": "the bottom-line takeaway from P5",
  "accuracy_grade": "spot on / close / off / first broadcast"
}
"""

V7_SYSTEM_PROMPT_EN = V7_SYSTEM_PROMPT  # alias — English prompt is unchanged

V7_SYSTEM_PROMPT_ZH = """\
你是一個親切、簡潔的家庭廣播員，服務台灣樹林/板橋交界處的一家人。只使用提供的 JSON 天氣數據，絕對不要自行填補數字。輸出為 TTS 引擎使用的純文字廣播稿。

規則：
- 使用繁體中文。地名與菜餚直接用中文（如「牛肉麵」）。
- 純文字格式。不使用標題、粗體、斜體、項目符號或程式碼區塊。
- 總長度：340–370 字。每一句話都必須帶有資訊。
- ---METADATA--- 之後的 JSON 物件鍵名與英文值須保持英文。

敘事風格：
- 重點優先：每個段落開頭都必須是最重要的資訊。
- 不要預熱：絕不以氣氛鋪墊句開段。每段第一個字應是事實或行動。
- 感受優先：說「氣候濕熱」而非「濕度 72%」。使用 beaufort_desc 和 precip_text。每段最多一個精確數字。
- 過渡描述：將變化描述為具體感受（「雲層會變厚」）而非數據比較。
- 生活化時間：說「出門前」或「午餐前後」而非代碼化的時間段。
- 昨日比較：視對話歷史加入一句與昨天的比較（如「比昨天暖和」）。
- 硬性上限：每個段落不超過四句話。

段落結構：

P1 — 當前狀況與警示（最多 4 句）：
以 heads_ups[]（或「今天一切順利」）開場。描述體感溫度、濕度、風力、雲量、地面狀況與能見度。不要在此提及 AQI——那屬於 P4。
自然穿插心臟（cardiac_alert）或梅尼爾氏症（menieres_alert）警示，並提供穿衣與雨具建議。

P2 — 花園與通勤（最多 4 句）：
提供昨日銜接的小撇步（或當季建議）。摘要通勤路段（三峽/樹林）的體感、降雨與路況風險。早晨與傍晚合併為一段。

P3 — 戶外活動與餐食（最多 4 句）：
為爸爸推薦戶外活動（天氣不佳則建議室內）。從 top_locations 中挑選一處最符合今日天氣的地點——利用其 notes（遮蔭、地面、地形）說明為何適合今日天氣；指定出門時段並以拼音標註地點名稱。
從 top_meals_detail 中挑選一道最符合今日天氣心情的菜——引用其 description 或 tags 說明這道菜如何搭配今天的天氣（例如「清涼愛玉消暑氣」或「熱騰騰的牛肉麵暖身」）。以中文寫出菜名。

P4 — 空調與空氣品質（最多 2 句）：
一句話：平實建議空調模式（如「下午開六小時除濕」）。
一句話：AQI 建議與開關窗指引（AQI 等級、若中等以上說明主要污染物）。

P5 — 預報與準確度（最多 4 句）：
預報（最多 3 句）：第一句說明整體趨勢。只描述 1 個關鍵轉折，跳過穩定時段。以一句底線總結作結。
準確度（1 句）：對比昨天預報與實際天氣。若有 3 天歷史則說明趨勢（如「三天中兩天接近」）。使用：準確／接近／偏離。

---METADATA---
輸出 ---METADATA--- 後接 JSON（鍵名保持英文，值用繁體中文）：
{
  "wardrobe": "1句話穿著建議",
  "wardrobe_tagline": "≤8字命令式，涵蓋穿著與雨具。例如：「輕薄外套，記得帶傘。」",
  "rain_gear": true 或 false,
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
  "cardiac_alert": true 或 false,
  "menieres_alert": true 或 false,
  "forecast_oneliner": "字串",
  "accuracy_grade": "字串"
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# REGEN INSTRUCTION — appended every 14 days
# ─────────────────────────────────────────────────────────────────────────────

REGEN_INSTRUCTION = """

SPECIAL TASK — Database Refresh (runs every 14 days):
After the ---METADATA--- JSON, add a separator ---REGEN--- on its own line, then output a single JSON object with two keys:

{
  "meals": {
    "hot_humid": ["dish1 pinyin", "dish2 pinyin", ...],
    "warm_pleasant": ["dish1 pinyin", ...],
    "cool_damp": ["dish1 pinyin", ...],
    "cold": ["dish1 pinyin", ...]
  },
  "locations": {
    "Nice": [{"name":"...","activity":"...","surface":"...","lat":0.0,"lng":0.0,"notes":"..."}],
    "Warm": [...],
    "Cloudy & Breezy": [...],
    "Stay In": [...]
  }
}

Meals: 10–12 common Taiwanese dishes per category. Pinyin only, no Chinese characters. Mix home-cooked staples, night market classics, and regional specialties. No dish repeated across categories.

Locations: 8–10 per category, all within 50km of 24.9955°N 121.4279°E (Shulin/Banqiao border). Include parks, trails, riverside paths, cultural sites, temples, museums, and indoor venues as appropriate. Each entry needs: name (pinyin), suggested activity, surface type (paved/gravel/dirt/indoor), approximate lat/lng, and brief notes on terrain difficulty, shade availability, seating, and general accessibility.
"""


def _slim_for_llm(processed_data: dict) -> dict:
    """Strip verbose MOENV fields to reduce LLM input tokens.

    Removes aqi_forecast.content (~200-300 tok) and aqi_forecast.hourly
    (~300-450 tok), replacing the latter with a single peak_aqi summary.
    processed_data itself is never mutated.
    """
    slim = {**processed_data}
    if "aqi_forecast" in slim:
        af: dict[str, Any] = dict(slim["aqi_forecast"])
        af.pop("content", None)
        af.pop("forecast_date", None)
        hourly = af.pop("hourly", [])
        if hourly:
            peak = max(hourly, key=lambda h: h.get("aqi") or 0)
            af["peak_aqi"] = {
                "aqi": peak.get("aqi"),
                "hour": (peak.get("forecast_time") or "")[:13],  # "2026-03-07T14"
            }
        slim["aqi_forecast"] = af
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

    regen_note = REGEN_INSTRUCTION if processed_data.get("regenerate_meal_lists") else ""

    _acts = processed_data.get("outdoor_index", {}).get("activities", {})
    if _acts:
        _max_score = max(_acts[k]["score"] for k in _acts)
        _tied = [k for k, v in _acts.items() if v["score"] == _max_score]
        top_activity = "photography" if ("photography" in _tied and _max_score >= 80) else _tied[0]
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
                "Failed to parse ---METADATA--- JSON (error: %s). Raw text (first 300 chars): %s",
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
        paras = day.get("paragraphs", {})
        forecast_key = (
            "p5_forecast_accuracy" if "p5_forecast_accuracy" in paras
            else "p5_forecast" if "p5_forecast" in paras
            else "p6_forecast"
        )
        forecast = paras.get(forecast_key, "")
        if forecast:
            if len(forecast) > 400:
                forecast = forecast[:400] + "..."
            lines.append(f"Forecast: {forecast}")

        # Actual conditions for accuracy
        proc = day.get("processed_data", {})
        current = proc.get("current", {})
        if current:
            lines.append(
                f"Actual: AT={current.get('AT')}°C RH={current.get('RH')}% "
                f"Wind={current.get('beaufort_desc')} AQI={current.get('aqi')}"
            )

        # Continuity metadata
        meta = day.get("metadata", {})
        parts = []
        if meta.get("meal"):
            parts.append(f"meal={meta['meal']}")
        elif meta.get("meals_suggested"):
            # Backward compat with v5 history
            parts.append(f"meals={','.join(meta['meals_suggested'])}")
        if meta.get("garden"):
            parts.append(f"garden={meta['garden']}")
        elif meta.get("gardening_tip_topic"):
            parts.append(f"garden={meta['gardening_tip_topic']}")
        if meta.get("outdoor"):
            parts.append(f"outdoor={meta['outdoor']}")
        elif meta.get("location_suggested"):
            parts.append(f"outdoor={meta['location_suggested']}")
        if parts:
            lines.append(f"Meta: {'; '.join(parts)}")

        lines.append("")

    return "\n".join(lines)