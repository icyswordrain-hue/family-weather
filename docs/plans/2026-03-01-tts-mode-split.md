# TTS Mode Split & Transcript Decoupling Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** (1) In `LOCAL` mode, synthesise TTS eagerly during the pipeline refresh; in `CLOUD`/`MODAL` mode, keep TTS deferred to the `/api/tts` on-demand endpoint. (2) Always render the narration transcript in the player sheet regardless of whether TTS audio is available.

**Architecture:** A single guard in `_pipeline_steps` (inside `app.py`) checks `RUN_MODE`. If `LOCAL`, it calls the existing `synthesise_with_cache` from `narration/tts_client.py` and stores the result in `audio_urls`. The frontend already handles a non-null `full_audio_url` by setting `audio.src` directly and skipping the on-demand click handler. No new API surface needed.

**Tech Stack:** Python (Flask), `narration/tts_client.py` (`edge_tts`, local file storage), `config.py` (`RUN_MODE`), `web/static/app.js`.

---

## Context: current state

### `app.py` lines 356-361 (inside `_pipeline_steps`)
```python
# 5.5 Synthesize TTS
yield {"type": "log", "message": "Audio briefing TTS (deferred to on-demand)..."}

summaries = parsed.get("cards", {})
audio_urls = {"full_audio_url": None}
```
`audio_urls` is always `None` → player bar always falls back to the on-demand click handler regardless of mode.

### `narration/tts_client.py` — `synthesise_with_cache`
Already handles both modes:
- `LOCAL` → renders via `edge_tts`, saves to `local_data/audio/`, returns `/local_assets/audio/<name>`.
- `CLOUD`/`MODAL` → uploads to GCS, returns public URL.

### `web/static/app.js` — `render()` lines 383-391
```js
// transcript + audio wiring — currently gated on audio URL
if (data.audio_urls && data.audio_urls.full_audio_url) {
  ...
  window._playerBarSetAudio(url, paragraphs, meta);
}
```
When `full_audio_url` is `null`, `_playerBarSetAudio` is never called → **transcript never renders**.
`_playerBarSetAudio` already handles a null URL (installs on-demand click handler), so the fix is to always call it.

---

## Task 1: Eager TTS in LOCAL pipeline

**Files:**
- Modify: `app.py` lines 356-361

**Step 1: Write the failing test**

Add to `tests/test_pipeline.py` (at the bottom):

```python
# ── TTS mode split ────────────────────────────────────────────────────────────

from unittest.mock import patch

def _fake_pipeline_result(steps):
    """Drain a _pipeline_steps generator and return the result payload."""
    result = None
    for step in steps:
        if step.get("type") == "result":
            result = step["payload"]
    return result
```

Add `tests/test_tts_mode_split.py` (new file):

