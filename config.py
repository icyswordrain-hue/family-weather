"""
config.py — Environment variables and constants for the Family Weather Dashboard.
All secrets are loaded from environment variables (set via Google Secret Manager in Cloud Run).
"""

import os

# ── API Keys ──────────────────────────────────────────────────────────────────
CWA_API_KEY = os.environ.get("CWA_API_KEY", "")
MOENV_API_KEY = os.environ.get("MOENV_API_KEY", "")

# ── Google Cloud ───────────────────────────────────────────────────────────────
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "family-weather-dashboard")
GCP_REGION = os.environ.get("GCP_REGION", "asia-east1")

# ── CWA Endpoints ─────────────────────────────────────────────────────────────
CWA_BASE_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"

# Current conditions — Station observations (O-A0003-001)
CWA_CURRENT_DATASET = "O-A0003-001"
# Banqiao station ID
CWA_STATION_ID = "C0D660"  # Banqiao (板橋) automatic station

# Forecast — Township forecast (F-D0047-071 = New Taipei City townships)
CWA_FORECAST_DATASET = "F-D0047-071"
# Location names for Sanxia and Banqiao townships
CWA_FORECAST_LOCATIONS = ["三峽區", "板橋區"]

# ── MOENV Endpoints ───────────────────────────────────────────────────────────
MOENV_BASE_URL = "https://data.moenv.gov.tw/api/v2"
MOENV_AQI_DATASET = "aqx_p_432"   # Real-time AQI
MOENV_FORECAST_DATASET = "aqx_p_02"  # Daily AQI forecast
# Tucheng station
MOENV_STATION_NAME = "土城"

# ── Location Reference ────────────────────────────────────────────────────────
LOCATION_LAT = 24.9955
LOCATION_LON = 121.4279
TIMEZONE = "Asia/Taipei"

# ── Gemini / Vertex AI ────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_MAX_TOKENS = 4096

# ── Cloud TTS ─────────────────────────────────────────────────────────────────
TTS_LANGUAGE_CODE = "cmn-TW"
TTS_VOICE_NAME = os.environ.get("TTS_VOICE_NAME", "cmn-TW-Chirp3-HD-Aoede")
TTS_KIDS_VOICE_NAME = os.environ.get("TTS_KIDS_VOICE_NAME", "cmn-TW-Chirp3-HD-Charon")
TTS_SPEAKING_RATE = 0.95
TTS_KIDS_SPEAKING_RATE = 1.1

# ── GCS Object Keys ───────────────────────────────────────────────────────────
GCS_HISTORY_KEY = "history/conversation.json"
GCS_BROADCAST_PREFIX = "broadcasts"   # broadcasts/YYYY-MM-DD/
GCS_AUDIO_FILENAME = "broadcast.mp3"
GCS_KIDS_AUDIO_FILENAME = "broadcast_kids.mp3"
GCS_TEXT_FILENAME = "broadcast.json"

# ── Flask ─────────────────────────────────────────────────────────────────────
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
FLASK_PORT = int(os.environ.get("PORT", 8080))
