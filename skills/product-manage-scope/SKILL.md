---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: Track scope changes when items move between in-scope and out-of-scope. Logs the change with rationale and date. Use when scope decisions are made during any phase.
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Scope Change Tracker

Log a scope change for: $ARGUMENTS

## Process

1. **Read current scope** from `.sweetclaude/`'s PRD or scope document.

2. **Identify the change:**
   - What item is moving?
   - Direction: in-scope to out-of-scope, or out-of-scope to in-scope?
   - Which phase are we in?
   - What is the rationale?

3. **Append to scope log** at `.sweetclaude/state/scope-changes.md` in `.sweetclaude/`:

```markdown
| {{date}} | {{item}} | {{direction}} | {{phase}} | {{rationale}} |
```

4. **Update the PRD** scope section if it exists — move the item between In Scope and Out of Scope lists.

5. **Check for ripple effects** — does this scope change affect:
   - Stories already written?
   - Architecture decisions?
   - Tests already created?
   - If yes, flag what needs updating.

## Rules

- Always log with rationale. "Because we decided" is not a rationale.
- Scope changes are normal, not failures. Do not frame them negatively.
- If a scope change invalidates existing work, flag it but do not delete the work. The user decides what to do.
