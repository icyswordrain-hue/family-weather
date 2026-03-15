"""
tts_client.py — Calls Google Cloud Text-to-Speech (Chirp 3: HD) and saves
the resulting audio to Cloud Storage.

Generates two clips:
  1. Full broadcast (all paragraphs) — for the main dashboard
  2. Kids clip (P1 apparent temp + cloud cover only, ≤ 15s) — for the kids view
"""

import hashlib, io, asyncio, logging, os, re
from datetime import date, timedelta
from pathlib import Path
from config import (RUN_MODE, GCS_BUCKET_NAME, GCS_AUDIO_PREFIX,
                     TTS_PROVIDER, TTS_VOICE_EN, TTS_VOICE_ZH, TTS_SPEAKING_RATE)

log = logging.getLogger(__name__)

VOICES = {
    "zh-TW": "zh-TW-HsiaoChenNeural",
    "en":    "en-US-JennyNeural",
}

def tts_cache_key(text: str, lang: str, date: str, slot: str) -> str:
    h = hashlib.md5(text.strip().encode()).hexdigest()[:12]
    return f"{GCS_AUDIO_PREFIX}/{date}/{slot}_{lang}_{h}.mp3"


def _upload_to_gcs(audio_bytes: bytes, gcs_path: str) -> str:
    from google.cloud import storage
    blob = storage.Client().bucket(GCS_BUCKET_NAME).blob(gcs_path)
    blob.upload_from_string(audio_bytes, content_type="audio/mpeg")
    log.info("TTS uploaded to GCS: %s (%d bytes) → %s", gcs_path, len(audio_bytes), blob.public_url)
    return blob.public_url


def _render_google_tts(text: str, lang: str) -> bytes:
    from google.cloud import texttospeech
    client = texttospeech.TextToSpeechClient()
    voice_name = TTS_VOICE_ZH if lang == "zh-TW" else TTS_VOICE_EN
    # Derive lang_code from the voice name prefix (e.g. "en-GB-Neural2-C" → "en-GB")
    lang_code = "cmn-TW" if lang == "zh-TW" else voice_name.rsplit("-", 2)[0]
    resp = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=texttospeech.VoiceSelectionParams(language_code=lang_code, name=voice_name),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=TTS_SPEAKING_RATE,
            pitch=2.0,
        ),
    )
    return resp.audio_content


def _render_edge_tts(text: str, lang: str) -> bytes:
    import edge_tts
    buf = io.BytesIO()
    async def _collect():
        communicate = edge_tts.Communicate(text, VOICES[lang], pitch="+5Hz")
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        # Inside an existing event loop (e.g. Modal/FastAPI) — run in a new thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(asyncio.run, _collect()).result()
    else:
        asyncio.run(_collect())
    return buf.getvalue()


def _render_tts(text: str, lang: str) -> bytes:
    has_gcp = "GOOGLE_APPLICATION_CREDENTIALS" in os.environ
    log.info("TTS render: provider=%s, has_gcp=%s, text_len=%d, lang=%s",
             TTS_PROVIDER, has_gcp, len(text), lang)
    # Edge TTS primary (free, no API key); Google Cloud TTS as fallback
    try:
        audio = _render_edge_tts(text, lang)
        log.info("Edge TTS succeeded (%d bytes)", len(audio))
        return audio
    except Exception:
        log.warning("Edge TTS failed, falling back to Google Cloud TTS", exc_info=True)
    if has_gcp:
        try:
            audio = _render_google_tts(text, lang)
            log.info("Google Cloud TTS succeeded (%d bytes)", len(audio))
            return audio
        except Exception:
            log.error("Google Cloud TTS also failed", exc_info=True)
            raise
    raise RuntimeError("Edge TTS failed and no GCP credentials for fallback")


def _extract_lang_from_filename(name: str) -> str:
    """Extract language from '{slot}_{lang}_{hash}.mp3' → e.g. 'zh-TW' or 'en'."""
    stem = name.rsplit(".", 1)[0]  # drop .mp3
    parts = stem.rsplit("_", 1)    # ["{slot}_{lang}", "{hash}"]
    return parts[0].split("_", 1)[1] if len(parts) == 2 else "unknown"


