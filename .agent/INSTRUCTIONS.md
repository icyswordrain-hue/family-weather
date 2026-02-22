# AGENT OPERATING INSTRUCTIONS
> Load at session start. All rules are unconditional.

---

## OUTPUT FORMAT

- Never output an entire file unless the user explicitly writes "full file" or "rewrite entire file".
- Output only the specific function, class, or block being modified.
- Wrap every change in a SEARCH/REPLACE block with exactly 3 lines of surrounding context above and below.
- End every response with exactly one line: `// Changed: [what] — [why]`
- No preamble. No postamble. No apologies. 
- No markdown headers or bullet walkthroughs inside code responses.

---

## THINKING BUDGET

| Task | Max Thinking Tokens |
|---|---|
| Rename, typo, CSS tweak, regex, boilerplate | 0 |
| New function from clear spec, unit test | 1,500 |
| Bug fix with non-obvious cause | 4,000 |
| Multi-file refactor, architecture decision | 10,000 |

Do not exceed the ceiling for the task category. Default to the lower tier when uncertain.

---

## FILE AND CONTEXT LOADING

- Do not read, scan, or summarize any file not explicitly named in the current user message.
- Do not speculatively load dependencies, imports, or related files.
- If a second file is genuinely required, name it and state why — then wait for user confirmation before loading.
- Do not reference or carry over content from previous sessions.

---

## CLARIFICATION

- Do not ask clarifying questions unless two or more valid implementations exist with meaningfully different outcomes.
- When uncertain, make one reasonable assumption, state it in the change summary, and proceed.
- Never ask more than one clarifying question per response.

---

## SESSION SCOPE

- Treat each session as scoped to a single task or a single file.
- If a second unrelated task appears mid-session, complete the current task first, then append:
  `// Note: new task detected — consider opening a fresh session.`

---

## PROHIBITED

- Do not summarize what you are about to do before doing it.
- Do not list planned steps before executing them.
- Do not restate the user's request back to them.
- Do not use placeholder comments like `// rest of file unchanged` — use SEARCH/REPLACE blocks only.
