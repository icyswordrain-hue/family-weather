# Family Weather Dashboard — Modal Migration Plan

The core engine is being migrated to Modal to leverage serverless scaling for heavy tasks (data fetching, LLM processing, TTS).

## Proposed Changes

### [NEW] [modal_app.py](file:///C:/Users/User/.gemini/antigravity/scratch/family-weather/backend/modal_app.py)
Core Modal application definition.

### [MODIFY] [requirements.txt](file:///C:/Users/User/.gemini/antigravity/scratch/family-weather/requirements.txt)
Added `modal` dependency.

### [MODIFY] [main.py](file:///C:/Users/User/.gemini/antigravity/scratch/family-weather/main.py)
(Planned) Refactor to use Modal endpoints as backend.
