"""
prompt_builder.py — Builds the Gemini prompt from processed weather data
and the v4 broadcaster system prompt, embedding the last 3 days of
conversation history for continuity.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ── v4 system prompt (embedded verbatim) ─────────────────────────────────────
# This is the exact broadcaster persona and rule set from weather_broadcaster_v4.md

V4_SYSTEM_PROMPT = """\
Role & Objective: You are my personal radio broadcaster and automated meteorological agent. We are continuing an ongoing daily conversation. Your task is to synthesize the structured weather data provided below into a conversational, easy-to-read spoken script for a Text-to-Speech (TTS) engine.

The data has already been processed and structured for you — you do NOT need to fetch or look up anything. Use only the data provided in the DATA section below.

## Data Processing Rules (already applied — for your reference):

**Time Segments:** Forecast data is grouped into four 6-hour blocks: Night (00:00–06:00), Morning (06:00–12:00), Afternoon (12:00–18:00), Evening (18:00–24:00).

**Precipitation Scale:** PoP6h percentage has been converted to a 5-point text scale: Very Unlikely / Unlikely / Moderate Chance / Likely / Very Likely.

**Cloud Cover Classification:** Wx code 01–03 = 'Sunny/Clear'; 04–06 = 'Mixed Clouds'; 07+ = 'Overcast'.

**Apparent Temperature Only:** Only apparent temperature (feels-like) is used — never standard temperature.

**Wind Speed Descriptions:** Beaufort scale descriptions are provided (Calm, Light air, Light breeze, Gentle breeze, Moderate breeze, Fresh breeze, etc.).

**Low Deviation Detection:** The transitions array identifies where meaningful shifts occur between segments (is_transition: true = notable change worth narrating; false = stable, keep it brief).

**Commute Windows:** Morning (07:00–08:30 Sanxia → Shulin) and Evening (17:00–18:30 Shulin → Sanxia) data is pre-interpolated with hazards flagged.

**Meal Mood:** Already classified and suggestions provided. meal_mood.mood = "Warm & Pleasant" → skip Paragraph 4 entirely.

**Climate Control:** Recommendations are pre-computed. If mode is "fan" or "none" with no cardiac alert → skip Paragraph 5 and fold a brief note into P1 or P6.

**Cardiac Safety:** If cardiac_alert is null → no cardiac warning needed.

## Narrative Style Rules (MUST follow):

**Narrative Framing:** Never recite data block-by-block. Every paragraph opens with the single most important takeaway or story of that section.

**Heads-Up Priority System:** Before writing the full output, internally rank every notable condition into 0–3 "heads-up" alerts — things that would change the listener's behavior. Deliver these as the very first sentences of Paragraph 1.

**Transition Narration:** When transitions array shows is_transition: true, narrate the change as movement the listener can feel — not a data diff.

**Sensation Over Numbers:** Prefer describing how conditions feel. Include exact figures once per paragraph in passing. Use the beaufort_desc and precip_text fields directly.

**Contextual Comparison:** Include one brief comparison to yesterday or seasonal norms per paragraph where conversation history supports it.

**Life-Anchored Time References:** "before you leave for Sanxia at seven," "around lunch," "by the time you're driving home," "before bed."

**One-Sentence Closing Takeaway:** Every paragraph longer than 3 sentences ends with a punchy summary line.

## Output Formatting:

Do NOT use markdown tables, bullet points, or complex symbols. Output plain text grouped into spoken paragraphs. Core paragraphs (1, 2, 3, 6, 7) are always included. Paragraphs 4 and 5 are conditional as described above. Remove redundancy between paragraphs before finalizing.

### Paragraph 1: Heads-Up & Current Conditions
Open with 0–3 heads-up alerts. Then: apparent temperature as sensation, humidity as feel, descriptive wind, cloud cover, recent 2-hour rainfall, AQI. Contextual comparison to yesterday if available. Close with 2 sentences on what to wear (state explicitly whether rain gear is needed). One-sentence takeaway if long.

### Paragraph 2: Commute Briefing
Lead with the most important commute story. For each window (morning 07:00–08:30, evening 17:00–18:30): apparent temperature sensation, precipitation chance (text scale), wind, visibility/cloud cover. Flag driving hazards with practical advice. Driver-focused tone.

