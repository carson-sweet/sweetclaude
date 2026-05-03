---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Walk through the pipeline step by step. Figures out where you are, picks the right skill for the next step, invokes it, and loops. Stops at phase gates for approval."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Running pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# SweetClaude Next Steps

Drive the pipeline. Figure out what comes next. Do it. Move on.

## How It Works

1. **Read current position.** Run the status check (same as `/sweetclaude:status`) to determine phase, what is done, what is pending.

2. **Determine the next step.** Based on phase and existing artifacts, identify the single most important thing to do next. Use phase gate exit criteria to determine what is still needed.

3. **Announce and invoke.** Tell the user what is next and why:
   > "Next: {action}. Needed because {reason — references phase gate criteria}. Running `/sweetclaude:{skill}` now."

   Then invoke the skill.

4. **After the skill completes, loop.** Re-assess position. Determine the next step. Announce and invoke. Repeat.

5. **Stop at phase gates.** When all exit criteria for a phase are met, do NOT auto-advance. Present the phase gate check and wait for the user:
   > "All {phase} exit criteria are met. Improvement check-in and phase transition are ready when you are."

6. **Stop when the user redirects.** If the user interrupts, changes topic, or says stop — follow immediately. Resume with `/sweetclaude:next-steps` when ready.

## Phase → Skill Mapping

Picks skills based on what's missing for the current phase gate:

**DISCOVER — what's needed → what to run:**
- No concept articulated → `product/discovery`
- No personas defined → `product/user-personas`
- No competitive landscape → `product/competition`
- No scope boundary → `product/manage-scope`

**DEFINE — what's needed → what to run:**
- No product brief → `product/product-brief`
- No PRD → `product/prd`
- Scope not explicit → `product/manage-scope`

**DESIGN — what's needed → what to run:**
- No architecture → `design/architecture`
- No tech spec → `design/tech-spec`
- No data model → `design/data-model`
- No API design → `design/api-design`
- Solutioning gate not passed → `design/solutioning-gate`

**PLAN — what's needed → what to run:**
- No user stories → `product/user-stories`
- No .feature files → `product/user-tdd-tests`
- No sprint plan → `product/sprint-plan`

**IMPLEMENT — what's needed → what to run:**
- Change impact not assessed → `design/change-impact-analysis`
- New feature to build → `sweetclaude:code-feature`
- Issue to implement → `sweetclaude:code-issue`
- Tech debt to address → `sweetclaude:code-debt`

**VERIFY — what's needed → what to run:**
- Code not reviewed → `sweetclaude:code-review`
- Security not reviewed → `sweetclaude:code-testing`
- Tests not validated → `sweetclaude:code-testing`
- Docs not updated → `design/update-docs`
- PR not ready → `sweetclaude:code-testing`

**SHIP — deferred.**

## Rules

- **One step at a time.** Never batch multiple skills into one step. Announce, invoke, complete, then assess the next step.
- **The user is always in control.** Next-steps suggests and executes, but the user can redirect, skip, or stop at any point.
- **Respect deference level.** At Collaborative, pause after every sub-step within a skill. At Guided, pause between skills. At Autonomous, only pause at phase gates.
- **Never skip phase gates.** Even in Autonomous mode, phase transitions require user approval.
- **If a skill fails or gets stuck,** report what happened and ask the user how to proceed. Do not retry blindly.