def cleanup_old_audio(keep_days: int = 30) -> int:
    """Remove stale TTS audio from GCS (or local disk).
    Keep last 30 days + 1 blob per language on each 1st-of-month."""
    run_mode = os.environ.get("RUN_MODE", RUN_MODE)
    cutoff = date.today() - timedelta(days=keep_days)

    if run_mode in ("MODAL", "CLOUD"):
        return _cleanup_gcs(cutoff)

    from config import LOCAL_DATA_DIR
    return _cleanup_local(Path(LOCAL_DATA_DIR) / "audio", cutoff)


def _cleanup_gcs(cutoff: date) -> int:
    """Delete stale audio blobs from GCS bucket."""
    from google.cloud import storage
    bucket = storage.Client().bucket(GCS_BUCKET_NAME)
    prefix = GCS_AUDIO_PREFIX + "/"
    by_date: dict[str, list] = {}
    for blob in bucket.list_blobs(prefix=prefix):
        # blob.name = "audio/2026-03-14/morning_zh-TW_abc123.mp3"
        parts = blob.name[len(prefix):].split("/", 1)
        if len(parts) != 2 or not parts[1].endswith(".mp3"):
            continue
        m = re.fullmatch(r"\d{4}-\d{2}-\d{2}", parts[0])
        if not m:
            continue
        by_date.setdefault(parts[0], []).append(blob)

    removed = 0
    for date_str, blobs in sorted(by_date.items()):
        dir_date = date.fromisoformat(date_str)
        if dir_date >= cutoff:
            continue
        if dir_date.day == 1:
            by_lang: dict[str, list] = {}
            for b in blobs:
                lang = _extract_lang_from_filename(b.name.rsplit("/", 1)[-1])
                by_lang.setdefault(lang, []).append(b)
            for lang, lang_blobs in by_lang.items():
                lang_blobs.sort(key=lambda b: b.updated, reverse=True)
                for b in lang_blobs[1:]:
                    b.delete()
                    removed += 1
        else:
            for b in blobs:
                b.delete()
                removed += 1
    if removed:
        log.info("Audio cleanup (GCS): removed %d stale blob(s)", removed)
    return removed


def _cleanup_local(audio_root: Path, cutoff: date) -> int:
    """Delete stale audio files from local disk."""
    if not audio_root.is_dir():
        return 0
    removed = 0
    for entry in sorted(audio_root.iterdir()):
        if not entry.is_dir():
            continue
        m = re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry.name)
        if not m:
            continue
        dir_date = date.fromisoformat(entry.name)
        if dir_date >= cutoff:
            continue
        mp3s = list(entry.glob("*.mp3"))
        if not mp3s:
            entry.rmdir()
            continue
        if dir_date.day == 1:
            by_lang: dict[str, list[Path]] = {}
            for f in mp3s:
                lang = _extract_lang_from_filename(f.name)
                by_lang.setdefault(lang, []).append(f)
            for lang, files in by_lang.items():
                files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                for f in files[1:]:
                    f.unlink()
                    removed += 1
        else:
            for f in mp3s:
                f.unlink()
                removed += 1
            try:
                entry.rmdir()
            except OSError:
                pass
    if removed:
        log.info("Audio cleanup (local): removed %d stale file(s)", removed)
    return removed


def synthesise_with_cache(text: str, lang: str, date: str, slot: str) -> str:
    """Returns a playable audio URL. GCS public URL for MODAL/CLOUD, local path for LOCAL."""
    from config import LOCAL_DATA_DIR
    run_mode = os.environ.get("RUN_MODE", RUN_MODE)
    gcs_path = tts_cache_key(text, lang, date, slot)
    rel_path = gcs_path[len("audio/"):]  # "{date}/{slot}_{lang}_{hash}.mp3"

    if run_mode in ("MODAL", "CLOUD"):
        from google.cloud import storage
        blob = storage.Client().bucket(GCS_BUCKET_NAME).blob(gcs_path)
        if blob.exists():
            log.info("TTS cache hit (GCS): %s → %s", gcs_path, blob.public_url)
            return blob.public_url
        audio = _render_tts(text, lang)
        url = _upload_to_gcs(audio, gcs_path)
        log.info("TTS synthesised and uploaded: %s", url)
        return url

    # LOCAL mode
    local_path = Path(LOCAL_DATA_DIR) / gcs_path
    if local_path.exists():
        log.info("TTS cache hit (local): %s", local_path)
        return f"/api/audio/{rel_path}"
    audio = _render_tts(text, lang)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(audio)
    return f"/api/audio/{rel_path}"
