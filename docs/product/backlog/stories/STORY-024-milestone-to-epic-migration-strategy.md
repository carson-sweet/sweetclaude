---
id: STORY-024
type: story
title: "Milestone-to-epic migration strategy for public launch"
status: new
priority: soon
effort: l
epic: EP-002
epic_sequence: 6
tags: [roadmap, migration]
created: 2026-05-16
updated: 2026-05-16
---

# Milestone-to-epic migration strategy for public launch

As a SweetClaude user with an existing milestone-based project, I want a reliable migration path from milestones to epics/releases so that I can adopt the new roadmap system without losing data or context.

## Context

The v4 roadmap system replaces milestones (MS-NNN) with epics (EP-NNN) grouped under releases (REL-NNN). Existing users may have complex milestone pipelines with contributing work items, dependency chains, and status history. The experimental rollout to syncog exposed that directory creation, cache backfill, and big-picture rendering all need to work correctly on a project that has never had epics.

## Acceptance criteria

- Given a project with MS-NNN milestone files and BL-NNN/STORY-NNN contributing work items, when I run the migration, then each milestone becomes an EP-NNN epic with its contributing items linked via `epic: EP-NNN` frontmatter
- Given milestones with `Depends on: MS-001, MS-002` references, when I run the migration, then epic `depends_on` fields reference the corresponding EP-NNN IDs
- Given a milestone with `Status: done`, when I run the migration, then the epic status is `done` and its stories retain their original status
- Given the migration completes, when I run `/sweetclaude:big-picture`, then the roadmap renders correctly with consistent counts
- The migration is idempotent — running it twice produces the same result
- A dry-run mode shows what would change without writing files
- Original milestone files are preserved in an archive directory
