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
    "en":    "en-US-GuyNeural",
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
    lang_code = "zh-TW" if lang == "zh-TW" else "en-US"
    resp = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=texttospeech.VoiceSelectionParams(language_code=lang_code, name=voice_name),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=TTS_SPEAKING_RATE,
        ),
    )
    return resp.audio_content


def _render_edge_tts(text: str, lang: str) -> bytes:
    import edge_tts
    buf = io.BytesIO()
    async def _collect():
        communicate = edge_tts.Communicate(text, VOICES[lang])
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
    # Check at call time — in Modal, GCP creds are bootstrapped after config import
    provider = TTS_PROVIDER
    has_gcp = "GOOGLE_APPLICATION_CREDENTIALS" in os.environ
    if provider == "EDGE" and has_gcp:
        provider = "GOOGLE"
    if provider == "GOOGLE":
        try:
            return _render_google_tts(text, lang)
        except Exception:
            log.warning("Google Cloud TTS failed, falling back to Edge TTS", exc_info=True)
    return _render_edge_tts(text, lang)


def cleanup_old_audio(audio_root: Path, keep_days: int = 30) -> int:
    """Remove stale TTS audio. Keep last 30 days + 1 file per language on each 1st-of-month."""
    if not audio_root.is_dir():
        return 0
    cutoff = date.today() - timedelta(days=keep_days)
    removed = 0
    for entry in sorted(audio_root.iterdir()):
        if not entry.is_dir():
            continue
        m = re.fullmatch(r"\d{4}-\d{2}-\d{2}", entry.name)
        if not m:
            continue
        dir_date = date.fromisoformat(entry.name)
        if dir_date >= cutoff:
            continue  # within rolling window — keep everything
        mp3s = list(entry.glob("*.mp3"))
        if not mp3s:
            entry.rmdir()
            continue
        if dir_date.day == 1:
            # Monthly snapshot — keep newest file per language
            by_lang: dict[str, list[Path]] = {}
            for f in mp3s:
                # filename: {slot}_{lang}_{hash}.mp3  e.g. morning_zh-TW_abc123.mp3
                parts = f.stem.rsplit("_", 1)  # ["{slot}_{lang}", "{hash}"]
                lang = parts[0].split("_", 1)[1] if len(parts) == 2 else "unknown"
                by_lang.setdefault(lang, []).append(f)
            for lang, files in by_lang.items():
                files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                for f in files[1:]:
                    f.unlink()
                    removed += 1
        else:
            # Not 1st-of-month and older than cutoff — delete all
            for f in mp3s:
                f.unlink()
                removed += 1
            try:
                entry.rmdir()
            except OSError:
                pass
    if removed:
        log.info("Audio cleanup: removed %d stale file(s) from %s", removed, audio_root)
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
            log.info("TTS cache hit (GCS): %s", gcs_path)
            return blob.public_url
        audio = _render_tts(text, lang)
        return _upload_to_gcs(audio, gcs_path)

    # LOCAL mode
    local_path = Path(LOCAL_DATA_DIR) / gcs_path
    if local_path.exists():
        log.info("TTS cache hit (local): %s", local_path)
        return f"/api/audio/{rel_path}"
    audio = _render_tts(text, lang)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(audio)
    return f"/api/audio/{rel_path}"
