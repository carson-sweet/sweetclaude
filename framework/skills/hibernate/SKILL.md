---
name: sweetclaude-hibernate
description: "Use when hibernating or unhibernating a project managed by SweetClaude. Extends hibernate-project with SweetClaude phase state, deference level, and improvement register handling. Triggers on 'hibernate', 'freeze', 'shelve', 'thaw', 'unhibernate', or presence of HIBERNATION.md."
---

<preflight-guard>
STOP. Before executing this skill, check: does state/phase.yaml exist in the project working repo or project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# SweetClaude Hibernate

Extends `hibernate-project` with SweetClaude-specific state management. Invoke `hibernate-project` for the core process.

---

## Hibernate — SweetClaude Additions

**Before hibernate-project Step 4 (Write HIBERNATION.md):** Gather SweetClaude state to include.

1. Read `state/phase.yaml` from the SweetClaude working repo. Extract:
   - Current phase
   - Current work type
   - Deference level
   - Any pending detour
2. Read `state/improvement-register.md`. Summarize entries.
3. Read `state/decision-log.md`. Note count and date range.
4. Check for in-progress stories, specs, or brainstorm outputs in working repo.

**During Step 4:** Add a "SweetClaude State" section to HIBERNATION.md using this template:

```
## SweetClaude State

- **Phase:** {phase name}
- **Work type:** {net-new feature / bug fix / enhancement / iteration}
- **Deference level:** {Collaborative / Guided / Autonomous}
- **Pending detour:** {description or "none"}
- **Improvement register:** {N} entries — {brief summary of key learnings}
- **Decision log:** {N} entries spanning {date range}
- **Working repo:** {path or "not found"}
```

If no SweetClaude working repo exists:

```
## SweetClaude State

SweetClaude was not initialized for this project.
```

---

## Unhibernate — SweetClaude Additions

**After hibernate-project Step 2 (Read Hibernation State):** Read the SweetClaude State section from HIBERNATION.md.

**During Step 5 (Propose Thaw Plan):** Add SweetClaude context:

- If SweetClaude state was recorded:
  > "SweetClaude was active at {phase}, {deference level}. Resume with that configuration, or reconfigure?"

  If confirmed, update `state/phase.yaml` to active. If changes wanted, ask for new deference level.

- If no SweetClaude state:
  > "This project didn't use SweetClaude before. Want to initialize it? SweetClaude manages a 7-phase development pipeline with structured processes for discovery, design, TDD, and review."

  If accepted, invoke `/sweetclaude:init`.

**During Step 6 (Update Docs):** If SweetClaude is active, update `state/phase.yaml` to reflect resumed status.
