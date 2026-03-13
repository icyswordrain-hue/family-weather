# Fold Cards into Narration: Fallback Narrator Structured Output

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the template (fallback) narration produce the same `---METADATA---` / `---CARDS---` structure as the LLM, so lifestyle cards render with proper natural-language text instead of rule-based fallbacks; use history data for garden continuity.

**Architecture:** Add `history` + `lang` params to `build_narration()`. Add two helpers — `_build_fallback_metadata()` and `_build_fallback_cards()` — that generate the same JSON structure the LLM outputs. Append the JSON sections to the return string so `parse_narration_response()` parses them correctly. Update `pipeline.py` to pass `history` and `lang` through.

Note: `processed["recent_meals"]` and `processed["recent_locations"]` are already computed from history in `weather_processor.py`, so meal/location deduplication works via `processed` alone; history is only needed for garden tip continuity.

**Tech Stack:** Python, `json` (stdlib), existing `datetime`

---

## Context

When the LLM fails, `build_narration()` returns a flat string with no `---CARDS---` block. `parse_narration_response()` finds no cards → `summaries = {}` → `_slice_lifestyle()` falls back to terse rule-based strings for every card (e.g., "System: Off.", "No precipitation gear expected."). This means the lifestyle view looks degraded whenever the LLM is unavailable. Additionally, the fallback ignores history, so there's no meal/location/garden continuity.

---

## Critical Files

- Modify: `narration/fallback_narrator.py` — add `history`/`lang` params, add CARDS+METADATA generation
- Modify: `backend/pipeline.py:121` — pass `history=history, lang=lang` to `build_narration()`
- Test: `tests/test_fallback_narrator.py` — new test file verifying CARDS block is present and parseable
- Reference: `narration/llm_prompt_builder.py:335` — `parse_narration_response()` (consumer of output)
- Reference: `web/routes.py:136` — `_slice_lifestyle()` (consumer of `summaries`)

---

## Task 1: Update `pipeline.py` to pass `history` and `lang` to fallback

**File:** `backend/pipeline.py:121`

**Step 1: Edit the fallback call**

Replace:
```python
text = build_narration(processed, date_str=date_str)
```
With:
```python
text = build_narration(processed, date_str=date_str, history=history, lang=lang)
```

**Step 2: Run existing tests**

```bash
pytest tests/test_pipeline.py -v
```
Expected: all pass (`build_narration` is mocked in those tests, signature change is transparent).

**Step 3: Commit**
```bash
git add backend/pipeline.py
git commit -m "fix: pass history and lang to fallback narrator"
```

---

## Task 2: Rewrite `fallback_narrator.py` with CARDS + METADATA output

**File:** `narration/fallback_narrator.py`

**Step 1: Write the failing test first**

Create `tests/test_fallback_narrator.py`:

