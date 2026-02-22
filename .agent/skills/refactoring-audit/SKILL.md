---
name: Refactoring Audit
description: Unified playbook for executing and auditing large-scale structural refactoring, renaming, and technical debt remediation.
---

## Unified Debug Process

### Phase 1: Triage (What class of problem is this?)
This process applies to structural codebase changes, specifically:
- **Comprehensive Renaming:** Changing filenames or core module names that have widespread references.
- **Code Extraction / Debt Remediation:** Splitting monolithic files into smaller modules or extracting shared helpers.
- **Refactor Auditing:** Verifying that a planned structural change was completely and cleanly implemented.

### Phase 2: Isolation (Narrow to the smallest reproducible case)
Before making any changes, map the entire "blast radius" of the target code:
- **Read entry points and configuration files:** Don't just look at source code. Check deployment scripts, Dockerfiles, HTML templates, and manifest files.
- **Review the architectural plan:** If this is an extraction or remediation, read the audit or planning document first to understand the target state.

### Phase 3: Diagnosis (Session-derived heuristics, ordered by likelihood)
When determining what went wrong during a refactor or where to start:
1. **The Line-Count Heuristic:** If a monolith was supposed to be extracted, check its total line count. If it hasn't significantly decreased to the target size, the extraction is incomplete or dead code was left behind.
2. **The Duplicate Definition Heuristic:** Check the original monolithic file for local definitions of functions/constants that were supposed to be imported from the newly extracted modules.
3. **The Plan-vs-Reality Heuristic:** Manually cross-reference the task checklist against the actual file system. Do the newly specified test files actually exist? Is there a missing orchestration file?
4. **The Stale Reference Heuristic:** Search the entire codebase for the old filenames or old function names.

### Phase 4: Fix Protocol (Verified patterns from sessions, with conditions)

**If Condition:** You are renaming modules or files with widespread dependencies.
**Fix approach:**
1. Copy the file to the new name.
2. Patch all import references across the codebase (including HTML, config, and deployment scripts).
3. Update docstrings inside the renamed files.
4. Run a codebase-wide regex/grep search for the old name.
5. *Only after* confirming zero stale references, delete the old files.
6. Run one final grep to catch any stragglers, and patch them.

**If Condition:** You are extracting domain logic or moving shared helpers.
**Fix approach:**
1. Organize the work into logical batches (e.g., Batch 1: Code extraction and dead code removal. Batch 2: Dependency version pinning).
2. Extract the code to the new module.
3. **Crucial:** Immediately delete the duplicate code from the original source file. Do not leave it as dead code.
4. Wire up the imports in the original file to point to the new module.

### Phase 5: Regression Check (What broke last time after a fix)
- **The Grep Guarantee:** Always run a strict search for the exact old names/variables. A successful refactor must yield *zero* results for deprecated terms.
- **Test Suite Verification:** Verify that new test files were actually created for the newly extracted modules. Do not confuse legacy ad-hoc testing scripts with formal test suites (e.g., missing pytest coverage).
- **Dangling Imports:** Check for missing imports or broken signatures (like a missing injected parameter) in the files that originally contained the monolithic code.

### Phase 6: Known Edge Cases (Unresolved or partially resolved from sessions)
- **The "Phantom Extraction" Edge Case:** An agent successfully creates the new extracted module and wires up the imports, but completely forgets to delete the original code block from the monolith. *Workaround — Root cause unresolved:* The code functions correctly, but the technical debt (file size) is not reduced. This requires manual auditing (Phase 3) to uncover and fix.
- **Hidden Dependencies:** References to renamed files often hide in non-source files like build scripts, Dockerfiles, or frontend templates. Standard IDE refactoring tools usually miss these, necessitating the heavy grep protocol.
- **Test File Confusion:** Legacy scripts with names similar to formal test files can trick agents into believing a test suite exists.
