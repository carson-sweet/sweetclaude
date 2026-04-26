---
name: sweetclaude:product-prd
description: Write a Product Requirements Document — functional requirements, non-functional requirements, epics, and success metrics. Scales to available input depth.
---

# Product PRD

Write a Product Requirements Document (PRD) from the discovery, research, brief, and persona work completed so far.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read available state files:
- `.sweetclaude/state/discovery.yaml`
- `.sweetclaude/state/brief.yaml`
- `.sweetclaude/state/personas.yaml`
- `.sweetclaude/state/research.yaml`

If brief state is missing, recommend running `product-brief` first. Accept if user declines. Log degraded status.

## Pre-Write Flow

Same four steps as product-brief:

**Step 1 — Outline:** Present proposed PRD structure. Typical modern PRD sections:
```
- Executive Summary
- Problem Statement (with concrete scenario)
- Goals and Success Metrics (measurable, binary criteria)
- Functional Requirements (numbered, testable)
- Non-Functional Requirements (performance, security, compliance, scalability)
- Epics and User Story Summary
- Out of Scope
- Assumptions and Constraints
- Open Questions
- Additional Development
```
"Adjust the outline before I write."

**Step 2 — Style:** Bullets or narrative?

**Step 3 — Audience:** Internal, investors, customers, or hybrid?

**Step 4 — Sensitive content:** Anything to omit?

## Writing

Write the PRD per the confirmed outline. Every paragraph numbered `[N]` (draft only).

**Functional requirements** must be numbered and testable. Format:
```
FR-001: {The system shall...}
FR-002: {The system shall...}
```

**Success metrics** must be observable and binary (true/false after ship). Bad: "Users are happy." Good: "User completes primary workflow in under 3 steps."

Always end with **Additional Development** — sections and requirements typically present in a PRD at this stage that were not covered.

## Collaborative Revision

Same revision workflow as product-brief — minor changes get minor bump, major changes get major bump. Previous file deprecated on revision.

## Document Production System

File naming: `{project-name}-prd-{status}-v{major}.{minor}-{yyyymmdd}.md`

Front matter: same schema as product-brief.

## Exit

Write `.sweetclaude/state/prd.yaml`:

```yaml
epics: []
functional_requirements_count: 0
nfrs: []
current_version: {}
current_file: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — product-prd (n/a)

**Status:** completed | degraded
**Produced:** {filename}
**Key decisions:** {bullets}
**Open questions:** {bullets}
```
