---
spdx-license: AGPL-3.0-or-later
description: "Plan a sprint by selecting stories from the backlog, estimating scope, and producing a sprint commitment."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Sprint Plan

Plan a sprint for: $ARGUMENTS

## State Check

Read `.sweetclaude/state/skills.yaml`.

**Schema migration:** If `skills.yaml` exists with `schema_version: 1`, migrate this skill's entry before proceeding:
- `enabled: true` → `status: active`, `last_changed_at: {onboarded_at or today}`, `last_changed_by: migrated`
- `enabled: false` with `onboarded_at` set → `status: paused`, `last_changed_at: {offboarded_at or onboarded_at or today}`, `last_changed_by: migrated`
- `enabled: false` with `onboarded_at: ~` → `status: uninitialized`, `last_changed_at: ~`, `last_changed_by: ~`
Drop `onboarded_at`/`offboarded_at`. Set `schema_version: 2`. Write atomically (see write protocol below).

**Dependency check:**
Read `~/.claude/config/sweetclaude/skills-registry.yaml`. Find `skills.product-sprint-plan.dependencies`: `[product-backlog]`.
Read `skills.product-backlog.status` from `skills.yaml`. If it is not `active`:
> "Sprint planning requires backlog to be active first. Run `/sweetclaude:product-backlog` to set it up." Stop.

**If `skills.yaml` does not exist, OR exists but has no entry for `skills.product-sprint-plan`:**
- Sprint planning has no data files to infer from — write entry with `status: uninitialized`, `last_changed_at: ~`, `last_changed_by: ~`
- Use write protocol below.

**If `skills.yaml` exists and has an entry for `skills.product-sprint-plan`:**
- `status: active` → proceed normally
- `status: paused` AND `$ARGUMENTS` not in `[onboard, offboard, pause]`:
  > "Sprint planning is currently paused. Resume? [yes/no]"
  If yes: write `status: active`, `last_changed_at: {today}`, `last_changed_by: resume` (using write protocol). Proceed normally.
  If no: stop.
- `status: uninitialized` AND `$ARGUMENTS` not in `[onboard, offboard, pause]`:
  → Run lightweight first-invocation flow (see below)
- `$ARGUMENTS` is `pause` → run pause operation
- `$ARGUMENTS` is `offboard` and `status: uninitialized`: "Sprint planning isn't set up yet. Nothing to offboard." Stop.
- `$ARGUMENTS` is `pause` and `status: paused`: "Already paused." Stop.
- `$ARGUMENTS` is `pause` and `status: uninitialized`: "Not set up yet. Nothing to pause." Stop.

**Write protocol — all skills.yaml writes must follow this:**
1. Read and parse current `.sweetclaude/state/skills.yaml` (or start from default v2 structure if absent)
2. Merge your entry — do NOT remove or overwrite other skills' entries
3. Write merged content to `.sweetclaude/state/.skills.yaml.tmp`
4. Run: `mv .sweetclaude/state/.skills.yaml.tmp .sweetclaude/state/skills.yaml`

**State writes (use write protocol for all):**
- End of lightweight first-invocation (success): `status: active`, `last_changed_at: {today}`, `last_changed_by: first-invocation`
- End of onboard (success): `status: active`, `last_changed_at: {today}`, `last_changed_by: onboard`
- Pause operation: `status: paused`, `last_changed_at: {today}`, `last_changed_by: pause`
- Resume: `status: active`, `last_changed_at: {today}`, `last_changed_by: resume`
- End of offboard: `status: uninitialized`, `last_changed_at: {today}`, `last_changed_by: offboard`

---

## Pause — Temporarily stop using this skill

Invoked with argument `pause`.

Sets sprint planning to `paused` status. Sprint planning doesn't own data files, so nothing is affected. Resume anytime.

Write atomically (using write protocol):
- `skills.product-sprint-plan.status: paused`
- `skills.product-sprint-plan.last_changed_at: {today ISO date}`
- `skills.product-sprint-plan.last_changed_by: pause`

Say: "Sprint planning paused. Your backlog and stories are unaffected. Resume anytime by running `/sweetclaude:product-sprint-plan`."

---

## Offboarding — Stop using this skill

Invoked with argument `offboard`.

Sprint planning does not own data files — it reads from backlog and stories. There is nothing to export or delete here.

Present:
> "Sprint planning doesn't store its own data — it reads from your backlog and stories. Stopping sprint planning just means not running this skill anymore.
>
> If you also want to offboard backlog or stories, run:
>   `/sweetclaude:product-backlog offboard`
>   `/sweetclaude:product-user-stories offboard`"

Write state (using write protocol): `status: uninitialized`, `last_changed_at: {today}`, `last_changed_by: offboard`.

Stop.

---

## Lightweight first-invocation — Quick setup on first use

Runs when the skill is invoked normally but `status` is `uninitialized`.

Sprint planning has no data files to set up — it reads from backlog and stories. Initialization just confirms the dependency and activates the skill.

1. Confirm backlog is active (dependency check above already passed if we're here).

2. Say: "Sprint planning is now active for this project. I'll plan sprints by pulling from your backlog."

3. Write state (using write protocol): `status: active`, `last_changed_at: {today}`, `last_changed_by: first-invocation`.

4. Proceed to the user's originally requested operation.

---

## Onboarding — First-time setup

If `$ARGUMENTS` is `onboard`:

1. Check whether `{base_path}/backlog/BACKLOG-INDEX.md` exists.
   - If not: > "Sprint planning requires the backlog to be set up first. Setting up the backlog now." Then invoke `sweetclaude:product-backlog onboard` and wait for it to complete.
   - If yes: continue.

2. Check whether `{base_path}/milestones/MILESTONES-INDEX.md` exists.
   - If not: > "Sprint planning works best with milestones defined so each sprint can be tied to a roadmap target. Want to set up milestones now? (yes/skip)"
     - If yes: invoke `sweetclaude:product-milestones onboard` and wait.
     - If skip: continue.

3. Tell the user: "Sprint planning is ready. Run `/sweetclaude:product-sprint-plan` when you're ready to plan a sprint."

---

## SweetClaude Context

- Pull candidate stories from `stories/` and `product/backlog`.
- Respect scope boundaries from `product/manage-scope`.
- No time estimates. Scope by artifact count and complexity, not calendar days.

## Execute

1. Select candidate stories from backlog based on complexity and scope.
2. After the sprint commitment is finalized, read each selected story's `**Milestone:**` header from its file.
3. Aggregate and report:

   ```
   Sprint advances:
     → MS-001 Exit Stealth   2 stories
     → MS-003 MVP Shipped    1 story
   ⚠ Unassigned: 1 story
   ```

4. If more than 50% of sprint stories are unassigned to any milestone, flag it:

   > "{N} of {total} stories have no milestone. This sprint may be unfocused. Consider running `/sweetclaude:product-milestones unassigned` to triage, or confirm the sprint is intentionally tactical."

5. If no milestones exist at all, skip this step silently — no milestones is not a sprint-planning problem.
