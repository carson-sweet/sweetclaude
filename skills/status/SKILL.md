---
description: "Orient to the current project. Shows what phase you're in, what's been done, what's pending, and what the logical next step is. Use when starting a session, returning after a break, or asking 'where are we?'"
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Running pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# SweetClaude Status

Show where the project stands: what is done, what is open, what comes next.

## Process

### Step 1: Read project state

Read `.sweetclaude/state/phase.yaml` from `.sweetclaude/`. Extract:
- Current phase
- Current work type
- Deference level
- Active bucket (strategy/product/design/code)
- Any pending detour

### Step 2: Read recent activity

1. **Git log** — last 5-10 commits. What was worked on most recently?
2. **Uncommitted state** — any uncommitted files in `.sweetclaude/`? Recent decision log entries?
3. **Improvement register** — any learnings from previous sessions?
4. **Open artifacts** — check for:
   - In-progress specs in `docs/`
   - Incomplete stories in `.sweetclaude/stories/`
   - Brainstorm outputs in `.sweetclaude/brainstorm/`
   - Strategy artifacts in `strategy/`
5. **Active milestones** — scan `docs/milestones/MS-*.md`. For each with `**Status:** active`, compute the `n/N criteria met` count from Measuring-success checkboxes.

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

Active milestones:
  - {MS-XXX Title        n/N criteria met}
  - {MS-XXX Title        n/N criteria met — ready to complete if all met}
  (omit this section if no milestones are active)

Next:
  → {the logical next step based on phase, open artifacts, and exit criteria}

Recent activity:
  {last 3-5 commits, one line each}
```

### Step 4: Suggest action

Based on the status, propose one concrete next action:

> "Next step: {action}. Run `/sweetclaude:{skill}` to do that, or `/sweetclaude:auto-flow` to walk through the pipeline."

Do not start doing the work. Orient and suggest. The user decides what to do.
