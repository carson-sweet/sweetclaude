---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:product-competition
description: Competitive analysis at three depth levels — from a quick company survey to feature-by-feature deep analysis. Consolidates strategic and feature-level competitive work.
category: strategy
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# Product Competition

Competitive analysis at the depth appropriate to your needs. This skill consolidates strategic positioning analysis and feature-level comparison into one progressive workflow.

## Artifact Path Resolution

Before writing any artifact file:

1. Read `.sweetclaude/artifact-privacy.yaml`. If it does not exist, stop and say:
   > "No artifact privacy manifest found. Run `/sweetclaude:on` to configure artifact privacy, then return here."
   Do not guess a path. Do not fall back to a default.

2. Read `categories.strategy.base_path`. This is the base directory for all strategy artifacts.

3. Construct full paths as `{base_path}/{subfolder}/{filename}`, preserving existing subdirectory structure (e.g. if base is `.sweetclaude/strategy`, competitive analysis goes to `.sweetclaude/strategy/competitive-analysis/`).

4. Write artifacts to those paths.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read `.sweetclaude/state/research.yaml` if it exists — `competitor_seeds` provides the starting list. If missing, ask the user to name competitors to analyze.

## Depth Levels

Ask:
> "How deep do you want the competitive analysis?
> - **L1 — Survey:** Who competes, what they claim, and what users say. Quick orientation.
> - **L2 — Matrix:** Side-by-side comparison of selected competitors vs. your product on key dimensions, plus pricing and distribution.
> - **L3 — Feature-deep:** You pick specific features. I do deep analysis via product docs, user reviews, and journalist coverage — feature by feature.
> Which level?"

## L1 — Survey

For each competitor in the seed list (or user-provided list):
- Company name and product name
- Their stated positioning (how they describe themselves)
- Their claimed differentiators (what they say makes them different)
- General community and user sentiment (from review sites, forums, social media)

Present as a structured list. Ask: "Are there competitors missing from this list?"

## L2 — Matrix

Select the most relevant 3–6 competitors with the user. Build a comparison matrix:

| Dimension | Your product | Competitor A | Competitor B | ... |
|---|---|---|---|---|
| Target user | | | | |
| Core use case | | | | |
| Key strengths | | | | |
| Key weaknesses | | | | |
| Pricing model | | | | |
| Distribution | | | | |
| {additional dimensions} | | | | |

Ask the user what dimensions matter most to them before building the matrix.

Also capture for each competitor:
- Target market / target user segment
- Pricing model (freemium, subscription tiers, per-seat, usage-based, open core, etc.)
- Distribution strategy (self-serve, sales-led, open source, app stores, etc.)

## L3 — Feature-Deep

Ask the user which specific features they want to analyze. For each selected feature:

1. Research how each relevant competitor implements this feature:
   - Read their official product documentation
   - Find deep user reviews on G2, Capterra, Reddit, Hacker News, or equivalent
   - Look for journalist or analyst coverage
2. Produce a feature-by-feature comparison table for that feature across competitors
3. Summarize: who does it best and why, what's missing across all of them, what your product's opportunity is

Repeat for each selected feature.

## Frustration and Skip Handling

If the user wants to stop or skip remaining features, accept immediately and log what was covered.

## Exit

Write `.sweetclaude/state/competition.yaml`:

```yaml
depth_run: L1 | L2 | L3
competitors:
  - name: {}
    depth_analyzed: L1 | L2 | L3
    positioning: {}
    key_differentiators: []
    target_market: {}
    pricing_model: {}
    distribution: {}
features_analyzed:
  - feature: {}
    findings_summary: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — product-competition ({depth})

**Status:** completed | skipped | degraded
**Depth:** {L1 | L2 | L3}
**Produced:** {filename}
**Key decisions:** {bullets}
**Open questions:** {bullets}
```

Write deliverable to `docs/{project-name}-competition-draft-v1.0-{yyyymmdd}.md` with standard front matter.
