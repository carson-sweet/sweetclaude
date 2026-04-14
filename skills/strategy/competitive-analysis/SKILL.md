---
name: strategy/competitive-analysis
description: "Strategic-level competitive landscape analysis. Who else operates in this space, how they're positioned, where the gaps are, and what your differentiation is. Distinct from product/feature-competitive which focuses on features."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Strategic Competitive Analysis

Analyze the competitive landscape for: $ARGUMENTS

## Context

Read `strategy/concept.md` and `strategy/pain-thesis.md` if they exist. This analysis is strategic — positioning, business model, market dynamics — not feature-level (use `product/feature-competitive` for that).

## Process

### 1. Landscape scan

Search for organizations, projects, and products operating in the same space. Include:
- Direct competitors (solving the same problem for the same audience)
- Indirect competitors (solving an adjacent problem, or the same problem for a different audience)
- Open-source alternatives
- The "do nothing" option (what happens if the user just lives with the problem)

### 2. For each competitor

- **Name and URL**
- **What they do** (~25 words)
- **Target audience** — who are they built for?
- **Business model** — how do they make money?
- **Positioning** — how do they describe themselves?
- **Strengths** — what do they do well?
- **Weaknesses** — where do they fall short?

### 3. Strategic patterns

- **Market dynamics** — is this space growing, consolidating, fragmenting?
- **Barriers to entry** — what makes it hard to compete here?
- **Differentiation opportunities** — where can you be meaningfully different, not just incrementally better?
- **Threats** — what could a well-funded competitor do that would undermine your position?

### 4. SWOT

```
Strengths (internal):     | Weaknesses (internal):
- {strength}              | - {weakness}
                          |
Opportunities (external): | Threats (external):
- {opportunity}           | - {threat}
```

### 5. Save

Save to `strategy/competitive-analysis.md`. Feeds into product/positioning-statement and strategy/market-messaging.
