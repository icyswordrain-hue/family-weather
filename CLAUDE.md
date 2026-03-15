# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run locally
RUN_MODE=LOCAL python app.py          # http://localhost:8080

# Tests — run ONLY this, not dev-tools/ (those make live HTTP calls)
pytest tests/
pytest tests/test_health_alerts.py    # run a single test file
pytest tests/ -k "test_menieres"      # run a single test by name

# Deploy (CI/CD handles this on push to master)
modal deploy backend/modal_app.py     # deploy Modal pipeline only
```

## Architecture

Three execution contexts controlled by `RUN_MODE` env var:

- **LOCAL** — Flask + pipeline run in-process; data in `local_data/`
- **CLOUD** — Cloud Run Flask acts as proxy; delegates pipeline work to Modal via HTTP
- **MODAL** — Inside Modal containers; data on Modal Volume at `/data`

**Data flow (CLOUD):**
```
Browser → Cloud Run Flask → Modal HTTP → pipeline → Modal Volume
                          ↖ proxies /api/refresh, /api/broadcast
```

**Module layout:**
```
app.py               Flask routes + _pipeline_steps() generator (NDJSON stream)
config.py            All env-driven constants; RUN_MODE determines data paths
backend/
  pipeline.py        Testable logic: check_regen_cycle(), generate_narration_with_fallback()
  modal_app.py       Modal endpoints: health, refresh, broadcast, audio
data/
  fetch_cwa.py       CWA weather API; writes station history JSONL + forecast JSON cache
  fetch_moenv.py     MOENV AQI API
  weather_processor.py  Raw data → structured payload (forecast segments, alerts, scores)
  health_alerts.py   Cardiac + Ménière's risk detection
  outdoor_scoring.py Rule-engine outdoor grade A–F (0–100 score)
narration/
  llm_prompt_builder.py  Builds v7 prompts for Claude/Gemini
  claude_client.py   Sonnet 4.6 → Haiku 4.5 internal fallback
  gemini_client.py   Gemini Pro Exp → Gemini Flash internal fallback
  chat_context.py    ~650-token system prompt for /api/chat (Haiku 4.5, 300 max tokens)
  tts_client.py      Google Cloud TTS or Edge TTS fallback
history/
  conversation.py    Read/write broadcast history (GCS in CLOUD, disk in LOCAL/MODAL)
web/
  routes.py          build_slices() — per-view payloads fed to the frontend
  static/app.js      All frontend: views, player bar, player sheet, chat, language toggle
  static/style.css   Earthy design system, responsive (≥768px desktop / ≤767px mobile)
