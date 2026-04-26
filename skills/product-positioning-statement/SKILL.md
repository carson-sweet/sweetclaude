---
description: "Define how the product is positioned — for whom, what category, what differentiates it, and why that matters. Runs after discovery, research, competition, and personas are complete."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Product Positioning Statement

Define how this product is positioned in the market.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read available state files and use them to pre-populate context:
- `.sweetclaude/state/competition.yaml` — key differentiators found
- `.sweetclaude/state/personas.yaml` — target user segment
- `.sweetclaude/state/discovery.yaml` — pain thesis and problem framing

If any are missing, note this and recommend completing those skills first. Accept if the user declines and proceed with what's available.

## Context

Read `strategy/concept.md`, `strategy/pain-thesis.md`, and `strategy/ideal-customer-profile.md` if they exist. Positioning builds on all three.

## Process

### 1. Category

What category does this product belong in? If it creates a new category, what existing categories is it adjacent to? The category determines what the user compares you to.

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
- Is the benefit the one the ICP cares most about, or the one you are proudest of?
- Is the category right? Too broad means invisible. Too narrow means limited.

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

## Exit

Write `.sweetclaude/state/positioning.yaml`:

```yaml
target_segment: {}
positioning_statement: {}
differentiators: []
category: {}
current_file: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — product-positioning-statement (n/a)

**Status:** completed | degraded
**Produced:** {filename}
**Key decisions:** {bullets}
```