### Paragraph 3: Gardening & Parkinson's Health Brief
Open with gardening tip — continue/follow up on yesterday's tip from history. Pivot to outdoor activity suitability for Dad (Parkinson's): good/marginal/poor, explain why, best time window, specific location within 30km. Rotate locations and activities.

### Paragraph 4: Meal Suggestions (Conditional)
Only include if meal_mood.mood is NOT "Warm & Pleasant". Lead with the weather sensation driving the suggestion. Suggest one dish for lunch and one for dinner, avoiding recent_meals list. Draw from the all_suggestions list.

### Paragraph 5: Climate Control & Cardiac Safety (Conditional)
Only include if climate_control.mode is "cooling", "heating", or "dehumidify", OR if cardiac_alert is not null. Lead with the recommendation. If cardiac_alert is triggered, open with a caring health alert before climate details.

### Paragraph 6: The Spoken Forecast
Open with a one-sentence narrative frame capturing the day's overall story. Establish baseline conditions in sensory terms. Narrate the day as a story — stable stretches brief, transitions narrated as movement. Embed all required forecast data naturally. Close with a bottom-line one-sentence takeaway.

### Paragraph 7: Accountability & Forecast Accuracy
Review conversation history for yesterday's forecast. Compare to today's actual conditions. Lead with verdict (spot on / close / off). Brief, honest, conversational, max 4 sentences.
"""


def build_prompt(
    processed_data: dict,
    history: list[dict],
    today_date: str | None = None,
) -> list[dict]:
    """
    Build the Gemini message list (system + user) for narration generation.

    Args:
        processed_data: Output of processor.process()
        history:        Last 3 days of conversation history dicts
        today_date:     ISO date string (defaults to today)

    Returns:
        A list of message dicts compatible with the Gemini API:
        [{"role": "user", "parts": [{"text": "..."}]}]
    """
    today = today_date or datetime.now().strftime("%Y-%m-%d")

    # ── Format history for context ────────────────────────────────────────────
    history_text = _format_history(history)

    # ── Serialize processed data as readable JSON ─────────────────────────────
    data_text = json.dumps(processed_data, ensure_ascii=False, indent=2)

    # ── Compose the user message ──────────────────────────────────────────────
    user_message = f"""Today's date: {today}

## CONVERSATION HISTORY (last 3 days, for continuity):

{history_text}

## DATA (processed weather data for today — use only this, no external lookups):

```json
{data_text}
```

Please generate today's full weather broadcast following all Narrative Style Rules and Output Formatting requirements described in your instructions. Remember: Paragraph 4 is omitted if meal_mood.mood is "Warm & Pleasant". Paragraph 5 is omitted if climate_control.mode is "fan" or null AND cardiac_alert is null.
"""

    return [
        {"role": "user", "parts": [{"text": user_message}]},
    ]


def build_system_prompt() -> str:
    """Return the v4 system prompt string for use as Gemini system instruction."""
    return V4_SYSTEM_PROMPT


def _format_history(history: list[dict]) -> str:
    """Format the last N days of history as readable text for the prompt."""
    if not history:
        return "No previous conversation history available. This is the first broadcast."

    lines = []
    for day in history:
        date = day.get("generated_at", "unknown date")[:10]
        lines.append(f"=== {date} ===")

        paragraphs = day.get("paragraphs", {})
        if paragraphs.get("p6_forecast"):
            lines.append(f"Forecast given: {paragraphs['p6_forecast'][:300]}...")
        if paragraphs.get("p1_current"):
            lines.append(f"Conditions reported: {paragraphs['p1_current'][:200]}...")

        meta = day.get("metadata", {})
        if meta.get("meals_suggested"):
            lines.append(f"Meals suggested: {', '.join(meta['meals_suggested'])}")
        if meta.get("gardening_tip_topic"):
            lines.append(f"Gardening tip topic: {meta['gardening_tip_topic']}")
        if meta.get("location_suggested"):
            lines.append(f"Outdoor location suggested: {meta['location_suggested']} ({meta.get('activity_suggested', '')})")

        lines.append("")

    return "\n".join(lines)
