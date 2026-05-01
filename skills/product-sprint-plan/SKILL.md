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

**If `skills.yaml` does not exist:**
- Write `skills.yaml` with `skills.product-sprint-plan.enabled: false`. Route to `onboard`.

**If `skills.yaml` exists:**
- If `skills.product-sprint-plan.enabled: true`: proceed normally.
- If `skills.product-sprint-plan.enabled: false` AND `$ARGUMENTS` is not `onboard` or `offboard`: say "Sprint planning hasn't been set up for this project yet. Starting onboarding..." and route to `onboard`.
- If `$ARGUMENTS` is `offboard` and `enabled: false`: say "Sprint planning is not currently enabled. Nothing to offboard." Stop.

**State writes:**
- End of `onboard` (success): set `skills.product-sprint-plan.enabled: true`, `onboarded_at: {today ISO date}`
- End of `offboard`: set `skills.product-sprint-plan.enabled: false`, `offboarded_at: {today ISO date}`

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

Stop.

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
