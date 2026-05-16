---
id: STORY-021
type: story
title: Spike — SQLite as unified state store to replace drift-prone file/index system
status: new
priority: soon
effort: m
epic: null
milestone: null
sprint: null
tags: [spike, sqlite, state, drift, architecture, indexes]
origin: manual
created: 2026-05-14
updated: 2026-05-15
closed_date: null
---

## Description

As a developer using SweetClaude, I want to explore replacing the current file-per-artifact + index-file system with a local SQLite database, so that state drift between files and their indexes is structurally impossible rather than something we detect and repair after the fact.

The current system has a recurring class of bugs where index files (INDEX.md, BACKLOG-INDEX.md, migration-registry.yaml counters) fall out of sync with the files they describe. Every migration, counter recovery, and drift-gate scan exists to compensate for this fundamental mismatch. SQLite would make the index and the data the same thing.

## Spike Questions

1. **Feasibility**: Can Claude Code skills read and write SQLite reliably? What's the Python/shell surface for this in a skill context?
2. **Git compatibility**: SQLite `.db` files are binary — how do they interact with git diff, merge, and the project's existing gitignore strategy? Is WAL mode or a SQL dump approach better for version-controlled state?
3. **Migration path**: How would existing YAML state files and MD backlog items be ingested? Is this a hard cutover or can both formats coexist during transition?
4. **Skill complexity**: Skills currently read/write files directly. SQLite requires a schema, queries, and connection management. Does this add more complexity than it removes?
5. **Offline/portability**: SQLite is a single file — does this make the `.sweetclaude/` directory easier or harder to share, back up, and inspect without tooling?
6. **Human readability**: A key property of the current system is that all state is human-readable markdown/YAML. SQLite is not. What is lost?

## Acceptance Criteria

- [ ] Spike findings documented in `docs/internal/` covering all six questions above
- [ ] At minimum one proof-of-concept: backlog INDEX.md replaced with a SQLite query, showing drift is impossible
- [ ] Decision recorded: proceed with SQLite migration / hybrid approach / stay with files + better tooling / something else
- [ ] If proceeding: follow-on stories created covering schema design, migration, and skill updates

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
