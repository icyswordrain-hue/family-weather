"""
narration/llm_summarizer.py — Uses Claude Haiku to summarize narration paragraphs into 
concise lifestyle card snippets with specific sentence constraints.
"""

import logging
import json
from narration.claude_client import generate_narration
from config import CLAUDE_FALLBACK_MODEL

logger = logging.getLogger(__name__)

def summarize_for_lifestyle(paragraphs: dict[str, str], lang: str = 'en') -> dict[str, str]:
    """
    Summarize narration paragraphs into card-sized snippets.
    
    Constraints:
    - Wardrobe, Rain Gear, Commute, Meals, HVAC: Exactly 2 sentences.
    - Garden Health, Outdoor Activity: Exactly 4 sentences.
    """
    if not paragraphs:
        return {}

    # Combine paragraphs into a single context for Haiku
    context = "\n\n".join([f"[{k}]: {v}" for k, v in paragraphs.items() if v])
    
    if lang == 'zh-TW':
        prompt = f"""你是一個助理，將天氣廣播稿濃縮成簡短有力的儀表板卡片說明。
請用繁體中文輸出，語氣口語自然。回傳一個 JSON 物件，各鍵名保持英文（後端解析用），值為繁體中文字串。

上下文內容：
{context}

規則：
1. 只使用上下文中的資訊。
2. 回傳有效的 JSON 物件。
3. 句子數量限制必須嚴格遵守：
   - "wardrobe": 正好 2 句。
   - "rain_gear": 正好 2 句。（若提及降雨，重點放在雨傘/雨衣/雨鞋）。
   - "commute": 正好 2 句。
   - "meals": 正好 2 句。
   - "hvac": 正好 2 句。
   - "garden": 正好 4 句。
   - "outdoor": 正好 4 句。（重點放在爸爸的帕金森氏症安全和建議活動）。

輸出格式 (鍵名保持英文，值為繁體中文)：
{{
  "wardrobe": "...",
  "rain_gear": "...",
  "commute": "...",
  "meals": "...",
  "hvac": "...",
  "garden": "...",
  "outdoor": "..."
}}
"""
    else:
        prompt = f"""You are a helpful assistant that summarizes weather narration into short, punchy dashboard card snippets. 
User needs a JSON object with specific sentence counts for each card.

CONTEXT:
{context}

RULES:
1. Use ONLY the information in the CONTEXT.
2. Return a valid JSON object.
3. Sentence counts are STRICT:
   - "wardrobe": Exactly 2 sentences.
   - "rain_gear": Exactly 2 sentences. (Focus on umbrella/raincoat/boots if rain is mentioned).
   - "commute": Exactly 2 sentences.
   - "meals": Exactly 2 sentences.
   - "hvac": Exactly 2 sentences.
   - "garden": Exactly 4 sentences.
   - "outdoor": Exactly 4 sentences. (Focus on Dad's Parkinson's safety and suggested activities).

OUTPUT FORMAT:
{{
  "wardrobe": "...",
  "rain_gear": "...",
  "commute": "...",
  "meals": "...",
  "hvac": "...",
  "garden": "...",
  "outdoor": "..."
}}
"""

    messages = [
        {"role": "user", "parts": [{"text": prompt}]}
    ]

    try:
        # Use Haiku for speed and cost
        raw_output = generate_narration(messages, model_override=CLAUDE_FALLBACK_MODEL)
        
        # Strip potential markdown fences
        clean_json = raw_output.strip()
        if clean_json.startswith("```"):
            clean_json = clean_json.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
            if clean_json.startswith("json"):
                clean_json = clean_json[4:].strip()
        
        try:
            summaries = json.loads(clean_json)
            if not isinstance(summaries, dict):
                logger.error(f"Lifestyle summary returned {type(summaries)}, expected dict: {clean_json}")
                return {}
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed for lifestyle summary: {e}")
            logger.debug(f"Raw problematic JSON: {clean_json}")
            return {}

        logger.info("Lifestyle summarization successful via Haiku.")
        return summaries
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        # Return empty or fallbacks? For now, empty is safer than broken JSON
        return {}

def summarize_aqi_forecast(content: str, lang: str = 'en') -> str:
    """
    Summarize the MOENV AQI forecast content (Chinese) into concise English or Chinese.
    Exactly 2–3 sentences.
    """
    if not content:
        return ""

    if lang == 'zh-TW':
        prompt = f"""你是一位專精台灣空氣品質的環境專家。
請將以下北台灣空氣品質預報摘要成繁體中文，簡潔口語，2–3 句話。

上下文內容：
{content}

規則：
1. 準確翻譯，但重點放在高層次的影響。
2. 提供正好 2–3 句簡短有力的句子。
3. 主要污染物可用中文或英文（例如「細懸浮微粒（PM2.5）」或「臭氧」均可）。
4. 如果數據為空或過於籠統，提供安全的備案摘要。

輸出：繁體中文摘要（純文字，2–3 句）。
"""
    else:
        prompt = f"""You are an environmental expert specializing in Taiwan's air quality.
Summarize the following Chinese air quality forecast for Northern Taiwan into a concise English update.

CONTEXT:
{content}

RULES:
1. Translate accurately but focus on high-level impact.
2. Provide EXACTLY 2–3 short, punchy sentences.
3. Mention the primary pollutant (e.g., PM2.5, Ozone) in English.
4. DO NOT include any Chinese characters or specific terminology titles like "細懸浮微粒" or "臭氧" in the output.
5. If the data is empty or generic, provide a safe fallback summary.

OUTPUT: Concise English summary (text only).
"""

    messages = [
        {"role": "user", "parts": [{"text": prompt}]}
    ]

    try:
        raw_output = generate_narration(messages, model_override=CLAUDE_FALLBACK_MODEL)
        # Strip potential markdown fences
        clean_text = raw_output.strip()
        if clean_text.startswith("```"):
            clean_text = clean_text.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
        
        logger.info("AQI summarization successful via Haiku.")
        return clean_text
    except Exception as e:
        logger.error(f"AQI summarization failed: {e}")
        return ""
