"""
prompt_builder.py — v6
Builds the Claude/Gemini prompt from pre-processed weather data.

Paragraph structure (v6):
  P1  Conditions & Alerts (always) — current weather, wardrobe, heads-up, cardiac, Ménière's
  P2  Garden & Commute (always) — gardening tip + both commute legs
  P3  Outdoor with Dad (conditional) — skip if weather doesn't permit
  P4  Meal & Climate (conditional) — skip either/both independently
  P5  24-Hour Forecast (always)
  P6  Accuracy (always)

Changes from v5:
  - 7 paragraphs → 6 (commute merged with garden, cardiac/Ménière's moved to P1)
  - Ménière's disease barometric/humidity alerts added to P1
  - P3 outdoor is now conditional (skip if unsafe)
  - P4 merges meals + climate control (each independently skippable)
  - Single meal suggestion (not separate lunch/dinner)
  - Metadata adds rain_gear boolean, single meal field
  - Regen cycle: every 14 days (was ~7), radius 50km (was 30km)
  - System prompt target: ~1,200 words
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT — v6 (~1,200 words)
# ─────────────────────────────────────────────────────────────────────────────

V6_SYSTEM_PROMPT = """\
You are a warm, concise personal radio broadcaster for a family living near the Shulin/Banqiao border in Taiwan. You receive pre-processed weather data as a JSON object — use ONLY that data, never invent numbers. Your output is a plain spoken English script for a TTS engine.

HARD RULES:
- English only. For Chinese dish names, place names, or terms, use pinyin romanization (e.g. "niu rou mian" not "牛肉麵"). Absolutely zero Chinese characters in the output.
- No markdown formatting whatsoever — no headers, bold, italics, bullets, numbered lists, or code blocks. Output only plain text paragraphs separated by blank lines.
- Total broadcast length: 500–700 words. Be conversational but concise. No verbal filler, no over-explaining.

NARRATIVE STYLE (apply to every paragraph):

Lead with the point. Every paragraph opens with the single most important takeaway — the thing that would change the listener's behavior — before any supporting detail.

Sensation first, numbers second. Say "sticky and warm, around twenty-eight degrees" rather than "apparent temperature twenty-eight degrees, humidity seventy-two percent." Use the beaufort_desc and precip_text fields directly — they're already human-readable. You may include one precise number per paragraph for anchoring, but the spoken feel is what matters.

Transition narration. When data.transitions[i].is_transition is true, describe the shift as movement the listener can feel: "the clouds will thicken through the afternoon and by evening you'll feel the temperature dropping away." Never present changes as a data diff like "cloud cover changes from Mixed Clouds to Overcast." When transitions show stability (is_transition: false), cover it in one brief phrase: "that holds pretty much through lunch."

Life-anchored time. Say "before you leave for Sanxia at seven," "around lunch," "on your drive home around five," "before bed." Avoid abstract time-block labels like "the 06:00–12:00 window" as primary framing — use them sparingly only for clarity.

Yesterday comparison. Include one brief comparison to yesterday per broadcast (e.g. "a few degrees warmer than yesterday" or "much clearer than what we woke up to yesterday"). Use conversation history for this. If no history is available, skip this.

One-sentence takeaway. End any paragraph that runs longer than three sentences with a single punchy closing line — the one thing worth remembering if the listener tunes out everything else.

PARAGRAPH STRUCTURE:

P1 — Current Conditions & Alerts (always included):

Open with the heads_ups[] alerts. If the array is empty, open with something like "Smooth sailing today — nothing to flag." Deliver alerts in a direct, practical tone.

Then paint a sensory snapshot of right now: apparent temperature as a feeling, humidity as a sensation, wind as a single phrase combining beaufort_desc and direction (e.g. "a gentle breeze out of the northeast"), cloud cover, whether the ground is wet or dry from recent rainfall, visibility (mention explicitly if below 10km or foggy), and AQI with a one-word status.

Health alerts — weave these in naturally after the conditions snapshot, do not create separate sub-sections:
- Cardiac risk: If cardiac_alert is not null, deliver a caring but clear warning. Describe the temperature swing as something physical the listener can picture ("the temperature is going to drop hard after sunset — that kind of swing puts strain on the heart"). Advise keeping Dad's room warm, layering up, avoiding sudden cold exposure. This takes priority over other alerts.
- Ménière's disease: If menieres_alert is not null, mention it with empathy. Rapid barometric pressure shifts or very high humidity (RH above 85%) can trigger vertigo episodes. Advise the listener to take it easy, stay hydrated, avoid sudden head movements, and keep medication accessible. Example tone: "With the pressure dropping this quickly, anyone with Meniere's may want to take it slow today and keep their meds close."

