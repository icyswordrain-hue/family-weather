"""
config.py — Environment variables and constants for the Family Weather Dashboard.
All secrets are loaded from environment variables (set via Google Secret Manager in Cloud Run).
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Local Execution Mode ──────────────────────────────────────────────────────
RUN_MODE = os.environ.get("RUN_MODE", "CLOUD").upper() # "LOCAL" or "CLOUD"
LOCAL_DATA_DIR = os.environ.get("LOCAL_DATA_DIR", "local_data")

# ── API Keys ──────────────────────────────────────────────────────────────────
CWA_API_KEY = os.environ.get("CWA_API_KEY", "").strip()
MOENV_API_KEY = os.environ.get("MOENV_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# ── Google Cloud ───────────────────────────────────────────────────────────────
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "family-weather-dashboard")
GCP_REGION = os.environ.get("GCP_REGION", "asia-east1")

# ── CWA Endpoints ─────────────────────────────────────────────────────────────
CWA_BASE_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"

# Current conditions — Station observations (O-A0001-001)
CWA_CURRENT_DATASET = "O-A0001-001"
CWA_STATION_ID = "C0AJ80"  # Banqiao (Real) - was C0AC70 (Xinyi)

# Forecast — Township forecast (F-D0047-071 = New Taipei City townships)
CWA_FORECAST_DATASET = "F-D0047-071"
# Location names for Sanxia and Banqiao townships
CWA_FORECAST_LOCATIONS = ["三峽區", "板橋區"]

# ── MOENV Endpoints ───────────────────────────────────────────────────────────
MOENV_BASE_URL = "https://data.moenv.gov.tw/api/v2"
MOENV_AQI_DATASET = "aqx_p_432"   # Real-time AQI
MOENV_FORECAST_DATASET = "AQF_P_01"  # 3-Day Regional Forecast
MOENV_FORECAST_AREA = "北部"   # Northern Air Quality Zone (API uses short name)
# Tucheng station
MOENV_STATION_NAME = "土城"

# ── Location Reference ────────────────────────────────────────────────────────
LOCATION_LAT = 24.9955
LOCATION_LON = 121.4279
TIMEZONE = "Asia/Taipei"

# ── Anthropic Claude ──────────────────────────────────────────────────────────
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-3-haiku-20240307")
GEMINI_MAX_TOKENS = 8192  # max_tokens for Claude narration output

# ── Google Cloud Credentials (Local) ──────────────────────────────────────────
_LOCAL_KEY_PATH = os.path.join(os.getcwd(), LOCAL_DATA_DIR, "service-account.json")
if RUN_MODE == "LOCAL" and os.path.exists(_LOCAL_KEY_PATH):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _LOCAL_KEY_PATH

# ── Cloud TTS ─────────────────────────────────────────────────────────────────
TTS_LANGUAGE_CODE = "en-US"
TTS_VOICE_NAME = os.environ.get("TTS_VOICE_NAME", "en-US-Neural2-D")
TTS_KIDS_VOICE_NAME = os.environ.get("TTS_KIDS_VOICE_NAME", "en-US-Neural2-F")
TTS_SPEAKING_RATE = 0.95
TTS_KIDS_SPEAKING_RATE = 1.1

# Default to Google if credentials exist, otherwise Edge
_HAS_GCP_CREDS = "GOOGLE_APPLICATION_CREDENTIALS" in os.environ
TTS_PROVIDER = os.environ.get("TTS_PROVIDER", "GOOGLE" if _HAS_GCP_CREDS else "EDGE")

# ── GCS Object Keys ───────────────────────────────────────────────────────────
GCS_HISTORY_KEY = "history/conversation.json"
GCS_BROADCAST_PREFIX = "broadcasts"   # broadcasts/YYYY-MM-DD/
GCS_AUDIO_FILENAME = "broadcast.mp3"
GCS_KIDS_AUDIO_FILENAME = "broadcast_kids.mp3"
GCS_TEXT_FILENAME = "broadcast.json"

# ── Flask ─────────────────────────────────────────────────────────────────────
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
FLASK_PORT = int(os.environ.get("PORT", 8080))
