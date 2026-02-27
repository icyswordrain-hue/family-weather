# Phase 4 Remediation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Clean up dead code, redundant helpers, and stale documentation identified in Phase 4.

**Architecture:** Apply targeted deletions and consolidate scattered helper functions to resolve tech debt items DC1, DC2, A4, P1, and D1.

**Tech Stack:** Python, JavaScript

---

### Task 1: Delete `narration_utils.py` (DC1)

**Files:**
- Delete: `narration/narration_utils.py`

**Step 1: Write the failing test**

```bash
python -c "import os; assert os.path.exists('narration/narration_utils.py')"
```

**Step 2: Run test to verify it fails**

Run: `python -c "import os; assert os.path.exists('narration/narration_utils.py')"`
Expected: FAIL (if the file doesn't exist, meaning already deleted) or PASS (file exists and ready to be deleted)

**Step 3: Write minimal implementation**

Delete the file:
```bash
rm narration/narration_utils.py
```

**Step 4: Run test to verify it passes**

Run: `python -c "import os; assert not os.path.exists('narration/narration_utils.py')"`
Expected: PASS

**Step 5: Commit**

```bash
git rm narration/narration_utils.py
git commit -m "refactor(narration): remove unused narration_utils.py (DC1)"
```

---

### Task 2: Strip Stale Design Docs from `conversation.py` (D1)

**Files:**
- Modify: `history/conversation.py`

**Step 1: Write the failing test**

Run: `grep "History format" history/conversation.py`
Expected: FAIL (matches found)

**Step 2: Run test to verify it fails**

Run: `grep "History format" history/conversation.py`
Expected: match found

**Step 3: Write minimal implementation**

Remove the block of commented-out design documentation at the top of `history/conversation.py` (around lines 4-26).

**Step 4: Run test to verify it passes**

Run: `grep "History format" history/conversation.py`
Expected: PASS (no output)

**Step 5: Commit**

```bash
git add history/conversation.py
git commit -m "docs(history): strip stale design documentation from conversation.py (D1)"
```

---

### Task 3: Remove Unused JS Functions (DC2)

**Files:**
- Modify: `web/static/app.js`

**Step 1: Write the failing test**

Run: `grep -E "renderHealthCard|makeCard|aqiClass" web/static/app.js`
Expected: FAIL (returns matches if they still exist)

**Step 2: Run test to verify it fails**

Run: `grep -E "renderHealthCard|makeCard|aqiClass" web/static/app.js`
Expected: matches found

**Step 3: Write minimal implementation**

Search for and delete the unused functions `renderHealthCard()`, `makeCard()`, and `aqiClass()` inside `web/static/app.js` entirely.

**Step 4: Run test to verify it passes**

Run: `grep -E "renderHealthCard|makeCard|aqiClass" web/static/app.js`
Expected: PASS (no output)

**Step 5: Commit**

```bash
git add web/static/app.js
git commit -m "refactor(web): remove unused JS functions (DC2)"
```

---

### Task 4: Move Helpers to `data/helpers.py` (A4, P1)

**Files:**
- Modify: `data/fetch_cwa.py`
- Modify: `data/fetch_moenv.py`
- Modify: `data/helpers.py`

**Step 1: Write the failing test**

Run: `grep -E "def _safe_float|def _safe_int" data/fetch_cwa.py data/fetch_moenv.py`
Expected: FAIL (matches found in fetch scripts)

**Step 2: Run test to verify it fails**

Run: `grep -E "def _safe_float|def _safe_int" data/fetch_cwa.py data/fetch_moenv.py`
Expected: matches found

**Step 3: Write minimal implementation**

1. Extract `_safe_float` and `_safe_int` definitions from `data/fetch_cwa.py` and `data/fetch_moenv.py` (both files).
2. Ensure they are centralized in `data/helpers.py`.
3. Update imports in `data/fetch_cwa.py`, `data/fetch_moenv.py`, and any other reliant files to import them from `data/helpers.py`.

**Step 4: Run test to verify it passes**

Run: `grep -E "def _safe_float|def _safe_int" data/fetch_cwa.py data/fetch_moenv.py`
Expected: PASS (no results found in those files)

**Step 5: Commit**

```bash
git add data/fetch_cwa.py data/fetch_moenv.py data/helpers.py
git commit -m "refactor(data): consolidate safe casting helpers into data/helpers.py (A4, P1)"
```
