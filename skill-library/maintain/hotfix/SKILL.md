---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Hotfix — minimal patch for a production issue with expedited review and mandatory post-mortem."
---


!`bash ${CLAUDE_SKILL_DIR}/../../hooks/read-state.sh session-state`

<preflight-guard>
STOP. Before executing this skill, check: if pre-loaded state above shows STATE_NOT_FOUND, or neither .sweetclaude/state/sweetclaude.yaml nor .sweetclaude/state/phase.yaml exists, do not proceed. Instead say: "This project is not configured for SweetClaude. Running pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# SweetClaude Hotfix

Minimal patch for a production issue. Fix only the immediate problem — no refactoring, no cleanup, no related improvements.

**Phases:** DIAGNOSE → IMPLEMENT → SHIP → POST-MORTEM (follow-on).

---

## Step 1: Confirm production impact (DIAGNOSE)

```bash
git log --oneline -5 2>/dev/null
```

> "What is broken in production? I need:
>
> 1. What is the specific failure — error message, broken behavior, or degraded state?
> 2. Severity — P0 (service down / data loss / security), P1 (core workflow broken, no workaround), P2 (degraded, workaround exists)?
> 3. Scope — all users or a subset?"

Record: `INCIDENT_DESCRIPTION`, `SEVERITY`, `SCOPE`.

---

## Step 2: Identify root cause (DIAGNOSE)

> "What is the root cause? If known, point me at the file and function. If not, what's the working hypothesis?"

If the user doesn't know the root cause, help narrow it down:

```bash
git log --oneline --since="48 hours ago" 2>/dev/null | head -10
```

> "These are the recent changes. Is the breakage correlated with any of them?"

Once root cause is identified (or best hypothesis established):

```bash
# Read the affected code
```

Record: `ROOT_CAUSE`, `AFFECTED_FILES`.

---

## Step 3: Scope the fix (DIAGNOSE → IMPLEMENT gate)

State the fix explicitly before writing code:

> "Here's the minimal fix:
>
> - **What changes:** {specific change}
> - **What does NOT change:** {explicitly list anything tempting to clean up that must be left alone}
> - **Files to touch:** {list}
>
> This is a hotfix — I will not refactor, clean up, or improve anything beyond the immediate fix."

Wait for approval before proceeding.

Log to `.sweetclaude/state/decision-log.md`:

```markdown
| {next #} | {today} | Hotfix scoped: {INCIDENT_DESCRIPTION} | Fix: {one-line description}. Severity: P{N}. | N/A |
```

---

## Step 4: Implement the fix (IMPLEMENT)

**TDD Level 0** — fix + regression test in the same session.

1. Write a regression test that reproduces the production failure (RED).
2. Implement the minimal fix (GREEN).
3. Run the full test suite to confirm no regressions.

```bash
# Run project test suite
```

**Scope enforcement:** If you find yourself editing files not in the `AFFECTED_FILES` list, stop. That's scope creep. The hotfix touches only what's broken.

---

## Step 5: Expedited review (IMPLEMENT → SHIP gate)

Normal code review is relaxed for hotfixes, but not eliminated. At minimum one of:

Present via AskUserQuestion:

| Option | Description |
|---|---|
| **Self-review checklist** | Walk through a structured self-review and log it |
| **Async notification** | Send a message to a teammate for async review post-deploy |

**If self-review:** walk through these checks and log each as pass/fail:

1. Fix targets root cause, not just symptom
2. No unrelated changes in the diff
3. Regression test covers the failure mode
4. No secrets or credentials in the diff
5. No new dependencies added

Log the review to `.sweetclaude/state/decision-log.md`:

```markdown
| {next #} | {today} | Hotfix review: {method} | {pass/fail summary} | N/A |
```

**If async notification:** ask who to notify and what channel. The user sends the notification — do not send messages on their behalf.

---

## Step 6: Ship (SHIP)

```bash
git diff --stat
```

> "Ready to ship. The diff above is the hotfix.
>
> **Rollback plan:** {state how to undo — git revert, feature flag, redeploy previous}
>
> For P0/P1: deploy now, monitor after. For P2: normal deploy cadence is fine."

Offer via AskUserQuestion:

| Option | Description |
|---|---|
| **Commit and open PR** | Commit with conventional message, open PR via `gh pr create` |
| **Commit, merge, and push** | Commit, merge to main, push — fastest path for P0/P1 |
| **Commit only** | Commit staged changes; I'll handle deploy myself |

After deploy:

> "Confirm the fix is working in production:
>
> 1. Is the broken behavior resolved?
> 2. Error rates back to baseline?
> 3. Any side effects?"

If not resolved: reassess. Consider rollback (`/sweetclaude:maintain rollback-revert`) or a different fix approach.

---

## Step 7: Spawn post-mortem (required)

Every hotfix requires a post-mortem. No exceptions.

Log to `.sweetclaude/state/decision-log.md`:

```markdown
| {next #} | {today} | POST-MORTEM required for hotfix: {INCIDENT_DESCRIPTION} | Required after all hotfixes — root cause analysis and prevention | N/A |
```

Ask via AskUserQuestion:

| Option | Description |
|---|---|
| **Create POST-MORTEM backlog item now** | Write an ISSUE for the post-mortem and link it to this hotfix |
| **Skip — I'll create it later** | The decision-log entry marks the obligation |

If "Create now": derive next issue ID and write the backlog item:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cache.py --project-dir . --query next-id --prefix ISSUE
```

Write to `.sweetclaude/product/backlog/ISSUE-{NNN}-post-mortem-{slug}.md`:

```yaml
id: ISSUE-{NNN}
title: POST-MORTEM — {INCIDENT_DESCRIPTION}
type: enhancement
priority: now
status: new
created: {today}
labels:
- post-mortem
- hotfix
```

Body: "Follow-on from hotfix. Document timeline, root cause (5 whys), contributing factors, and action items to prevent recurrence. If the fix was a workaround, also create a tech-debt follow-up.\n\nRun `/sweetclaude:maintain postmortem` to begin."

Rebuild cache:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cache.py --project-dir . --rebuild
```

> "Hotfix complete. {ISSUE-NNN} created for the post-mortem — run `/sweetclaude:maintain postmortem` when ready."

If "Skip": log the skip to decision log.

---

## Rules

- **Minimal fix only.** No refactoring, no cleanup, no related improvements. Fix the immediate problem and stop.
- **Regression test is not optional.** The test happens in this session, not later. TDD Level 0.
- **Scope enforcement is active.** If you touch files outside the identified affected area, stop and justify.
- **Do not skip the review entirely.** Expedited means self-review or async notification — not no review.
- **Post-mortem is mandatory.** A hotfix that ships without spawning a post-mortem work item is incomplete.
- **For P0/P1:** compress the ceremony but not the discipline. Every step still happens; documentation can be terse.
- **Rollback is always an option.** If the fix isn't working, recommend `/sweetclaude:maintain rollback-revert` instead of iterating on a broken patch.
