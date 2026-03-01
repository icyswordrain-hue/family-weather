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
@modal.web_endpoint()
def health():
    return {"status": "ok", "timestamp": datetime.now(_TAIPEI_TZ).isoformat()}


@app.function(image=image, secrets=secrets, volumes={"/data": volume}, timeout=300)
@modal.web_endpoint(method="POST")
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
        except Exception as e:
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"
        finally:
            try:
                volume.commit()
            except Exception:
                pass  # non-fatal

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@app.function(image=image, secrets=secrets, volumes={"/data": volume})
@modal.web_endpoint()
def broadcast(date: str = None):
    import sys
    _bootstrap_gcp_credentials()
    sys.path.insert(0, "/app")
    from history.conversation import get_today_broadcast
    from web.routes import build_slices

    date_str = date or datetime.now(_TAIPEI_TZ).strftime("%Y-%m-%d")
    cached = get_today_broadcast(date_str)

    if not cached:
        return {"error": f"No broadcast found for {date_str}"}, 404

    slices = build_slices(cached)
    return {**cached, "slices": slices}