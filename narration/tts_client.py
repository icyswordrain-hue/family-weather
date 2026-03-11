"""
tts_client.py — Calls Google Cloud Text-to-Speech (Chirp 3: HD) and saves
the resulting audio to Cloud Storage.

Generates two clips:
  1. Full broadcast (all paragraphs) — for the main dashboard
  2. Kids clip (P1 apparent temp + cloud cover only, ≤ 15s) — for the kids view
"""

import hashlib, io, asyncio, logging
from pathlib import Path
from config import RUN_MODE, GCS_BUCKET_NAME, GCS_AUDIO_PREFIX

log = logging.getLogger(__name__)

VOICES = {
    "zh-TW": "zh-TW-HsiaoChenNeural",
    "en":    "en-US-GuyNeural",
}

def tts_cache_key(text: str, lang: str, date: str, slot: str) -> str:
    h = hashlib.md5(text.strip().encode()).hexdigest()[:12]
    return f"{GCS_AUDIO_PREFIX}/{date}/{slot}_{lang}_{h}.mp3"


def _upload_to_gcs(audio_bytes: bytes, gcs_path: str) -> str:
    from google.cloud import storage
    blob = storage.Client().bucket(GCS_BUCKET_NAME).blob(gcs_path)
    blob.upload_from_string(audio_bytes, content_type="audio/mpeg")
    return blob.public_url


def _render_edge_tts(text: str, lang: str) -> bytes:
    import edge_tts
    buf = io.BytesIO()
    async def _collect():
        communicate = edge_tts.Communicate(text, VOICES[lang])
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
    asyncio.run(_collect())
    return buf.getvalue()


def synthesise_with_cache(text: str, lang: str, date: str, slot: str) -> str:
    """Returns /api/audio/... URL (modal), public GCS URL (cloud), or local path (local). Checks cache first."""
    from config import LOCAL_DATA_DIR
    gcs_path = tts_cache_key(text, lang, date, slot)
    # gcs_path = "audio/{date}/{slot}_{lang}_{hash}.mp3"
    rel_path = gcs_path[len("audio/"):]  # "{date}/{slot}_{lang}_{hash}.mp3"

    if RUN_MODE == "MODAL":
        local_path = Path(LOCAL_DATA_DIR) / gcs_path  # /data/audio/{date}/...
        if local_path.exists():
            log.info("TTS cache hit (volume): %s", local_path)
            return f"/api/audio/{rel_path}"
        audio = _render_edge_tts(text, lang)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(audio)
        return f"/api/audio/{rel_path}"

    if RUN_MODE == "CLOUD":
        from google.cloud import storage
        blob = storage.Client().bucket(GCS_BUCKET_NAME).blob(gcs_path)
        if blob.exists():
            log.info(f"TTS cache hit: {gcs_path}")
            return blob.public_url
        audio = _render_edge_tts(text, lang)
        return _upload_to_gcs(audio, gcs_path)

    # LOCAL mode
    audio = _render_edge_tts(text, lang)
    out = Path("local_data/audio") / Path(gcs_path).name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(audio)
    return f"/local_assets/audio/{out.name}"
