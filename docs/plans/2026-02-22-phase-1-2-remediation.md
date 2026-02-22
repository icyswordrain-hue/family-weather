# Phase 1 & 2 Remediation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Resolve critical security vulnerabilities (API keys, XSS, SSL validation) and immediate breaking bugs (NameErrors, stale imports) identified in the tech debt audit.

**Architecture:** We will systematically apply minimal, targeted fixes to each module. Test-driven development will be used where applicable, relying on pytest for backend Python logic. For file structure and configuration changes (e.g. `.env`, `.gitignore`), we use direct modifications and manual verification steps.

**Tech Stack:** Python, Flask, JavaScript, Pytest

---

### Task 1: Clean Secrets, Requirements, and Gitignore (S1, TS1, DEP1)

**Files:**
- Modify: `.env`
- Modify: `.gitignore`
- Modify: `requirements.txt`

**Step 1: Write the failing test (verification step)**

Run: `grep -E "sk-ant|AIzaSy" .env`
Expected: FAIL (returns matched keys, indicating secrets are present)

Run: `grep "test_\*\.py" .gitignore`
Expected: FAIL (returns the gitignore line)

Run: `grep "anthropic" requirements.txt`
Expected: FAIL (empty output, meaning missing)

**Step 2: Write minimal implementation**

1. In `.env`, replace actual API keys with placeholders:
```env
ANTHROPIC_API_KEY=your_anthropic_key_here
CWA_API_KEY=your_cwa_key_here
MOENV_API_KEY=your_moenv_key_here
GEMINI_API_KEY=your_gemini_key_here
RUN_MODE=LOCAL
NARRATION_PROVIDER=GEMINI
```

2. In `.gitignore`, remove `test_*.py` on line 18.

3. In `requirements.txt`, append `anthropic`.

**Step 3: Run test to verify it passes**

Run: `grep -E "sk-ant|AIzaSy" .env`
Expected: PASS (empty output)

Run: `grep "test_\*\.py" .gitignore`
Expected: PASS (empty output)

Run: `grep "anthropic" requirements.txt`
Expected: PASS (returns `anthropic`)

**Step 4: Commit**

```bash
git rm --cached .env || true
git add .env .gitignore requirements.txt
git commit -m "fix(sec): remove secrets from env, track tests, add missing anthropic dep"
```

---

### Task 2: Gate `/debug/log` Endpoint (S7)

**Files:**
- Modify: `app.py:91-100`
- Create: `tests/test_app.py`

**Step 1: Write the failing test**

```python
# tests/test_app.py
import pytest
from app import app
from config import RUN_MODE

def test_debug_log_forbidden_in_cloud(monkeypatch):
    monkeypatch.setattr("app.RUN_MODE", "CLOUD")
    with app.test_client() as client:
        res = client.post("/debug/log", json={"msg": "test"})
        assert res.status_code == 403
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_app.py -v`
Expected: FAIL (returns 200 OK instead of 403)

**Step 3: Write minimal implementation**

```python
# In app.py
@app.route("/debug/log", methods=["POST"])
def debug_log():
    """Receive and log frontend messages."""
    if RUN_MODE != "LOCAL":
        abort(403)
    data = request.get_json(silent=True) or {}
    type_ = data.get("type", "info").upper()
    msg = data.get("msg", "")
    ts = data.get("ts", "")
    logger.info(f"[BROWSER][{type_}][{ts}] {msg}")
    return jsonify({"status": "ok"})
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_app.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "fix(sec): restrict debug endpoint to LOCAL mode only"
```

---

### Task 3: Fix `fetch_cwa.py` Bugs (E3, D3)

**Files:**
- Modify: `data/fetch_cwa.py`
- Create: `tests/test_fetch_cwa_bugs.py`

**Step 1: Write the failing test**

```python
# tests/test_fetch_cwa_bugs.py
import pytest
from data.fetch_cwa import fetch_forecast

def test_fetch_forecast_name_error(mocker):
    # Mock requests.get to return a parsed structure where WeatherCode appears before PoP6h, triggering NameError if val is unassigned.
    mock_resp = mocker.Mock()
    mock_resp.json.return_value = {
        "success": "true",
        "records": {
            "locations": [{"location": [{"locationName": "三峽區", "weatherElement": [
                {"elementName": "WeatherDescription", "time": [{"startTime": "2026-02-22T18:00:00+08:00", "endTime": "2026-02-23T06:00:00+08:00", "elementValue": [{"value": "Clear"}]}]}
            ]}]}]
        }
    }
    mocker.patch("requests.get", return_value=mock_resp)
    
    # Should not raise NameError
    try:
        fetch_forecast()
    except NameError:
        pytest.fail("NameError was raised")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_fetch_cwa_bugs.py`
Expected: FAIL (NameError: free variable 'val' referenced before assignment)

**Step 3: Write minimal implementation**

In `data/fetch_cwa.py`, inside `fetch_forecast` around line 231, replace the scope of `val`:
Change from:
```python
                        elif el_name in ("WeatherCode", "Weather"):
                            slot[el_name] = _safe_int(val)
```
to:
```python
                        elif el_name in ("WeatherCode", "Weather"):
                            slot[el_name] = _safe_int(tv["value"])
```
Also, remove the duplicated, unused loop in `fetch_forecast_7day` (lines 305–311).

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_fetch_cwa_bugs.py`
Expected: PASS

**Step 5: Commit**

```bash
git add data/fetch_cwa.py tests/test_fetch_cwa_bugs.py
git commit -m "fix(data): resolve NameError in fetch_cwa and remove dead code loop"
```

---

### Task 4: Fix `conversation.py` UnboundLocalError (E5)

**Files:**
- Modify: `history/conversation.py:100-140`

**Step 1: Write the failing test**

```python
# python -c script to verify failure
import os
os.environ["RUN_MODE"] = "CLOUD"
from history.conversation import save_day

