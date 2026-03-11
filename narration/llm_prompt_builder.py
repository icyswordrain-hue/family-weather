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
Recommend an outdoor activity for Dad (or indoor if weather is poor). Name a time (e.g., "mid-morning") and ONE location from top_locations (pinyin). Note surface comfort and any weather-related caution. Add ONE pinyin dish from top_suggestions matching the weather mood.

P4 — HVAC & Air Quality (2 sentences max):
One sentence: plain advice on AC/heater/dehumidifier mode (e.g., "dehumidify for six hours this afternoon").
One sentence: AQI advisory and window guidance (AQI level, main pollutant if moderate or above, open/close windows).

P5 — Forecast & Accuracy (4 sentences max):
Forecast (up to 3 sentences): One opening sentence naming the overall pattern. The `transitions` array in the data flags segments where significant change occurs (is_transition: true) — use the first such entry as your 1 key transition; skip stable stretches. Close with one bottom-line sentence.
Accuracy (1 sentence): Compare yesterday's forecast to actual. If 3 days of history available, note trend (e.g., "2 of 3 days close"). Use grades: spot on / close / off.

---METADATA---
Output exact separator ---METADATA--- then a single JSON:
{
  "wardrobe": "1-sentence",
  "rain_gear": true or false,
  "commute_am": "1-sentence",
  "commute_pm": "1-sentence",
  "meal": "single dish name in pinyin, or null if P4 meal section was skipped",
  "outdoor": "1-sentence Dad outing summary, or null if P3 was skipped",
  "garden": "3-5 word gardening tip topic for history tracking",
  "climate": "1-sentence climate control summary, or null if skipped",
  "cardiac_alert": true or false,
  "menieres_alert": true or false,
  "forecast_oneliner": "the bottom-line takeaway from P5",
  "accuracy_grade": "spot on / close / off / first broadcast"
}

---CARDS---
Output exact separator ---CARDS--- then a single JSON:
{
  "wardrobe": "Exactly 1 sentence. What to wear based on apparent temperature only. Do not mention rain or rain gear — that is covered by the rain_gear card.",
  "rain_gear": "Exactly 1 sentence. Whether to carry umbrella, raincoat, or boots.",
  "commute": "Exactly 2 sentences. Morning and evening commute road conditions. Must incorporate the exact commute hazards provided in the HINTS.",
  "meals": "Exactly 1 sentence. Meal suggestion matching the weather mood.",
  "hvac": "Exactly 1 sentence. Air conditioning, heating, or ventilation recommendation. Must recommend the exact HVAC mode provided in the HINTS.",
  "garden": "Exactly 2 sentences. Garden tasks and soil or plant care advice.",
  "outdoor": "Exactly 2 sentences. You MUST use the exact top outdoor activity provided in the HINTS section. Best time window and any weather caution. Must reflect the provided outdoor grade from the HINTS.",
  "air_quality": "Exactly 1 sentence. Outdoor air quality advisory for tomorrow. If Good (AQI ≤50): reassure, e.g. 'Tomorrow's air looks clean — no precautions needed.' If Moderate (51–100): name the main pollutant and note that sensitive groups should take care. If Unhealthy or above: recommend limiting outdoor exposure and keeping windows closed.",
  "alert": {
    "text": "1–2 sentences. Summarise today's health risks (cardiac, Ménière's) and commute hazards from P1. Do NOT include air quality — that has its own dedicated card. If nothing significant to flag, leave this as an empty string.",
    "level": "INFO or WARNING or CRITICAL"
  }
}

All card values must be written in the same language as the narration paragraphs above.
Level guide: CRITICAL = cardiac or Ménière's health risk mentioned in P1; WARNING = significant commute or safety heads-up; INFO = mild health or commute note. Leave text empty for clear uneventful days.
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
為爸爸推薦戶外活動（天氣不佳則建議室內）。指定時間段，從 top_locations 挑選一處地點（中文名），描述地面舒適度與天氣注意事項。
從 top_suggestions 挑選一道符合天氣心情的菜名。

P4 — 空調與空氣品質（最多 2 句）：
一句話：平實建議空調模式（如「下午開六小時除濕」）。
一句話：AQI 建議與開關窗指引（AQI 等級、若中等以上說明主要污染物）。

P5 — 預報與準確度（最多 4 句）：
預報（最多 3 句）：第一句說明整體趨勢。只描述 1 個關鍵轉折，跳過穩定時段。以一句底線總結作結。
準確度（1 句）：對比昨天預報與實際天氣。若有 3 天歷史則說明趨勢（如「三天中兩天接近」）。使用：準確／接近／偏離。