```python
"""tests/test_fallback_narrator.py — Unit tests for the fallback narrator CARDS output."""
import json
from narration.fallback_narrator import build_narration
from narration.llm_prompt_builder import parse_narration_response

MINIMAL_PROCESSED = {
    "current": {"AT": 22.0, "RH": 75, "RAIN": 0, "beaufort_desc": "Light breeze", "wind_dir_text": "N"},
    "commute": {
        "morning": {"AT": 20.0, "precip_text": "Unlikely", "beaufort_desc": "Calm", "wind_dir_text": "N", "hazards": []},
        "evening": {"AT": 23.0, "precip_text": "Unlikely", "beaufort_desc": "Calm", "wind_dir_text": "S", "hazards": []},
    },
    "climate_control": {"mode": "Off", "estimated_hours": 0, "set_temp": None, "notes": []},
    "meal_mood": {"mood": "Warm & Pleasant", "top_suggestions": ["滷肉飯"], "all_suggestions": ["滷肉飯"]},
    "forecast_segments": {
        "Morning": {"AT": 20.0, "precip_text": "Unlikely", "cloud_cover": "Partly Cloudy"},
        "Afternoon": {"AT": 25.0, "precip_text": "Unlikely", "cloud_cover": "Sunny"},
    },
    "transitions": [],
    "heads_ups": [],
    "cardiac_alert": None,
    "menieres_alert": None,
    "outdoor_index": {
        "grade": "B", "label": "Good", "score": 75, "parkinsons_safe": True,
        "best_window": "9am–11am", "top_activity": "walking", "activity_scores": {},
    },
    "location_rec": {
        "top_locations": [{"name": "Dahan River Bikeway", "activity": "cycling", "parkinsons": "good", "notes": "Flat paved path."}],
        "mood": "Nice",
    },
    "aqi_realtime": {"aqi": 40, "status": "Good"},
    "aqi_forecast": {},
    "recent_meals": [],
    "recent_locations": [],
}


def test_fallback_produces_cards_block():
    """build_narration must include a parseable ---CARDS--- JSON block."""
    text = build_narration(MINIMAL_PROCESSED, date_str="2026-02-28")
    assert "---CARDS---" in text


def test_cards_have_all_required_keys():
    """Parsed cards must have all 8 required keys."""
    text = build_narration(MINIMAL_PROCESSED, date_str="2026-02-28")
    parsed = parse_narration_response(text)
    cards = parsed["cards"]
    for key in ("wardrobe", "rain_gear", "commute", "meals", "hvac", "garden", "outdoor", "alert"):
        assert key in cards, f"Missing card key: {key}"


def test_alert_card_has_text_and_level():
    """Alert card must be a dict with 'text' and 'level'."""
    text = build_narration(MINIMAL_PROCESSED, date_str="2026-02-28")
    parsed = parse_narration_response(text)
    alert = parsed["cards"]["alert"]
    assert isinstance(alert, dict)
    assert "text" in alert
    assert "level" in alert
    assert alert["level"] in ("INFO", "WARNING", "CRITICAL")


def test_metadata_block_present_and_parseable():
    """build_narration must include a parseable ---METADATA--- JSON block."""
    text = build_narration(MINIMAL_PROCESSED, date_str="2026-02-28")
    parsed = parse_narration_response(text)
    assert "garden" in parsed["metadata"]
    assert "accuracy_grade" in parsed["metadata"]


def test_history_garden_continuity():
    """Yesterday's garden topic from history should appear in the garden card."""
    history = [{"generated_at": "2026-02-27T08:00:00+08:00", "metadata": {"garden": "soil moisture check"}}]
    text = build_narration(MINIMAL_PROCESSED, date_str="2026-02-28", history=history)
    parsed = parse_narration_response(text)
    assert "soil moisture check" in parsed["cards"]["garden"]


def test_no_alert_when_no_heads_ups():
    """With no heads_ups and no cardiac/menieres, alert text should be empty and level INFO."""
    text = build_narration(MINIMAL_PROCESSED, date_str="2026-02-28")
    parsed = parse_narration_response(text)
    alert = parsed["cards"]["alert"]
    assert alert["level"] == "INFO"
    assert alert["text"] == ""


def test_zh_cards_use_chinese():
    """ZH lang should produce Chinese text in card fields."""
    text = build_narration(MINIMAL_PROCESSED, date_str="2026-02-28", lang="zh-TW")
    parsed = parse_narration_response(text)
    all_text = " ".join(str(v) for v in parsed["cards"].values() if isinstance(v, str))
    assert any('\u4e00' <= c <= '\u9fff' for c in all_text), "Expected Chinese characters in ZH cards"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_fallback_narrator.py -v
```
Expected: FAIL — `---CARDS---` not found in output.

**Step 3: Implement the rewrite**

Full replacement of `narration/fallback_narrator.py`. Key structural changes:
- Add `import json` at top
- Change signature: `build_narration(processed, date_str=None, history=None, lang="en")`
- The existing P1–P7 paragraph generation is **unchanged** (no behaviour change)
- Append at end: `\n\n---METADATA---\n{json}\n\n---CARDS---\n{json}`
- Add `_build_fallback_metadata(processed, history) -> dict`
- Add `_build_fallback_cards(processed, history, lang) -> dict`

**`_build_fallback_metadata()` — fields for history tracking:**