try:
    save_day("2026-02-22", {}, {}, "", {}, {}, {})
except UnboundLocalError:
    print("FAIL: UnboundLocalError raised")
except Exception as e:
    # Google cloud exceptions are expected if not authed, but UnboundLocalError should not happen
    if "blob" in str(e) or isinstance(e, UnboundLocalError):
        print("FAIL: UnboundLocalError raised")
    else:
        print("PASS")
```

**Step 2: Run test to verify it fails**

Run: `python check_unbound.py`
Expected: FAIL: UnboundLocalError raised

**Step 3: Write minimal implementation**

In `history/conversation.py`, move the `blob` instantiation so it is available outside the try/except block.

```python
    try:
        if RUN_MODE == "LOCAL":
            history_map = _load_history_map_local()
        else:
            client = storage.Client()
            bucket = client.bucket(GCS_BUCKET_NAME)
            blob = bucket.blob(GCS_HISTORY_KEY) # defined here unconditionally for CLOUD
            
            try:
                raw = blob.download_as_text(encoding="utf-8")
                history_map: dict[str, dict] = json.loads(raw)
            except NotFound:
                history_map = {}

    except Exception as exc:
        logger.warning("Could not load existing history for merge: %s — starting fresh", exc)
        history_map = {}
        # Ensure blob is defined if it failed earlier
        if RUN_MODE != "LOCAL" and 'blob' not in locals():
            client = storage.Client()
            bucket = client.bucket(GCS_BUCKET_NAME)
            blob = bucket.blob(GCS_HISTORY_KEY)
```

**Step 4: Run test to verify it passes**

Run: `python check_unbound.py`
Expected: PASS

**Step 5: Commit**

```bash
git add history/conversation.py
git commit -m "fix(history): resolve UnboundLocalError when history load fails in CLOUD mode"
```

---

### Task 5: Fix Stale Import in Tests (TS2)

**Files:**
- Modify: `tests/test_processor.py:4`
- Modify: `tests/test_processor.py` to use pytest

**Step 1: Write the failing test**

Run: `pytest tests/test_processor.py`
Expected: FAIL (ImportError: cannot import name 'processor' from 'data')

**Step 2: Write minimal implementation**

In `tests/test_processor.py`, replace:
```python
from data import processor
```
with:
```python
from data import weather_processor as processor
```

**Step 3: Run test to verify it passes**

Run: `pytest tests/test_processor.py`
Expected: PASS

**Step 4: Commit**

```bash
git add tests/test_processor.py
git commit -m "fix(test): update stale data.processor import in tests"
```

---

### Task 6: Remove `verify=False` and Global Patching (S4, S5, A3)

**Files:**
- Modify: `app.py:19-32`
- Modify: `data/fetch_cwa.py:46, 145, 281`
- Modify: `data/fetch_moenv.py:22, 43, 91`

**Step 1: Write the failing test**

Run: `grep "verify=False" data/fetch_cwa.py`
Expected: FAIL (matches 3 occurrences)

**Step 2: Write minimal implementation**

1. In `app.py`, remove lines 19-32 entirely.
2. In `data/fetch_cwa.py`, change `requests.get(..., verify=False)` to `requests.get(...)` on lines 46, 145, 281.
3. In `data/fetch_moenv.py`, remove `urllib3.disable_warnings(...)` on line 22, and remove `verify=False` on lines 43, 85.

**Step 3: Run test to verify it passes**

Run: `grep "verify=False" data/fetch_cwa.py`
Expected: PASS (empty output)

Run: `grep "disable_warnings" data/fetch_moenv.py`
Expected: PASS (empty output)

**Step 4: Commit**

```bash
git add app.py data/fetch_cwa.py data/fetch_moenv.py
git commit -m "fix(sec): remove insecure verify=False and global request monkeypatching"
```

---

### Task 7: Fix XSS via `innerHTML` in `app.js` (S6)

**Files:**
- Modify: `web/static/app.js`

**Step 1: Write the failing test**

Run: `grep "innerHTML = " web/static/app.js`
Expected: FAIL (matches occurrences in `app.js`)

**Step 2: Write minimal implementation**

In `web/static/app.js`, refactor instances of `.innerHTML = \`<span class="log-msg">...${msg}...</span>\`` to use safe DOM building or strictly separate the HTML structure from variable values using `.textContent`.

Example replacement for `window.onerror` log injection:
```javascript
    const div = document.createElement('div');
    div.className = 'log-entry error';
    const span = document.createElement('span');
    span.className = 'log-msg';
    span.textContent = `Runtime Error: ${msg}`;
    div.appendChild(span);
    logList.appendChild(div);
```

Refactor alert UI generation (lines 211+), Timeline card generation (lines 288+), and Narration text blocks (lines 476+) to assign text content using `.textContent` instead of injecting template strings into `.innerHTML`.

**Step 3: Run test to verify it passes**

Run evidence check: Manually inspect `app.js` to ensure variables like `msg`, `item.title`, `item.text`, `seg.display_name`, `p.text`, etc. are explicitly assigned via `el.textContent = ...` or DOM node creation.

**Step 4: Commit**

```bash
git add web/static/app.js
git commit -m "fix(sec): replace unsafe innerHTML assignments with textContent in app.js"
```
