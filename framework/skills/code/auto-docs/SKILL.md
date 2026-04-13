---
name: sweetclaude-code-auto-docs
description: Automatically update documentation when implementation changes behavior. Runs during Verify phase. Detects which docs reference changed behavior, proposes updates for user approval.
---

<preflight-guard>
STOP. Before executing this skill, check: does state/phase.yaml exist in the project working repo or project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Auto-Documentation Updates

When implementation changes behavior, identify and update affected documentation.

## Process

1. **Identify changed behavior.** Read the diff (staged or recent commits). Extract: new functions/endpoints, changed function signatures, modified behavior, removed capabilities.

2. **Scan for affected docs.** Search these locations for references to changed behavior:
   - Project README.md
   - API documentation (if exists)
   - CLAUDE.md (project-level)
   - docs/adr/ (architecture decision records)
   - Working repo specs (PRD, tech spec, architecture)
   - Inline doc comments in changed files

3. **For each affected doc:**
   - Show the current text that's now stale
   - Propose the updated text
   - Wait for user approval before writing

4. **Update traceability.** If the change affects the requirements → tests → code chain, update `traceability/requirements-map.md` in the working repo.

## Rules

- Only update docs that exist. Never create new docs unprompted.
- Propose changes, don't write them silently.
- If a doc reference is ambiguous (might or might not be affected), flag it and ask.
- Skip style-only changes — only update when behavior or interface changed.
- If the change invalidates an ADR, flag it prominently: "ADR-XXX may need revision."