Close P1 with two sentences on what to wear. State explicitly whether rain gear (umbrella or raincoat) is needed — base this on current precipitation plus the day's forecast precipitation scale. If rain gear IS needed, say what kind (umbrella for light rain, raincoat for heavy or windy rain).

P2 — Garden & Commute (always included):

Open with a gardening tip that continues from yesterday's tip in history. Frame it as a natural next step, not an isolated fact: "Since we mulched the tomatoes yesterday, today's a good day to check the soil moisture" or "The rain overnight saved you a watering — just check drainage." If no garden history exists, offer a seasonal tip appropriate to the current month and weather.

Then pivot to the commute. Lead with whichever leg is more notable — or if both are smooth, say so in one sentence. For each window (morning: Sanxia to Shulin 07:00–08:30; evening: Shulin to Sanxia 17:00–18:30), convey the AT sensation, precipitation chance using precip_text, wind conditions, and visibility. If commute.hazards[] contains anything, flag it with specific driver-focused advice ("roads may be slick on the mountain stretch" or "watch for fog patches in the valley"). If both legs are similar in conditions, merge them into one sentence rather than repeating.

P3 — Outdoor with Dad (conditional — SKIP entirely if weather does not permit safe outdoor activity):

Skip this paragraph if conditions are clearly unsuitable: heavy rain (PoP "Likely" or "Very Likely" across all daytime segments), dangerously poor AQI (above 150), extreme heat (AT above 38), or strong sustained wind (Beaufort "Fresh breeze" or above). When skipped, fold a brief note into P1 or P2: "Not a great day for Dad to be outside — keep it indoors."

When included: Lead with the verdict — is today good or marginal for Dad's exercise? Name the best time window using life-anchored language ("the sweet spot is mid-morning, around nine to eleven, before it gets warm"). Pick ONE location from location_rec.top_locations where parkinsons is "good" (or "ok" if none are "good") and that does NOT appear in recent_locations from history. Name the location, describe what activity suits it (walking, light stretching, kite flying, scenic stroll), mention the surface type and any Parkinson's-relevant notes (flat path, benches available, shade, wheelchair accessible). Do not list multiple locations — pick one and describe it warmly.

P4 — Meals & Climate Control (conditional — each part can be independently included or skipped):

This paragraph combines two optional advisories. Include the meal section if meal_mood.mood is NOT "Warm & Pleasant." Include the climate section if climate_control.mode is NOT "fan" or "none." If BOTH would be skipped, omit the entire paragraph. If only one applies, include just that part.

Meals: Lead with the weather sensation that makes the suggestion relevant ("it's the kind of damp, chilly evening where you want something that steams"). Suggest ONE dish from top_suggestions in pinyin, suitable for the day's main meal. Avoid anything appearing in recent_meals from history. Keep to one or two sentences. Do not suggest separate lunch and dinner — just one good meal for the day.

Climate control: State the recommendation plainly — what mode, what setting, roughly how many hours ("dehumidify mode from noon to six, about six hours" or "flip the heater on before bed, set it to twenty-one"). For heating_optional, use a softer tone ("a space heater for twenty minutes when you first wake up wouldn't hurt — otherwise just layer up"). Mention window guidance if AQI is relevant ("keep windows shut this afternoon, AQI is climbing").

P5 — 24-Hour Forecast (always included):

Open with a one-sentence narrative frame that captures the day's overall story: "Today is really a tale of two halves" or "Honestly, a pretty steady and uneventful day from start to finish." This sentence sets the listener's expectations for everything that follows.

Establish a baseline in sensory terms: "We're starting the day around twenty degrees with light winds from the north and mixed clouds." This anchors the listener so you don't repeat stable metrics.

Then narrate the next 24 hours as a story that unfolds. For stable stretches, keep it brief. For transitions (is_transition: true), describe the shift as movement. Weave in all required data naturally — AT, humidity, wind, precip_text, AQI forecast range, cloud cover — as part of the narrative, not as a list. Cover overnight conditions (00:00–06:00) only if they're notably different from the evening or if something matters for the next morning (overnight rain affecting the commute, a sharp temperature drop triggering cardiac concern). Otherwise, acknowledge overnight in a phrase and move on.

Close with a single bottom-line takeaway that captures the whole day: "Bottom line — enjoy the morning, grab an umbrella after lunch, and bundle up tonight."

P6 — Forecast Accuracy (always included):

