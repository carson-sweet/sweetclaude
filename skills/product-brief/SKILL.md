---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:product-brief
description: Write a product brief — a strategic document describing what is being built, for whom, why it matters, and what success looks like. Scales to available input depth.
category: product
---

# Product Brief

Write a product brief from the discovery, research, competition, and persona work completed so far. Sections and depth scale to what's available.

## Artifact Path Resolution

Before writing any artifact file:

1. Read `.sweetclaude/artifact-privacy.yaml`. If it does not exist, stop and say:
   > "No artifact privacy manifest found. Run `/sweetclaude:on` to configure artifact privacy, then return here."
   Do not guess a path. Do not fall back to a default.

2. Read `categories.product.base_path`. This is the base directory for all product artifacts.

3. Construct full paths as `{base_path}/{subfolder}/{filename}`, preserving existing subdirectory structure (e.g. if base is `.sweetclaude/product`, milestones go to `.sweetclaude/product/milestones/MS-001.md`).

4. Write artifacts to those paths.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read all available state files:
- `.sweetclaude/state/discovery.yaml`
- `.sweetclaude/state/research.yaml`
- `.sweetclaude/state/competition.yaml`
- `.sweetclaude/state/personas.yaml`
- `.sweetclaude/state/positioning.yaml`

If none exist, note graceful degradation and proceed with what the user provides directly.

## Pre-Write Flow

Work through these four steps before writing anything:

**Step 1 — Outline:** Present a bullet-point outline of sections based on available input. For example:
```
Proposed outline:
- Executive Summary
- Problem Statement
- Target Audience
- Solution Overview
- Business Objectives
- Scope (in-scope and out-of-scope)
- Success Criteria
- Risks and Assumptions
- Additional Development (sections not yet covered)
```
"Does this outline look right? Add, remove, or reorder before I write."

Wait for confirmation or adjustments.

**Step 2 — Style:** "Would you prefer a bullets-style brief (faster to read, easier to update) or a narrative-style brief (better for external audiences and investors)?"

**Step 3 — Audience:** "Who is the primary audience? Internal team, investors, potential customers, or a hybrid?"

**Step 4 — Sensitive content:** "Are there any details you'd like to omit — competitive strategy, financial projections, partner names, or anything under NDA?"

## Writing

Write the brief per the confirmed outline and style. Every paragraph is numbered `[N]` at the start (draft only).

The brief always ends with an **Additional Development** section — a bulleted list of content and sections that would typically appear in a product brief at this stage but were not covered in this pass. This tells the user what remains to be developed.

## Collaborative Revision

After presenting the draft:
> "Review it and let me know what you'd like to change. Minor changes (wording, additions, clarifications) get a minor version bump. Major changes (structure, direction, voice) get a major version bump."

On revision: write a new file per the naming convention. Update the previous file's front matter `status` to `deprecated` and rename it accordingly.

When the user approves as final: offer to remove paragraph numbers before writing the final version.

## Document Production System

File naming: `{project-name}-product-brief-{status}-v{major}.{minor}-{yyyymmdd}.md`

Front matter:
```yaml
---
title: {Project Name} Product Brief
version: {major}.{minor}
status: draft | final | deprecated
author: {user's name — ask if not known}
assisted_by: Claude Code + SweetClaude
date: {YYYY-MM-DD}
audience: {internal | investors | customers | hybrid}
nda: false | "NDA: {statement}"
changes: {what changed, or "initial draft"}
previous_file: {prior filename, or "none"}
---
```

## Exit

Write `.sweetclaude/state/brief.yaml`:

```yaml
audience: {}
nda: true | false
sections_present: []
key_decisions: []
current_version: {}
current_file: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — product-brief (n/a)

**Status:** completed | degraded
**Degraded because:** {if applicable}
**Produced:** {filename}
**Key decisions:** {bullets}
**Open questions:** {bullets}
```
