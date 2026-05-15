---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Define system architecture — components, boundaries, communication patterns, data flow, and compliance requirements."
category: technical
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:design-architecture" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# Design Architecture

## Artifact Path Resolution

Before writing any artifact file:

1. Read `.sweetclaude/artifact-privacy.yaml`. If it does not exist, stop and say:
   > "No artifact privacy manifest found. Run `/sweetclaude:setup` to configure artifact privacy, then return here."
   Do not guess a path. Do not fall back to a default.

2. Read `categories.technical.base_path`. This is the base directory for all technical artifacts.

3. Construct full paths as `{base_path}/{filename}`, e.g. `{base_path}/architecture.md`, `{base_path}/tech-spec-v1.md`.

4. Write artifacts to those paths.

Define the architecture for your system. This skill conducts a structured interview, produces Architectural Decision Records (ADRs) for each significant decision, and generates an architecture document ready for development.

## Entry

Check for `.sweetclaude/` directory. If not found, tell the user to run `/sweetclaude:init` first. Stop.

Check for `.sweetclaude/log.md`. If not found, create it.

Read available state:
- `.sweetclaude/state/brief.yaml`
- `.sweetclaude/state/prd.yaml`
- `.sweetclaude/state/personas.yaml`
- `.sweetclaude/state/stories.yaml`

Note any missing state files — the interview is the primary input, but prior artifacts inform decisions.

**ultraplan option:** For large or complex architectural decisions, Anthropic's ultraplan (3 explorer agents + 1 critic) produces more thorough results than a single-context pass. Offer via AskUserQuestion before starting the interview:
- **Run native design interview** (default) — structured interview → SweetClaude produces the architecture document
- **Use ultraplan** — invoke `sweetclaude:ultraplan` to prepare context, launch ultraplan, and ingest the result

If the user picks ultraplan: invoke `sweetclaude:ultraplan`. Do not start the interview below.

## Step 1 — Architecture Interview

Ask one question at a time. Always offer a recommendation before asking the user to decide.

**Platform decisions:**
1. "What programming language(s) will this be built in? I can recommend based on your team, use case, and ecosystem if helpful."
2. "What type of application is this primarily — web app, CLI tool, CLI utility, desktop app, mobile app, or something else?"
3. "How will this be deployed — SaaS (cloud-hosted, you manage), on-premises (customer hosts), locally run (runs on user's machine), or a hybrid?"

**Architecture style:**
4. "What's your instinct on architecture style — monolith (simpler, one deployable), services (microservices or macro-services, more complex), or are you unsure?" Offer a recommendation based on team size and scale indicators from prior state. A solo founder with an early-stage product should start with a monolith unless there's a strong reason not to.

**Data:**
5. "What kind of database do you need — relational (structured data, SQL), document (flexible schema, JSON), time-series, graph, or a mix?" Recommend based on the use case.

**Compliance and security interview (mandatory, do not skip):**
6. "Does your product handle any of the following regulated data types? Answer yes or no for each:
   - PII (personally identifiable information — names, emails, addresses, IDs)
   - PHI (protected health information — anything health/medical related)
   - PCI data (payment card numbers, CVVs, cardholder data)
   - Financial data subject to regulatory oversight (SOX, SEC, etc.)
   - Any other regulated data or compliance frameworks your industry requires (GDPR, CCPA, HIPAA, SOC 2, etc.)"

**If any regulated data:** "These are legal requirements, not design preferences. I'll flag specific compliance constraints throughout the architecture and tech spec." Surface and label these as HARD REQUIREMENTS.

**Additional questions as needed** based on what the prior answers imply (auth requirements, third-party integrations, offline capability, etc.)

## Step 2 — Analyze

Review all interview answers alongside available prior artifacts. Surface any conflicts: does the architecture interview imply something inconsistent with what the PRD or stories require?

## Step 3 — Decision List

Produce a list of architectural decisions to be made. Walk through each with the user. For each decision:
- State the decision to be made
- Give a recommendation with reasoning
- Note any compliance requirements that constrain the options
- Record the decision once made

## Step 4 — ADRs

Create an ADR for each significant decision. Use the following format (standard ADR format):

```markdown
# ADR-{NNN}: {Title}

**Date:** {YYYY-MM-DD}
**Status:** Accepted | Proposed | Deprecated | Superseded

## Context

{What situation or requirement prompted this decision?}

## Decision

{What was decided?}

## Rationale

{Why this option over alternatives?}

## Consequences

{What becomes easier or harder as a result of this decision?}

## Alternatives Considered

{What other options were evaluated and why were they rejected?}
```

Save each ADR to `{base_path}/adr/ADR-{NNN}-{kebab-title}.md`.

## Step 5 — Boundary Design

**If service-oriented architecture:**
Define service boundaries:
- Which services exist?
- What does each service own (data, business logic)?
- How do services communicate (REST, gRPC, message queue, events)?
- Where are the seams — what can change in one service without affecting others?

**If monolith:**
Define module/domain boundaries:
- What are the bounded contexts within the monolith?
- What are the internal module boundaries?
- What are the domain seams — where would you split if you needed to?
- What must not bleed across module boundaries?

## Step 6 — Architecture Document

Write the architecture document. Standard sections:
- Overview and guiding principles
- Technology decisions (language, framework, database, deployment)
- Architecture style and rationale
- Component diagram (ASCII or description)
- Data flow
- Compliance and security requirements (labeled as HARD REQUIREMENTS if applicable)
- Boundary design (services or modules)
- ADR index (links to each ADR)
- Open questions

## Document Production System

ADRs: `{base_path}/adr/ADR-{NNN}-{title}-{yyyymmdd}.md`
Architecture doc: `{base_path}/{project-name}-architecture-draft-v1.0-{yyyymmdd}.md`

Both follow the standard front matter schema.

## Exit

Write `.sweetclaude/state/architecture.yaml`:

```yaml
style: monolith | services | hybrid
tech_stack:
  language: {}
  framework: {}
  database: {}
  deployment: {}
compliance_requirements: []
adr_ids: []
boundary_design_type: services | modules
current_architecture_file: {}
```

Append to `.sweetclaude/log.md`:

```markdown
## {ISO datetime} — design-architecture (n/a)

**Status:** completed | degraded
**Produced:** {architecture doc filename}, {ADR count} ADRs
**Compliance flags:** {list or none}
**Key decisions:** {bullets}
**Open questions:** {bullets}
```
