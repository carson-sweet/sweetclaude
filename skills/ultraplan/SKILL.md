---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Prepare a structured ultraplan prompt from current phase artifacts, launch ultraplan, and ingest the resulting plan as the DESIGN phase architecture artifact."
category: design
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# ultraplan Integration

Use Anthropic's ultraplan (multi-agent planning with 3 explorers + 1 critic) for architectural decisions, with SweetClaude handling the context preparation and plan ingestion.

SweetClaude cannot invoke `/ultraplan` directly — ultraplan is a Claude Code feature, not a skill. This skill's job is to prepare the best possible prompt and pick up where you left off when you bring the plan back.

---

## Step 1: Read phase context

Read available state files:

```bash
cat .sweetclaude/state/brief.yaml 2>/dev/null
cat .sweetclaude/state/prd.yaml 2>/dev/null
cat .sweetclaude/state/personas.yaml 2>/dev/null
cat .sweetclaude/state/architecture.yaml 2>/dev/null
cat .sweetclaude/state/decision-log.md 2>/dev/null | tail -50
```

Also read the current work item from session state: `active_work_item.title` and `active_work_item.type`.

Identify what is available:
- **Problem statement** — from product brief (`problem_statement`, `solution_approach`)
- **Target users** — from personas (`name`, `primary_tasks`, `success_criteria`)
- **Functional scope** — from PRD epics and non-functional requirements
- **Prior decisions** — from architecture.yaml and decision-log.md
- **Constraints** — compliance requirements, team size, deployment model (if set)

If no brief or PRD exists: tell the user "ultraplan works best with a product brief and PRD — run `/sweetclaude:product-brief` and `/sweetclaude:product-prd` first, or proceed and I'll work with what we have."

---

## Step 2: Compose the ultraplan prompt

Produce a structured prompt in this format:

```
## Context

**Project:** {project name or work item title}
**What we're building:** {one paragraph: the core problem, who has it, how this solves it}
**Target users:** {1–3 personas with their primary tasks and success criteria}
**Scale and deployment:** {expected load, deployment model, solo/team}

## Functional scope

{Bullet list of epics or major feature areas from the PRD. 5–10 items.}

## Non-functional requirements

{Performance, availability, compliance, security requirements. Mark any HARD REQUIREMENTS from compliance context.}

## Constraints and prior decisions

{Any decisions already made — language, framework, database, deployment target. From architecture.yaml and decision-log.}

## What we need

Design the architecture for this system. Specifically:
- Component breakdown and responsibilities
- Communication patterns between components
- Data model and storage strategy
- API surface (internal and external)
- Deployment architecture
- Key risks and how the design mitigates them

Produce a structured architecture document with Architectural Decision Records (ADRs) for each significant decision.
```

Show the composed prompt to the user. Ask: "Does this accurately capture the context? Edit anything before I present it for ultraplan."

Wait for confirmation or edits. Apply any changes before continuing.

---

## Step 3: Launch ultraplan

Present the final prompt formatted for easy copying:

```
Your ultraplan prompt is ready. Run this in Claude Code:

/ultraplan {paste the full prompt here}

When ultraplan finishes, bring the plan output back here and I'll ingest it as your architecture artifact.
```

Offer via AskUserQuestion:
- **I've got the plan — paste it here** — continue to Step 4
- **I don't have ultraplan access** — fall back to native design (invoke `sweetclaude:design-architecture`)
- **Something else**

Wait. Do not proceed until the user responds.

---

## Step 4: Ingest the plan

The user pastes the ultraplan output. Accept it as text input.

Parse and extract:
1. **Architecture overview** — the main design narrative
2. **Component list** — named components with responsibilities
3. **ADRs** — any "Decision:" or "ADR:" sections (or structured decision blocks)
4. **Identified risks** — any risk or concern sections

If the output doesn't fit this structure cleanly, extract what's present and note what's missing.

---

## Step 5: Write the architecture artifact

### Artifact path resolution

Read `.sweetclaude/artifact-privacy.yaml`. If missing: stop and tell the user to run `/sweetclaude:setup` first.

Read `categories.technical.base_path`. Construct: `{base_path}/architecture.md`.

Write the architecture document, structured as:

```markdown
# Architecture: {project name}

> Source: ultraplan output — {date}
> SweetClaude phase: DESIGN

## Overview

{architecture overview from the plan}

## Components

{component list with responsibilities}

## Communication Patterns

{from plan — or note if not addressed}

## Data Model

{from plan — or note if not addressed}

## Deployment Architecture

{from plan — or note if not addressed}

## Architectural Decision Records

{ADRs extracted from the plan, each as:}

### ADR-NNN: {title}
**Status:** proposed
**Decision:** {what was decided}
**Rationale:** {why}
**Consequences:** {trade-offs}

## Risks

{risks identified by ultraplan}

## Open Questions

{anything the plan flagged as unresolved}
```

### Update state

Write `.sweetclaude/state/architecture.yaml`:

```yaml
source: ultraplan
produced_at: {ISO timestamp}
current_architecture_file: {artifact path}
adr_count: {N}
open_questions: {list}
compliance_requirements_applied: {from context, or []}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — ultraplan (DESIGN)

**Status:** completed
**Produced:** {architecture file path}
**Source:** ultraplan output ingested
**ADRs:** {N}
**Open questions:** {list or none}
```

---

## Step 6: Review and next steps

Present a summary:

```
Architecture artifact written: {path}
ADRs captured: {N}
Open questions: {list or "none"}
```

Then ask: "Anything in the plan you want to clarify or adjust before we move to tech spec?" Remain available for iteration. Do not suggest advancing to the next phase — the user decides when design is done.