```python
"""test_tts_mode_split.py — TDD for Task 1: TTS mode split in _pipeline_steps."""
import importlib
from unittest.mock import patch, MagicMock


def _collect_result(gen):
    for step in gen:
        if step.get("type") == "result":
            return step["payload"]
    return None


# ── LOCAL mode: TTS should be synthesised eagerly ─────────────────────────────

@patch("app.config.RUN_MODE", "LOCAL")
@patch("app.synthesise_with_cache", return_value="/local_assets/audio/test.mp3")
@patch("app.build_slices", return_value={})
@patch("app.save_day")
@patch("app.parse_narration_response", return_value={
    "paragraphs": {"P1": "Hello."}, "metadata": {}, "regen": None, "cards": {}
})
@patch("app.generate_narration_with_fallback", return_value=("Hello.", "gemini"))
@patch("app.process", return_value={"current": {}})
@patch("app.fetch_all_aqi", return_value={})
@patch("app.fetch_all_forecasts_7day", return_value={})
@patch("app.fetch_all_forecasts", return_value={})
@patch("app.fetch_current_conditions", return_value={})
@patch("app.load_history", return_value=[])
@patch("app.check_regen_cycle", return_value=False)
def test_local_tts_is_eager(
    mock_regen, mock_hist, mock_cur, mock_fc, mock_7d, mock_aqi,
    mock_proc, mock_narr, mock_parse, mock_save, mock_slices, mock_tts
):
    import app
    result = _collect_result(app._pipeline_steps("2026-03-01", lang="en"))
    assert result is not None
    assert result["audio_urls"]["full_audio_url"] == "/local_assets/audio/test.mp3"
    mock_tts.assert_called_once()


# ── CLOUD mode: TTS should remain None ────────────────────────────────────────

@patch("app.config.RUN_MODE", "CLOUD")
@patch("app.synthesise_with_cache")
@patch("app.build_slices", return_value={})
@patch("app.save_day")
@patch("app.parse_narration_response", return_value={
    "paragraphs": {"P1": "Hello."}, "metadata": {}, "regen": None, "cards": {}
})
@patch("app.generate_narration_with_fallback", return_value=("Hello.", "gemini"))
@patch("app.process", return_value={"current": {}})
@patch("app.fetch_all_aqi", return_value={})
@patch("app.fetch_all_forecasts_7day", return_value={})
@patch("app.fetch_all_forecasts", return_value={})
@patch("app.fetch_current_conditions", return_value={})
@patch("app.load_history", return_value=[])
@patch("app.check_regen_cycle", return_value=False)
def test_cloud_tts_is_deferred(
    mock_regen, mock_hist, mock_cur, mock_fc, mock_7d, mock_aqi,
    mock_proc, mock_narr, mock_parse, mock_save, mock_slices, mock_tts
):
    import app
    result = _collect_result(app._pipeline_steps("2026-03-01", lang="en"))
    assert result is not None
    assert result["audio_urls"]["full_audio_url"] is None
    mock_tts.assert_not_called()
```

**Step 2: Run test to verify it fails**

```
pytest tests/test_tts_mode_split.py -v
```
Expected: both tests FAIL — `synthesise_with_cache` not imported in `app.py` / always `None`.

**Step 3: Write minimal implementation**

In `app.py`, at the top import block, add:

```python
from narration.tts_client import synthesise_with_cache
```

In `_pipeline_steps`, replace lines 356-361:

```python
# 5.5 Synthesize TTS (LOCAL: eager; CLOUD/MODAL: on-demand)
summaries = parsed.get("cards", {})
if RUN_MODE == "LOCAL":
    yield {"type": "log", "message": "Synthesising TTS audio locally…"}
    try:
        full_audio_url = synthesise_with_cache(narration_text, lang, date_str, slot)
    except Exception as exc:
        logger.warning("Local TTS failed (%s) — player will fall back to on-demand.", exc)
        full_audio_url = None
    audio_urls = {"full_audio_url": full_audio_url}
else:
    yield {"type": "log", "message": "Audio briefing TTS (deferred to on-demand)..."}
    audio_urls = {"full_audio_url": None}
```

**Step 4: Run test to verify it passes**

```
pytest tests/test_tts_mode_split.py -v
```
Expected: both PASS.

**Step 5: Run full test suite to check no regressions**

```
pytest tests/ -v
```
Expected: all existing tests pass.

**Step 6: Commit**

```
git add app.py tests/test_tts_mode_split.py
git commit -m "feat: eager TTS in LOCAL mode, on-demand TTS in CLOUD/MODAL"
```

---

## Task 2: Always render transcript regardless of audio URL

**Files:**
- Modify: `web/static/app.js` lines 383-391

**Step 1: Write the failing test**

This is a browser-level concern — manually verify before and after (Step 5).
For automated coverage, add to `tests/test_tts_mode_split.py`:

```python
# Task 2 — transcript invariant (unit-level; JS tested manually)
# Documented here as a spec contract, not an automated test.
# The render() guard removal is verified in Manual Verification below.
```

**Step 2: Implement the fix**

In `web/static/app.js`, replace the gated block in `render()` (lines 383-391):

