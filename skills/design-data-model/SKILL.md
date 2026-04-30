---
spdx-license: AGPL-3.0-or-later
description: "Design the data model: entities, relationships, constraints, indexes, and migration strategy. Produces schema definitions and migration plans."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Data Model Design

Design the data model for: $ARGUMENTS

## Context

Read architecture doc and tech spec from `docs/` if they exist. Read existing schema if the project has a database.

## Process

### 1. Identify entities

From the PRD, user stories, and domain language, identify the core things this system tracks. For each entity:
- Name (singular, domain language)
- Purpose (one sentence)
- Key attributes (not exhaustive — the important ones)

### 2. Define relationships

For each pair of related entities:
- Relationship type (one-to-one, one-to-many, many-to-many)
- Direction and naming (an Organization HAS MANY People)
- Required vs optional
- Cascade behavior (what happens on delete?)

### 3. Design the schema

For each entity, produce the full schema:
- All fields with types
- Primary keys
- Foreign keys with references
- Constraints (unique, not null, check)
- Indexes (what queries need to be fast?)
- Default values
- Timestamps (created_at, updated_at)

Present in the project's ORM/migration format if one is detected (Drizzle, Prisma, Alembic, etc.), otherwise as SQL DDL.

### 4. Migration strategy

If modifying an existing schema:
- What migrations are needed?
- Are any destructive (DROP, rename)? Flag them for expand/contract pattern.
- What's the rollback plan?
- Data backfill needed?

### 5. Save

Save to `docs/data-model.md`. Record key decisions via `design/manage-decisions`.
