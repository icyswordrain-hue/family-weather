
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def extract_paragraphs(narration_text: str) -> dict[str, str]:
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
    
    print(f"DEBUG: Found {len(raw_chunks)} chunks.")

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
        print(f"Scanning for {key} with keywords: {keywords}")
        for i, chunk in enumerate(raw_chunks):
            if i in used_indices:
                continue
            chunk_lower = chunk.lower()
            found_kw = next((kw for kw in keywords if kw.lower() in chunk_lower), None)
            if found_kw:
                print(f"  MATCH: Chunk {i} matched {key} on keyword '{found_kw}'")
                safe_chunk = chunk[:30].encode('ascii', 'replace').decode('ascii')
                print(f"  Chunk start: {safe_chunk}...")
                paragraphs[key] = chunk
                used_indices.add(i)
                break

    # P1 is always the first unmatched chunk (current conditions / heads-up)
    for i, chunk in enumerate(raw_chunks):
        if i not in used_indices:
            print(f"  FALLBACK: Chunk {i} assigned to p1_current")
            paragraphs["p1_current"] = chunk
            used_indices.add(i)
            break

    # Ensure all keys exist (empty string if not present)
    for key in para_keys:
        paragraphs.setdefault(key, "")

    return paragraphs

text = """No surprises today — pretty smooth all around. Right now at the xìn yì station, the air feels like a mild 18 degrees with a calm, barely-there wind. Humidity sits at 79%, which is comfortable enough — not sticky yet, though that changes later. AQI is 59, moderate, and the forecast office does flag that early morning diffusion is poor today, so if you're sensitive to particulates, hold off on outdoor exercise until mid-morning. No rain in the past two hours, none on the horizon. Yesterday felt similar in temperature, so no jarring change. A light jacket is all you need this morning — no rain gear required.

For your drive to Sān Xiá at seven, conditions are easy. The sky is overcast but dry — precipitation is very unlikely, and a gentle breeze at about 3.7 meters per second keeps things comfortable at around 21 or 22 degrees apparent. No hazards flagged. On the way home from Shù Lín between five and six-thirty, the temperature eases back to about 20 degrees, humidity climbs to 88%, and a light breeze accompanies you under a fully overcast sky. Still very unlikely to rain, but the damp air will make it feel a touch heavier. Both commutes are clean — just keep the headlights on under those thick clouds.

Since yesterday we talked about soil prep, today is a good moment to think about what goes into it. If you've been loosening and enriching the bed, it's ready for a shallow sow — something low-maintenance like spring onions or lettuce does well in this cool, moist weather. For Dad, outdoor conditions today are good — the temperature is comfortable, there's no rain, and the breeze is gentle. The best window is around nine to ten in the morning, before the humidity thickens further. Today's spot: the Bì tán Scenic Area in Xīn diàn. It's a paved promenade along the river — flat, shaded, with gentle terrain and a beautiful suspension bridge to walk toward. Perfect for a slow, steady stroll without worrying about uneven ground.

The mood today is cool and damp, so something warming makes sense. For lunch, a bowl of niú ròu miàn — beef noodle soup — would hit the spot, rich and hearty against the grey overcast. For dinner, má yóu jī, sesame oil chicken, is a classic choice for this kind of cool, humid evening — it warms from the inside out.

The AC stays on today — keep it set between 26 and 27 degrees, and plan for around 12 hours of use. Windows should stay closed; outside humidity climbs toward 88 to 90% by evening, and letting that damp air in will just make the indoor air feel heavier without any real benefit.

Today's story is a gentle, grey, warming arc. The small hours are cool and mixed-cloudy — around 14 to 15 degrees apparent, 90% humidity, a light breeze, and virtually no rain chance. Then as morning arrives, the sky closes over into full overcast and the air jumps nearly seven degrees warmer — that's the one meaningful shift today, and you'll feel it clearly as you head out. The afternoon data isn't available, but the evening settles back to about 20 degrees with humidity near 88% and a light breeze under continued overcast. Rain remains very unlikely all day. AQI holds at moderate — acceptable, but the AQI forecast warns of fine particulate accumulation through the week as easterly winds keep the western side of Taiwan in a pocket of poor dispersion. Bottom line: a mild, grey, quietly damp day — dress in layers you can peel off by mid-morning.

Yesterday's forecast called for a cool, damp night around 14 to 16 degrees warming into a 21-degree overcast morning — and the actual reading came in at 18.1 degrees with 79% humidity and calm winds. That's pretty close — the temperature landed right in the middle of the predicted range, humidity was a touch lower than the 90% forecast for the overnight period, and the wind was even calmer than expected. A solid call overall, just slightly warmer and drier than projected."""

result = extract_paragraphs(text)
import json
print("\nResult:")
print(json.dumps(result, indent=2))
