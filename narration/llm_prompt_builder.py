"""
prompt_builder.py — v6
Builds the Claude/Gemini prompt from pre-processed weather data.

Paragraph structure (v6):
  P1  Conditions & Alerts (always) — current weather, wardrobe, heads-up, cardiac, Ménière's
  P2  Garden & Commute (always) — gardening tip + both commute legs
  P3  Outdoor with Dad (always) — now always included
  P4  Meal & Climate (always) — now always included
  P5  24-Hour Forecast (always)
  P6  Accuracy (always)

Changes from v5:
  - 7 paragraphs → 6 (commute merged with garden, cardiac/Ménière's moved to P1)
  - Ménière's disease barometric/humidity alerts added to P1
  - P3/P4 now always included (no longer conditional)
  - P4 merges meals + climate control (each independently skippable)
  - Single meal suggestion (not separate lunch/dinner)
  - Metadata adds rain_gear boolean, single meal field
  - Regen cycle: every 14 days (was ~7), radius 50km (was 30km)
  - System prompt target: ~800 words
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT — v6 (~800 words)
# ─────────────────────────────────────────────────────────────────────────────

V6_SYSTEM_PROMPT = """\
You are a warm, concise broadcaster for a family near Shulin/Banqiao, Taiwan. Use ONLY the provided JSON weather data; never invent numbers. Output a plain-text script for a TTS engine.

RULES:
- English only. Use pinyin for Chinese terms (e.g., "niu rou mian"). Zero Chinese characters.
- Plain text only. No markdown, headers, bullets, or code blocks.
- Total length: 320–350 words. Tight and direct. Every sentence must carry information.

STYLE:
- Lead with the point: Every paragraph opens with the most important takeaway.
- No wind-ups: Never open a paragraph with atmosphere-setting sentences. The first word of each paragraph should be a fact or action.
- Sensation first: Say "sticky and warm" rather than "humidity 72%." Use the provided beaufort_desc and precip_text. One precise number per paragraph maximum.
- Transition narration: Describe shifts as physical movement ("clouds will thicken through the afternoon") rather than data diffs.
- Life-anchored time: Use "before you leave at seven" or "around lunch" instead of "06:00–12:00."
- Yesterday comparison: Include one brief comparison (e.g., "warmer than yesterday") using history. Skip if no history.
- Hard limit: Every paragraph must be 4 sentences or fewer.

STRUCTURE:

P1 — Current Conditions & Alerts:
Open with heads_ups[] alerts (or "Smooth sailing" if empty). State apparent temperature, humidity sensation, wind (e.g., "gentle breeze out of the north"), clouds, ground wetness, visibility, and AQI status.
Health: Weave in Cardiac (if cardiac_alert) and Ménière's (if menieres_alert) naturally. Focus on physical sensations and practical advice (e.g., "keep Dad's room warm" or "take it slow today").
Close with wardrobe. State explicitly if rain gear (umbrella or raincoat) is needed.

P2 — Garden & Commute:
Start with a gardening tip based on history (or seasonal if no history). Pivot to the commute (Sanxia/Shulin). Cover AT, precip_text, wind, and hazards. Combine morning and evening legs into one summary.

P3 — Outdoor with Dad:
Recommendation for Dad's exercise. If weather is poor, recommend indoor activity. Name a time (e.g., "mid-morning") and ONE location from top_locations (pinyin). Describe the activity and surface/safety notes (flat paths, seating).

P4 — Meals & Climate Control:
Meals: Suggest ONE pinyin dish from top_suggestions matching the weather mood (e.g., "steamy niu rou mian for a chilly night").
Climate: Plain advice on AC/heater/dehumidifier mode ("dehumidify for six hours this afternoon"). Include window guidance if AQI is relevant.

P5 — 24-Hour Forecast:
One opening sentence naming the overall pattern. Cover only the 1–2 key transitions — skip stable stretches entirely. Close with one bottom-line sentence. Maximum 5 sentences total.

P6 — Forecast Accuracy:
One sentence: verdict (spot on / close / off) plus the single biggest difference or confirmation. Maximum 2 sentences.

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
  "commute": "Exactly 2 sentences. Morning and evening commute road conditions.",
  "meals": "Exactly 1 sentence. Meal suggestion matching the weather mood.",
  "hvac": "Exactly 1 sentence. Air conditioning, heating, or ventilation recommendation.",
  "garden": "Exactly 2 sentences. Garden tasks and soil or plant care advice.",
  "outdoor": "Exactly 2 sentences. Outdoor activity for Dad — Parkinson's safety considerations and best time window.",
  "air_quality": "Exactly 1 sentence. Outdoor air quality advisory for tomorrow. If Good (AQI ≤50): reassure, e.g. 'Tomorrow's air looks clean — no precautions needed.' If Moderate (51–100): name the main pollutant and note that sensitive groups should take care. If Unhealthy or above: recommend limiting outdoor exposure and keeping windows closed.",
  "alert": {
    "text": "1–2 sentences. Summarise today's health risks (cardiac, Ménière's) and commute hazards from P1. Do NOT include air quality — that has its own dedicated card. If nothing significant to flag, leave this as an empty string.",
    "level": "INFO or WARNING or CRITICAL"
  }
}

