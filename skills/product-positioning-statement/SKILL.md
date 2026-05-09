---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Define how the product is positioned — for whom, what category, what differentiates it, and why that matters."
category: strategy
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Product Positioning Statement

Define how this product is positioned in the market.

## Artifact Path Resolution

Before writing any artifact file:

1. Read `.sweetclaude/artifact-privacy.yaml`. If it does not exist, stop and say:
   > "No artifact privacy manifest found. Run `/sweetclaude:setup` to configure artifact privacy, then return here."
   Do not guess a path. Do not fall back to a default.

2. Read `categories.strategy.base_path`. This is the base directory for all strategy artifacts.

3. Construct full paths as `{base_path}/{subfolder}/{filename}`, preserving existing subdirectory structure (e.g. if base is `.sweetclaude/strategy`, competitive analysis goes to `.sweetclaude/strategy/competitive-analysis/`).

4. Write artifacts to those paths.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read available state files and use them to pre-populate context:
- `.sweetclaude/state/competition.yaml` — key differentiators found
- `.sweetclaude/state/personas.yaml` — target user segment
- `.sweetclaude/state/discovery.yaml` — pain thesis and problem framing

If any are missing, note this and recommend completing those skills first. Accept if the user declines and proceed with what's available.

## Context

Read `{base_path}/concept.md`, `{base_path}/pain-thesis.md`, and `{base_path}/ideal-customer-profile.md` if they exist. Positioning builds on all three.

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

Save to `{base_path}/positioning-statement.md`. This feeds into product/market-messaging and product/product-brief.

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
