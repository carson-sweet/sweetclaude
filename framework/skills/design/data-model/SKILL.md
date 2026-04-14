---
name: sweetclaude-design-data-model
description: "Design the data model: entities, relationships, constraints, indexes, and migration strategy. Produces schema definitions and migration plans."
---

<preflight-guard>
STOP. Before executing this skill, check: does state/phase.yaml exist in the project working repo or project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Data Model Design

Design the data model for: $ARGUMENTS

## Context

Read architecture doc and tech spec from `specs/` if they exist. Read existing schema if the project has a database.

## Process

### 1. Identify entities

From the PRD, user stories, and domain language — what are the core things this system tracks? For each entity:
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
- Are any destructive (DROP, rename)? Flag for expand/contract pattern.
- What's the rollback plan?
- Data backfill needed?

### 5. Save

Save to `specs/data-model.md` in the working repo. Record key decisions via `design/manage-decisions`.