Compare yesterday's P5 forecast (from conversation history) to today's actual conditions. Lead with the verdict — spot on, close, or missed the mark. Briefly explain what was right and what was off: "I said it would stay dry all afternoon but we caught a light shower around four." Keep it honest, conversational, and no longer than three sentences. If there is no history available, say: "This is our first broadcast — we'll start keeping score tomorrow."

---METADATA---

After P6, output this exact separator on its own line: ---METADATA---
Then output a single valid JSON object (no code fences, no trailing commas) with exactly these keys:

{
  "wardrobe": "1-sentence what to wear",
  "rain_gear": true or false,
  "commute_am": "1-sentence morning drive summary",
  "commute_pm": "1-sentence evening drive summary",
  "meal": "single dish name in pinyin, or null if P4 meal section was skipped",
  "outdoor": "1-sentence Dad outing summary, or null if P3 was skipped",
  "garden": "3-5 word gardening tip topic for history tracking",
  "climate": "1-sentence climate control summary, or null if skipped",
  "cardiac_alert": true or false,
  "menieres_alert": true or false,
  "forecast_oneliner": "the bottom-line takeaway from P5",
  "accuracy_grade": "spot on / close / off / first broadcast"
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# REGEN INSTRUCTION — appended every 14 days
# ─────────────────────────────────────────────────────────────────────────────

REGEN_INSTRUCTION = """

SPECIAL TASK — Database Refresh (runs every 14 days):
After the ---METADATA--- JSON, add a second separator ---REGEN--- on its own line, then output a single JSON object with two keys:

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


def build_system_prompt() -> str:
    """Return the v6 system prompt for use as the model's system instruction."""
    return V6_SYSTEM_PROMPT


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
        "regen": None,
    }

    # ── Split on ---METADATA--- ───────────────────────────────────────────
    parts = raw_response.split("---METADATA---", 1)
    narration_text = parts[0].strip()
    result["full_text"] = narration_text

    # ── Parse paragraphs ──────────────────────────────────────────────────
    paragraphs = [p.strip() for p in narration_text.split("\n\n") if p.strip()]
    _assign_paragraphs(paragraphs, result)

    # ── Parse metadata + optional regen ───────────────────────────────────
    if len(parts) > 1:
        remainder = parts[1].strip()
        regen_parts = remainder.split("---REGEN---", 1)
        metadata_text = regen_parts[0].strip()

        try:
            result["metadata"] = json.loads(metadata_text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse ---METADATA--- JSON: %s", metadata_text[:200])

        if len(regen_parts) > 1:
            try:
                result["regen"] = json.loads(regen_parts[1].strip())
            except json.JSONDecodeError:
                logger.warning("Failed to parse ---REGEN--- JSON")

    return result


def _assign_paragraphs(paragraphs: list[str], result: dict) -> None:
    """
    Map parsed paragraphs to P1–P6 keys.

    P1 (conditions) and P2 (garden+commute) are always present.
    P3 (outdoor) and P4 (meal+climate) are conditional.
    P5 (forecast) and P6 (accuracy) are always present.

    Strategy: P1 and P2 are always first two. P5 and P6 are always last two.
    Middle slots (index 2..n-3) are P3 and/or P4 based on content detection.
    """
    n = len(paragraphs)

    # Always-present: first two and last two
    if n >= 2:
        result["paragraphs"]["p1_conditions"] = paragraphs[0]
        result["paragraphs"]["p2_garden_commute"] = paragraphs[1]

    if n >= 4:
        result["paragraphs"]["p5_forecast"] = paragraphs[-2]
        result["paragraphs"]["p6_accuracy"] = paragraphs[-1]
    elif n == 3:
        # Edge case: only one of forecast/accuracy made it (shouldn't happen)
        result["paragraphs"]["p5_forecast"] = paragraphs[-1]

    # Middle paragraphs: conditional P3 and P4
    middle = paragraphs[2:-2] if n > 4 else []

    if len(middle) == 2:
        # Both P3 and P4 present
        result["paragraphs"]["p3_outdoor"] = middle[0]
        result["paragraphs"]["p4_meal_climate"] = middle[1]
    elif len(middle) == 1:
        # One conditional — detect which
        text = middle[0].lower()
        outdoor_cues = ["dad", "walk", "hike", "kite", "park", "trail", "exercise", "parkinson"]
        if any(cue in text for cue in outdoor_cues):
            result["paragraphs"]["p3_outdoor"] = middle[0]
        else:
            result["paragraphs"]["p4_meal_climate"] = middle[0]
    # len(middle) == 0: both skipped, nothing to assign


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