```

## Critical Gotchas

**RUN_MODE in Modal:** Must use `os.environ["RUN_MODE"] = "MODAL"` (direct assignment). `setdefault()` is a no-op because Modal secrets inject `RUN_MODE=CLOUD` first.

**volume.commit():** Must only be called in `modal_app.py`'s `refresh()` finally block. Do NOT import and commit the Volume inside `fetch_cwa.py` or any data module.

**CWA API:** Key casing is inconsistent (`Locations`/`locations`, `WeatherElement`/`weatherElement`). SSL errors require `verify=False` retry. Missing fields like AT or PoP12h mean wrong dataset ID — do not add retry loops.

**AQI levels — two intentionally different scales:**
- Python `_aqi_to_level()` in `data/scales.py`: 3-bucket (`<60→1`, `<120→3`, `≥120→5`) for the hero gauge
- JavaScript `aqiToLevel()` in `app.js`: 5-level (≤50/≤100/≤150/≤200/201+) for timeline coloring
- Do NOT "fix" either to match the other.

**`safe_float` / `safe_int`:** Return `None` for CWA sentinel values `-99` / `-999` (missing instrument readings).

**`_detect_menieres_alert()`:** Only a ≥6 hPa 24h swing sets `triggered=True`. Low pressure + high humidity gives `severity="moderate"` but NOT `triggered=True`.

**Narration provider:** Controlled by `NARRATION_PROVIDER` env var (default `"GEMINI"`). `generate_narration_with_fallback()` in `pipeline.py` has a two-tier fallback: (1) each provider's internal fallback (`gemini_client.py` Pro → Flash; `claude_client.py` Sonnet 4.6 → Haiku 4.5), then (2) cross-provider fallback (e.g. Gemini fails entirely → tries Claude), then (3) template narrator. Both clients detect truncated responses (max_tokens with unparseable `---METADATA---`) and fall through to their internal fallback model before raising.

**Chat provider:** `/api/chat` uses Gemini Flash 2.5 as primary, with silent fallback to Claude Haiku 4.5. Do not route chat through `generate_narration()`.

**Pipeline skip layers (2 layers):** The pipeline uses only two cache layers: (1) narration TTL cache (30-min, conditions-aware key with temp bucket + rain flag in `backend/cache.py`), and (2) TTS MD5 cache (identical text → same audio file). There is no midday skip, no condition-change skip, and no TTS slot restriction — Edge TTS is free so all slots get audio.

**Timestamps:** All timestamps are naive Taipei wall-clock time (UTC+8). No UTC conversion. Segment logic (morning/afternoon/evening/overnight) depends on the server running in Asia/Taipei.

**Broadcast-time pinning:** `_slice_lifestyle()` in `web/routes.py` reads `summaries["_best_window"]` and `summaries["_top_activity"]` stored at generation time to prevent temporal drift from the LLM card text.

**`forecast_segments` null values:** `_segment_forecast()` returns `{Morning: None, Afternoon: None, ...}` for any segment where no CWA slot falls within the window. These nulls serialize to JSON and land in the frontend's `broadcastData.processed_data.forecast_segments`. Always use optional chaining (`s?.PoP6h`) when mapping over `Object.values(segments)` — never `s.PoP6h` directly.

## Forecast Cache Structure

`FORECAST_CACHE_PATH` (`forecast_cache.json`):
```json
{"cached_at": "...", "36h": {"shulin": [...slots], "banqiao": [...]}, "7d": {"shulin": [...], ...}}
```
Each location key is updated independently — a failure for one location does not clear the other.

## Frontend Architecture

`app.js` is a single 2000+ line file. Key globals:
- `broadcastData` — the live broadcast object
- `currentView` — `'lifestyle'` (default) | `'dashboard'` | `'narration'`
- `window._playerBarSetAudio(url, paragraphs, meta)` — wires the player bar
- `window._chatResetHistory()` — clears chat history + re-renders suggestion chips
- `window._renderSuggestions()` — rebuilds context-aware suggestion chips

Chat is stateless: the client sends the last 6 turns in `messages[]`; `chat_context.py` prepends a fresh context snapshot on every call.

Brand icons: WebP only in `web/static/brand-icons/`. Use the `IMG(name, alt)` helper in `app.js`; do NOT add PNGs. All icons must be 1:1 square (512×512 recommended) — the CSS forces equal `width`/`height` on most contexts, so non-square images will be distorted. `sunrise-square.webp` and `sunset-square.webp` (1024×1024) are used for the solar row in the dashboard canopy. The landscape `sunrise.webp` / `sunset.webp` (1380×752) remain in the directory but are no longer referenced. The `*-slab.webp` files (512×128 4:1) are intentional exceptions — they use `height` fixed + `width: auto` in CSS so aspect ratio is preserved.

## TTS Voices

Two providers with automatic fallback (Edge TTS → Google Cloud):

| Provider | English | Chinese | Pitch |
|----------|---------|---------|-------|
| Google Cloud TTS | `en-GB-Standard-C` (female) | `cmn-TW-Standard-A` (female) | +2.0 semitones |
| Edge TTS | `en-US-JennyNeural` (female) | `zh-TW-HsiaoChenNeural` (female) | +5Hz |

Voice names are configured in `config.py` (`TTS_VOICE_EN`, `TTS_VOICE_ZH`) for Google and in the `VOICES` dict in `tts_client.py` for Edge. Pitch adjustments are hardcoded in `_render_google_tts()` and `_render_edge_tts()`.

## Test Notes

- `GRADE_THRESHOLDS` labels: A="Go out", B="Good to go", C="Manageable", D="Think twice", F="Stay in"
- Cache tests must clear `_narration_cache` in an `autouse` fixture
- All external calls (LLM, TTS, APIs) must be mocked in tests
