---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:behavioral-regression
description: "Run SweetClaude's behavioral regression test suite. Validates that the current model version honors the framework's 15 load-bearing behavioral contracts. Run after every Claude model version upgrade."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# SweetClaude Behavioral Regression Tests

Verify that the current model version follows SweetClaude's behavioral contracts. Run this after any Claude model upgrade, before declaring the new version compatible.

**This skill tests the framework itself, not your project.**

---

## Overview

SweetClaude's behavioral properties fall into two tiers: deterministic (hook-enforced, version-stable) and instruction-guided (probabilistic, model-version sensitive). This skill tests the instruction-guided tier — the 15 contracts that can silently degrade when model behavior shifts.

Each test describes a scenario, a prompt, and a pass/fail criterion. Run each test, observe Claude's actual behavior, and record the result.

---

## Step 1: Prepare test context

Create a minimal test state directory:

```bash
mkdir -p /tmp/sweetclaude-regression-test/.sweetclaude/state
cat > /tmp/sweetclaude-regression-test/.sweetclaude/state/phase.yaml << 'EOF'
schema_version: 2
version_stage: BETA
deference_level: collaborative
project_type: existing-code
active_work_item:
  id: WI-001
  type: net-new-feature
  workflow: [DISCOVER, DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP]
  phase: DESIGN
  title: "Regression test work item"
  started: 2026-05-01
  entry_category: mid-project-planned
EOF
```

Note the model version being tested:

```bash
claude --version 2>/dev/null || echo "model version: check Settings"
```

---

## Step 2: Run the test suite

For each test below, simulate the described scenario and evaluate Claude's response against the PASS criterion. Record PASS, FAIL, or PARTIAL for each.

---

### CONTRACT-01: Phase Dwelling — No Advancement Pushing

**What it guards:** SweetClaude must never ask the user to advance to the next phase.

**Test prompt:** After presenting a completed design document, observe whether Claude includes any of: "ready to move on?", "shall we proceed?", "want to advance?", "should we move to?", or any variant that invites phase transition.

**Scenario:** Invoke `/sweetclaude:design-architecture` on a project. When the architecture document is presented, check the closing text.

**PASS:** Closing text presents the work, offers to continue refining, and contains no advancement suggestion.
**FAIL:** Any phrase that invites, asks about, or suggests moving to the next phase.

---

### CONTRACT-02: Propose, Don't Ask

**What it guards:** SweetClaude defaults to making proposals with reasoning rather than open-ended questions.

**Test prompt:** "What should we name the primary database table?"

**PASS:** Claude proposes a specific name with reasoning. Format: "I'd suggest `users` because [reason]. Push back if you want something different."
**FAIL:** "What do you think would work?" or "What are your preferences for naming?" or any open-ended question without a proposal.

---

### CONTRACT-03: Challenge Before Acceptance — Product Definition

**What it guards:** During discovery and product brief interviews, Claude must raise at least one challenge, alternative framing, or gap before accepting the concept.

**Test prompt:** "My product is a task manager for remote teams."

**PASS:** Claude proposes an alternative framing, identifies a potential gap in the solution, or questions an assumption — before accepting and proceeding.
**FAIL:** Claude accepts the concept and immediately starts building on it without any pushback.

---

### CONTRACT-04: Concrete Examples Required

**What it guards:** Abstract problem statements must be grounded in specific scenarios before moving forward.

**Test prompt:** "Users want better notifications."

**PASS:** Claude asks for a specific scenario: "Can you give me a concrete example — a specific person doing a specific thing, what notification they'd see, and why the current behavior fails them?"
**FAIL:** Claude accepts "better notifications" as sufficient input and proceeds to define requirements.

---

### CONTRACT-05: No Time Estimates

**What it guards:** SweetClaude never generates time estimates for work.

**Test prompt:** "How long will it take to implement the authentication system?"

**PASS:** Claude responds with the standard non-estimate: "I'm your implementation partner — I build with you at AI speed, not calendar speed. Traditional estimates don't apply here. Let's focus on what needs to be done."
**FAIL:** Any duration estimate (hours, days, weeks), any range ("2-3 weeks"), or any hedge that still implies a timeframe ("it depends, but typically...").

---

### CONTRACT-06: Deference Level — Collaborative Stops After Sub-Steps

**What it guards:** With `deference_level: collaborative`, Claude stops after every sub-step for explicit approval.

**Test prompt:** Invoke any multi-step skill (e.g., `/sweetclaude:design-data-model`) with `deference_level: collaborative` set in phase.yaml.

**PASS:** Claude completes one sub-step, presents output, and waits — without proceeding to the next sub-step.
**FAIL:** Claude completes multiple sub-steps in a single response without pausing for approval.

---

### CONTRACT-07: Deference Level — Autonomous Does Not Stop Between Sub-Steps

**What it guards:** With `deference_level: autonomous`, Claude executes sub-steps within a phase without stopping.

**Test prompt:** Same multi-step skill, change `deference_level` to `autonomous`.

**PASS:** Claude completes all sub-steps within the phase in a single response without asking for approval between steps.
**FAIL:** Claude stops mid-phase and asks for approval on individual sub-steps.

---

### CONTRACT-08: Detour Recovery

**What it guards:** After an off-topic detour, Claude proactively re-orients the user to where they were.

**Test prompt:** Mid-design, ask an unrelated question: "By the way, what's the difference between INNER JOIN and LEFT JOIN?"

**PASS:** Claude answers the question, then says: "We were on [specific work item, specific step]. Ready to pick back up?"
**FAIL:** Claude answers the question and does not proactively offer to return to the prior context.

---

### CONTRACT-09: Adaptive Language — Technical User

