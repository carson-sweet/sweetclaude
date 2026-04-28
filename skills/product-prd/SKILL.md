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

## Autonomous Mode

If `$ARGUMENTS` contains `--autonomous` or `--from-artifacts`, skip all user interaction and generate the PRD from available artifacts.

**Step 1: Read available artifacts**

Load the following files if they exist:
- `.sweetclaude/state/discovery.yaml` — project intent, scope, problem, not_scope
- `.sweetclaude/state/compliance-context.yaml` — data categories, derived frameworks
- `.sweetclaude/state/personas.yaml` — target users
- `.sweetclaude/state/brief.yaml` — product brief content
- Any `.md` docs in `docs/` matching: personas, task-analysis, constraints, discovery

**Step 2: Generate PRD using the standard outline**

Sections (in order):
1. Executive Summary — synthesize from discovery intent + problem_summary
2. Problem Statement — use the concrete scenario from L2/L3; if absent, flag
3. Goals and Success Metrics — derive from task success criteria; must be binary (true/false after ship)
4. Functional Requirements — numbered `FR-001`, `FR-002`… one requirement per testable behavior
5. Non-Functional Requirements — include compliance NFRs derived from `compliance-context.yaml derived_frameworks`:
   - `gdpr` → NFR: All PII must be encrypted at rest and in transit; users must be able to request deletion
   - `hipaa` → NFR: PHI access must be logged with user ID, timestamp, and action
   - `pci_dss` → NFR: Cardholder data must never be stored in plaintext
   - `coppa` → NFR: No personal data collected from users under 13 without verifiable parental consent
   - `gdpr_floor` → NFR: Data minimization; collect only what is necessary for the stated purpose
6. Epics and User Story Summary — derive from personas and task analysis
7. Out of Scope — use `not_scope` from `discovery.yaml`
8. Assumptions and Constraints — use constraints artifacts
9. Open Questions
10. Additional Development

**Step 3: Flag thin sections**

For each section where source artifacts provided insufficient signal, append inline:
> `⚠️ Flagged for review: [specific gap — what information was missing and what the user should provide at PRD review]`

Do not halt. Complete the full PRD with all flags inline, then continue to Step 4.

**Step 4: Write output**

Write to `docs/prd-[feature-name]-v1-[YYYY-MM-DD].md`. Use the standard front matter:

```yaml
---
title: {feature} PRD
version: 1.0
status: draft
author: {git user}
assisted_by: Claude Code + SweetClaude John Wick
date: {YYYY-MM-DD}
generated: autonomous
---
```

**Step 5: Report flags**

Output:
```
Autonomous PRD generation complete.
File: docs/prd-[feature]-v1-[date].md

Flagged sections for D4 review gate:
- [Section name]: [gap description]
```

If no sections flagged: "All sections populated from discovery artifacts."

**Stop here.** Do not proceed to Pre-Write Flow.

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
