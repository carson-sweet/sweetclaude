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

Read `.sweetclaude/state/phase.yaml` from `.sweetclaude/`. Check `schema_version` first:
- If `schema_version` is absent or `1`, warn the user: "Your `phase.yaml` is on schema v1. Active work item tracking requires schema v2. Run `/sweetclaude:master` to upgrade." Display only `version_stage` and `deference_level` from the file, then stop — do not proceed to Steps 3 or 4.

Extract:
- `version_stage` — lifecycle stage (PROTOTYPE / ALPHA / BETA / GA / SCALED / MAINTAINED). Default: PROTOTYPE if not set.
- `active_work_item.type` — work type (e.g. bug-fix, net-new-feature). May be `~` if no active work item.
- `active_work_item.phase` — current phase within this work item's workflow
- `active_work_item.workflow` — ordered list of phases for this work item (e.g. [DIAGNOSE, IMPLEMENT, VERIFY, SHIP])
- `active_work_item.title` — short description of the work
- `active_work_item.entry_category` — how work was initiated (cold-start / mid-project-planned / mid-project-reactive)
- `deference_level`

### Step 2: Read recent activity

1. **Git log** — last 5-10 commits. What was worked on most recently?
2. **Uncommitted state** — any uncommitted files in `.sweetclaude/`? Recent decision log entries?
3. **Improvement register** — any learnings from previous sessions?
4. **Open artifacts** — check for:
   - In-progress specs in `docs/`
   - Incomplete stories in `.sweetclaude/stories/`
   - Brainstorm outputs in `.sweetclaude/brainstorm/`
   - Strategy artifacts in `strategy/`
5. **Active milestones** — scan `docs/milestones/MS-*.md` if the directory exists. For each with `**Status:** active`, compute the `met/total criteria met` count from Measuring-success checkboxes. If the directory does not exist, omit the milestones section from the output.

### Step 3: Present status

If the `active_work_item` key is present AND type, phase, and workflow are not `~` or null, use this template.

Compute before rendering:
- **step_N** = 1-based position of `active_work_item.phase` within `active_work_item.workflow` (first phase = 1). If `active_work_item.phase` is not found in the workflow list, display `(phase position unknown)` instead of `(step N of M)` and show the full workflow without any highlighting.
- **step_M** = total number of phases in `active_work_item.workflow`
- **Workflow line** = all phases joined by ` → `, with only the current phase wrapped in `*asterisks*`. Render the complete list — no split notation. Example for IMPLEMENT as current in [DIAGNOSE, IMPLEMENT, VERIFY, SHIP]: `DIAGNOSE → *IMPLEMENT* → VERIFY → SHIP`

```
SweetClaude Status — {project name}
═══════════════════════════════════

Version stage:  {version_stage}
Work item:      [{active_work_item.id}] {active_work_item.title} [{active_work_item.type}]
Phase:          {active_work_item.phase}  (step {step_N} of {step_M})
Workflow:       {all phases joined by →, current in *asterisks*}
Deference:      {deference_level}

Done:
  - {completed artifact or milestone}
  - ...

In progress:
  - {artifact or task currently open}
  - ...

Active milestones:
  - {MS-XXX Title        met/total criteria met}
  - {MS-XXX Title        met/total criteria met — ready to complete if all met}
  (omit this section if no milestones are active or if docs/milestones/ does not exist)

Next:
  → {the logical next step based on phase, open artifacts, and exit criteria}

Recent activity:
  {last 3-5 commits, one line each}
```

If the `active_work_item` key is absent OR any of type, phase, workflow is `~` or null, use this template instead:

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

If no active work item (idle template was used): suggest running `/sweetclaude:find-skill` to start one. Skip entry_category tailoring.

If an active work item exists, propose one concrete next action. Tailor it using `active_work_item.entry_category`:
- **cold-start** or **mid-project-planned**: suggest the next phase skill or artifact to produce
- **mid-project-reactive**: lead with urgency — surface the resolution skill or escalation path first
- **absent or unrecognized**: default to cold-start behavior

> "Next step: {action}. Run `/sweetclaude:{skill}` to do that, or `/sweetclaude:next-steps` to walk through the pipeline."

Do not start doing the work. Orient and suggest. The user decides what to do.
