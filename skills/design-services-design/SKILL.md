---
description: "Design service boundaries: which services exist, how they communicate, what each owns, and where the boundaries are."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Services Design

Design service boundaries for: $ARGUMENTS

## Context

Read architecture doc from `specs/`. This skill fills in the service-level detail that the architecture doc outlines at a higher level.

## Process

### 1. Service inventory

List each service or module. For each:
- Name
- Responsibility (one sentence. If you need two, it is two services.)
- What data it owns
- What it does NOT own

### 2. Communication patterns

For each service-to-service interaction:
- Sync (HTTP/gRPC) or async (events/queues)?
- Who initiates?
- What data flows?
- What happens when the call fails?

### 3. Boundaries

- What can each service change without coordinating with others?
- Where are the shared contracts (API schemas, event schemas)?
- What requires a coordinated deployment?

### 4. Save

Save to `specs/services-design.md`. Record key decisions via `design/manage-decisions`.