All card values must be written in the same language as the narration paragraphs above.
Level guide: CRITICAL = cardiac or Ménière's health risk mentioned in P1; WARNING = significant commute or safety heads-up; INFO = mild health or commute note. Leave text empty for clear uneventful days.
"""

V6_SYSTEM_PROMPT_EN = V6_SYSTEM_PROMPT  # alias — English prompt is unchanged

V6_SYSTEM_PROMPT_ZH = """\
你是一個親切、簡潔的家庭廣播員，服務台灣樹林/板橋交界處的一家人。只使用提供的 JSON 天氣數據，絕對不要自行填補數字。輸出為 TTS 引擎使用的純文字廣播稿。

規則：
- 使用繁體中文。地名與菜餚直接用中文（如「牛肉麵」）。
- 純文字格式。不使用標題、粗體、斜體、項目符號或程式碼區塊。
- 總長度：420–460 字。每一句話都必須帶有資訊。
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

P1 — 當前狀況與警示：
以 heads_ups[]（或「今天一切順利」）開場。描述體感溫度、濕度、風力、雲量、地面狀況、能見度與 AQI 狀態。自然穿插心臟（cardiac_alert）或梅尼爾氏症（menieres_alert）警示，並提供穿衣與雨具建議。

P2 — 花園與通勤：
提供昨日銜接的小撇步（或當季建議）。摘要通勤路段（三峽/樹林）的體感、降雨與路況風險。

P3 — 爸爸的戶外活動：
運動建議。若天氣不佳則建議室內活動。指定時間段，從 top_locations 挑選一處地點（中文名），描述活動內容、地面與安全性注意事項。

P4 — 餐食與空調建議：
餐食：根據天氣心情建議 top_suggestions 中的一道菜名。
空調：平實建議模式、設定與時間（如「下午開六小時除濕」）。加入 AQI 相關的開關窗建議。

P5 — 24 小時預報：
第一句說明整體趨勢。只描述 1–2 個關鍵轉折，跳過穩定時段。以一句底線總結作結。最多五句話。

P6 — 預報準確度：
一句話：結論（準確／接近／偏離）加上最重要的一項差異或吻合點。最多兩句話。

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
  "commute": "精確 2 句話。早晨和傍晚通勤的道路狀況。",
  "meals": "精確 1 句話。符合天氣心情的餐食建議。",
  "hvac": "精確 1 句話。空調、暖氣或通風建議。",
  "garden": "精確 2 句話。花園工作和土壤或植物護理建議。",
  "outdoor": "精確 2 句話。爸爸的戶外活動建議——帕金森氏症安全考量及最佳時間窗口。",
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
    "Nice": [{"name":"...","activity":"...","surface":"...","parkinsons":"good|ok|avoid","lat":0.0,"lng":0.0,"notes":"..."}],
    "Warm": [...],
    "Cloudy & Breezy": [...],
    "Stay In": [...]
  }
}

Meals: 10–12 common Taiwanese dishes per category. Pinyin only, no Chinese characters. Mix home-cooked staples, night market classics, and regional specialties. No dish repeated across categories.

Locations: 8–10 per category, all within 50km of 24.9955°N 121.4279°E (Shulin/Banqiao border). Include parks, trails, riverside paths, cultural sites, temples, museums, and indoor venues as appropriate. Each entry needs: name (pinyin), suggested activity, surface type (paved/gravel/dirt/indoor), parkinsons suitability ("good" = flat and accessible, "ok" = manageable with care, "avoid" = uneven or steep), approximate lat/lng, and brief notes on accessibility, shade, seating, and Parkinson's-relevant safety considerations.
"""


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
    data_text = json.dumps(processed_data, ensure_ascii=False, indent=2)

    regen_note = REGEN_INSTRUCTION if processed_data.get("regenerate_meal_lists") else ""

    user_message = f"""Date: {today}

HISTORY:
{history_text}

DATA:
{data_text}
{regen_note}
Generate today's broadcast."""

    return [
        {"role": "user", "parts": [{"text": user_message}]},
    ]


def build_system_prompt(lang: str = 'en') -> str:
    """Return the system prompt for the given language code.
    Supported: 'en' (default), 'zh-TW'. Unknown codes fall back to English.
    """
    if lang == 'zh-TW':
        return V6_SYSTEM_PROMPT_ZH
    return V6_SYSTEM_PROMPT_EN


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
            logger.warning("Failed to parse ---METADATA--- JSON: %s", metadata_text[:200])

        if cards_text:
            try:
                raw = cards_text.strip("` \n")
                if raw.startswith("json"):
                    raw = raw[4:].strip()
                result["cards"] = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Failed to parse ---CARDS--- JSON: %s", cards_text[:200])

        if regen_text:
            try:
                result["regen"] = json.loads(regen_text)
            except json.JSONDecodeError:
                logger.warning("Failed to parse ---REGEN--- JSON")

    return result


def _assign_paragraphs(paragraphs: list[str], result: dict) -> None:
    """
    Map parsed paragraphs to P1–P6 keys. All 6 are now always present.
    """
    n = len(paragraphs)
    keys = ["p1_conditions", "p2_garden_commute", "p3_outdoor", "p4_meal_climate", "p5_forecast", "p6_accuracy"]

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

        # Yesterday's forecast for P6 accuracy comparison
        paras = day.get("paragraphs", {})
        forecast_key = "p5_forecast" if "p5_forecast" in paras else "p6_forecast"
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