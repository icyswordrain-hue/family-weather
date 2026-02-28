# AQI Forecast Decoupling Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Completely decouple the "Tomorrow's Air Quality" dashboard feature from the LLM summarizer by using deterministic regex extraction and standard localization.

**Architecture:** We will replace the non-deterministic `summarize_aqi_forecast` LLM call with a robust regex extractor in `weather_processor.py`. The regex will pinpoint the specific condition for the "Northern" (北部) air quality zone from the raw MOENV API text. This extracted localized status (e.g., "良好", "普通") will then be mapped to standardized translated sentences using predefined language dictionaries, ensuring consistent, fast, and free output in both English and Traditional Chinese.

**Tech Stack:** Python, `re` (regex patterns)

---

### Task 1: Implement Regex Extractor and Localizer

**Files:**
- Modify: `data/weather_processor.py` (add translation dictionaries and parsing logic)

**Step 1: Define the structured mappings**
At the top of `data/weather_processor.py`, define the mapping from Chinese terms to standard statuses:
```python
AQI_STATUS_MAP = {
    "良好": {"en": "Expected to be Good", "zh_TW": "預測為「良好」"},
    "普通": {"en": "Expected to be Moderate", "zh_TW": "預測為「普通」"},
    "橘色提醒": {"en": "Expected to be Unhealthy for Sensitive Groups", "zh_TW": "預測為「橘色提醒」"},
    "紅害": {"en": "Expected to be Unhealthy", "zh_TW": "預測為「紅害」"},
    "紫爆": {"en": "Expected to be Very Unhealthy", "zh_TW": "預測為「紫爆」"},
}

def extract_aqi_summary(content: str, lang: str = "zh_TW") -> str:
    import re
    if not content:
        return "No forecast data available." if lang == "en" else "暫無預測資料。"
    
    # Try to find the status for Northern region (北部)
    match = re.search(r'北部[^「]*「([^」]+)」', content)
    if match:
        status_zh = match.group(1)
        if status_zh in AQI_STATUS_MAP:
            if lang == "en":
                return f"Tomorrow's air quality is {AQI_STATUS_MAP[status_zh]['en']}."
            else:
                return f"明日北部空氣品質{AQI_STATUS_MAP[status_zh]['zh_TW']}等級。"
                
    # Fallback to a truncated version of the raw content if regex fails
    return content[:100] + "..." if len(content) > 100 else content
```

**Step 2: Integrate into the processor**
Update the `process` function in `data/weather_processor.py` to append `summary_en` and `summary_zh` to the `aqi_forecast` dictionary before it's returned.

```python
# In `process()` right before returning:
processed_data["aqi_forecast"]["summary_en"] = extract_aqi_summary(processed_data["aqi_forecast"].get("content", ""), "en")
processed_data["aqi_forecast"]["summary_zh"] = extract_aqi_summary(processed_data["aqi_forecast"].get("content", ""), "zh_TW")
```

**Step 3: Test the extraction manually**
Run the existing script to make sure the weather processor generates the new fields safely:
Run: `python -c "from data.weather_processor import process; print(process()['aqi_forecast'])"`
Expected: Output dict contains `"summary_en"` and `"summary_zh"`.

---

### Task 2: Remove LLM Dependencies

**Files:**
- Modify: `backend/pipeline.py`
- Modify: `narration/llm_summarizer.py`

**Step 1: Disconnect `summarize_aqi_forecast` from pipeline**
In `backend/pipeline.py`, remove the parallel execution of `summarize_aqi_forecast`.
```python
# Remove these imports and lines in run_parallel_summarization:
# aqi_future = executor.submit(summarize_aqi_forecast, aqi_forecast_raw.get("content", ""), lang)
# aqi_summary = aqi_future.result()
```
The `aqi_summary` field is no longer needed in the result dictionary, because the frontend fetches the localized fields `summary_en` and `summary_zh` generated directly by the `weather_processor`.

**Step 2: Clean up the LLM code**
In `narration/llm_summarizer.py`, completely delete the `summarize_aqi_forecast` function, as it is replaced by our fast regex parser.

**Step 3: Update Frontend Reference**
In `web/static/app.js`, ensure the AQI forecast rendering block defaults to the pre-generated localized summary instead of attempting to use `aqi.content` directly or waiting for the narration API.
```javascript
// Change in renderOverviewView:
const aqiSummary = lang === 'en' ? aqi.summary_en : aqi.summary_zh;
aqiForecastEl.textContent = aqiSummary || aqi.content || 'N/A';
```

**Step 4: Run full application integration test**
Run: `python app.py` and trigger a dashboard refresh.
Expected: The "Tomorrow's Air Quality" section renders a translated string instantly without LLM involvement, improving latency and eliminating costs.
