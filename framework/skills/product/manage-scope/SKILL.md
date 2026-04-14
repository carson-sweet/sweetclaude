---
name: sweetclaude-product-manage-scope
description: Track scope changes when items move between in-scope and out-of-scope. Logs the change with rationale and date. Use when scope decisions are made during any phase.
---

<preflight-guard>
STOP. Before executing this skill, check: does state/phase.yaml exist in the project working repo or project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Scope Change Tracker

Log a scope change for: $ARGUMENTS

## Process

1. **Read current scope** from the working repo's PRD or scope document.

2. **Identify the change:**
   - What item is moving?
   - Direction: in-scope → out-of-scope, or out-of-scope → in-scope?
   - Which phase are we in?
   - What's the rationale?

3. **Append to scope log** at `state/scope-changes.md` in the working repo:

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

- Always log with rationale — "because we decided" is not a rationale.
- Scope changes are normal, not failures. Don't frame them negatively.
- If a scope change invalidates existing work, flag it but don't delete the work — the user decides what to do.
