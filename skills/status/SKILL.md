---
name: status
description: "Orient to the current project. Shows what phase you're in, what's been done, what's pending, and what the logical next step is. Use when starting a session, returning after a break, or asking 'where are we?'"
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# SweetClaude Status

Orient to the project. Answer: where are we, what's done, what's next.

## Process

### Step 1: Read project state

Read `.sweetclaude/state/phase.yaml` from `.sweetclaude/`. Extract:
- Current phase
- Current work type
- Deference level
- Active bucket (strategy/product/design/code)
- Any pending detour

### Step 2: Read recent activity

1. **Git log** — last 5-10 commits in the code repo. What was worked on most recently?
2. **Working repo changes** — any uncommitted state in `.sweetclaude/`? Recent decision log entries?
3. **Improvement register** — any learnings from previous sessions?
4. **Open artifacts** — check for:
   - In-progress specs in `specs/`
   - Incomplete stories in `stories/`
   - Brainstorm outputs in `brainstorm/`
   - Strategy artifacts in `strategy/`

### Step 3: Present status

```
SweetClaude Status — {project name}
═══════════════════════════════════

Phase:       {phase} ({bucket})
Work type:   {type}
Deference:   {level}

Done:
  - {completed artifact or milestone}
  - {completed artifact or milestone}
  - ...

In progress:
  - {artifact or task currently open}
  - ...

Next:
  → {the logical next step based on phase, open artifacts, and exit criteria}

Recent activity:
  {last 3-5 commits, one line each}
```

### Step 4: Suggest action

Based on the status, propose one concrete next action:

> "The logical next step is {action}. Run `/sweetclaude:{skill}` to do that, or `/sweetclaude:auto-flow` to let me walk you through it."

Do not start doing the work. Just orient and suggest. The user decides what to do.
