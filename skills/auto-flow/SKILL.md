---
description: "Walk through the pipeline step by step. Figures out where you are, picks the right skill for the next step, invokes it, and moves to the next when done. Stops at phase gates for approval. Use when you want SweetClaude to drive the process."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# SweetClaude Auto-Flow

Drive the pipeline. Figure out the next step, do it, move on. The user approves or redirects at each step.

## How It Works

1. **Read current position.** Run the status check (same as `/sweetclaude:status`) to determine phase, what's done, what's pending.

2. **Determine the next step.** Based on the current phase and what artifacts exist, identify the single most important thing to do next. Use the phase gate exit criteria to determine what's still needed.

3. **Announce and invoke.** Tell the user what's next and why:
   > "Next: {action}. This is needed because {reason — references phase gate criteria}. Running `/sweetclaude:{skill}` now."
   
   Then invoke the skill.

4. **After the skill completes, loop.** Re-assess position. Determine the next step. Announce and invoke. Repeat.

5. **Stop at phase gates.** When all exit criteria for a phase are met, do NOT auto-advance. Present the phase gate check and wait for the user to signal readiness:
   > "All {phase} exit criteria are met. Run the improvement check-in and phase transition when you're ready — I won't push."

6. **Stop when the user redirects.** If the user interrupts, changes topic, or says stop — follow immediately. Auto-flow is a mode, not a cage. Resume with `/sweetclaude:auto-flow` when the user wants to pick back up.

## Phase → Skill Mapping

Auto-flow picks skills based on what's missing for the current phase gate:

**DISCOVER — what's needed → what to run:**
- No concept articulated → `strategy/concept`
- No personas defined → `product/discovery`
- No competitive landscape → `strategy/competitive-analysis` or `product/feature-competitive`
- No scope boundary → `product/manage-scope`

**DEFINE — what's needed → what to run:**
- No product brief → `product/product-brief`
- No PRD → `product/prd`
- No success criteria → `product/user-success-criteria`
- Scope not explicit → `product/manage-scope`

**DESIGN — what's needed → what to run:**
- No architecture → `design/architecture`
- No tech spec → `design/tech-spec`
- No data model → `design/data-model`
- No API design → `design/api-design`
- Solutioning gate not passed → `design/solutioning-gate`

**PLAN — what's needed → what to run:**
- No user stories → `product/user-story`
- No .feature files → `product/user-tdd-tests`
- No sprint plan → `product/sprint-plan`

**IMPLEMENT — what's needed → what to run:**
- Change impact not assessed → `design/change-impact-analysis`
- Tests not written → `code/tdd`
- Issue to implement → `code/work-issue`
- Tech debt to address → `code/work-debt`

**VERIFY — what's needed → what to run:**
- Code not reviewed → `code/code-review`
- Security not reviewed → `code/security-testing`
- Tests not validated → `code/mutation-testing`
- Docs not updated → `design/update-docs`
- PR not ready → `code/pr-precheck`

**SHIP — deferred.**

## Rules

- **One step at a time.** Never batch multiple skills into one step. Announce, invoke, complete, then assess the next step.
- **The user is always in control.** Auto-flow suggests and executes, but the user can redirect, skip, or stop at any point.
- **Respect deference level.** At Collaborative, pause after every sub-step within a skill. At Guided, pause between skills. At Autonomous, only pause at phase gates.
- **Never skip phase gates.** Even in Autonomous mode, phase transitions require user approval.
- **If a skill fails or gets stuck,** report what happened and ask the user how to proceed. Don't retry blindly.
