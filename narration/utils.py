"""
narration/utils.py — Shared utilities for LLM narration (text extraction, metadata).
"""

import re
import logging

logger = logging.getLogger(__name__)

def clean_narration_text(text: str) -> str:
    """
    Remove auxiliary JSON blocks (e.g. meal regeneration) from the narration text.
    """
    if not text:
        return ""
    
    # Pattern 1: Markdown code blocks containing JSON
    # Matches ```json ... ``` (dotall)
    text = re.sub(r"```json\s*\{.*?\}\s*```", "", text, flags=re.DOTALL | re.IGNORECASE)
    
    # Pattern 2: Raw JSON starting with specific keys if fences are missing
    # "regenerated_meals": ...
    text = re.sub(r'\{\s*"regenerated_meals".*?\}\s*$', "", text, flags=re.DOTALL | re.IGNORECASE)
    
    return text.strip()


def extract_paragraphs(narration_text: str) -> dict[str, str]:
    """
    Extract individual paragraphs from the narration text using content heuristics.

    Returns a dict with keys p1_current through p7_accountability.
    """
    para_keys = [
        "p1_current",
        "p2_commute",
        "p3_garden_health",
        "p4_meals",
        "p5_climate_cardiac",
        "p6_forecast",
        "p7_accountability",
    ]

    # Split on blank lines; filter empty chunks
    raw_chunks = [c.strip() for c in re.split(r"\n{2,}", narration_text) if c.strip()]

    # Content-based keyword matchers (checked in priority order)
    _HEURISTICS = [
        ("p7_accountability", ["forecast accuracy", "forecast called for", "actual reading", "solid call", "prediction", "verdict", "call overall", "yesterday's forecast"]),
        ("p5_climate_cardiac", ["The AC", "air condition", "indoor air", "keep it set", "heater", "climate control", "dehumidify", "heating mode", "cooling mode", "cardiac alert", "heart health"]),
        ("p4_meals", ["lunch", "dinner", "dish", "meal suggestion", "niú", "miàn", "guō", "fàn", "tāng", "jī"]),
        ("p3_garden_health", ["gardening", "parkinson", "outdoor activity", "dad", "seedling", "plant", "prune", "soil"]),
        ("p2_commute", ["commute", "drive", "traffic", "road conditions", "shulin", "sanxia", "route"]),
        ("p6_forecast", ["today's story", "unfolding story", "bottom line", "throughout the day", "overnight"]),
    ]

    paragraphs: dict[str, str] = {}
    used_indices: set[int] = set()

    # First pass: match chunks to paragraph keys using heuristics
    for key, keywords in _HEURISTICS:
        for i, chunk in enumerate(raw_chunks):
            if i in used_indices:
                continue
            chunk_lower = chunk.lower()
            if any(kw.lower() in chunk_lower for kw in keywords):
                paragraphs[key] = chunk
                used_indices.add(i)
                break

    # Collect all remaining unmatched chunks
    unmatched = []
    for i, chunk in enumerate(raw_chunks):
        if i not in used_indices:
             unmatched.append(chunk)
    
    # If p1_current is empty, start with first unmatched
    # If p1_current has content (matched via heuristic?), append others to it or distinct key?
    # Heuristics for p1 are None.
    
    if unmatched:
        # If p1 was already set by some heuristic (unlikely for p1), append?
        # Actually p1 key is reserved for "Current".
        # Let's just join all unmatched into p1 and p6 (Outlook) if p1 full?
        # Simpler: Join all unmatched and put in p1 if p1 empty, or append to p6 if p1 full.
        
        # But wait, p1 is "Current & Outlook".
        # Let's just assign the first unmatched to p1 if empty.
        # And any SUBSEQUENT unmatched to p6 (Forecast) or append to p1.
        
        if "p1_current" not in paragraphs:
             paragraphs["p1_current"] = unmatched[0]
             rest = unmatched[1:]
        else:
             rest = unmatched

        if rest:
             # Append rest to p6_forecast (Outlook)
             existing = paragraphs.get("p6_forecast", "")
             paragraphs["p6_forecast"] = (existing + "\n\n" + "\n\n".join(rest)).strip()

    # Ensure all keys exist (empty string if not present)
    for key in para_keys:
        paragraphs.setdefault(key, "")

    return paragraphs


def extract_metadata(
    narration_text: str,
    meal_suggestions: list[str],
    location_suggestions: list[str] = [],
) -> dict:
    """
    Extract structured metadata from the narration text.
    """
    metadata: dict = {
        "meals_suggested": [],
        "gardening_tip_topic": "",
        "location_suggested": "",
        "activity_suggested": "",
    }

    # Detect which dish names from the suggestion pool appear in the narration
    text_lower = narration_text.lower()
    for dish in meal_suggestions:
        # Extract pinyin portion from format: "涼麵 (liáng miàn, cold sesame noodles)"
        pinyin_match = re.search(r"\(([^)]+?)(?:,|\))", dish)
        if pinyin_match:
            pinyin = pinyin_match.group(1).strip().lower()
            if pinyin in text_lower:
                metadata["meals_suggested"].append(dish.split("(")[0].strip())
        else:
            dish_clean = dish.split("(")[0].strip()
            if dish_clean and dish_clean.lower() in text_lower:
                metadata["meals_suggested"].append(dish_clean)

    # Match location names from the curated pool
    if location_suggestions:
        for loc_name in location_suggestions:
            if loc_name.lower() in text_lower:
                metadata["location_suggested"] = loc_name
                break

    # Fallback: regex pattern for Taipei-area place names
    if not metadata["location_suggested"]:
        location_patterns = [
            r"(\b(?:Banqiao|Shulin|Sanxia|Yingge|Tucheng|Zhonghe|Xinzhuang|Tamsui|Bitan|Daan|Zhongshan)\b[^.]{0,30}(?:park|trail|riverside|plaza|forest|garden|bikeway|greenway|museum|center|courtyard))",
            r"(\b(?:park|trail|riverside|plaza|garden|bikeway|greenway)\b)",
        ]
        for pattern in location_patterns:
            location_match = re.search(pattern, narration_text, re.IGNORECASE)
            if location_match:
                metadata["location_suggested"] = location_match.group(1).strip()
                break

    # Look for activity keywords
    for activity in ["hiking", "biking", "kite", "walking", "jogging", "cycling",
                     "tai chi", "stretching", "strolling", "paddleboat", "e-bike"]:
        if activity.lower() in text_lower:
            metadata["activity_suggested"] = activity
            break

    # Gardening topic
    gardening_match = re.search(
        r"(seedling|transplant|watering|pruning|fertiliz|harvest|sowing|compost|soil|pot|seedbed|mulch|weed|pest|herb)",
        narration_text, re.IGNORECASE
    )
    if gardening_match:
        metadata["gardening_tip_topic"] = gardening_match.group(1).lower()

    return metadata
