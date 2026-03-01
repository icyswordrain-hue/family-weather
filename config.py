"""
config.py — Environment variables and constants for the Family Weather Dashboard.
All secrets are loaded from environment variables (set via Google Secret Manager in Cloud Run).
"""

import os
from datetime import timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv

CST = timezone(timedelta(hours=8))

load_dotenv(override=True)

# ── Local Execution Mode ──────────────────────────────────────────────────────
RUN_MODE = os.environ.get("RUN_MODE", "CLOUD").upper() # "LOCAL", "CLOUD", or "MODAL"

if RUN_MODE == "MODAL":
    LOCAL_DATA_DIR = os.environ.get("LOCAL_DATA_DIR", "/data")
else:
    LOCAL_DATA_DIR = os.environ.get("LOCAL_DATA_DIR", "local_data")

STATION_HISTORY_PATH = Path(
    os.environ.get("STATION_HISTORY_PATH", os.path.join(LOCAL_DATA_DIR, "station_history.jsonl"))
)
STATION_HISTORY_DAYS = int(os.environ.get("STATION_HISTORY_DAYS", 7))

# ── API Keys ──────────────────────────────────────────────────────────────────
CWA_API_KEY = os.environ.get("CWA_API_KEY", "").strip()
MOENV_API_KEY = os.environ.get("MOENV_API_KEY", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# ── Google Cloud ───────────────────────────────────────────────────────────────
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "family-weather-dashboard")
GCP_REGION = os.environ.get("GCP_REGION", "asia-east1")

# ── CWA Data ────────────────────────────────────────────────────────────────────
CWA_BASE_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
# AI AGENT NOTE: For a list of all verified station IDs, see docs/reference/stations.txt
# If you need to know exactly what elements the 7-day API returns, see docs/reference/cwa_7day_elements.json
CWA_STATION_ID = "466881"  # Banqiao (Manual) - Full synoptic station (Vis, Cloud, WxText) + Auto sensors
CWA_CURRENT_DATASET = "O-A0003-001" # Manual stations

# AI AGENT NOTE: Correct Dataset IDs for New Taipei City (F-D0047 Series)
# Per docs/reference/API_QUIRKS.md:
# - F-D0047-069: 36-hour forecast (hourly point-in-time slots). Feeds the 24h segment view.
# - F-D0047-071: 7-day forecast (12-hour period slots). Feeds the weekly timeline.
CWA_FORECAST_DATASET = "F-D0047-069" # New Taipei City Township Forecast (36h segments)
CWA_FORECAST_7DAY_DATASET = "F-D0047-071" # New Taipei City Township Forecast (7-day)
# Visibility data

# Location names for Sanxia and Banqiao townships
CWA_FORECAST_LOCATIONS = ["三峽區", "板橋區"]

# ── MOENV Endpoints ───────────────────────────────────────────────────────────
MOENV_BASE_URL = "https://data.moenv.gov.tw/api/v2"

# AI AGENT NOTE: MOENV AQI Forecast Structure vs Realtime Structure
# Real-time datasets (aqx_p_432) use a list of objects per station.
# Forecast datasets (AQF_P_01) provide area-wide narratives (e.g., "北部") rather than per-station.
MOENV_AQI_DATASET = "aqx_p_432"   # Real-time AQI
MOENV_FORECAST_DATASET = "AQF_P_01"  # 3-Day Regional Forecast
MOENV_FORECAST_AREA = "北部"   # Northern Air Quality Zone (API uses short name)
# Tucheng station
MOENV_STATION_NAME = "土城"

# ── Location Reference ────────────────────────────────────────────────────────
LOCATION_LAT = 24.9955
LOCATION_LON = 121.4279
# AI AGENT NOTE: Timezone — This value is the single source of truth for the
# UTC+8 assumption used throughout the codebase.  CWA API timestamps carry
# "+08:00"; they are stripped to naive wall-clock datetimes and compared against
# naive datetime.now() in weather_processor._segment_forecast.  Both sides of
# that comparison are only equal when the server process itself runs in
# Asia/Taipei.  If you ever change this value, audit every .replace(tzinfo=None)
# call and every datetime.now() call in data/ and update API_QUIRKS.md accordingly.
# For new code that needs the current Taipei time, use the explicit-offset pattern
# from fetch_moenv.fetch_forecast_aqi: datetime.now(timezone(timedelta(hours=8)))
TIMEZONE = "Asia/Taipei"  # UTC+8 — all forecast segment logic depends on this

# ── Google Gemini ─────────────────────────────────────────────────────────
GEMINI_PRO_MODEL = os.environ.get("GEMINI_PRO_MODEL",   "gemini-2.0-pro-exp")
GEMINI_FLASH_MODEL = os.environ.get("GEMINI_FLASH_MODEL",  "gemini-2.0-flash")
GEMINI_MAX_TOKENS = 4096
# ── Anthropic Claude ──────────────────────────────────────────────────────
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
CLAUDE_FALLBACK_MODEL = os.environ.get("CLAUDE_FALLBACK_MODEL", "claude-haiku-4-5-20251001")
CLAUDE_MAX_TOKENS = 4096
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

