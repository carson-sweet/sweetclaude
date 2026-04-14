---
name: sweetclaude-strategy-ideal-customer-profile
description: "Define who specifically has this pain and will pay or use your solution. Demographics, behaviors, triggers, deal-breakers. Builds on concept and pain-thesis."
---

<preflight-guard>
STOP. Before executing this skill, check: does state/phase.yaml exist in the project working repo or project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Ideal Customer Profile

Define who specifically has this pain and will use this solution.

## Context

Read `strategy/concept.md` and `strategy/pain-thesis.md` if they exist. The pain thesis identifies who feels the pain — this skill sharpens that into a targetable profile.

## Process

Work through each section one at a time.

### 1. Demographics

Not a market segment — a describable person or organization:
- **For B2B:** company size, industry, stage, tech stack, team structure
- **For B2C:** role, experience level, context (work, personal, both)
- **For developer tools:** language/framework, team size, deployment model, pain frequency

Ask: "Describe your ideal first 10 users. Not a category — specific kinds of people."

### 2. Behaviors

What do they already do that signals they'd want this?
- What tools do they currently use?
- What communities are they in?
- What have they tried and abandoned?
- What do they complain about?

### 3. Triggers

What moment makes them go looking for a solution?
- A specific event (project kickoff, scale threshold, incident, hire)
- A specific frustration reaching a breaking point
- A specific conversation or discovery

Ask: "What would make someone google for this today?"

### 4. Deal-breakers

What would make them walk away even if the product is good?
- Price threshold
- Missing integration
- Required expertise
- Trust/credibility bar
- Platform/stack incompatibility

### 5. Anti-profile

Who is explicitly NOT the target? Defining who you're not building for is as important as who you are.
- Who would use it wrong?
- Who would churn immediately?
- Who would demand features that dilute the core value?

### 6. The profile

```
## Ideal Customer Profile: {Project Name}

**Primary ICP:**
- Role: {specific}
- Context: {specific situation}
- Size/stage: {if B2B}
- Behaviors: {what they already do}
- Trigger: {what makes them look}

**Anti-profile (NOT for):**
- {who and why not}

**Deal-breakers:**
- {list}

**Where to find them:**
- {communities, channels, events}
```

### Step 7: Save

Save to `strategy/ideal-customer-profile.md`. This feeds into product/discovery (personas are refined from ICP) and strategy/market-messaging (messaging targets ICP).

Do not push to the next step. Present the profile and wait.
