---
spdx-license: AGPL-3.0-or-later
name: something-broke
user-invocable: true
description: "Reactive production incident skill. DIAGNOSE → SHIP → POST-MORTEM. Triage scope and severity, identify root cause, decide fix vs. rollback, resolve, and spawn the required postmortem. Entry point for anything broken in a live environment."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# SweetClaude Something Broke

Production incident triage. Fast, structured, nothing skipped.

**Phases:** DIAGNOSE → SHIP (resolution) → POST-MORTEM (required follow-on).

---

## Step 1: Check for a runbook

```bash
ls docs/runbook.md RUNBOOK.md docs/RUNBOOK.md .sweetclaude/state/runbook.md 2>/dev/null && echo "RUNBOOK_EXISTS" || echo "NO_RUNBOOK"
```

If `RUNBOOK_EXISTS`: read the runbook and surface any relevant failure modes or recovery steps at the top of the triage.

```bash
git log --oneline -5 2>/dev/null
git log --oneline --since="24 hours ago" 2>/dev/null | head -5
```

Note the last 1-3 commits and whether a deploy happened recently — correlated incidents save triage time.

---

## Step 2: Triage — ≤ 3 questions

Ask these in order. Stop as soon as you have enough to classify severity and propose a resolution path.

**Question 1:** "What exactly is broken — and when did it start?" (Probe for: error message or behavior, scope of impact, which users/endpoints affected)

**Question 2:** "Is this a regression from a recent change?" (Show the last few commits from Step 1 and ask if any are related)

**Question 3 (if needed):** "Are you seeing this everywhere or only in specific conditions?" (Probe for: specific user accounts, certain inputs, specific regions/environments)

Do not ask more than 3 questions before proposing a resolution path. If still ambiguous after 3, make a working hypothesis and state it clearly.

---

## Step 3: Classify severity

Based on triage:

| Severity | Criteria |
|---|---|
| **P0** | Service completely down, data loss risk, security breach, payment processing broken |
| **P1** | Core workflow broken for significant % of users, no workaround |
| **P2** | Degraded behavior, workaround exists, limited user impact |

State the classification:
> "This is a **P{N}** incident: {one-sentence justification}"

P0 behavior: move immediately to Step 4, compress documentation. Circle back to postmortem after resolution.
P1 behavior: follow normal flow but move with urgency.
P2 behavior: follow normal flow at normal pace.

---

## Step 4: Fix-vs-rollback decision

Present both options explicitly. Wait for user to decide:

> "**Option A — Rollback:** Revert to the last known-good state. Fastest path to recovery. Best when: the breakage was introduced by the last deploy and a rollback is clean.
>
> **Option B — Patch:** Fix the issue in-place and redeploy. Best when: rollback isn't possible (data migration), the fix is small and well-understood, or rolling back would revert other needed changes.
>
> Which path: rollback or patch?"

Log the decision to `.sweetclaude/state/decision-log.md`:
```markdown
| {next #} | {today} | P{N} incident: {brief description} | Resolution path: {rollback/patch} — {reason} | {alternative considered} |
```

---

## Step 5: Execute resolution

**If ROLLBACK:**
> "Running rollback. Use `/sweetclaude:rollback-revert` for the execution steps."

Surface the rollback work type and hand off. Come back to Step 6 after rollback is confirmed.

**If PATCH:**
> "Patching in-place. Use `/sweetclaude:hotfix` for the implementation steps."

For P0/P1: the hotfix checklist is compressed:
- Minimum code review: async notification to a stakeholder OR self-review checklist logged
- Skip non-essential steps (no doc updates during the incident)
- Come back to this skill after the fix is deployed

For P2: use the full hotfix pipeline.

---

## Step 6: Confirm resolution

After rollback or patch is deployed:

> "Is the incident resolved? Walk me through:
> 1. Can affected users access/use the system normally?
> 2. Are the error rates back to baseline?
> 3. Any residual issues?"

If not resolved: loop back to Step 4 — try the other option, or dig deeper into root cause.

Once confirmed resolved:

Log to `.sweetclaude/state/decision-log.md`:
```markdown
| {next #} | {today} | Incident resolved: {brief description} | Resolution: {what was done, by whom} | N/A |
```

---

## Step 7: Spawn postmortem (required)

Every completed `something-broke` incident requires a postmortem work item. No exceptions.

Add to `.sweetclaude/state/decision-log.md`:
```markdown
| {next #} | {today} | POST-MORTEM required for {incident brief} | Required after all incidents — root cause analysis and prevention | N/A |
```

Tell the user:
> "Incident resolved. A postmortem is required — it doesn't need to happen today, but it needs to happen.
>
> Run `/sweetclaude:postmortem` when ready to document:
> - Timeline of events
> - Root cause analysis (5 whys)
> - Contributing factors
> - Action items to prevent recurrence
>
> If the fix was a workaround rather than a real fix, a follow-on tech-debt item should also be created."

---

## Step 8: Update phase.yaml

If this was an active work item:
```bash
cat .sweetclaude/state/phase.yaml
```

Update `active_work_item` to reflect the incident work item at `phase: SHIP` completed, or clear it if it was a reactive one-off.

---

## Rules

- **≤ 3 questions before proposing a resolution path.** If you need more than 3, make a working hypothesis and state it.
- **Severity must be classified before any fix work begins.** P0 changes the pace, not the structure.
- **Fix-vs-rollback decision must be explicit and logged.** Never implicit.
- **Do not try to diagnose local/development bugs** — this skill handles live production incidents only. Static code errors and failing local tests belong in `sweetclaude:code-tdd` and `sweetclaude:code-testing`.
- **Postmortem is mandatory.** A `something-broke` incident that completes without spawning a postmortem work item is incomplete.
- **For P0/P1:** compressed checklist is allowed; postmortem is not compressed.
- **Surface the runbook first** if it exists — checking known failure modes before asking questions saves time.
