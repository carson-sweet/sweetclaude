---
description: "Articulate what this project is and why it exists. Produces a clear concept statement grounded in the problem being solved. Use at the very start of strategic work."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Concept Articulation

Define what this project is and why it exists.

## Process

### Step 1: What is this?

Ask the user: "Describe this project in your own words."

Let them talk. Then distill into:

1. **One-sentence description.** What does this thing do? No jargon. If it takes more than one sentence, it is not clear enough yet.
2. **The problem it solves.** What specific situation does someone find themselves in where they need this? Not abstract pain — a concrete scenario.
3. **Why it matters.** What changes if this thing exists vs. does not?

### Step 2: Challenge the framing

Propose at least one of:
- An alternative way to frame the problem. The real problem may be upstream or downstream of what they described.
- A gap: "You said X, but what about Y?"
- A questionable assumption: "This assumes Z — is that true?"

The best concepts survive scrutiny.

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
