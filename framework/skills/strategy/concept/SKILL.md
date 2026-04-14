---
name: sweetclaude-strategy-concept
description: "Articulate what this project is and why it exists. Produces a clear concept statement grounded in the problem being solved. Use at the very start of strategic work."
---

<preflight-guard>
STOP. Before executing this skill, check: does state/phase.yaml exist in the project working repo or project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Concept Articulation

Define what this project is and why it exists.

## Process

### Step 1: What is this?

Ask the user to describe the project in their own words. Don't constrain the format — let them talk. Then distill into:

1. **One-sentence description.** What does this thing do? Plain language, no jargon. If you can't say it in one sentence, it's not clear enough yet.
2. **The problem it solves.** What specific situation does someone find themselves in where they need this? Not abstract pain — a concrete scenario.
3. **Why it matters.** What's different about the world if this thing exists vs. doesn't?

### Step 2: Challenge the framing

Propose at least one of:
- An alternative way to frame the problem (maybe the problem is upstream or downstream of what they described)
- A potential gap ("you said X, but what about Y?")
- An assumption worth questioning ("this assumes Z — is that actually true?")

This is not obstruction. The best concepts survive scrutiny.

### Step 3: Sharpen

After the back-and-forth, produce the concept statement:

```
## Concept: {Project Name}

**What:** {one-sentence description}

**Problem:** {the specific situation this solves — concrete, not abstract}

**Why it matters:** {what changes if this exists}

**Key assumptions:**
- {assumption 1}
- {assumption 2}

**What this is NOT:** {at least one explicit boundary}
```

### Step 4: Save

Save to `strategy/concept.md` in the project. This document is referenced by pain-thesis, ideal-customer-profile, and product/discovery.

Do not push to the next step. Present the concept and wait.
