---
description: "Product-level competitive analysis focused on features and capabilities. Compare your feature set against competitors, identify table-stakes features, find differentiation opportunities."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Feature Competitive Analysis

Compare features against competitors for: $ARGUMENTS

## Context

Read `strategy/competitive-analysis.md` if it exists for the strategic landscape. This skill goes deeper at the feature level.

## Process

### 1. Identify competitors

List 3-8 direct competitors or alternatives. For each:
- Name and URL
- One-line description
- How users currently encounter them (search, recommendation, migration from)

### 2. Build the feature matrix

Define feature categories relevant to this product. For each category, list specific features and check which competitors have them:

```
| Feature | Us | Comp A | Comp B | Comp C |
|---|---|---|---|---|
| {feature} | ✓/✗/planned | ✓/✗ | ✓/✗ | ✓/✗ |
```

### 3. Identify patterns

- **Table stakes** — features that 3+ competitors all have. You need these.
- **Differentiators** — features only 1-2 have. Potential opportunities.
- **Gaps** — features nobody has. Either innovation or a sign the market does not want it.
- **Our unique** — features we have or plan that nobody else does.

### 4. Recommendations

For each table-stakes feature we lack, use AskUserQuestion with these options:
- "Include" — add to scope
- "Exclude" — skip (document the rationale)

For each differentiator opportunity:
> Worth pursuing? What does it take?

### 5. Save

Save to `strategy/feature-competitive.md`. Feeds into product/manage-scope and product/product-brief.
