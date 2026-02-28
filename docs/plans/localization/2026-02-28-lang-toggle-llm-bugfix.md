# Language Toggle LLM Bugfix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the language toggle bug so the LLM generation clients explicitly request the localized system prompt.

**Architecture:** The `lang` parameter is currently dropped between `backend/pipeline.py` and the LLM clients (`gemini_client.py` and `claude_client.py`). We will update the LLM client function signatures to accept the `lang` parameter and explicitly pass it when loading the system prompt from `llm_prompt_builder.py`.

**Tech Stack:** Python

---

### Task 1: Update Gemini Client

**Files:**
- Modify: `c:\Users\User\.gemini\antigravity\scratch\family-weather\narration\gemini_client.py:24-34`

**Step 1: Write the failing test**

*(No formal unit tests exist for this specific parameter plumbing; this is an integration fix. We will rely on manual test of the pipeline.)*

**Step 2: Run test to verify it fails**

*(Skip formal unit test)*

**Step 3: Write minimal implementation**

```python
def _load_system_prompt(lang: str = 'en') -> str:
    """Import the system prompt from prompt_builder to avoid duplication."""
    from narration.llm_prompt_builder import build_system_prompt
    return build_system_prompt(lang=lang)


def generate_narration(messages: list[dict], model_override: str | None = None, lang: str = 'en') -> str:
    """
    Send the prepared message list to Gemini and return the narration text.
    """
    system_prompt = _load_system_prompt(lang)
```

**Step 4: Run test to verify it passes**

*(Skip formal unit test)*

**Step 5: Commit**

```bash
git add narration/gemini_client.py
git commit -m "fix: pass lang parameter to gemini system prompt"
```

### Task 2: Update Claude Client

**Files:**
- Modify: `c:\Users\User\.gemini\antigravity\scratch\family-weather\narration\claude_client.py:29-50`

**Step 1: Write the failing test**

*(Skip formal unit test)*

**Step 2: Run test to verify it fails**

*(Skip formal unit test)*

**Step 3: Write minimal implementation**

```python
def _load_system_prompt(lang: str = 'en') -> str:
    """Import the system prompt from prompt_builder."""
    from narration.llm_prompt_builder import build_system_prompt
    return build_system_prompt(lang=lang)


def generate_narration(messages: list[dict], model_override: str | None = None, lang: str = 'en') -> str:
    """
    Send the prepared message list to Claude and return the narration text.

    Args:
        messages: Output of prompt_builder.build_prompt() (Gemini format).
                 We need to convert this to Claude format.

    Returns:
        The full broadcast narration as a plain-text string.

    Raises:
        RuntimeError if the API call fails.
    """
    client = _get_client()
    system_prompt = _load_system_prompt(lang)
```

**Step 4: Run test to verify it passes**

*(Skip formal unit test)*

**Step 5: Commit**

```bash
git add narration/claude_client.py
git commit -m "fix: pass lang parameter to claude system prompt"
```

### Task 3: Update LLM Prompt Builder

**Files:**
- Modify: `c:\Users\User\.gemini\antigravity\scratch\family-weather\narration\llm_prompt_builder.py:249-254`

**Step 1: Write the failing test**

*(Skip formal unit test)*

**Step 2: Run test to verify it fails**

*(Skip formal unit test)*

**Step 3: Write minimal implementation**

*(Remove unused `lang` param from `build_prompt` strictly for cleanliness to prevent future confusion)*

```python
def build_prompt(
    processed_data: dict,
    history: list[dict],
    today_date: str | None = None,
) -> list[dict]:
```

**Step 4: Run test to verify it passes**

*(Skip formal unit test)*

**Step 5: Commit**

```bash
git add narration/llm_prompt_builder.py
git commit -m "refactor: remove unused lang parameter from build_prompt"
```

### Task 4: Update Backend Pipeline

**Files:**
- Modify: `c:\Users\User\.gemini\antigravity\scratch\family-weather\backend\pipeline.py:96-112`

**Step 1: Write the failing test**

*(Skip formal unit test)*

**Step 2: Run test to verify it fails**

*(Skip formal unit test)*

**Step 3: Write minimal implementation**

```python
        messages = build_prompt(processed, history, date_str)
        if provider_upper == "GEMINI":
            if generate_gemini is None:
                logger.error("Gemini client is None (likely import failure or missing key)")
                raise RuntimeError("Gemini client not available")
            logger.info("Calling Gemini client...")
            text = generate_gemini(messages, lang=lang)
            logger.info("Gemini narration successful.")
            result = text, "gemini"
        elif provider_upper == "CLAUDE":
            if generate_claude is None:
                logger.error("Claude client is None (likely import failure or missing key)")
                raise RuntimeError("Claude client not available")
            logger.info("Calling Claude client...")
            text = generate_claude(messages, lang=lang)
            logger.info("Claude narration successful.")
            result = text, "claude"
```

**Step 4: Run test to verify it passes**

*(Integration check: manual validation pipeline processes zh-TW correctly)*

**Step 5: Commit**

```bash
git add backend/pipeline.py
git commit -m "fix: pass lang parameter to generation clients in pipeline"
```
