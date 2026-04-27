---
description: "Plan a sprint by selecting stories from the backlog, estimating scope, and producing a sprint commitment."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Sprint Plan

Plan a sprint for: $ARGUMENTS

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