---METADATA---
輸出 ---METADATA--- 後接 JSON：
{
  "wardrobe": "1句話",
  "rain_gear": true 或 false,
  "commute_am": "1句話",
  "commute_pm": "1句話",
  "meal": "單一菜名拼音，若跳過 P4 則為 null",
  "outdoor": "1句話爸爸外出摘要，若跳過 P3 則為 null",
  "garden": "3-5 字的花園主題用以歷史追蹤",
  "climate": "1句話空調摘要，若跳過則為 null",
  "cardiac_alert": true 或 false,
  "menieres_alert": true 或 false,
  "forecast_oneliner": "字串",
  "accuracy_grade": "字串"
}

---CARDS---
輸出 ---CARDS--- 後接 JSON：
{
  "wardrobe": "精確 1 句話。根據體感溫度說明穿著建議。不要提及雨具或降雨，那屬於 rain_gear 卡片。",
  "rain_gear": "精確 1 句話。是否需要攜帶雨傘、雨衣或雨靴。",
  "commute": "精確 2 句話。早晨和傍晚通勤的道路狀況。必須整合 HINTS 中提供的通勤危險提示。",
  "meals": "精確 1 句話。符合天氣心情的餐食建議。",
  "hvac": "精確 1 句話。空調、暖氣或通風建議。必須推薦 HINTS 中提供的空調模式。",
  "garden": "精確 2 句話。花園工作和土壤或植物護理建議。",
  "outdoor": "精確 2 句話。必須使用 HINTS 中提供的精確最佳戶外活動。最佳時間窗口及天氣注意事項。必須反映 HINTS 中提供的戶外等級。",
  "air_quality": "精確 1 句話。明日戶外空氣品質建議。若良好（AQI ≤50）：令人放心，如「明天空氣清新，無需特別防護。」若普通（51–100）：指出主要污染物，提醒敏感族群留意。若不健康或以上：建議減少戶外活動並關閉窗戶。",
  "alert": {
    "text": "1–2 句話。摘要 P1 中的健康風險（心臟、梅尼爾氏症）及通勤危險。不要包含空氣品質資訊——那已有專屬卡片。若無特別需要提醒的事項，請留空字串。",
    "level": "INFO 或 WARNING 或 CRITICAL"
  }
}

所有卡片值必須使用與上方廣播段落相同的語言（繁體中文）撰寫。
等級說明：CRITICAL = P1 提及的心臟或梅尼爾氏症健康風險；WARNING = 重要通勤或安全提示；INFO = 輕微健康或通勤注意事項。平靜無事的一天請留空字串。
"""

# ─────────────────────────────────────────────────────────────────────────────
# REGEN INSTRUCTION — appended every 14 days
# ─────────────────────────────────────────────────────────────────────────────

REGEN_INSTRUCTION = """

SPECIAL TASK — Database Refresh (runs every 14 days):
After the ---CARDS--- JSON, add a separator ---REGEN--- on its own line, then output a single JSON object with two keys:

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

    climate_mode = processed_data.get("climate_control", {}).get("mode", "Off")

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
- HVAC mode to recommend: {climate_mode}
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

    # ── Split on ---METADATA--- ───────────────────────────────────────────
    parts = raw_response.split("---METADATA---", 1)
    narration_text = parts[0].strip()
    result["full_text"] = narration_text

    # ── Parse paragraphs ──────────────────────────────────────────────────
    paragraphs = [p.strip() for p in narration_text.split("\n\n") if p.strip()]
    _assign_paragraphs(paragraphs, result)

    # ── Parse metadata + optional cards + optional regen ─────────────────
    if len(parts) > 1:
        remainder = parts[1].strip()

        # Split off ---CARDS--- first (if present)
        cards_parts = remainder.split("---CARDS---", 1)
        metadata_text = cards_parts[0].strip()
        cards_and_regen = cards_parts[1].strip() if len(cards_parts) > 1 else ""

        # Then split cards from ---REGEN---
        regen_parts = cards_and_regen.split("---REGEN---", 1)
        cards_text = regen_parts[0].strip()
        regen_text = regen_parts[1].strip() if len(regen_parts) > 1 else ""

        try:
            result["metadata"] = json.loads(metadata_text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse ---METADATA--- JSON: %s", metadata_text[:200])  # type: ignore

        if cards_text:
            try:
                raw = cards_text.strip("` \n")
                if raw.startswith("json"):
                    raw = raw[4:].strip()  # type: ignore
                result["cards"] = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Failed to parse ---CARDS--- JSON: %s", cards_text[:200])  # type: ignore

        if regen_text:
            try:
                result["regen"] = json.loads(regen_text)
            except json.JSONDecodeError:
                logger.warning("Failed to parse ---REGEN--- JSON")

    return result


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