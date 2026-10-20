---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Roll back or revert a deployment — identify the cause, execute the rollback, confirm recovery."
---


!`bash ${CLAUDE_SKILL_DIR}/../../hooks/read-state.sh session-state`

<preflight-guard>
STOP. Before executing this skill, check: if pre-loaded state above shows STATE_NOT_FOUND, or neither .sweetclaude/state/sweetclaude.yaml nor .sweetclaude/state/phase.yaml exists, do not proceed. Instead say: "This project is not configured for SweetClaude. Running pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# SweetClaude Rollback / Revert

Execute a rollback of a specific deploy or change. No implementation phase — this is purely identification, execution, and verification.

**Phases:** DIAGNOSE → SHIP.

---

## Step 1: Identify what to roll back

```bash
git log --oneline -10 2>/dev/null
```

```bash
git tag --sort=-creatordate | head -5 2>/dev/null
```

Ask:

> "What deploy or change caused the problem? I see these recent commits and tags.
>
> 1. Which specific commit, tag, or deploy is the cause?
> 2. How was the problem detected — monitoring, user report, or manual discovery?"

Record: `CAUSE_COMMIT`, `CAUSE_DESCRIPTION`, `DETECTION_METHOD`.

---

## Step 2: Confirm impact and choose rollback method

> "Before rolling back, I need to confirm:
>
> 1. **Impact scope** — what's broken, who's affected?
> 2. **Data impact** — will rolling back leave data in an inconsistent state? (e.g., a migration ran forward that can't be undone by reverting code)
> 3. **Stakeholders** — who needs to know this is happening?"

Then present the rollback method via AskUserQuestion:

| Option | Description |
|---|---|
| **Git revert** | Create a revert commit that undoes the change. Clean history, easy to redo later. Best when: single commit or small range, no data migration involved. |
| **Deploy previous artifact** | Redeploy the last known-good build/tag. Best when: CI/CD pipeline supports it, faster than building a new commit. |
| **Feature flag off** | Disable the feature behind a flag. Best when: the change is flag-gated and the flag can be toggled without a deploy. |

Log the decision to `.sweetclaude/state/decision-log.md`:

```markdown
| {next #} | {today} | Rollback: {CAUSE_DESCRIPTION} | Method: {chosen method}. Data impact: {assessment}. | {alternatives considered} |
```

---

## Step 3: Execute rollback

Guide the user through execution based on the chosen method. **Do not execute destructive commands yourself — the user runs them.**

**If git revert:**

```bash
git log --oneline {CAUSE_COMMIT}~1..{CAUSE_COMMIT}
```

> "To revert, run:
> ```
> git revert {CAUSE_COMMIT}
> ```
> {If multiple commits: `git revert {oldest}..{newest}`}
>
> Review the revert commit, then deploy."

**If deploy previous artifact:**

> "Deploy the last known-good artifact:
> - Tag/version: {last good tag from Step 1}
> - Deploy command: {project-specific if known, otherwise ask}
>
> Run the deploy now."

**If feature flag off:**

> "Toggle the feature flag:
> - Flag name: {ask user}
> - Target state: OFF
>
> Toggle it now."

---

## Step 4: Confirm recovery

After the rollback is executed:

> "Rollback deployed. Confirm recovery:
>
> 1. Is the broken behavior resolved?
> 2. Are error rates back to baseline?
> 3. Any side effects from the rollback — features or data that regressed?"

If not resolved: state clearly that the rollback did not fix the problem. Ask whether to try a different rollback target or switch to a patch approach (`/sweetclaude:maintain hotfix`).

If resolved, log to `.sweetclaude/state/decision-log.md`:

```markdown
| {next #} | {today} | Rollback confirmed: {CAUSE_DESCRIPTION} | Recovery verified. Method: {method}. | N/A |
```

---

## Step 5: Spawn post-mortem (required)

Every rollback requires a post-mortem. No exceptions.

Log to `.sweetclaude/state/decision-log.md`:

```markdown
| {next #} | {today} | POST-MORTEM required for rollback of {CAUSE_DESCRIPTION} | Required after all rollbacks — root cause analysis and prevention | N/A |
```

> "Rollback complete and verified. A post-mortem is required — it doesn't need to happen today, but it needs to happen.
>
> Run `/sweetclaude:maintain postmortem` when ready."

---

## Rules

- **Do not execute destructive commands yourself.** Guide the user through rollback steps. The user runs `git revert`, deploys, or toggles flags.
- **Data impact assessment is mandatory before execution.** A code rollback with a forward-only data migration can make things worse. Surface this risk explicitly.
- **Post-mortem is mandatory.** A rollback without a post-mortem work item is incomplete.
- **If the rollback fails, do not retry blindly.** Diagnose why it failed and either try a different target or switch to `/sweetclaude:maintain hotfix`.
- **Inform stakeholders before executing.** Ask who needs to know and confirm they've been notified.
