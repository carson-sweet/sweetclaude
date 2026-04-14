---
name: sweetclaude-strategy-pain-thesis
description: "Structured analysis of the pain your product addresses. Who feels it, how badly, what they do today, and why existing solutions fail. Uses a guided framework."
---

<preflight-guard>
STOP. Before executing this skill, check: does state/phase.yaml exist in the project working repo or project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Pain Thesis

Analyze the pain this product addresses.

## Context

Read `strategy/concept.md` if it exists — the problem statement there is the starting point. If it doesn't exist, ask the user to describe the problem before proceeding.

## Process

Work through each section one at a time. Probe before moving on.

### 1. Who feels this pain?

Not a market segment — a specific person in a specific situation.
- What's their role?
- What are they trying to accomplish when this pain hits?
- How often does it happen?
- Ask for a real example or scenario.

### 2. How bad is it?

Quantify the pain along these dimensions:
- **Frequency:** How often does this pain occur? (daily, weekly, per-project, once)
- **Severity:** When it happens, how much does it hurt? (annoying, costly, blocking, dangerous)
- **Duration:** How long does the pain persist? (seconds, hours, the whole project)
- **Workaround cost:** What do they do today, and how much does that cost them? (time, money, quality, morale)

### 3. What do they do today?

Map the current alternatives:
- **Do nothing** — live with it. What's the cost of inaction?
- **Manual workaround** — what specifically? How long does it take?
- **Existing tools** — what have they tried? Why does it fall short?
- **Build their own** — have they? What happened?

### 4. Why do existing solutions fail?

For each alternative from step 3, identify the specific failure:
- Too expensive?
- Too complex?
- Wrong abstraction?
- Solves adjacent problem but not this one?
- Requires expertise the user doesn't have?

### 5. The thesis

Synthesize into a pain thesis statement:

```
## Pain Thesis: {Project Name}

**Who:** {specific person in specific situation}

**Pain:** {what they're trying to do and what goes wrong}

**Frequency × Severity:** {how often × how bad = urgency}

**Current alternatives and why they fail:**
1. {alternative} — fails because {reason}
2. {alternative} — fails because {reason}

**The gap:** {what doesn't exist that should}

**Our thesis:** {why we believe we can close this gap — what insight or capability do we have}
```

### Step 6: Save

Save to `strategy/pain-thesis.md` in the project. This feeds into ideal-customer-profile and product/discovery.

Do not push to the next step. Present the thesis and wait.
