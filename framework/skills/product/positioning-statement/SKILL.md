---
name: sweetclaude:product/positioning-statement
description: "Define how the product is positioned — for whom, what category, what differentiates it, and why that matters. Builds on strategy/concept and strategy/ideal-customer-profile."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Product Positioning Statement

Define how this product is positioned in the market.

## Context

Read `strategy/concept.md`, `strategy/pain-thesis.md`, and `strategy/ideal-customer-profile.md` if they exist. Positioning builds on all three.

## Process

### 1. Category

What category does this product belong in? If it's creating a new category, what existing categories is it adjacent to? The category determines what the user compares you to.

### 2. Positioning framework

Work through this structure with the user:

**For** {target customer — from ICP}
**Who** {statement of need or pain — from pain thesis}
**Our product is a** {product category}
**That** {key benefit — the one thing that matters most}
**Unlike** {primary competitive alternative}
**Our product** {primary differentiation — what you do that they can't}

### 3. Challenge and refine

- Is the differentiation defensible? Can a competitor copy it in 6 months?
- Is the benefit the one the ICP actually cares most about, or the one you're proudest of?
- Is the category right? Too broad = invisible. Too narrow = limited.

### 4. Produce the statement

```
## Product Positioning: {Project Name}

**For** {target}
**Who** {need}
**{Product}** is a {category}
**That** {key benefit}
**Unlike** {alternative}
**We** {differentiation}

**Supporting claims:**
1. {claim backed by proof point}
2. {claim backed by proof point}
3. {claim backed by proof point}
```

### 5. Save

Save to `strategy/positioning-statement.md`. This feeds into strategy/market-messaging and product/product-brief.
