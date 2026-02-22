"""meal_classifier.py — Weather-based meal mood classification."""

import random
from typing import Optional

# These would ideally be in config but are currently in weather_processor.py or config
# For now, we'll assume they are accessible or provide fallbacks
try:
    from config import (
        MEAL_FALLBACK_DISH,
        CLIMATE_TEMP_HOT,
        CLIMATE_RH_HOT,
    )
except ImportError:
    MEAL_FALLBACK_DISH = "滷肉飯 (lǔ ròu fàn)"
    CLIMATE_TEMP_HOT = 30
    CLIMATE_RH_HOT = 70

def _classify_meal_mood(segmented: dict[str, Optional[dict]]) -> dict:
    """
    Classify the day into one of four meal moods using daytime segments.
    Uses Afternoon as the primary driver, with Morning as secondary.
    """
    # Gather daytime apparent temperatures and humidity
    ats = []
    rhs = []
    is_rainy = False

    for seg_name in ["Morning", "Afternoon", "Evening"]:
        seg = segmented.get(seg_name)
        if seg:
            if seg.get("AT") is not None:
                ats.append(seg["AT"])
            if seg.get("RH") is not None:
                rhs.append(seg["RH"])
            if (seg.get("PoP6h") or 0) >= 61:
                is_rainy = True

    avg_at = sum(ats) / len(ats) if ats else 20.0
    avg_rh = sum(rhs) / len(rhs) if rhs else 60.0

    if avg_at >= CLIMATE_TEMP_HOT and avg_rh >= CLIMATE_RH_HOT:
        mood = "Hot & Humid"
        suggestions = [
            "涼麵 (liáng miàn, cold sesame noodles)",
            "愛玉冰 (ài yù bīng)",
            "涼拌小黃瓜 (marinated cucumber)",
            "竹筍湯 (bamboo shoot soup)",
            "豆花 (dòuhuā) with shaved ice",
        ]
    elif avg_at >= 22 and avg_rh < CLIMATE_RH_HOT:
        mood = "Warm & Pleasant"
        suggestions = [
            "滷肉飯 (lǔ ròu fàn)",
            "蚵仔煎 (ô-á-tsian)",
            "鹹酥雞 (yán sū jī)",
            "便當 (biàndāng) with assorted sides",
            "水餃 (shuǐ jiǎo)",
            "炒米粉 (chǎo mǐ fěn)",
        ]
    elif avg_at >= 15 or is_rainy:
        mood = "Cool & Damp"
        suggestions = [
            "牛肉麵 (niú ròu miàn)",
            "麻油雞 (má yóu jī)",
            "藥燉排骨 (herbal pork rib soup)",
            "火鍋 (huǒ guō)",
            "鹹粥 (savory congee)",
            "四神湯 (sì shén tāng)",
        ]
    else:
        mood = "Cold"
        suggestions = [
            "薑母鴨 (jiāng mǔ yā)",
            "羊肉爐 (yáng ròu lú)",
            "麻辣鍋 (málà hot pot)",
            "燒酒雞 (shāo jiǔ jī)",
            "花生豬腳湯 (peanut pig trotter soup)",
        ]

    return {
        "mood": mood,
        "avg_at": round(float(avg_at), 1),
        "avg_rh": round(float(avg_rh), 1),
        "is_rainy": is_rainy,
        "all_suggestions": suggestions,
    }

def _extract_recent_meals(history: list[dict], days: int = 3) -> list[str]:
    """Extract meal suggestions from the last N days of history."""
    meals = []
    for day in history[-days:]:
        day_meals = day.get("metadata", {}).get("meals_suggested", [])
        meals.extend(day_meals)
    return meals
