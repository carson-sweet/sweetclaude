---
name: sweetclaude:strategy/pain-thesis
description: "Build a pain thesis document — a narrative diagnostic that determines whether your company is solving a necessary problem. Walks through 11 sections from industry background through validation plan. Based on The Pain Thesis: A Founder's Guide by Carson Sweet."
---

<preflight-guard>
STOP. Before executing this skill, check: does state/phase.yaml exist in the project working repo or project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Pain Thesis

Build a pain thesis for: $ARGUMENTS

A pain thesis is a narrative diagnostic. It determines whether the company is solving a necessary problem — one that reliably commands budget and executive attention — or a merely interesting one.

## Context

Read `strategy/concept.md` if it exists. The concept statement provides the starting point. If it doesn't exist, start by asking the user to describe what they're building and why before proceeding.

## Core Principles

These govern the entire process:

- **Empathy before ideation.** You are a researcher, not a salesperson. Understand the pain bearer's world, not your solution.
- **Evidence over assumption.** Every belief is an assumption until validated by specific quotes from specific buyers describing specific experiences. Observed behavior, not stated intentions. Money spent on workarounds, not theoretical willingness to pay.
- **Iteration as discovery.** You will not get this right on the first pass. Every conversation refines the thesis. Treat surprises as data.

## Process

Work through each section one at a time. For each section:
1. Explain what the section needs and why it matters
2. Ask the user what they know
3. Offer to help research or brainstorm where they have gaps
4. Draft the section together
5. Do not move to the next section until the user is satisfied

---

### Section 0: How to Read This Document

Draft the framing: state that this is a narrative diagnostic, not a pitch deck. Define the core hypothesis. Explain the medicine vs. vitamins distinction as it applies to this domain.

Ask: "What is the core hypothesis — the thing that must be true for this business to work? And is your product medicine (must-have, budget already exists) or a vitamin (nice-to-have, discretionary)?"

---

### Section 1: Industry Background

What structural forces created this pain? Why is it acute now? What analogous pattern has played out before in a related industry?

Ask: "What's changing in the industry that makes this problem worse or more urgent than it was two years ago?"

Offer: "Want me to research industry trends, regulatory changes, or market dynamics that create the structural pressure?"

---

### Section 2: Pain Ownership

Who is personally accountable if this problem is not solved? Why do they lack control over the forces that create it? What is the accountability-control asymmetry?

Ask: "Who gets fired, fined, or blamed when this goes wrong? And why can't they just fix it themselves?"

---

### Section 3: The Pain in Detail

What does this problem look and feel like from the inside? What questions can the pain bearer not answer? How does the pain compound over time? What is the escalation chain?

Ask: "Walk me through what happens when this problem hits. What's the sequence of events, and how does it get worse if nobody intervenes?"

Offer: "Want me to help map the escalation chain — from first symptom through worst-case outcome?"

---

### Section 4: Why Existing Approaches Fail

What have buyers tried? What are the structural reasons those approaches are insufficient? Why is this an unsolved problem rather than an ignored one?

Ask: "What do people do today to deal with this? And why doesn't it work — what specifically fails?"

Offer: "Want me to research existing solutions and analyze their failure modes?"

---

### Section 5: What an Effective Solution Must Do

What functional capabilities are required? What non-functional constraints must be met? What will cause a technically good solution to be rejected?

Ask: "If you could wave a magic wand, what would the solution need to do? And what would make a buyer reject it even if it technically works?"

---

### Section 6: Your Strategic Wedge

What are your candidate wedges? Which one do you choose and why? What are you deferring and why?

A wedge is not a feature — it's a market entry strategy. The right wedge gets you into accounts quickly, generates revenue, creates reference customers, and establishes trust.

Ask: "What's the narrowest, most painful slice of this problem that a buyer would pay to solve on its own — before seeing anything else on your roadmap?"

Offer: "Want me to help evaluate candidate wedges using the checkbook test — if you walked into a meeting and described only this one capability, would they write a check?"

---

### Section 7: How Buyers Will Judge Success

What measurable outcomes define success? What shifts from "we think" to "we know"?

Ask: "If a pilot customer adopted your wedge, how would they measure whether it worked — in their language, not yours?"

---

### Section 8: Ideal Customer Profile

Who buys fastest? Who should you avoid? What organizational characteristics predict purchasing velocity?

Ask: "Describe your ideal first 10 customers. Not a market segment — specific types of organizations with specific characteristics that make them likely to buy fast."

---

### Section 9: Solution Mapping

Where are you strong? Where are the gaps? What must be true before you can run a paid pilot?

Ask: "Map your current capabilities against what sections 5 and 6 require. Where are you ready, where are you close, and where do you have nothing?"

---

### Section 10: Validation Plan

How many buyers will you interview? What are your validation criteria? What happens if the thesis is validated? What happens if it is not?

Ask: "How will you test this thesis with real buyers? How many conversations do you need, and what signals would tell you the thesis is right vs. wrong?"

Offer: "Want me to help design the validation interview guide using the 10-ICP interview framework?"

---

## After All Sections

1. **Assemble the document.** Combine all sections into a single pain thesis document.

2. **Run the validation rubric.** For each element, assess the Red/Yellow/Green status:

| Element | Red (Assumption) | Yellow (Qualitative) | Green (Quantified) |
|---|---|---|---|
| Pain exists | Intuition or industry reading | 3+ buyers describe unprompted | 5+ buyers with specific costs/incidents |
| Pain is owned | Identified a likely role | 3+ buyers confirm role and accountability | Buyers name people and career consequences |
| Budget exists | Believe category is funded | Buyers describe related spending | Buyers identify budget lines or create budget path |
| Existing solutions fail | Evaluated competitors | Buyers describe specific failures | Buyers quantify gap between current and need |
| Wedge resonates | Believe it solves right problem first | Buyers confirm most immediate need | Buyers express willingness to pilot specifically |

Present the rubric results. The goal is to move every critical element from Red to Yellow, and the top three from Yellow to Green, before committing to a wedge.

3. **Save** to `strategy/pain-thesis.md`.

4. Do not push to the next step. Present the thesis and wait.

## Attribution

Based on *The Pain Thesis: A Founder's Guide* by Carson Sweet.
