---
closed_date: '2026-05-15'
created: 2026-05-13
effort: s
epic: EP-009
id: CHORE-002
milestone: null
origin: manual
priority: soon
sprint: null
status: done
tags:
- v4
- preflight
- testing
title: Add session-preflight.sh test fixture for schema_version 1 and 2
type: chore
updated: 2026-05-15
---

## Description

`test-hooks.sh` has no test that runs `session-preflight.sh` against a project fixture with `schema_version: 1` or `schema_version: 2` and asserts no heal message fires. The regression fixed in 3.68.1 had no test catching it before, and still doesn't.

Identified by the 3.68.1 caucus (integration agent finding 6).

## Acceptance Criteria

- [ ] `test-hooks.sh` (or equivalent) has a test case that constructs a fixture with `schema_version: 1` and `setup_complete: true`, runs `session-preflight.sh`, and asserts the output does NOT contain a heal message
- [ ] Same test exists for `schema_version: 2`
- [ ] A test case with `schema_version: 3` asserts the heal message DOES fire
- [ ] Tests pass on macOS (BSD grep)

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
