---
description: Update documentation when implementation changes behavior. Runs during Verify phase. Detects which docs reference changed behavior, proposes updates for user approval.
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Auto-Documentation Updates

Find and update documentation affected by implementation changes.

## Process

1. **Identify changed behavior.** Read the diff (staged or recent commits). Extract: new functions or endpoints, changed function signatures, modified behavior, removed capabilities.

2. **Scan for affected docs.** Search these locations for references to changed behavior:
   - Project README.md
   - API documentation (if exists)
   - CLAUDE.md (project-level)
   - docs/adr/ (architecture decision records)
   - Working repo specs (PRD, tech spec, architecture)
   - Inline doc comments in changed files

3. **For each affected doc:**
   - Show the current text that is now stale
   - Propose the updated text
   - Wait for user approval before writing

4. **Update traceability.** If the change affects the requirements-to-tests-to-code chain, update `traceability/requirements-map.md` in `.sweetclaude/`.

## Rules

- Only update docs that exist. Never create new docs unprompted.
- Propose changes. Do not write them silently.
- If a doc reference is ambiguous, flag it and ask.
- Skip style-only changes. Only update when behavior or interface changed.
- If the change invalidates an ADR, flag it prominently: "ADR-XXX may need revision."