# ── Pipeline Behaviour ────────────────────────────────────────────────────────
HISTORY_DAYS = int(os.environ.get("HISTORY_DAYS", 3))
REGEN_CYCLE_DAYS = int(os.environ.get("REGEN_CYCLE_DAYS", 14))

# ── Processor Thresholds ──────────────────────────────────────────────────────
MEAL_FALLBACK_DISH = "Sandwich"
AQI_ALERT_THRESHOLD = 100          # heads-up + outdoor/windows alert
CLIMATE_TEMP_HOT = 30              # °C — cooling needed
CLIMATE_TEMP_WARM_UPPER = 30       # °C — optional AC upper bound
CLIMATE_TEMP_WARM_LOWER = 26       # °C — optional AC lower bound
CLIMATE_TEMP_COLD_UPPER = 18       # °C — optional heating upper bound
CLIMATE_TEMP_COLD_LOWER = 15       # °C — optional heating lower bound
CLIMATE_TEMP_FREEZE = 14           # °C — definite heating needed
CLIMATE_RH_HOT = 70               # % — hot & humid threshold
CLIMATE_RH_WARM = 60              # % — warm & pleasant lower RH bound
CLIMATE_RH_AC_TRIGGER = 80        # % — high RH triggers cooling/AC

# ── Timeouts (Seconds) ──────────────────────────────────────────────────
CWA_TIMEOUT = 20
MOENV_TIMEOUT = 20
NARRATION_TIMEOUT_PRO = 240
NARRATION_TIMEOUT_FLASH = 90
TTS_TIMEOUT = 30

# ── Narration Provider ────────────────────────────────────────────────────
# Options: "GEMINI", "CLAUDE", "TEMPLATE"
NARRATION_PROVIDER = os.environ.get("NARRATION_PROVIDER", "CLAUDE").upper()

# ── Google Cloud Credentials (Local) ──────────────────────────────────────────
_LOCAL_KEY_PATH = os.path.join(os.getcwd(), LOCAL_DATA_DIR, "service-account.json")
if RUN_MODE == "LOCAL" and os.path.exists(_LOCAL_KEY_PATH):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _LOCAL_KEY_PATH

# ── Cloud TTS ─────────────────────────────────────────────────────────────────
# Per-language TTS voice defaults (overridable via env)
TTS_VOICE_EN = os.environ.get("TTS_VOICE_NAME", "en-US-Neural2-D")
TTS_VOICE_ZH = os.environ.get("TTS_VOICE_ZH", "zh-TW-Wavenet-B")

# Legacy aliases — used where language selection isn't yet implemented
TTS_LANGUAGE_CODE = "zh-TW"
TTS_VOICE_NAME = TTS_VOICE_ZH
TTS_SPEAKING_RATE = 0.95

# Default to Google if credentials exist, otherwise Edge
_HAS_GCP_CREDS = "GOOGLE_APPLICATION_CREDENTIALS" in os.environ
TTS_PROVIDER = os.environ.get("TTS_PROVIDER", "GOOGLE" if _HAS_GCP_CREDS else "EDGE")

# ── GCS Object Keys ───────────────────────────────────────────────────────────
GCS_HISTORY_KEY = "history/conversation.json"
GCS_BROADCAST_PREFIX = "broadcasts"   # broadcasts/YYYY-MM-DD/
GCS_AUDIO_FILENAME = "broadcast.mp3"
GCS_TEXT_FILENAME = "broadcast.json"

# ── Flask ─────────────────────────────────────────────────────────────────────
if RUN_MODE == "LOCAL":
    FLASK_DEBUG = True
else:
    FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
FLASK_PORT = int(os.environ.get("PORT", 8080))

# ── Outdoor Index Rules ───────────────────────────────────────────────────────
OUTDOOR_TEMP_EXTREME_HOT = 36
OUTDOOR_TEMP_HOT = 32
OUTDOOR_TEMP_COLD = 12
OUTDOOR_TEMP_EXTREME_COLD = 8
OUTDOOR_RH_VERY_HIGH = 90
OUTDOOR_RH_HIGH = 85
OUTDOOR_AQI_UNHEALTHY = 150
OUTDOOR_AQI_SENSITIVE = 100
OUTDOOR_UVI_EXTREME = 11
OUTDOOR_UVI_VERY_HIGH = 8
OUTDOOR_VIS_VERY_POOR = 1.0
OUTDOOR_VIS_POOR = 2.0

# ── GCS & Audio Config ────────────────────────────────────────────────────────
GCS_AUDIO_PREFIX   = os.getenv("GCS_AUDIO_PREFIX", "audio")
GCS_REGEN_PATH     = os.getenv("GCS_REGEN_PATH", "regen/regen.json")
DESKTOP_TTS_URL    = os.getenv("DESKTOP_TTS_URL")
DESKTOP_TTS_SECRET = os.getenv("DESKTOP_TTS_SECRET")
DESKTOP_TTS_TIMEOUT = int(os.getenv("DESKTOP_TTS_TIMEOUT", "8"))
