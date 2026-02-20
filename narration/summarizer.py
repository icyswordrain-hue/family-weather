"""
summarizer.py — Uses Claude Haiku to summarize narration paragraphs into 
concise lifestyle card snippets with specific sentence constraints.
"""

import logging
import json
from narration.claude_client import generate_narration
from config import CLAUDE_FALLBACK_MODEL

logger = logging.getLogger(__name__)

def summarize_for_lifestyle(paragraphs: dict[str, str]) -> dict[str, str]:
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
        
        summaries = json.loads(clean_json)
        logger.info("Lifestyle summarization successful via Haiku.")
        return summaries
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        # Return empty or fallbacks? For now, empty is safer than broken JSON
        return {}
