# Technical Debt Audit Report

**Project**: family-weather  
**Date**: 2026-02-22  
**Auditor**: Senior Software Engineer  
**Files Reviewed**: 25 source files (~5,800 LOC)

---

## 1. Architecture Problems

| # | File | Lines | Issue | Severity | Effort |
|---|---|---|---|---|---|
| A1 | [weather_processor.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/data/weather_processor.py) | 1–1561 | **God module** — 1,561 lines containing data processing, scale definitions, outdoor scoring, meal classification, cardiac alerts, Ménière's detection, location pools, and climate control. Should be split into ≥ 4 focused modules. | **High** | Large |
| A2 | [app.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/app.py) | 180–374 | **God function** — `_pipeline_steps()` is a 195-line generator mixing orchestration, lazy imports, regen logic, parallel submission, and persistence. | **Medium** | Medium |
| A3 | [app.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/app.py#L22-L31) | 22–31 | **Monkey-patching** — `requests.get` is globally patched to `verify=False` at import time when `RUN_MODE == "LOCAL"`. This silently affects all library code too. | **High** | Small |
| A4 | [conversation.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/history/conversation.py#L174-L252) | 174–252 | **80 lines of commented-out design thinking** left inline as narrative comments. This is design documentation, not code. Obscures actual implementation. | **Low** | Small |
| A5 | [weather_processor.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/data/weather_processor.py#L198-L279) | 198–279 | **Hardcoded location data** — 80 lines of curated location dicts embedded directly in a processing module. Should be a JSON/YAML data file. | **Medium** | Medium |

---

## 2. Security Issues

| # | File | Lines | Issue | Severity | Effort |
|---|---|---|---|---|---|
| S1 | [.env](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/.env) | 1–4 | **Plaintext API keys** — Anthropic (`sk-ant-api03-...`), CWA, MOENV, and Gemini API keys are stored in `.env`. While `.gitignore` lists `.env`, these keys may already be committed to version history. | **Critical** | Small |
| S2 | [fetch_cwa.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/data/fetch_cwa.py#L39) | 39 | **API key in query parameter** — `CWA_API_KEY` sent as a URL query param (`?Authorization=...`). This leaks the key in server logs, browser history, and proxy caches. Same pattern at lines 145, 277. | **High** | Small |
| S3 | [fetch_moenv.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/data/fetch_moenv.py#L37) | 37, 85 | **API key in query parameter** — `MOENV_API_KEY` sent as `?api_key=...`. Same exposure risk as S2. | **High** | Small |
| S4 | [fetch_cwa.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/data/fetch_cwa.py#L46) | 46, 145, 281 | **SSL verification disabled** — `verify=False` on all three `requests.get()` calls. MitM attacks can intercept data. | **High** | Small |
| S5 | [fetch_moenv.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/data/fetch_moenv.py#L22) | 22, 43, 91 | **SSL warnings globally suppressed** — `urllib3.disable_warnings()` hides evidence of failed certificate checks. | **Medium** | Small |
| S6 | [app.js](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/web/static/app.js#L30-L31) | 30–31, 211–216, 288–304, 458–465 | **XSS via innerHTML** — Server-returned data (alert text, weather descriptions, hazard strings) injected directly via `.innerHTML` without sanitisation. An LLM-injected `<script>` tag would execute. | **High** | Medium |
| S7 | [app.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/app.py#L91-L99) | 91–99 | **Debug endpoint in production** — `/debug/log` accepts arbitrary POST data and logs it. No auth, no rate limiting. | **Medium** | Small |

---

## 3. State Management

| # | File | Lines | Issue | Severity | Effort |
|---|---|---|---|---|---|
| SM1 | [app.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/app.py#L53) | 53 | **Global mutable state** — `_refresh_counter` uses a `global` mutated inside a generator. Not thread-safe under gunicorn with multiple workers. | **Medium** | Small |
| SM2 | [app.js](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/web/static/app.js#L43-L46) | 43–46 | **Module-level globals** — `broadcastData`, `currentView`, `tempChart`, `loadingInterval` are loose globals. No encapsulation; any script in scope can clobber them. | **Low** | Medium |
| SM3 | [weather_processor.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/data/weather_processor.py#L546) | 546 | **Implicit time dependency** — `_segment_forecast()` calls `datetime.now()` directly, making results non-deterministic and untestable. Should accept `now` as a parameter. | **Medium** | Small |

---

## 4. Error Handling

| # | File | Lines | Issue | Severity | Effort |
|---|---|---|---|---|---|
| E1 | [fetch_cwa.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/data/fetch_cwa.py#L91) | 91 | **Bare `except:`** — `except: pass` inside visibility parsing hides all errors including `KeyboardInterrupt`. | **Medium** | Small |
| E2 | [fetch_cwa.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/data/fetch_cwa.py#L145-L146) | 145–146 | **Unhandled HTTP error** — `fetch_forecast()` calls `resp.raise_for_status()` but is not wrapped in a try/except, unlike `fetch_current_conditions()`. | **Medium** | Small |
| E3 | [fetch_cwa.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/data/fetch_cwa.py#L231) | 231 | **NameError risk** — References `val` variable that is only defined inside an earlier `elif` branch. If the code reaches the `WeatherCode`/`Weather` branch without hitting the PoP branch first, `val` will be undefined. | **High** | Small |
| E4 | [tts_client.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/narration/tts_client.py#L268) | 262–268 | **Silent failure** — `_synthesize_edge()` catches all exceptions and returns empty bytes `b""`. Downstream code may attempt to write/upload a 0-byte "audio" file without realising synthesis failed. | **Medium** | Small |
| E5 | [conversation.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/history/conversation.py#L134-L135) | 134–135 | **Potential UnboundLocalError** — `blob` is only defined inside the `else` branch of `RUN_MODE == "LOCAL"`, but is used unconditionally at line 135 for upload. Would crash in non-LOCAL mode if the history load failed. | **High** | Small |
| E6 | [app.js](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/web/static/app.js#L706-L709) | 706–709 | **Swallowed JSON parse errors** — NDJSON stream parsing catches JSON errors with `console.warn` and silently continues, potentially losing real error payloads from the server. | **Low** | Small |

---

## 5. Code Duplication

| # | Files | Issue | Severity | Effort |
|---|---|---|---|---|
| D1 | [fetch_cwa.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/data/fetch_cwa.py#L427-L438) L427–438, [fetch_moenv.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/data/fetch_moenv.py#L153-L164) L153–164 | **`_safe_float()` and `_safe_int()` duplicated verbatim** in both data-fetching modules. Should be extracted to a shared `data/helpers.py`. | **Medium** | Small |
| D2 | [fetch_cwa.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/data/fetch_cwa.py#L270-L406) L270–406 vs L134–256 | **`fetch_forecast` and `fetch_forecast_7day` share ~70% identical structure** — same request pattern, location matching, element parsing, slot assembly. Only field names differ. | **Medium** | Medium |
| D3 | [fetch_cwa.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/data/fetch_cwa.py#L305-L311) | 305–311 | **Duplicated loop** — `for element in we_list:` body appears twice in `fetch_forecast_7day()`. The first loop (lines 305–311) does nothing useful — it assigns `el_name` and `time_list` then falls through without processing. | **High** | Small |
| D4 | [app.js](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/web/static/app.js#L383-L394) L383–394, [weather_processor.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/data/weather_processor.py#L1487-L1504) L1487–1504 | **AQI status translation duplicated** — Chinese → English mapping exists in both `translateAQIText()` (JS) and `translate_aqi_status()` (Python). Backend should send already-translated strings. | **Low** | Small |

---

## 6. Dead Code

| # | File | Lines | Issue | Severity | Effort |
|---|---|---|---|---|---|
| DC1 | [narration_utils.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/narration/narration_utils.py) | 1–173 | **Entire module never imported** — `grep` confirmed no `import narration_utils` or `from narration.narration_utils` anywhere in the codebase. 173 lines of dead code. | **Medium** | Small |
| DC2 | [app.js](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/web/static/app.js#L555-L577) | 555–577 | **Unused functions** — `renderHealthCard()`, `makeCard()`, and `aqiClass()` are defined but never called. | **Low** | Small |
| DC3 | [weather_processor.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/data/weather_processor.py#L607-L617) | 607–617 | **Unused function** — `_average_slots()` is defined but only called from `_commute_window()`. However, the function is accessible and tested indirectly. (Not strictly dead, but worth noting its limited use.) | **Low** | — |
| DC4 | [app.js](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/web/static/app.js#L45) | 45 | **Unused chart variable** — `tempChart` is initialised to `null` but never assigned a Chart.js instance. The chart-rendering code at line 772 is an empty section header. | **Low** | Small |

---

## 7. Type Safety

| # | File | Lines | Issue | Severity | Effort |
|---|---|---|---|---|---|
| T1 | All `.py` files | — | **No static type checker configured** — `pyrightconfig.json` was not found. `# pyre-ignore` pragmas appear 10+ times across `weather_processor.py` and `conversation.py`, indicating past type-checker usage that was abandoned. | **Medium** | Medium |
| T2 | [weather_processor.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/data/weather_processor.py#L868-L871) | 868, 870 | **`# pyre-ignore[6]` suppressing type errors** on `round(float(avg_at), 1)` — the underlying issue is that `avg_at` can be `float | int` depending on branch, and the round() call is safe. The pragmas are misleading. | **Low** | Small |
| T3 | [app.js](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/web/static/app.js) | — | **No TypeScript or JSDoc types** — 772 lines of untyped JavaScript. All data shapes from the API are implicit. | **Low** | Large |

---

## 8. Performance

| # | File | Lines | Issue | Severity | Effort |
|---|---|---|---|---|---|
| P1 | [fetch_cwa.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/data/fetch_cwa.py#L138-L146) | 138–146 | **Entire dataset fetched for single location** — `fetch_forecast()` downloads all township forecasts from CWA, then filters client-side. The `locationName` param is commented out (line 142). Wastes bandwidth on every call. | **Medium** | Small |
| P2 | [conversation.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/history/conversation.py#L148) | 148 | **Full 30-day history loaded for cache check** — `get_today_broadcast()` calls `load_history(days=30)` and linearly scans for today's date. Should query by date key directly. | **Medium** | Small |
| P3 | [tts_client.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/narration/tts_client.py#L283) | 279–283 | **Audio bytes concatenated with `+=`** — `audio_data += chunk["data"]` in a loop creates O(n²) byte copies. Should use `bytearray` or `io.BytesIO`. | **Low** | Small |
| P4 | [app.js](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/web/static/app.js#L79) | 79 | **Clock updated every 1 second** — `setInterval(updateClock, 1000)` manipulates CSS transforms on 3 SVG elements + text every second. Minor but adds continuous layout work. | **Low** | Small |
| P5 | [fetch_cwa.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/data/fetch_cwa.py#L145) | 145 | **Hardcoded 15s timeout** instead of using `CWA_TIMEOUT` constant (which is set to 20s in config). Inconsistent with `fetch_current_conditions()`. Same at line 281. | **Low** | Small |

---

## 9. Testing

| # | File | Issue | Severity | Effort |
|---|---|---|---|---|
| TS1 | [.gitignore](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/.gitignore#L18) L18 | **All test files gitignored** — `test_*.py` pattern in `.gitignore` means tests are never committed to version control. Tests cannot be run in CI/CD. | **Critical** | Small |
| TS2 | [tests/test_processor.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/tests/test_processor.py#L4) L4 | **Stale import** — `from data import processor` references the old module name. This test has been broken since the rename. | **High** | Small |
| TS3 | — | **Zero test coverage** on: `app.py` (routes, pipeline), `narration/` (all 5 modules), `web/routes.py`, `history/conversation.py`. The only tests are 2 ad-hoc scripts with `print()` assertions. | **High** | Large |
| TS4 | [test_outdoor_scoring.py](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/data/test_outdoor_scoring.py) | **No pytest framework** — Tests use `print()` and manual `assert` without a test runner. No setup, teardown, or fixtures. | **Medium** | Medium |

---

## 10. Dependencies

| # | File | Issue | Severity | Effort |
|---|---|---|---|---|
| DEP1 | [requirements.txt](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/requirements.txt) | **`anthropic` package missing** — `narration/claude_client.py` imports `anthropic`, but it is not listed in `requirements.txt`. Deployment will crash if Claude is selected as provider. | **Critical** | Small |
| DEP2 | [requirements.txt](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/requirements.txt) | **Unpinned packages** — `python-dotenv`, `edge-tts`, and `modal` have no version pins. Builds are non-reproducible. | **Medium** | Small |
| DEP3 | [requirements.txt](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/requirements.txt) | **`modal` included in production image** — The `modal` package (serverless framework) is presumably only needed for `backend/modal_app.py`, not for the main Flask app. Adds unnecessary attack surface and image size. | **Low** | Small |
| DEP4 | [requirements.txt](file:///c:/Users/User/.gemini/antigravity/scratch/family-weather/requirements.txt) | **`google-cloud-secret-manager` unused** — No import of `google.cloud.secretmanager` found anywhere in the codebase. Dead dependency. | **Low** | Small |

---

## Prioritized Remediation Plan

### Phase 1 — Security Fixes (Immediate)

| Priority | Issue | Action | Effort |
|---|---|---|---|
| 🔴 P0 | S1 | Rotate **all 4 API keys** immediately. Scrub from git history with `git filter-repo` or BFG. | Small |
| 🔴 P0 | DEP1 | Add `anthropic` to `requirements.txt` with pinned version. | Small |
| 🔴 P0 | TS1 | Remove `test_*.py` from `.gitignore`. Commit existing tests. | Small |
| 🟠 P1 | S6 | Replace all `.innerHTML` assignments in `app.js` with `textContent` or a sanitisation function. | Medium |
| 🟠 P1 | S4, S5 | Remove `verify=False` from production code. Pin CA bundle or set `REQUESTS_CA_BUNDLE` for local dev. | Small |
| 🟠 P1 | S7 | Gate `/debug/log` behind `RUN_MODE == "LOCAL"` check. | Small |

### Phase 2 — Breaking Bugs (This Sprint)

| Priority | Issue | Action | Effort |
|---|---|---|---|
| 🟠 P1 | E3 | Fix `NameError` — `val` is used before assignment in `fetch_forecast()` line 231. | Small |
| 🟠 P1 | E5 | Fix `UnboundLocalError` — `blob.upload_from_string()` in `conversation.py` when history load fails in CLOUD mode. | Small |
| 🟠 P1 | TS2 | Fix stale import in `tests/test_processor.py` (`from data import processor` → `from data import weather_processor`). | Small |
| 🟠 P1 | D3 | Remove duplicated no-op `for element in we_list:` loop in `fetch_forecast_7day()`. | Small |

### Phase 3 — Architectural Cleanup (Next 2 Sprints)

| Priority | Issue | Action | Effort |
|---|---|---|---|
| 🟡 P2 | A1 | Split `weather_processor.py` into: `scales.py`, `outdoor_scoring.py`, `health_alerts.py`, `meal_classifier.py`, `weather_processor.py` (core). | Large |
| 🟡 P2 | A2 | Extract `_pipeline_steps()` into a `pipeline.py` module. Move regen, parallel-submission, and persistence logic into dedicated functions. | Medium |
| 🟡 P2 | A5 | Move `OUTDOOR_LOCATIONS` dict to `data/locations.json`. | Medium |
| 🟡 P2 | SM3 | Add `now: datetime` parameter to `_segment_forecast()` for testability. | Small |
| 🟡 P2 | TS3 | Build a pytest test suite covering: pipeline orchestration, data processing core, narration parsing, and route/slice building. | Large |

### Phase 4 — Low-Hanging Fruit (Backlog)

| Priority | Issue | Action | Effort |
|---|---|---|---|
| 🔵 P3 | D1 | Extract `_safe_float`/`_safe_int` to `data/helpers.py`, import in both fetch modules. | Small |
| 🔵 P3 | DC1 | Delete `narration/narration_utils.py` or wire it in where needed. | Small |
| 🔵 P3 | DC2 | Delete unused `renderHealthCard()`, `makeCard()`, `aqiClass()` from `app.js`. | Small |
| 🔵 P3 | A4 | Remove 80 lines of commented-out design notes from `conversation.py`. | Small |
| 🔵 P3 | P1 | Uncomment `locationName` filter in `fetch_forecast()` to reduce API payload. | Small |
| 🔵 P3 | P2 | Rewrite `get_today_broadcast()` to load by date key instead of scanning full history. | Small |
| 🔵 P3 | DEP2 | Pin all dependency versions in `requirements.txt`. | Small |
| 🔵 P3 | DEP3, DEP4 | Remove `modal` and `google-cloud-secret-manager` from main `requirements.txt`; create a separate `requirements-modal.txt`. | Small |
| 🔵 P3 | D4 | Remove duplicate AQI translation from `app.js`; use pre-translated values from backend. | Small |
| 🔵 P3 | A3 | Replace monkey-patched `requests.get` with a session-based approach or env-var `REQUESTS_CA_BUNDLE`. | Small |
