---
description: "Design API endpoints: routes, request/response shapes, authentication, pagination, error responses, and versioning strategy."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# API Design

Design the API for: $ARGUMENTS

## Context

Read architecture doc, data model, and user stories from `docs/` and `.sweetclaude/stories/`.

## Process

### 1. Endpoint inventory

List every endpoint needed. For each:
- HTTP method and path
- Purpose (one sentence)
- Who can call it (auth requirements)

### 2. Detailed design per endpoint

For each endpoint:

```
### {METHOD} {path}

**Purpose:** {what it does}
**Auth:** {required role/permission}

Request:
  Headers: {required headers}
  Params: {path and query params with types}
  Body: {JSON shape with types}

Response 200:
  {JSON shape with types}

Response 4xx:
  {error shapes — 400 validation, 401 unauth, 403 forbidden, 404 not found}

Response 5xx:
  {generic error shape}
```

### 3. Cross-cutting concerns

- **Pagination:** pattern (cursor vs offset), defaults, maximums
- **Filtering/sorting:** query param conventions
- **Versioning:** strategy (URL path, header, none)
- **Rate limiting:** if applicable
- **CORS:** allowed origins

### 4. Save

Save to `docs/api-design.md`. Record key decisions via `design/manage-decisions`.
