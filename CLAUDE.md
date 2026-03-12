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
                          ↖ proxies /api/refresh, /api/broadcast, /api/tts
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
  claude_client.py   Anthropic primary (Sonnet 4.6) → Haiku 4.5 fallback
  gemini_client.py   Gemini primary; Gemini → Claude fallback chain in pipeline.py
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

**Narration provider chain:** `pipeline.py` calls Gemini first, falls back to Claude. `claude_client.py` internally tries Sonnet 4.6, falls back to Haiku 4.5. Do not route chat (`/api/chat`) through `generate_narration()` — call `_get_client().messages.create()` directly.

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

**Player-sheet tabs:** The Narration / Settings / Ask tabs inside `#player-sheet` are visible on **both** desktop and mobile — do NOT add `display: none` for `.player-sheet-tabs` at `≥768px`. Hiding them on desktop made the sheet permanently stuck on the chat panel after the Ask button was used.

**Chat panel padding:** `#ps-panel-chat` sets `padding: 0` to override the inherited `.ps-tab-panel { padding: 14px 16px }`. The `.chat-messages` and `.chat-input-row` elements carry their own padding; the outer padding must not be re-added or it double-pads the layout.

Brand icons: WebP only in `web/static/brand-icons/`. Use the `IMG(name, alt)` helper in `app.js`; do NOT add PNGs.

## Test Notes

- `GRADE_THRESHOLDS` labels: A="Go out", B="Good to go", C="Manageable", D="Think twice", F="Stay in"
- Cache tests must clear `_narration_cache` in an `autouse` fixture
- All external calls (LLM, TTS, APIs) must be mocked in tests
