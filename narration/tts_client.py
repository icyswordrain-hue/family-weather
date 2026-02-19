"""
tts_client.py — Calls Google Cloud Text-to-Speech (Chirp 3: HD) and saves
the resulting audio to Cloud Storage.

Generates two clips:
  1. Full broadcast (all paragraphs) — for the main dashboard
  2. Kids clip (P1 apparent temp + cloud cover only, ≤ 15s) — for the kids view
"""

from __future__ import annotations

import logging
from datetime import datetime

from google.cloud import texttospeech
from google.cloud import storage

from config import (
    GCS_BUCKET_NAME,
    GCS_BROADCAST_PREFIX,
    GCS_AUDIO_FILENAME,
    GCS_KIDS_AUDIO_FILENAME,
    TTS_LANGUAGE_CODE,
    TTS_VOICE_NAME,
    TTS_KIDS_VOICE_NAME,
    TTS_SPEAKING_RATE,
    TTS_KIDS_SPEAKING_RATE,
)

logger = logging.getLogger(__name__)


def synthesize_and_upload(
    narration_text: str,
    date_str: str | None = None,
) -> dict[str, str]:
    """
    Synthesize the full narration and a short kids clip, upload both to GCS.

    Args:
        narration_text: Full broadcast narration from Gemini.
        date_str:       ISO date string (YYYY-MM-DD). Defaults to today.

    Returns:
        Dict with 'full_audio_url' and 'kids_audio_url' (GCS public URLs).
    """
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    prefix = f"{GCS_BROADCAST_PREFIX}/{date_str}"

    tts_client = texttospeech.TextToSpeechClient()
    gcs_client = storage.Client()
    bucket = gcs_client.bucket(GCS_BUCKET_NAME)

    # ── Full broadcast ────────────────────────────────────────────────────────
    full_audio = _synthesize(
        client=tts_client,
        text=narration_text,
        voice_name=TTS_VOICE_NAME,
        speaking_rate=TTS_SPEAKING_RATE,
    )
    full_blob_name = f"{prefix}/{GCS_AUDIO_FILENAME}"
    full_url = _upload_to_gcs(bucket, full_blob_name, full_audio)

    # ── Kids clip (first ~60 words of narration, roughly 15 seconds) ─────────
    kids_text = _make_kids_text(narration_text)
    kids_audio = _synthesize(
        client=tts_client,
        text=kids_text,
        voice_name=TTS_KIDS_VOICE_NAME,
        speaking_rate=TTS_KIDS_SPEAKING_RATE,
    )
    kids_blob_name = f"{prefix}/{GCS_KIDS_AUDIO_FILENAME}"
    kids_url = _upload_to_gcs(bucket, kids_blob_name, kids_audio)

    logger.info("TTS complete. Full: %s | Kids: %s", full_url, kids_url)
    return {
        "full_audio_url": full_url,
        "kids_audio_url": kids_url,
    }


def _synthesize(
    client: texttospeech.TextToSpeechClient,
    text: str,
    voice_name: str,
    speaking_rate: float,
) -> bytes:
    """Synthesize speech and return raw MP3 bytes."""
    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code=TTS_LANGUAGE_CODE,
        name=voice_name,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=speaking_rate,
    )

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config,
    )
    return response.audio_content


def _upload_to_gcs(
    bucket: storage.Bucket,
    blob_name: str,
    audio_bytes: bytes,
) -> str:
    """Upload bytes to GCS and return the public URL."""
    blob = bucket.blob(blob_name)
    blob.upload_from_string(audio_bytes, content_type="audio/mpeg")
    # Return the GCS URL (authenticated access via signed URL or IAP in prod)
    return f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{blob_name}"


def _make_kids_text(narration: str) -> str:
    """
    Extract a short, kid-friendly clip from the narration.
    Targets approximately 15 seconds of speech (~50–60 words).
    """
    words = narration.split()
    short = " ".join(words[:60])
    # Trim to last sentence boundary
    for punct in ("。", ".", "!", "！", "?", "？"):
        last = short.rfind(punct)
        if last > 20:
            short = short[: last + 1]
            break
    return short
