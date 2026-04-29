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
- `version_stage` — lifecycle stage (PROTOTYPE / ALPHA / BETA / GA / SCALED / MAINTAINED). Default: PROTOTYPE if not set.
- `active_work_item.type` — work type (e.g. bug-fix, net-new-feature). May be `~` if no active work item.
- `active_work_item.phase` — current phase within this work item's workflow
- `active_work_item.workflow` — ordered list of phases for this work item (e.g. [DIAGNOSE, IMPLEMENT, VERIFY, SHIP])
- `active_work_item.title` — short description of the work
- `active_work_item.entry_category` — how work was initiated
- `deference_level`
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

If `active_work_item` fields are set (type, phase, workflow are not `~`), use this template:

```
SweetClaude Status — {project name}
═══════════════════════════════════

Version stage:  {version_stage}
Work item:      {active_work_item.title} [{active_work_item.type}]
Phase:          {active_work_item.phase}  (step N of M in workflow)
Workflow:       {phase1} → {phase2} → ... → {phaseN}
                (current: {active_work_item.phase highlighted with *asterisks*})
Deference:      {deference_level}

Done:
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

If `active_work_item` is absent or all fields are `~`, use this template instead:

```
SweetClaude Status — {project name}
═══════════════════════════════════

Version stage:  {version_stage}
Work item:      (none — run /sweetclaude:find-skill to start one)
Deference:      {deference_level}

Recent activity:
  {last 3-5 commits, one line each}
```

### Step 4: Suggest action

Based on the status, propose one concrete next action:

> "Next step: {action}. Run `/sweetclaude:{skill}` to do that, or `/sweetclaude:next-steps` to walk through the pipeline."

Do not start doing the work. Orient and suggest. The user decides what to do.
