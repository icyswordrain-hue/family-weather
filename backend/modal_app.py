import modal
import os
import json
from datetime import datetime, timezone, timedelta

_TAIPEI_TZ = timezone(timedelta(hours=8))

# ── Image ─────────────────────────────────────────────────────────────────────
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("fastapi[standard]")
    .pip_install_from_requirements("requirements.txt")
    .add_local_dir(".", remote_path="/app")
)

# ── App ───────────────────────────────────────────────────────────────────────
app = modal.App("family-weather-engine")
volume = modal.Volume.from_name("family-weather-data", create_if_missing=True)
secrets = [modal.Secret.from_name("family-weather-secrets")]

# ── Helpers ───────────────────────────────────────────────────────────────────

def _bootstrap_gcp_credentials():
    """Decode GCP_SA_JSON (base64) from env and set GOOGLE_APPLICATION_CREDENTIALS."""
    sa_b64 = os.environ.get("GCP_SA_JSON")
    if sa_b64:
        import base64, tempfile
        sa_json = base64.b64decode(sa_b64).decode()
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp.write(sa_json)
        tmp.close()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.function(image=image, secrets=secrets, volumes={"/data": volume})
@modal.fastapi_endpoint()
def health():
    return {"status": "ok", "timestamp": datetime.now(_TAIPEI_TZ).isoformat()}


@app.function(image=image, secrets=secrets, volumes={"/data": volume}, timeout=300)
@modal.fastapi_endpoint(method="POST")
def refresh(payload: dict = None):
    import sys
    _bootstrap_gcp_credentials()
    os.environ["RUN_MODE"] = "MODAL"
    sys.path.insert(0, "/app")
    # Reset cached LLM clients so they re-initialise with injected secrets
    import narration.claude_client as _cc
    _cc._client = None
    from fastapi.responses import StreamingResponse
    from app import _pipeline_steps

    body = payload or {}
    date_str = body.get("date") or datetime.now(_TAIPEI_TZ).strftime("%Y-%m-%d")
    provider = body.get("provider")
    lang = body.get("lang", "en")
    slot = body.get("slot", "morning")

    def generate():
        try:
            for step in _pipeline_steps(date_str, provider_override=provider, lang=lang, slot=slot):
                yield json.dumps(step) + "\n"
                # Commit volume after pipeline writes (history, audio, etc.)
                if step.get("type") == "result":
                    try:
                        volume.commit()
                    except Exception:
                        pass
        except Exception as e:
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"
        finally:
            try:
                volume.commit()
            except Exception:
                pass  # non-fatal

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@app.function(image=image, secrets=secrets, volumes={"/data": volume})
@modal.fastapi_endpoint()
def broadcast(date: str = None, lang: str = "en"):
    import sys
    os.environ["RUN_MODE"] = "MODAL"
    _bootstrap_gcp_credentials()
    sys.path.insert(0, "/app")
    volume.reload()  # pick up data committed by refresh()
    from history.conversation import get_today_broadcast
    from web.routes import build_slices

    date_str = date or datetime.now(_TAIPEI_TZ).strftime("%Y-%m-%d")
    cached = get_today_broadcast(date_str)

    if not cached:
        return {"error": f"No broadcast found for {date_str}"}, 404

    # Build slices for every stored language so frontend can switch instantly
    from history.conversation import get_lang_data
    for _l in list(cached.get("langs", {})):
        _ld = get_lang_data(cached, _l)
        cached["langs"][_l]["slices"] = build_slices({
            "paragraphs": _ld.get("paragraphs", {}),
            "metadata": _ld.get("metadata", {}),
            "processed_data": cached.get("processed_data", {}),
            "summaries": _ld.get("summaries", {}),
        }, lang=_l)

    # Flatten requested lang for backwards compatibility
    ld = get_lang_data(cached, lang)
    return {
        **cached,
        "narration_text": ld.get("narration_text", ""),
        "paragraphs": ld.get("paragraphs", {}),
        "metadata": ld.get("metadata", {}),
        "audio_urls": ld.get("audio_urls", {}),
        "summaries": ld.get("summaries", {}),
        "slices": cached["langs"].get(lang, {}).get("slices", {}),
    }


@app.function(image=image, secrets=secrets, volumes={"/data": volume}, timeout=120)
@modal.fastapi_endpoint(method="POST")
def tts(payload: dict = None):
    """Re-synthesize TTS audio for both languages from the current broadcast."""
    import sys
    os.environ["RUN_MODE"] = "MODAL"
    _bootstrap_gcp_credentials()
    sys.path.insert(0, "/app")
    volume.reload()

    from history.conversation import get_today_broadcast, get_lang_data, save_day
    from narration.tts_client import synthesise_with_cache

    body = payload or {}
    date_str = body.get("date") or datetime.now(_TAIPEI_TZ).strftime("%Y-%m-%d")

    broadcast_data = get_today_broadcast(date_str)
    if not broadcast_data:
        return {"error": f"No broadcast found for {date_str}"}, 404

    updated_langs = dict(broadcast_data.get("langs", {}))
    tts_ts = datetime.now(_TAIPEI_TZ).isoformat()

    for _lang in ["zh-TW", "en"]:
        ld = get_lang_data(broadcast_data, _lang)
        text = ld.get("narration_text", "")
        if not text:
            continue
        try:
            url = synthesise_with_cache(text, _lang, date_str, "manual")
            if _lang in updated_langs:
                updated_langs[_lang] = {**updated_langs[_lang], "audio_urls": {"full_audio_url": url}}
        except Exception:
            pass

    save_day(
        date_str=date_str,
        raw_data=broadcast_data.get("raw_data", {}),
        processed_data=broadcast_data.get("processed_data", {}),
        langs=updated_langs,
        tts_generated_at=tts_ts,
    )

    try:
        volume.commit()
    except Exception:
        pass

    return {"status": "ok", "tts_generated_at": tts_ts}


