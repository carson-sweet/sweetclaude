---
name: design/manage-decisions
description: "Record and track design and architecture decisions with context, options considered, decision made, and rationale. Queryable later. Replaces ADR templates."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Manage Decisions

Record or query design decisions.

## Record a decision

When $ARGUMENTS describes a decision to record:

1. **Capture the context.** What situation prompted this decision? What forces are at play?

2. **List options considered.** For each option:
   - What is it?
   - Pros
   - Cons
   - Why it was or wasn't chosen

3. **State the decision.** What was decided?

4. **Rationale.** Why this option over the others? What was the deciding factor?

5. **Consequences.** What follows from this decision? What's easier now? What's harder?

6. **Write the entry:**

```
## DEC-{NNN}: {Title}

**Date:** {date}
**Status:** Accepted
**Context:** {what prompted this}

**Options:**
1. {option} — {pros/cons summary}
2. {option} — {pros/cons summary}

**Decision:** {what was decided}
**Rationale:** {why}
**Consequences:** {what follows}
```

7. **Append** to `.sweetclaude/state/decision-log.md` in `.sweetclaude/`. Increment DEC number from last entry.

## Query decisions

When $ARGUMENTS asks about a past decision:

- Read `.sweetclaude/state/decision-log.md`
- Find the relevant entry
- Present it with context

Common queries: "why did we choose X?", "what decisions have we made about Y?", "list all decisions"
