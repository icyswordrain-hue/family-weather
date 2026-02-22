"""
tts_client.py — Calls Google Cloud Text-to-Speech (Chirp 3: HD) and saves
the resulting audio to Cloud Storage.

Generates two clips:
  1. Full broadcast (all paragraphs) — for the main dashboard
  2. Kids clip (P1 apparent temp + cloud cover only, ≤ 15s) — for the kids view
"""

from __future__ import annotations

import logging
import asyncio
from datetime import datetime

import edge_tts
from google.cloud import texttospeech
from google.cloud import storage

from config import (
    GCS_BUCKET_NAME,
    GCS_BROADCAST_PREFIX,
    GCS_AUDIO_FILENAME,
    TTS_LANGUAGE_CODE,
    TTS_VOICE_NAME,
    TTS_SPEAKING_RATE,
    RUN_MODE,
    LOCAL_DATA_DIR,
    TTS_PROVIDER,
    TTS_TIMEOUT,
)
import config

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
        Dict with 'full_audio_url' (GCS public URL).
    """
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    prefix = f"{GCS_BROADCAST_PREFIX}/{date_str}"

    # Strip ---METADATA--- and anything after it — not meant to be spoken
    narration_text = narration_text.split("---METADATA---")[0].strip()

    if config.TTS_PROVIDER == "EDGE":
        return _generate_edge_audio(narration_text, date_str)

    try:
        if RUN_MODE == "LOCAL" and config.GEMINI_API_KEY:
            # Try using API Key if in LOCAL mode and key is available
            from google.api_core.client_options import ClientOptions
            options = ClientOptions(api_key=config.GEMINI_API_KEY)
            tts_client = texttospeech.TextToSpeechClient(client_options=options)
        else:
            tts_client = texttospeech.TextToSpeechClient()
    except Exception as exc:
        if RUN_MODE == "LOCAL":
            logger.warning("Google TTS credentials missing/invalid (%s). Falling back to Edge TTS.", exc)
            return _generate_edge_audio(narration_text, date_str)
        raise exc

    if RUN_MODE == "CLOUD":
        gcs_client = storage.Client()
        bucket = gcs_client.bucket(GCS_BUCKET_NAME)
    else:
        bucket = None # Not used in LOCAL or MODAL mode

    # ── Full broadcast ────────────────────────────────────────────────────────
    full_audio = _synthesize(
        client=tts_client,
        text=narration_text,
        voice_name=TTS_VOICE_NAME,
        speaking_rate=TTS_SPEAKING_RATE,
    )
    full_blob_name = f"{prefix}/{GCS_AUDIO_FILENAME}"
    if RUN_MODE in ["LOCAL", "MODAL"]:
        full_url = _save_local_audio(full_audio, full_blob_name)
    else:
        # pyre-ignore[6]: bucket is not None in CLOUD mode
        full_url = _upload_to_gcs(bucket, full_blob_name, full_audio)

    logger.info("TTS complete. Full: %s", full_url)
    return {
        "full_audio_url": full_url,
    }

def _synthesize(
    client: texttospeech.TextToSpeechClient,
    text: str,
    voice_name: str,
    speaking_rate: float,
) -> bytes:
    """
    Synthesize speech and return raw MP3 bytes.
    Handles text > 5000 characters by splitting into safe chunks.
    """
    # 5000-character limit per request. Use 4000 to be safe with multi-byte chars.
    MAX_CHARS = 4000
    
    if len(text) <= MAX_CHARS:
        return _synthesize_chunk(client, text, voice_name, speaking_rate)

    logger.info("Text length (%d) exceeds limit. Splitting into chunks...", len(text))
    
    # 1. Split into paragraphs
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    
    # 2. Further split paragraphs if any are too long
    safe_paragraphs: list[str] = []
    for p in paragraphs:
        if len(p) <= MAX_CHARS:
            safe_paragraphs.append(p)
        else:
            # Split by sentence boundaries if a paragraph is too long
            import re
            sentences = re.split(r'([.。!！?？])', p)
            current_p = ""
            for i in range(0, len(sentences), 2):
                sent = sentences[i]
                punct = sentences[i+1] if i+1 < len(sentences) else ""
                combined = sent + punct
                if len(current_p) + len(combined) < MAX_CHARS:
                    current_p += combined
                else:
                    if current_p:
                        safe_paragraphs.append(current_p)
                    current_p = combined
            if current_p:
                safe_paragraphs.append(current_p)
                
    # 2b. Safety check: Force-split any paragraph that is STILL too long (e.g. no punctuation)
    final_paragraphs: list[str] = []
    for p in safe_paragraphs:
        if len(p) <= MAX_CHARS:
            final_paragraphs.append(p)
        else:
            # Hard split by length
            for i in range(0, len(p), MAX_CHARS):
                final_paragraphs.append(p[i : i + MAX_CHARS])

    # 3. Combine safe paragraphs into chunks
    chunks: list[str] = []
    current_chunk = ""
    for p in final_paragraphs:
        if len(current_chunk) + len(p) + 2 < MAX_CHARS:
            current_chunk += ("\n\n" + p) if current_chunk else p
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = p
    if current_chunk:
        chunks.append(current_chunk)

    # 4. Synthesize each chunk
    audio_contents: list[bytes] = []
    for i, chunk in enumerate(chunks):
        logger.info("Synthesizing chunk %d/%d (%d chars)...", i+1, len(chunks), len(chunk))
        audio_contents.append(_synthesize_chunk(client, chunk, voice_name, speaking_rate))
    
    return b"".join(audio_contents)


def _synthesize_chunk(
    client: texttospeech.TextToSpeechClient,
    text: str,
    voice_name: str,
    speaking_rate: float,
) -> bytes:
    """Internal helper to synthesize a single chunk of text."""
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
        timeout=float(TTS_TIMEOUT),
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




def _save_local_audio(audio_bytes: bytes, blob_name: str) -> str:
    """
    Save audio bytes to local file system and return a local URL.
    blob_name is like 'broadcasts/2023-10-27/broadcast.mp3'
    """
    import os
    # Construct local path: local_data/broadcasts/2023-10-27/broadcast.mp3
    local_path = os.path.join(LOCAL_DATA_DIR, blob_name.replace("/", os.sep))
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    
    with open(local_path, "wb") as f:
        f.write(audio_bytes)
        
    logger.info("Saved local audio to %s", local_path)
    # Return a URL that the Flask app can serve
    # We will map /local_assets/ to LOCAL_DATA_DIR
    return f"/local_assets/{blob_name}"


# ── Edge TTS Fallback ────────────────────────────────────────────────────────

def _generate_edge_audio(narration_text: str, date_str: str) -> dict[str, str]:
    """
    Generate full and kids audio using Edge TTS (free, no credentials).
    """
    logger.info("Generating Edge TTS audio...")
    prefix = f"{GCS_BROADCAST_PREFIX}/{date_str}"
    
    # 1. Full Broadcast
    # Use Avri (Male) or Ava (Female) - Ava is a good neutral-ish modern voice
    # or "en-US-AndrewNeural" for a friendly male voice akin to the "Dad" persona?
    # Let's stick to a clean female voice as default, or use Andrew for variety.
    # The user asked for "options", we'll default to Ava.
    full_voice = "en-US-AvaNeural"
    full_audio = _synthesize_edge(narration_text, full_voice, rate="+0%")
    
    full_blob_name = f"{prefix}/{GCS_AUDIO_FILENAME}"
    full_url = _save_local_audio(full_audio, full_blob_name)
    
    logger.info("Edge TTS complete. Full: %s", full_url)
    return {
        "full_audio_url": full_url,
    }


def _synthesize_edge(text: str, voice: str, rate: str = "+0%") -> bytes:
    """Synchronous wrapper for async Edge TTS."""
    try:
        return asyncio.run(asyncio.wait_for(_synthesize_edge_async(text, voice, rate), timeout=TTS_TIMEOUT))
    except asyncio.TimeoutError:
        logger.error("Edge TTS synthesis timed out")
        return b""
    except Exception as exc:
        logger.error("Edge TTS failed: %s", exc)
        # return silent or empty bytes? 
        return b""


async def _synthesize_edge_async(text: str, voice: str, rate: str) -> bytes:
    # edge-tts doesn't have a direct timeout arg in Communicate, 
    # so we use asyncio.wait_for
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    audio_data = b""
    try:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
    except asyncio.TimeoutError:
        logger.error("Edge TTS timed out after %d seconds", TTS_TIMEOUT)
        return b""
    return audio_data
