---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Record and track design and architecture decisions with context, options considered, decision made, and rationale."
---


!`bash ${CLAUDE_SKILL_DIR}/../../hooks/read-state.sh session-state`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/sweetclaude.yaml or .sweetclaude/state/phase.yaml exist in the project directory? If NEITHER, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
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
   - Why it was or was not chosen

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

7. **Append** to `.sweetclaude/state/decision-log.md`. Increment DEC number from last entry.

8. **Per-item excerpt (if work-item artifacts are active):** Check `.sweetclaude/state/session-state.yaml` → `active_work_item.work_dir`. If set, also write a copy of the entry to `{work_dir}/decisions/DEC-{NNN}.md`. The global decision log remains authoritative — the per-item copy is for discoverability.

## Query decisions

When $ARGUMENTS asks about a past decision:

- Read `.sweetclaude/state/decision-log.md`
- Find the relevant entry
- Present it with context

Common queries: "why did we choose X?", "what decisions have we made about Y?", "list all decisions"
