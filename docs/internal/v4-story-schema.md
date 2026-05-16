# v4 Story Schema Reference

**Version:** 2.0
**Date:** 2026-05-12
**Status:** Canonical schema reference for v4. All skills and migration tools must validate against this document.
**Supersedes:** v4-story-schema.md v1.0 (2026-05-10), `docs/product/backlog/SCHEMA.md` (any version)

> This document is the **single source of truth** for v4 story, sprint, and INDEX schemas. The design and migration specs reference values here rather than restating them. Any divergence between this doc and another doc is a bug in the other doc.

---

## 1. Story frontmatter

All fields are required. `null` is the only sentinel for absent optional values. Skills must not check for field absence — they must check for `null`.

| Field | Type | Allowed values | Default |
|---|---|---|---|
| `id` | string | `STORY-NNN`, `BUG-NNN`, `DEBT-NNN`, `CHORE-NNN` (zero-padded 3 digits) | assigned at creation |
| `type` | string | `story`, `bug`, `debt`, `chore` | `story` |
| `title` | string | free text, ≤ 200 chars | (required at creation) |
| `status` | string | see [Status state machine](#3-status-state-machine) | `new` |
| `priority` | string | `next`, `sooner`, `soon`, `later`, `someday` | `soon` |
| `effort` | string | `xs`, `s`, `m`, `l`, `xl`, `xxl` | `m` |
| `epic` | string or null | qualified path `MS-NNN-slug/EP-NNN-slug` or `null` | `null` |
| `milestone` | string or null | milestone slug `MS-NNN-slug` or `null` | `null` |
| `sprint` | string or null | sprint ID `SPRINT-NNN` or `null` (see [Sprint schema](#5-sprint-frontmatter)) | `null` |
| `tags` | list | list of strings, case-insensitive on read | `[]` |
| `origin` | string | `manual`, `inferred`, `imported` | `manual` |
| `created` | date | `YYYY-MM-DD` | today |
| `updated` | date | `YYYY-MM-DD` | today (set by SweetClaude on any mutation) |
| `closed_date` | date or null | `YYYY-MM-DD` (set when status → `done` or `abandoned`) or `null` | `null` |
| `prs` | list | list of `{number: int, branch: str, opened_at: date}` objects | `[]` |

### prs field

Tracks pull requests associated with this story. Populated by `sweetclaude:go` when the user confirms a PR number at VERIFY phase entry. PR state (open/merged/closed) is never stored — it is checked live at closeout time. Existing stories without `prs` are treated as `prs: []`; no migration required.

Example:
```yaml
prs:
  - number: 57
    branch: feat/v4-phase1-backlog
    opened_at: 2026-05-15
```

### Origin values

- `manual` — explicitly created by the user via a skill or direct file write
- `inferred` — created by Claude in Flow mode without user confirmation; needs user review before canonical
- `imported` — created via `project-gh-import-issues` or equivalent

The legacy v1.0 schema had `generated`; this has been replaced by `inferred`. Migration from v3 maps `source: generated` → `origin: inferred`.

### Type ↔ directory ↔ ID prefix

| Type | Backlog directory | Roadmap directory | ID prefix |
|---|---|---|---|
| `story` | `docs/product/backlog/stories/` | `docs/product/roadmap/milestones/MS-NNN-slug/epics/EP-NNN-slug/stories/` | `STORY-` |
| `bug` | `docs/product/backlog/bugs/` | …/`bugs/` | `BUG-` |
| `debt` | `docs/product/backlog/debt/` | …/`debt/` | `DEBT-` |
| `chore` | `docs/product/backlog/chores/` | …/`chores/` | `CHORE-` |

---

## 2. Filename and slug

Pattern: `<ID>-<slug>.md` (e.g. `STORY-007-add-oauth-login.md`)

### Slug generation

1. Take the title at creation time.
2. Lowercase.
3. Replace non-alphanumeric characters with `-`.
4. Collapse consecutive `-` to a single `-`.
5. Strip leading and trailing `-`.
6. Truncate to 50 characters at the last `-` boundary (do not break a word).

Slugs are **immutable**. The slug is generated once from the title at creation and never changes, regardless of subsequent title edits. The `title` field in frontmatter is the canonical display title. The filename is a stable identifier (preserves git history references, PR mentions, external links).

### Slug uniqueness

Before writing a new file, the creating skill must scan both backlog and roadmap directories for any file matching `<ID-prefix>NNN-<slug>.md` (same slug, any ID). If a collision is found, append `-2`, `-3`, etc. to the slug until unique. Document the suffix in the file's `created` log if useful.

---

## 3. Status state machine

Valid statuses: `new | ready | active | blocked | deferred | done | abandoned`

**Note:** `in_progress` and `in_review` are NOT valid v4 statuses. They are v3 statuses; the migration maps them to `active` (see [Migration mappings](#7-v3-to-v4-migration-mappings)).

### Allowed transitions

- `new` → `ready`, `active`, `deferred`, `abandoned`
- `ready` → `active`, `deferred`, `abandoned`
- `active` → `blocked`, `done`, `deferred`, `abandoned`
- `blocked` → `active`, `deferred`, `abandoned`
- `deferred` → `new`, `ready`, `active`, `abandoned`
- `done` → (terminal — no outbound transitions)
- `abandoned` → (terminal — no outbound transitions)

### Status ↔ directory contract

Any skill that writes `status: done` or `status: abandoned` **must** move the file to the appropriate `done/` subdirectory in the same operation. Any skill that moves a file to `done/` **must** write the corresponding status. The health check enforces this invariant retroactively; skills must enforce it at write time.

Files with `status: done` or `status: abandoned` live under `<type>s/done/`. Files with any other status live directly under `<type>s/`.

---

## 4. Body sections by type

Body sections are convention. Missing sections are treated as empty, not errors. However, `project-issues` and the migration skill must write the correct body structure when creating or migrating files.

### story

```markdown
## Description
As a [who], I want [what] so that [why].

## Acceptance Criteria
- [ ] Criterion 1

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

Sprint History is maintained exclusively by sprint skills and is initially empty.

---

## 5. Sprint frontmatter

Sprints are first-class entities in Agile mode. Sprint files live in the roadmap under either a milestone or an epic.

### Filename and location

Pattern: `SPRINT-NNN-<slug>.md`

| Location | Path |
|---|---|
| Milestone-level | `docs/product/roadmap/milestones/MS-NNN-slug/sprints/SPRINT-NNN-slug.md` |
| Epic-level | `docs/product/roadmap/milestones/MS-NNN-slug/epics/EP-NNN-slug/sprints/SPRINT-NNN-slug.md` |
| Completed | …/`sprints/done/SPRINT-NNN-slug.md` |

### Sprint frontmatter fields

All required. `null` for absent optional values.

| Field | Type | Allowed values | Default |
|---|---|---|---|
| `id` | string | `SPRINT-NNN` (zero-padded 3 digits) | assigned at creation |
| `type` | string | always `sprint` | `sprint` |
| `goal` | string | sprint goal, free text | (required at creation) |
| `status` | string | `planned`, `active`, `completed`, `abandoned` | `planned` |
| `milestone` | string or null | `MS-NNN-slug` if milestone-level; `null` if epic-level | depends on location |
| `epic` | string or null | qualified `MS-NNN-slug/EP-NNN-slug` if epic-level; `null` if milestone-level | depends on location |
| `committed_stories` | list | list of story IDs (e.g. `[STORY-007, BUG-003]`) committed at sprint start | `[]` |
| `created` | date | `YYYY-MM-DD` | today |
| `updated` | date | `YYYY-MM-DD` (set on any mutation) | today |
| `closed_date` | date or null | `YYYY-MM-DD` when status → `completed` or `abandoned` | `null` |

**Exactly one of `milestone` or `epic` must be non-null.** Skills enforce this at write time.

### Sprint body sections

```markdown
## Goal
[Restate the goal as a paragraph]

## Committed Stories
- [STORY-007 Add OAuth login](../stories/STORY-007-add-oauth-login.md)
- [BUG-003 Crash on empty input](../bugs/BUG-003-crash-on-empty-input.md)

## Added Mid-Sprint
- [STORY-012 Login analytics](../stories/STORY-012-login-analytics.md) — added 2026-05-14

## Removed Mid-Sprint
- [BUG-007 Mobile layout](../bugs/BUG-007-mobile-layout.md) — removed 2026-05-15, reason: blocked

## Outcome
[Filled at sprint close: what shipped, what carried over, what was abandoned]

## Retro Notes
[Filled at sprint close: what went well, what to change]
```

Sprint History on stories is generated from sprint files. The sprint skill writes both: a row in each affected story's Sprint History table, and the corresponding entry in this sprint's body.

### Sprint counter

The sprint counter is **project-wide**, not per-milestone or per-epic. Counter state is stored in `docs/product/roadmap/INDEX.md` frontmatter as `counters.sprint`. Counter recovery scans both milestone-level and epic-level sprint locations (both active and `done/`).

---

## 6. INDEX.md frontmatter

The backlog INDEX.md is the authoritative counter store for story-typed counters (`story`, `bug`, `debt`, `chore`). The roadmap INDEX.md is the authoritative counter store for the sprint counter AND the milestone counter. Each milestone's INDEX.md stores that milestone's epic counter.

### Backlog INDEX.md

Path: `docs/product/backlog/INDEX.md`

```yaml
---
counters:
  story: 7
  bug: 3
  debt: 2
  chore: 4
---
```

### Roadmap INDEX.md

Path: `docs/product/roadmap/INDEX.md`

```yaml
---
counters:
  sprint: 12
---
```

Milestone-level and epic-level INDEX.md files have **no counter frontmatter** — they are navigation manifests only. The milestone counter (MS-NNN) is incremented when a milestone is created; the epic counter (EP-NNN) is per-milestone (reset to 0 within each milestone directory). Both counters are stored at the navigation manifest level — `roadmap/INDEX.md` tracks `milestone`, and each `milestones/MS-NNN-slug/INDEX.md` tracks `epic` for that milestone.

Revised INDEX.md frontmatter:

```yaml
# docs/product/roadmap/INDEX.md
---
counters:
  milestone: 4
  sprint: 12
---
```

```yaml
# docs/product/roadmap/milestones/MS-001-platform-foundation/INDEX.md
---
counters:
  epic: 3
---
```

### INDEX.md write protocol

Writers must use the temp-file + atomic-rename pattern:

1. Read current INDEX.md
2. Compute updated content (counter increment + table row edit)
3. Write to `INDEX.md.tmp` in the same directory
4. `mv INDEX.md.tmp INDEX.md` (atomic on POSIX)

For counter increments specifically, the entire read-modify-write must be guarded by a file-level lock. The recommended pattern uses `mkdir` (atomic):

```bash
LOCKDIR="<INDEX-parent>/.counter.lock"
if mkdir "$LOCKDIR" 2>/dev/null; then
  trap "rmdir '$LOCKDIR'" EXIT
  # read-modify-write
else
  # another writer holds the lock; retry with backoff or fail loudly
fi
```

Skills running on Claude Code sessions (no shell long-running supervision) should: take the lock → perform the write → release the lock within a single tool invocation. Holding a lock across multiple invocations is not supported.

---

## 7. v3 to v4 migration mappings

The migration skill applies these transforms when remapping v3 fields to v4.

### Status mapping

| v3 value | v4 value | Notes |
|---|---|---|
| `backlog` | `new` | Initial state rename |
| `ready` | `ready` | Unchanged |
| `active` | `active` | Passthrough — some v3 projects already used `active` directly; preserved as-is |
| `in_progress` | `active` | v3 had granular "in progress" + "in review"; v4 collapses to `active` |
| `in_review` | `active` | Same |
| `blocked` | `blocked` | Unchanged |
| `deferred` | `deferred` | Unchanged |
| `done` | `done` | Unchanged |
| `cancelled` | `abandoned` | Renamed |

Pre-migration validation rejects any status value not in the v3 column.

### Type mapping

| v3 type | v4 type | Notes |
|---|---|---|
| `story` | `story` | Unchanged |
| `bug` | `bug` | Unchanged |
| `chore` | `chore` | Unchanged |
| `spike` | `story` | Spikes become stories with a spike-style description; no separate type in v4 |
| (no `debt` in v3) | — | v4 adds `debt` for new items; not migration-relevant |

### Source → origin

| v3 `source` | v4 `origin` |
|---|---|
| `manual` | `manual` |
| `inferred` | `inferred` |
| `generated` | `inferred` |
| `imported` | `imported` |

### Other field renames

- `sprint_history` (frontmatter YAML array) → Sprint History markdown table in body
- `cancelled_at` (if present) → `closed_date`
- `done_at` (if present) → `closed_date`

### ID renumbering

v3 used a single `I-NNN` or `BL-NNN` sequence across all types. v4 uses per-type counters starting at 001. Migration assigns new IDs deterministically:

1. Sort all v3 items by `id` ascending (numeric sort on the trailing digits)
2. Iterate in that order
3. For each item, increment the per-type counter and assign `<TYPE-prefix>NNN`

This order-locks the mapping: re-running migration on the same v3 input always produces the same v4 IDs.

---

## 8. Health check rules

Run automatically during `big-picture` and `project-backlog-triage`. Each rule is independent — a failure in one does not skip the others.

### Always-on rules

- No story ID appears in both `docs/product/backlog/{type}s/` and `docs/product/roadmap/.../{type}s/`. Counter recovery cannot resolve this; halt with a fatal error.
- Counter state in INDEX.md matches the actual file count per type (recompute via scan).
- No story file exists outside its expected type subdirectory.
- Any file under `done/` must have `status: done` or `status: abandoned`. Any file with those statuses must be under `done/`. If skills enforce this at write time, the rule should always pass — drift indicates a skill bug.
- Filename `<TYPE-prefix>NNN` matches the frontmatter `id` field.
- Slug rules followed (lowercase, no consecutive `-`, no leading/trailing `-`, ≤ 50 chars).
- Sprint files: exactly one of `milestone` or `epic` is non-null.

### Gated rules

- All roadmap stories are in epics (none loose on milestones) — **gated:** skip if `docs/product/roadmap/` does not exist.
- All active and future stories migrated from v3 (no `BL-NNN-*.md` files remain at `.sweetclaude/product/backlog/`, EXCEPT files explicitly skipped during migration and recorded in `MIGRATION-MAP.md` with `migrated: skipped`).

### Counter recovery

When `INDEX.md` is missing or its frontmatter fails to parse, the recovery procedure runs before any new file is written:

1. Scan all locations matching the appropriate file or directory pattern:
   - For story-type counters: files matching `<TYPE-prefix>NNN-*.md` under `docs/product/backlog/{type}s/` (including `done/`) and `docs/product/roadmap/milestones/*/epics/*/{type}s/` (including `done/`)
   - For sprint counter: files matching `SPRINT-NNN-*.md` under `docs/product/roadmap/milestones/*/sprints/` and `docs/product/roadmap/milestones/*/epics/*/sprints/` (including `done/` at each level)
   - For milestone counter: directories matching `MS-NNN-*` under `docs/product/roadmap/milestones/`
   - For per-milestone epic counter: directories matching `EP-NNN-*` under `docs/product/roadmap/milestones/MS-NNN-slug/epics/` — directories that do NOT match the `EP-NNN` pattern (e.g. `EP-MISC-general/`) are skipped entirely and do not participate in counter recovery
2. From each matching filename or directory name, extract the numeric N from the `NNN` component. Any name that does not match the numeric pattern is skipped (not zero, not an error — skipped).
3. If the same `<TYPE-prefix>NNN` stem appears in more than one location for a given counter, halt with a fatal "duplicate ID detected" error. Recovery cannot proceed until resolved manually.
4. Set `counter[type] = max(N)`, minimum 0. If no matching files/directories exist, counter is 0.
5. Reconstruct and write the INDEX.md with recovered counters and a rebuilt table (backlog stories only — roadmap stories are not duplicated in the backlog INDEX.md).
6. Log the recovery event (counter name, count recovered, reason, whether roadmap was scanned, whether any non-matching names like `EP-MISC-general` were encountered and skipped).

Skills must not silently assign ID 001 when INDEX.md is missing — that produces duplicate IDs in any project that has ever had stories.

---

## 9. Reserved slugs and IDs

- `epic-misc` and `EP-MISC-general` — reserved as the per-milestone fallback epic when stories haven't been organized into named epics. Health check tolerates this as a valid epic. Counter recovery handles it identically to any other epic except that it never increments the EP counter (it's a non-numeric fallback).
- `EP-999` — **deprecated, no longer reserved.** v3 used this as a "backlog holding epic"; v4 removes that concept entirely. The migration leaves any v3 `EP-999` references untouched in archived files but does not create new `EP-999` entries.

---

## 10. Cross-references

- Design doc: `docs/internal/v4-story-system-design-2026-05-10.md`
- Migration spec: `docs/internal/v4-migration-spec-2026-05-10.md`
- Story template: `docs/internal/v4-story-template.md`
- Sprint template: `docs/internal/v4-sprint-template.md`
- Caucus findings: `docs/internal/v4-caucus-findings-2026-05-12.md`

If a value in this schema conflicts with a value in the design doc or migration spec, this schema wins. Update the conflicting doc to match.