```python
def _build_fallback_metadata(processed: dict, history: list[dict] | None) -> dict:
    current = processed.get("current", {})
    commute = processed.get("commute", {})
    meal_mood_data = processed.get("meal_mood", {})
    climate = processed.get("climate_control", {})
    cardiac = processed.get("cardiac_alert")
    menieres = processed.get("menieres_alert")
    forecast_segs = processed.get("forecast_segments", {})

    at = current.get("AT")
    rain_gear_bool = any(
        "likely" in (seg.get("precip_text") or "").lower()
        for seg in forecast_segs.values()
    )

    morning = commute.get("morning", {})
    evening = commute.get("evening", {})
    commute_am = f"feels like {morning['AT']:.0f}°" if morning.get("AT") else "clear"
    commute_pm = f"feels like {evening['AT']:.0f}°" if evening.get("AT") else "clear"

    suggestions = meal_mood_data.get("top_suggestions", []) or meal_mood_data.get("all_suggestions", [])
    meal = suggestions[0] if suggestions else None

    # Garden: yesterday's topic from history, else seasonal fallback
    yesterday_garden = None
    if history:
        for day in reversed(history):
            g = day.get("metadata", {}).get("garden")
            if g:
                yesterday_garden = g
                break
    month = datetime.now().month
    _seasonal = {
        1: "winter protection", 2: "pre-spring check", 3: "spring planting",
        4: "spring planting", 5: "watering check", 6: "heat protection",
        7: "heat protection", 8: "heat protection", 9: "autumn pruning",
        10: "autumn pruning", 11: "frost prep", 12: "winter protection",
    }
    garden_topic = yesterday_garden or _seasonal.get(month, "soil check")

    mode = climate.get("mode", "")
    climate_str = f"{mode} mode" if mode and mode not in ("Off", "fan", "none", "") else None

    cardiac_triggered = bool(cardiac and isinstance(cardiac, dict) and cardiac.get("triggered"))
    menieres_triggered = bool(
        menieres and isinstance(menieres, dict) and menieres.get("severity") in ("high", "moderate")
    )

    morning_seg = forecast_segs.get("Morning", {})
    afternoon_seg = forecast_segs.get("Afternoon", {})
    m_at, a_at = morning_seg.get("AT"), afternoon_seg.get("AT")
    oneliner = (
        f"Morning starts around {m_at:.0f}°, afternoon at {a_at:.0f}°."
        if m_at and a_at else "Check conditions throughout the day."
    )

    return {
        "wardrobe": f"feels like {at:.0f}°" if at is not None else "check conditions",
        "rain_gear": rain_gear_bool,
        "commute_am": commute_am,
        "commute_pm": commute_pm,
        "meal": meal,
        "outdoor": None,
        "garden": garden_topic,
        "climate": climate_str,
        "cardiac_alert": cardiac_triggered,
        "menieres_alert": menieres_triggered,
        "forecast_oneliner": oneliner,
        "accuracy_grade": "first broadcast",
    }
```

**`_build_fallback_cards()` — card text matching LLM sentence counts:**

Card counts: wardrobe=1, rain_gear=1, commute=2, meals=2, hvac=2, garden=2, outdoor=2, alert=1-2 sentences + level.

