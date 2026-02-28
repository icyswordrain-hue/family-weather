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
        # Use Haiku for speed and cost. Override system prompt to avoid the broadcast formatting constraints.
        raw_output = generate_narration(messages, model_override=CLAUDE_FALLBACK_MODEL, lang=lang, system_prompt_override="")
        
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

        return summaries
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        # Return empty or fallbacks? For now, empty is safer than broken JSON
        return {}
