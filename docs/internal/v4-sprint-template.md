# v4 Sprint Template

**Version:** 1.0
**Date:** 2026-05-12
**See also:** `v4-story-schema.md` §5 (canonical sprint schema)

Sprint files are first-class entities in Agile mode. They live in the roadmap under either a milestone or an epic.

---

## Filename and location

Pattern: `SPRINT-NNN-<slug>.md`

| Location | Path |
|---|---|
| Milestone-level | `docs/product/roadmap/milestones/MS-NNN-slug/sprints/SPRINT-NNN-slug.md` |
| Epic-level | `docs/product/roadmap/milestones/MS-NNN-slug/epics/EP-NNN-slug/sprints/SPRINT-NNN-slug.md` |
| Completed | …/`sprints/done/SPRINT-NNN-slug.md` |

---

## Frontmatter

```yaml
---
id: SPRINT-NNN
type: sprint
goal: <one-sentence sprint goal>
status: planned
milestone: null | MS-NNN-slug
epic: null | MS-NNN-slug/EP-NNN-slug
committed_stories: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
closed_date: null
---
```

**Exactly one of `milestone` or `epic` must be non-null.**

`status` values: `planned`, `active`, `completed`, `abandoned`.

---

## Body

```markdown
## Goal

[Restate the goal as a paragraph with context]

## Committed Stories

- [STORY-NNN Title](../stories/STORY-NNN-slug.md)

## Added Mid-Sprint

- [STORY-NNN Title](../stories/STORY-NNN-slug.md) — added YYYY-MM-DD, reason: ...

## Removed Mid-Sprint

- [STORY-NNN Title](../stories/STORY-NNN-slug.md) — removed YYYY-MM-DD, reason: ...

## Outcome

[Filled at sprint close: what shipped, what carried over, what was abandoned]

## Retro Notes

[Filled at sprint close: what went well, what to change]
```

---

## Sprint History sync

When a story is added to a sprint, removed from a sprint, or the sprint closes:

1. The sprint file's Committed Stories / Added / Removed / Outcome sections are updated.
2. Each affected story's `Sprint History` body table gets a corresponding row.

Both writes happen in the same operation. If either fails, both are rolled back.