```js
// BEFORE
if (data.audio_urls && data.audio_urls.full_audio_url) {
  const narrationSlice = data.slices && data.slices.narration;
  const paragraphs = narrationSlice ? (narrationSlice.paragraphs || []) : [];
  const meta = narrationSlice ? (narrationSlice.meta || {}) : {};
  if (window._playerBarSetAudio) {
    window._playerBarSetAudio(data.audio_urls.full_audio_url, paragraphs, meta);
  }
}

// AFTER
{
  const narrationSlice = data.slices && data.slices.narration;
  const paragraphs = narrationSlice ? (narrationSlice.paragraphs || []) : [];
  const meta = narrationSlice ? (narrationSlice.meta || {}) : {};
  const audioUrl = data.audio_urls && data.audio_urls.full_audio_url || null;
  if (window._playerBarSetAudio) {
    window._playerBarSetAudio(audioUrl, paragraphs, meta);
  }
}
```

The `_playerBarSetAudio` function already branches on `!audioUrl` — installs on-demand click handler when null, sets `audio.src` directly when non-null. No further changes needed.

**Step 3: Manual verification (before fix)**
1. Run with `RUN_MODE=CLOUD` (or no audio in cached broadcast).
2. Open the player sheet → Narration tab → transcript should be empty. *(confirm bug)*

**Step 4: Manual verification (after fix)**
1. Same setup — open player sheet → Narration tab → transcript paragraphs render.
2. Play button still triggers on-demand TTS correctly.

**Step 5: Commit**

```
git add web/static/app.js
git commit -m "fix: always render narration transcript regardless of audio URL"
```

---

## Verification Plan

### Automated Tests
```
pytest tests/test_tts_mode_split.py -v   # new tests
pytest tests/ -v                          # full suite — no regressions
```

### Manual Verification (LOCAL)
1. Ensure `.env` has `RUN_MODE=LOCAL`.
2. Start server: `python app.py`
3. Open browser at `http://localhost:8080`.
4. Click **Refresh** in the sidebar.
5. Watch the server log — you should see: `Synthesising TTS audio locally…`
6. After refresh completes, the player bar should show the audio immediately (no "click to generate" state) and you can press play without any delay.
7. Check `local_data/audio/` — a new `.mp3` file should exist.

### Manual Verification (CLOUD — no regression)
The Flask app itself in CLOUD mode proxies to Modal, so there's nothing to start locally. Confirm that the Modal worker code (`_pipeline_steps` generator running remotely) still emits `audio_urls.full_audio_url = None` and the `/api/tts` on-demand endpoint still works when the user presses play on the deployed dashboard.

---

## Post-plan fixes (2026-03-01)

### Fix: `generate_claude` not patchable in `backend/pipeline.py`

**Problem:** `test_narration_claude_success` was failing with `AttributeError: <module 'backend.pipeline'> does not have the attribute 'generate_claude'`. The CLAUDE branch inside `generate_narration_with_fallback` used a runtime `importlib.reload` + local import, so `generate_claude` never existed as a module-level name — making `@patch("backend.pipeline.generate_claude")` impossible.

**Fix:** Added a module-level `try/except` import in `backend/pipeline.py` (mirroring the Gemini pattern) and updated the CLAUDE branch to call the module-level binding directly:

```python
try:
    from narration.claude_client import generate_narration as generate_claude
except Exception as e:
    generate_claude = None
```

**Commit:** `fix: add module-level generate_claude import so @patch resolves correctly`

---

### Change: default language `zh-TW`, default provider `CLAUDE`

**Defaults confirmed/set:**
- `config.py` `NARRATION_PROVIDER` — already `"CLAUDE"` ✅
- `app.py` `refresh()` — `lang` default changed `"en"` → `"zh-TW"`
- `app.py` `_pipeline_steps()` — `lang` default changed `"en"` → `"zh-TW"`

Frontend can still override both via `{"lang": "en", "provider": "GEMINI"}` in the POST body.

**Commit:** `feat: default lang zh-TW, confirm default provider CLAUDE`

