# Story File Schema (per-project copy)

> ⚠️ **Non-normative.** This is a convenience copy in your project for quick reference. The canonical schema is maintained in the SweetClaude framework at `docs/internal/v4-story-schema.md`. If anything here disagrees with the canonical schema, the canonical wins. Regenerated on each migration; do not edit by hand.

**Version:** 1.0
**Date:** 2026-05-10
**Canonical source:** `docs/internal/v4-story-schema.md` in the SweetClaude framework repo

Story files are first-class markdown files. Frontmatter is YAML, body sections are markdown by convention.

---

## Frontmatter (all types)

```yaml
---
id: STORY-007
type: story
title: Add OAuth login
status: new
priority: soon
effort: m
epic: null
milestone: null
sprint: null
tags: []
origin: manual
created: 2026-05-10
updated: 2026-05-10
closed_date: null
---
```

**All fields are always present.** `null` is the only valid empty-value sentinel — fields are never omitted.

### Field reference

| Field | Values | Notes |
|---|---|---|
| `id` | `STORY-NNN`, `BUG-NNN`, `DEBT-NNN`, `CHORE-NNN` | Never changes after creation |
| `type` | `story` / `bug` / `debt` / `chore` | Determines subdirectory and body template |
| `title` | string | Canonical display title; slug does not change when title changes |
| `status` | `new` / `ready` / `active` / `blocked` / `deferred` / `done` / `abandoned` | `done` and `abandoned` → move to `done/` subdirectory |
| `priority` | `next` / `sooner` / `soon` / `later` / `someday` | |
| `effort` | `xs` / `s` / `m` / `l` / `xl` / `xxl` | |
| `epic` | `MS-NNN-slug/EP-NNN-slug` or `null` | `null` = backlog story |
| `milestone` | `MS-NNN-slug` or `null` | `null` = backlog story |
| `sprint` | `SPRINT-NNN` or `null` | Required in Agile mode for active stories |
| `tags` | list of strings | Free-form; case-insensitive matching; optional `docs/product/tags.md` registry |
| `origin` | `manual` / `inferred` / `imported` | `inferred` = created by Claude (needs review) |
| `created` | `YYYY-MM-DD` | Set once at creation |
| `updated` | `YYYY-MM-DD` | Set by SweetClaude on every mutation |
| `closed_date` | `YYYY-MM-DD` or `null` | Set when status transitions to `done` or `abandoned` |

---

## File naming

`TYPE-NNN-slugged-title.md`

- Slug: lowercase, spaces → hyphens, punctuation stripped, max ~50 chars
- **Slug is immutable** — set once at creation, never changes regardless of title edits

---

## Body sections by type

### story

```markdown
## Description
As a [who], I want [what] so that [why].

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Sprint History
| Sprint | Added | Removed | Outcome |
|---|---|---|---|
```

### bug

```markdown
## Description
[What is broken and the impact]

## Steps to Reproduce
1. ...

## Expected / Actual
**Expected:** ...
**Actual:** ...

## Acceptance Criteria
- [ ] Bug no longer reproducible via above steps

## Sprint History
| Sprint | Added | Removed | Outcome |
|---|---|---|---|
```

### debt

```markdown
## Description
[What the debt is]

## Why This Is Debt
[How it accumulated, what problem it causes now]

## Risk If Not Addressed
[What gets worse if this isn't fixed]

## Sprint History
| Sprint | Added | Removed | Outcome |
|---|---|---|---|
```

### chore

```markdown
## Description
[What needs to be done]

## Definition of Done
- [ ] Item 1
- [ ] Item 2

## Sprint History
| Sprint | Added | Removed | Outcome |
|---|---|---|---|
```

Sprint History is always present, maintained exclusively by SweetClaude, initially empty. Body sections are conventions — missing section = empty, not an error.

---

## Status transitions

```
new → ready → active → done
           ↘          ↘ abandoned
            blocked → (resume)
            deferred → (resume)
```

`done` and `abandoned` trigger a physical file move to the `done/` subdirectory. No other status change moves the file.

---

## Counter recovery

When `INDEX.md` is missing or frontmatter is unparseable:

1. Scan `docs/product/backlog/{type}s/` (including `done/`)
2. Scan `docs/product/roadmap/milestones/*/epics/*/{type}s/` (including `done/`) — promoted stories are no longer in backlog but their IDs are still in the sequence
3. Set `counter[type] = max(N across all files of that type in both locations)`, minimum 0
4. Reconstruct and write `INDEX.md` with recovered counters and rebuilt story table (backlog stories only)
5. Log the recovery event

Never silently assign ID 001 when the counter file is missing.
