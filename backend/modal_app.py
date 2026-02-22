import modal
import os
import json
from datetime import datetime, timezone, timedelta

# ── Modal App Definition ──────────────────────────────────────────────────────

image = modal.Image.debian_slim(python_version="3.12").pip_install_from_requirements(
    "/app/requirements.txt"
)

app = modal.App("family-weather-engine")
volume = modal.Volume.from_name("family-weather-data", create_if_missing=True)

# ── Secrets ───────────────────────────────────────────────────────────────────
# Ensure these are set in your Modal dashboard:
# CWA_API_KEY, MOENV_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY
secrets = [modal.Secret.from_name("family-weather-secrets")]

_TAIPEI_TZ = timezone(timedelta(hours=8))

@app.function(
    image=image,
    secrets=secrets,
    volumes={"/data": volume},
    mounts=[modal.Mount.from_local_dir(".", remote_path="/app")],
)
@modal.web_endpoint()
def health():
    return {"status": "ok", "timestamp": datetime.now(_TAIPEI_TZ).isoformat()}

@app.function(
    image=image,
    secrets=secrets,
    volumes={"/data": volume},
    mounts=[modal.Mount.from_local_dir(".", remote_path="/app")],
    timeout=300, # 5 minutes for full pipeline
)
@modal.web_endpoint(method="POST")
def refresh(payload: dict = None):
    """
    Triggers the full data fetch + narration + TTS pipeline.
    Returns an NDJSON stream.
    """
    import sys
    sys.path.append("/app")
    import json
    from fastapi.responses import StreamingResponse
    from app import _pipeline_steps
    
    body = payload or {}
    date_str = body.get("date") or datetime.now(_TAIPEI_TZ).strftime("%Y-%m-%d")
    provider = body.get("provider")

    def generate():
        try:
            for step in _pipeline_steps(date_str, provider_override=provider):
                yield json.dumps(step) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")

@app.function(
    image=image,
    secrets=secrets,
    volumes={"/data": volume},
    mounts=[modal.Mount.from_local_dir(".", remote_path="/app")],
)
@modal.web_endpoint()
def broadcast(date: str = None):
    """
    Returns the broadcast data for a specific date.
    """
    import sys
    sys.path.append("/app")
    
    from history.conversation import get_today_broadcast
    from web.routes import build_slices
    
    date_str = date or datetime.now(_TAIPEI_TZ).strftime("%Y-%m-%d")
    cached = get_today_broadcast(date_str)
    
    if not cached:
        return {"error": f"No broadcast found for {date_str}"}, 404
        
    slices = build_slices(cached)
    return {**cached, "slices": slices}