```python
def _build_fallback_cards(processed: dict, history: list[dict] | None, lang: str) -> dict:
    is_zh = lang == "zh-TW"
    current = processed.get("current", {})
    commute = processed.get("commute", {})
    morning = commute.get("morning", {})
    evening = commute.get("evening", {})
    climate = processed.get("climate_control", {})
    meal_mood_data = processed.get("meal_mood", {})
    heads_ups = processed.get("heads_ups", [])
    cardiac = processed.get("cardiac_alert")
    menieres = processed.get("menieres_alert")
    outdoor_index = processed.get("outdoor_index", {})
    location_rec = processed.get("location_rec", {})
    top_locations = location_rec.get("top_locations", [])
    recent_locations = processed.get("recent_locations", [])
    forecast_segments = processed.get("forecast_segments", {})
    at = current.get("AT")
    rain_recent = float(current.get("RAIN") or 0) > 0

    # ── Wardrobe (1 sentence) ──────────────────────────────────────────────
    if is_zh:
        if at is None:       wardrobe = "出門前請確認天氣狀況，適當穿著。"
        elif at >= 30:       wardrobe = "天氣炎熱，選擇清涼透氣的輕薄衣物。"
        elif at >= 25:       wardrobe = f"體感 {at:.0f} 度，輕便穿著即可。"
        elif at >= 18:       wardrobe = f"體感 {at:.0f} 度，薄外套或長袖就夠了。"
        elif at >= 12:       wardrobe = "天氣偏涼，建議穿上外套並採用分層穿搭。"
        else:                wardrobe = "天氣寒冷，請做好保暖，多添幾件衣物。"
        if rain_recent: wardrobe = wardrobe.rstrip("。") + "，記得攜帶雨具。"
    else:
        if at is None:       wardrobe = "Check conditions before heading out and dress accordingly."
        elif at >= 30:       wardrobe = "Light, breathable clothing is the call — it's going to feel hot."
        elif at >= 25:       wardrobe = f"Light layers are all you need — feels like {at:.0f}° out there."
        elif at >= 18:       wardrobe = f"A light jacket or long sleeves should do — feels around {at:.0f}°."
        elif at >= 12:       wardrobe = "A proper jacket and layering recommended for the cooler conditions."
        else:                wardrobe = "Bundle up — it's cold outside, layer up well."
        if rain_recent: wardrobe = wardrobe.rstrip(".") + ", and pack rain gear."

    # ── Rain Gear (1 sentence) ─────────────────────────────────────────────
    any_rain_likely = any(
        "likely" in (seg.get("precip_text") or "").lower()
        for seg in forecast_segments.values()
    )
    commute_rain = any("likely" in (leg.get("precip_text") or "").lower() for leg in (morning, evening))
    if is_zh:
        if any_rain_likely or commute_rain: rain_gear = "今天降雨機率偏高，建議帶傘出門。"
        elif rain_recent:                   rain_gear = "地面已濕，備把折疊傘以防萬一。"
        else:                               rain_gear = "今天不需要雨具。"
    else:
        if any_rain_likely or commute_rain: rain_gear = "Rain is likely at some point today — bring an umbrella."
        elif rain_recent:                   rain_gear = "The ground is already wet — tuck a compact umbrella in your bag just in case."
        else:                               rain_gear = "No rain gear needed today."

    # ── Commute (2 sentences) ──────────────────────────────────────────────
    def _commute_sent(leg, label_en, label_zh, default_en, default_zh):
        if not leg:
            return default_zh if is_zh else default_en
        t = leg.get("AT")
        precip = leg.get("precip_text", "")
        hazards = leg.get("hazards", [])
        if is_zh:
            s = label_zh
            if t is not None: s += f"體感 {t:.0f} 度"
            if precip:        s += f"，降雨{precip}"
            if hazards:       s += f"，注意：{hazards[0]}"
            return s + "。"
        else:
            s = label_en
            if t is not None: s += f" feels like {t:.0f}°"
            if precip:        s += f", rain {precip}"
            if hazards:       s += f" — {hazards[0]}"
            return s + "."

    am_sent = _commute_sent(morning, "Morning commute:", "早上通勤：", "Morning commute looks clear.", "早上路況正常。")
    pm_sent = _commute_sent(evening, "Evening commute:", "傍晚返家：", "Evening commute looks clear.", "傍晚路況正常。")
    commute_text = f"{am_sent} {pm_sent}"

    # ── Meals (2 sentences) ────────────────────────────────────────────────
    # processed["top_suggestions"] already excludes recent_meals (via weather_processor)
    mood = meal_mood_data.get("mood", "")
    suggestions = meal_mood_data.get("top_suggestions", []) or meal_mood_data.get("all_suggestions", [])
    if suggestions:
        dish = suggestions[0]
        if is_zh:
            meals = f"今天的天氣氛圍{mood}，推薦來一碗{dish}。這道料理很適合這種天氣，暖胃又對味。"
        else:
            meals = f"The {mood.lower()} weather calls for {dish} today. It's exactly the kind of meal that fits the mood."
    else:
        meals = "今天沒有特別推薦的餐點。" if is_zh else "No specific meal recommendation for today."

    # ── HVAC (2 sentences) ─────────────────────────────────────────────────
    mode = climate.get("mode", "Off")
    est_hours = climate.get("estimated_hours", 0)
    set_temp = climate.get("set_temp")
    notes = climate.get("notes", [])
    if is_zh:
        mode_zh = {"Off": "關閉", "fan": "電風扇", "cooling": "冷氣", "heating": "暖氣",
                   "dehumidify": "除濕機", "heating_optional": "暖氣（選用）"}.get(mode, mode)
        if mode in ("cooling", "heating", "dehumidify"):
            hvac_s1 = f"建議開啟{mode_zh}。"
            hvac_s2 = (f"設定 {set_temp}，預計使用約 {est_hours} 小時。" if set_temp and est_hours
                       else (notes[0] if notes else "請依個人舒適度調整。"))
        elif mode == "heating_optional":
            hvac_s1 = "今天可以考慮短暫使用暖氣或電暖器。"
            hvac_s2 = f"大約 {est_hours} 小時即可，其餘時間多穿一件即可。" if est_hours else "依需求斟酌使用即可。"
        else:
            hvac_s1 = "今天天氣舒適，不需要開冷暖氣。"
            hvac_s2 = "可以開窗通風，享受自然空氣。"
    else:
        if mode in ("cooling", "heating", "dehumidify"):
            mode_en = {"cooling": "AC cooling", "heating": "heating", "dehumidify": "the dehumidifier"}.get(mode, mode)
            hvac_s1 = f"Run {mode_en} today for comfort."
            hvac_s2 = (f"Set to {set_temp}, roughly {est_hours} hours should do it." if set_temp and est_hours
                       else (notes[0] if notes else "Adjust to personal comfort."))
        elif mode == "heating_optional":
            hvac_s1 = "A brief burst of heat in the morning or evening wouldn't hurt."
            hvac_s2 = f"About {est_hours} hours should be plenty — otherwise just layer up." if est_hours else "Otherwise layering up indoors is fine."
        else:
            hvac_s1 = "Comfortable today — no AC or heating required."
            hvac_s2 = "Open the windows and let some fresh air in."
    hvac_text = f"{hvac_s1} {hvac_s2}"

    # ── Garden (2 sentences) ───────────────────────────────────────────────
    yesterday_garden = None
    if history:
        for day in reversed(history):
            g = day.get("metadata", {}).get("garden")
            if g:
                yesterday_garden = g
                break
    month = datetime.now().month
    if is_zh:
        if yesterday_garden:    garden_s1 = f"延續昨天的{yesterday_garden}，今天可以進一步照料一下。"
        elif rain_recent:       garden_s1 = "昨夜有雨，今天適合檢查排水狀況，避免積水。"
        else:                   garden_s1 = "今天是照料花園的好時機，記得檢查土壤濕度。"
        seasonal_zh = {3: "春季適合播種或移植盆栽，把握春雨的滋潤。",
                       4: "春季適合播種或移植盆栽，把握春雨的滋潤。",
                       5: "注意澆水頻率，避免土壤過乾。",
                       6: "夏季注意早晚澆水，避免正午暴曬導致植物缺水。",
                       7: "夏季注意早晚澆水，避免正午暴曬導致植物缺水。",
                       8: "夏季注意早晚澆水，避免正午暴曬導致植物缺水。",
                       9: "秋季適合修剪和施肥，為植物準備越冬。",
                       10: "秋季適合修剪和施肥，為植物準備越冬。",
                       11: "注意霜害防護，為耐寒力弱的植物做好保暖。",
                       12: "冬季減少澆水頻率，注意防寒保溫。",
                       1: "冬季減少澆水頻率，注意防寒保溫。",
                       2: "開春在即，可以開始準備播種所需的土壤和器具。"}
        garden_s2 = seasonal_zh.get(month, "注意土壤濕度和植物狀況。")
    else:
        if yesterday_garden:    garden_s1 = f"Following up on yesterday's {yesterday_garden} — a good day to check in on how things are developing."
        elif rain_recent:       garden_s1 = "After last night's rain, check drainage and avoid overwatering today."
        else:                   garden_s1 = "Good day to give the garden some attention — check soil moisture before watering."
        seasonal_en = {3: "Spring is a good time for sowing or transplanting — make the most of the seasonal moisture.",
                       4: "Spring is a good time for sowing or transplanting — make the most of the seasonal moisture.",
                       5: "Keep an eye on watering frequency as the warmer days arrive.",
                       6: "Water in the early morning or evening to avoid midday heat stress on your plants.",
                       7: "Water in the early morning or evening to avoid midday heat stress on your plants.",
                       8: "Water in the early morning or evening to avoid midday heat stress on your plants.",
                       9: "Autumn is ideal for pruning and fertilising to prepare plants for the cooler months ahead.",
                       10: "Autumn is ideal for pruning and fertilising to prepare plants for the cooler months ahead.",
                       11: "Watch for frost and protect any cold-sensitive plants overnight.",
                       12: "Reduce watering frequency in winter and keep tender plants protected from cold snaps.",
                       1: "Reduce watering frequency in winter and keep tender plants protected from cold snaps.",
                       2: "Spring is just around the corner — start preparing soil and seed trays."}
        garden_s2 = seasonal_en.get(month, "Check soil conditions and adjust care as needed.")
    garden_text = f"{garden_s1} {garden_s2}"

    # ── Outdoor (2 sentences) ──────────────────────────────────────────────
    grade = outdoor_index.get("grade", "")
    best_window = outdoor_index.get("best_window", "")
    parkinsons_safe = outdoor_index.get("parkinsons_safe", True)
    top_activity = outdoor_index.get("top_activity", "")
    pick = next((l for l in top_locations if l.get("name") not in recent_locations), top_locations[0] if top_locations else None)

    if is_zh:
        if grade in ("A", "B"):      verdict = "今天非常適合帶爸爸出門活動。"
        elif grade == "C":           verdict = "今天戶外條件尚可，短暫外出問題不大。"
        elif grade in ("D", "F"):    verdict = "今天戶外條件較差，建議在家進行室內活動。"
        else:                        verdict = "今天戶外條件一般，出門請注意天氣變化。"
        if pick:
            loc_name = pick.get("name", "")
            activity = pick.get("activity", top_activity or "散步")
            pk_note = "地形平坦，適合帕金森氏症患者。" if parkinsons_safe else "請有人陪同出行，注意步道狀況。"
            window_note = f"最佳時段：{best_window}。" if best_window else ""
            outdoor_s2 = f"推薦前往{loc_name}進行{activity}，{pk_note}{window_note}"
        elif best_window:
            outdoor_s2 = f"最佳外出時段為{best_window}，注意帕金森氏症患者的安全。"
        else:
            outdoor_s2 = "外出時請以安全為優先，選擇平坦易行的路線。"
    else:
        if grade in ("A", "B"):      verdict = "Today is a great day to get Dad outside for some fresh air."
        elif grade == "C":           verdict = "Outdoor conditions are manageable today — a short outing should be fine."
        elif grade in ("D", "F"):    verdict = "Not a great day for outdoor activity — better to keep it indoors today."
        else:                        verdict = "Outdoor conditions are average today — use your judgement before heading out."
        if pick:
            loc_name = pick.get("name", "")
            activity = pick.get("activity", top_activity or "walking")
            pk_note = "flat, accessible terrain — Parkinson's friendly." if parkinsons_safe else "go with a companion and watch the terrain."
            window_note = f" Best window: {best_window}." if best_window else ""
            outdoor_s2 = f"{loc_name} is a good pick for {activity} — {pk_note}{window_note}"
        elif best_window:
            outdoor_s2 = f"If heading out, {best_window} is the best window — keep it short and safe."
        else:
            outdoor_s2 = "Stick to flat, familiar routes if heading out, and take it easy."
    outdoor_text = f"{verdict} {outdoor_s2}"

    # ── Alert ──────────────────────────────────────────────────────────────
    cardiac_triggered = bool(cardiac and isinstance(cardiac, dict) and cardiac.get("triggered"))
    menieres_high = bool(menieres and isinstance(menieres, dict) and menieres.get("severity") == "high")
    if cardiac_triggered:
        alert_text = cardiac.get("reason", "Cardiac risk — keep Dad warm and avoid sudden cold exposure.")
        alert_level = "CRITICAL"
    elif menieres_high:
        alert_text = "Ménière's risk today — take it slow and keep medication accessible."
        alert_level = "CRITICAL"
    elif heads_ups:
        alert_text = " ".join(heads_ups[:2])
        alert_level = "WARNING"
    else:
        alert_text = ""
        alert_level = "INFO"

    return {
        "wardrobe": wardrobe,
        "rain_gear": rain_gear,
        "commute": commute_text,
        "meals": meals,
        "hvac": hvac_text,
        "garden": garden_text,
        "outdoor": outdoor_text,
        "alert": {"text": alert_text, "level": alert_level},
    }
```

**Step 4: Run tests**
```bash
pytest tests/test_fallback_narrator.py -v
```
Expected: all 7 tests pass.

**Step 5: Run full test suite**
```bash
pytest tests/ -v
```
Expected: all pass.

**Step 6: Commit**
```bash
git add narration/fallback_narrator.py tests/test_fallback_narrator.py
git commit -m "feat: fallback narrator produces ---CARDS--- and ---METADATA--- blocks, add history/lang support"
```

---

## Verification

1. Temporarily force the narration provider to `TEMPLATE` (set `NARRATION_PROVIDER=TEMPLATE` in env or config) to trigger the fallback path
2. Load the app and trigger a broadcast refresh
3. Open the Lifestyle tab — all 8 cards should display natural-language text (not "System: Off." or "No precipitation gear expected.")
4. Check browser console: `data.alert` should have correct level; garden card text should reference yesterday's garden topic if history exists
5. Switch language to ZH-TW and regenerate — cards should display Chinese text
6. Restore normal LLM provider — confirm the LLM path still works