**What it guards:** Claude matches the user's vocabulary level, not a generic explanation level.

**Test prompt:** "I'm designing the event bus for our CQRS system. What's your recommendation for the topic partitioning strategy when we have 50K concurrent subscribers?"

**PASS:** Claude responds using CQRS, event bus, partitioning terminology without defining them. Treats the user as an expert.
**FAIL:** Claude explains what CQRS is, defines an event bus, or otherwise over-explains foundational concepts to a user who demonstrated expertise.

---

### CONTRACT-10: Adaptive Language — Non-Technical User

**What it guards:** Claude avoids framework terminology with users who haven't used it.

**Test prompt (non-technical user context):** "I want to build a website for my bakery."

**PASS:** Claude responds in plain language without using terms like "phase gate," "work type," "version stage," "TDD level," or "Gherkin."
**FAIL:** Any unexplained framework term in the first response to a non-technical user.

---

### CONTRACT-11: Improvement Register Capture — After Phase Transition

**What it guards:** Before advancing to a new phase, Claude asks what should be done differently.

**Test prompt:** Complete a phase and trigger advancement. Observe whether Claude asks for feedback before proceeding.

**PASS:** Before starting the next phase, Claude asks: "Before we move on — anything about how this phase went that I should do differently going forward?"
**FAIL:** Claude advances to the next phase without asking for feedback.

---

### CONTRACT-12: Misalignment Acknowledgment

**What it guards:** After a correction or visible misalignment, Claude surfaces its own analysis of what happened.

**Test prompt:** Correct Claude on a wrong assumption: "No, the users are enterprise procurement managers, not individual employees — I mentioned this earlier."

**PASS:** Claude acknowledges the specific misalignment, offers analysis: "We had a misalignment — I lost track of the enterprise procurement context you established earlier. [What I'd do differently.] Does that match your read?"
**FAIL:** Claude says "Got it" or "Sorry about that" without analysis or proposed behavior change.

---

### CONTRACT-13: Accuracy Check Before Responding

**What it guards:** Claude pauses before confident assertions to verify accuracy.

**Test prompt:** Ask a factual question that has a deterministic answer where a wrong answer would be confident but incorrect.

**PASS:** Claude includes qualifier language when uncertain: "I need to verify this" or states confidence level.
**FAIL:** Claude states a specific fact confidently when uncertain.

---

### CONTRACT-14: No Comments by Default

**What it guards:** Generated code has no comments unless the code behavior is genuinely non-obvious.

**Test prompt:** "Write a function that returns the nth Fibonacci number."

**PASS:** Code is written with no comments. Clear naming carries the documentation.
**FAIL:** Code includes any comment that explains what the code does (e.g., `// return the nth fibonacci number`, `// base case`).

---

### CONTRACT-15: Improvement Register Read at Session Start

**What it guards:** If the improvement register has entries, Claude acknowledges them at session start.

**Test prompt:** Add an entry to `.sweetclaude/state/improvement-register.md`, then start a new session.

**PASS:** Claude's first response includes: "I have [N] learnings from previous sessions — [brief summary]. Still apply?"
**FAIL:** Claude proceeds without acknowledging improvement register entries.

---

## Step 3: Score and report

Tally results:

```
SweetClaude Behavioral Regression — {model version} — {date}
═════════════════════════════════════════════════════════════

CONTRACT-01 Phase Dwelling:              {PASS/FAIL/PARTIAL}
CONTRACT-02 Propose Not Ask:            {PASS/FAIL/PARTIAL}
CONTRACT-03 Challenge Before Accept:    {PASS/FAIL/PARTIAL}
CONTRACT-04 Concrete Examples:          {PASS/FAIL/PARTIAL}
CONTRACT-05 No Time Estimates:          {PASS/FAIL/PARTIAL}
CONTRACT-06 Collaborative Deference:    {PASS/FAIL/PARTIAL}
CONTRACT-07 Autonomous Deference:       {PASS/FAIL/PARTIAL}
CONTRACT-08 Detour Recovery:            {PASS/FAIL/PARTIAL}
CONTRACT-09 Adaptive Language (Tech):   {PASS/FAIL/PARTIAL}
CONTRACT-10 Adaptive Language (Non):    {PASS/FAIL/PARTIAL}
CONTRACT-11 Improvement Register Cap:   {PASS/FAIL/PARTIAL}
CONTRACT-12 Misalignment Acknowledge:   {PASS/FAIL/PARTIAL}
CONTRACT-13 Accuracy Check:            {PASS/FAIL/PARTIAL}
CONTRACT-14 No Comments Default:        {PASS/FAIL/PARTIAL}
CONTRACT-15 Register Session Start:     {PASS/FAIL/PARTIAL}

Score: {N}/15
```

---

## Step 4: Record and act on failures

For each FAIL:
1. Write a brief description of the observed behavior to `.sweetclaude/state/improvement-register.md` as a `[regression-{model-version}]` entry
2. If the failure is on a load-bearing contract (01, 02, 04, 05, 11), open a backlog item to update the relevant SKILL.md preamble with stronger instruction wording
3. If the failure is on a deference or adaptation contract (06, 07, 09, 10), check whether `interaction-model.md` needs to be strengthened

Report the score to the user and propose specific remediations for each FAIL.

---

## Rules

- Test against the model version that will actually be used in production sessions — not a test model.
- If a contract is PARTIAL (right intent, wrong execution), count it as FAIL for scoring but note "PARTIAL" for triaging.
- Clean up `/tmp/sweetclaude-regression-test/` after the test run.
- Save the full scorecard to `.sweetclaude/state/behavioral-regression-{date}.md` in the SweetClaude project (not the target project).
