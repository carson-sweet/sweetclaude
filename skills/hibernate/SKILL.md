---
spdx-license: AGPL-3.0-or-later
description: "Use when hibernating or unhibernating a project managed by SweetClaude. Extends hibernate-project with SweetClaude phase state, deference level, and improvement register handling. NEVER invoke without explicit user request. Triggers on explicit keywords: 'hibernate', 'freeze', 'shelve', 'thaw', 'unhibernate'."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Running pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# SweetClaude Hibernate

Extends `hibernate-project` with SweetClaude-specific state management. Invoke `hibernate-project` for the core process.

---

## Hibernate — SweetClaude Additions

**Before hibernate-project Step 4 (Write HIBERNATION.md):** Gather SweetClaude state to include.

1. Read `.sweetclaude/state/phase.yaml` from `.sweetclaude/`. Extract:
   - Current phase
   - Current work type
   - Deference level
   - Any pending detour
2. Read `.sweetclaude/state/improvement-register.md`. Summarize entries.
3. Read `.sweetclaude/state/decision-log.md`. Note count and date range.
4. Check for in-progress stories, specs, or brainstorm outputs in `.sweetclaude/`.

**During Step 4:** Add a "SweetClaude State" section to HIBERNATION.md using this template:

```
SweetClaude State
═════════════════

Phase:              {phase name}
Work type:          {net-new feature / bug fix / enhancement / iteration}
Deference level:    {Collaborative / Guided / Autonomous}
Pending detour:     {description or "none"}
Improvement register: {N} entries — {brief summary of key learnings}
Decision log:       {N} entries spanning {date range}
State dir:          {path or "not found"}
```

If `.sweetclaude/` does not exist:

```
## SweetClaude State

SweetClaude was not initialized for this project.
```

---

## Unhibernate — SweetClaude Additions

**After hibernate-project Step 2 (Read Hibernation State):** Read the SweetClaude State section from HIBERNATION.md.

**During Step 5 (Propose Thaw Plan):** Add SweetClaude context:

- If SweetClaude state was recorded:

  Use AskUserQuestion with these options:
  - "Resume" — keep {phase} phase at {deference level}
  - "Reconfigure" — change the deference level before resuming

  If "Resume," update `.sweetclaude/state/phase.yaml` to active. If "Reconfigure," ask for the new deference level.

- If no SweetClaude state:
  > "This project was not using SweetClaude before. SweetClaude manages a 7-phase development pipeline covering discovery, design, TDD, and review. Set it up now?"

  If accepted, invoke `/sweetclaude:init`.

**During Step 6 (Update Docs):** If SweetClaude is active, update `.sweetclaude/state/phase.yaml` to reflect resumed status.
