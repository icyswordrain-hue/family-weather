import inspect
from narration import llm_summarizer

def test_lifestyle_prompt_requests_chinese():
    """The lifestyle summarizer source must mention Traditional Chinese."""
    src = inspect.getsource(llm_summarizer.summarize_for_lifestyle)
    assert "Traditional Chinese" in src or "繁體中文" in src

def test_aqi_prompt_outputs_chinese():
    """The AQI summarizer source must mention Traditional Chinese output."""
    src = inspect.getsource(llm_summarizer.summarize_aqi_forecast)
    assert "Traditional Chinese" in src or "繁體中文" in src
