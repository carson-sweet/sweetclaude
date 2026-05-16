# v4 Story System Design
**Version:** 2.0
**Date:** 2026-05-12
**Status:** Implementation ready — caucus 3 findings resolved; A1/A3/A4/B1/B3/B4/D3 fixed 2026-05-13
**Canonical schema reference:** [`v4-story-schema.md`](v4-story-schema.md) — values, enums, and state machine live there
**Recovered from:** Session 41d83490 (00:20–14:10 UTC) after session crash
**Revision history:**
- v2.0 (2026-05-12) — incorporated caucus 3 findings: schema extracted to standalone reference; EP-999 fallback renamed to `EP-MISC-general`; sprint schema specified by reference; concurrency contract added; separation rule strengthened with write-time enforcement; roadmap `done/` structure standardized; `.gitignore` offer reframed; documentation plan added.
- v1.2 (2026-05-10) — fixed Health Check gating, Moving Stories auto-stage scope, counter recovery to scan roadmap directories
- v1.1 (2026-05-10) — added updated/closed_date fields, slug immutability, null canonicalization, sprint format, roadmap INDEX format, qualified epic paths, counter recovery, tag vocabulary, body section enforcement, mode behaviors
- v1.0 (2026-05-10) — two prior caucus rounds (C1–C38)

---

## Summary

v4 replaces the sc-artifact JSON-backed issue system with first-class markdown files organized in per-type subdirectories under `docs/product/`. The backlog and roadmap are completely separate structures with no shared IDs. Every story is its own file. The hierarchy is Milestone → Epic → Story (Sprint is optional, Agile only).

---

## What Changes from v3

| | v3 | v4 |
|---|---|---|
| Storage location | `.sweetclaude/product/backlog/` | `docs/product/backlog/` |
| Story names | "issues" (I-NNN) | "stories" (STORY-NNN, BUG-NNN, etc.) |
| ID scheme | Single `I-NNN` sequence | Per-type counters |
| Story types | story / bug / chore / spike | story / bug / debt / chore |
| Backlog structure | Flat `BL-NNN-*.md` files | Per-type subdirectories |
| Done stories | `status: done` in place | Physically moved to `done/` subdirectory |
| Roadmap stories | Not file-per-story | File-per-story, mirrors backlog structure |
| EP-999 concept | Used as backlog holding epic | **Removed entirely** |
| Initial status | `backlog` | `new` |
| Source field | `source: manual/inferred` | `origin: manual/inferred/imported` |
| Sprint history | YAML array in frontmatter | Markdown table in body |
| Storage engine | sc-artifact (Python + JSON index) | Markdown-as-primary-store |

---

## EP-999 Is Removed

The concept of EP-999 as a "backlog holding epic" is **explicitly removed**. Backlog items do not belong on the roadmap and do not need an epic. The backlog is a completely separate document and structure.

> "We want to get rid of the concept of EP-999 as a backlog epic... backlog items do not belong on the roadmap at all, so do not need an epic. Backlog has to be a TRULY SEPARATE DOCUMENT AND STRUCTURE." — Session [13]

User-guide docs that reference the v3 `EP-999` concept must be updated. As of 2026-05-12, `docs/user-guide/planning-concepts.md` does not exist in the repo; any v4 documentation explaining epics/milestones must be written fresh (see Documentation Plan section below) rather than amended.

---

## Backlog and Roadmap Are Completely Separate

- No story ID ever appears in both the backlog and the roadmap — not even for historical purposes.
- When a story is promoted from backlog to roadmap, it **physically moves** (file moves, no copy).
- Backlog stories do not require epics.
- Stories can be worked directly from the backlog — especially bugs, chores, debt.

### Write-time enforcement contract

The "no ID in both locations" rule is not a convention enforced only by health check. Every skill that writes a story file must enforce it at write time:

1. **Story creation skills** check both `docs/product/backlog/<type>s/` and `docs/product/roadmap/milestones/*/epics/*/<type>s/` (including all `done/` subdirectories) for any existing file matching the proposed `<TYPE>-NNN-*.md` pattern. If found, the write is rejected and counter recovery is triggered.

2. **Story promotion skills** (backlog → roadmap) implement the move as: validate the destination doesn't exist → read source → write destination (temp + atomic rename) → update both INDEX.md files → delete source → commit. If any step fails after the destination is written, the move is rolled back (destination deleted, source restored) before surfacing the error.

3. **No skill ever writes a story file by `cp`-style duplication.** Copy is never the operation; only move.

The health check rule remains as a backstop for drift caused by bugs, but the contract is "skills don't violate it in the first place."

---

## Story Types

**story / bug / debt / chore**

- **story:** A user-facing feature or capability
- **bug:** Something broken that needs fixing
- **debt:** Any accumulated technical liability (broader than just refactoring)
- **chore:** Infrastructure, maintenance, housekeeping

"Spike" is dropped as a named type. Spikes are stories with a spike-style description (question to answer + deliverable). A separate `refactor` type may be added later but is not a v4 requirement.

---

## ID Scheme

Each type has its own counter starting at 001. IDs are uppercase:

| Type | Format | Example |
|---|---|---|
| story | STORY-NNN | STORY-007 |
| bug | BUG-NNN | BUG-003 |
| debt | DEBT-NNN | DEBT-001 |
| chore | CHORE-NNN | CHORE-004 |

IDs never change — not when a story moves from backlog to roadmap, not when it's archived.

Counter state is stored in `docs/product/backlog/INDEX.md` frontmatter.

---

## File Naming

`TYPE-NNN-slugged-title.md`

Slug: lowercase, spaces → hyphens, punctuation stripped, max ~50 chars.

**Slugs are immutable.** The slug is generated once from the title at creation time and never changes, regardless of subsequent title edits. The `title` field in frontmatter is the canonical display title. The filename is a stable identifier. This preserves git history references, PR mentions, and external links.

```
STORY-007-add-oauth-login.md
BUG-003-crash-on-empty-input.md
DEBT-001-remove-legacy-auth-middleware.md
CHORE-004-update-dependencies.md
```

---

## Directory Structure

### Backlog

```
docs/product/backlog/
  INDEX.md
  stories/
    STORY-001-slug.md
    STORY-002-slug.md
    done/
      STORY-OLD-slug.md
  bugs/
    BUG-001-slug.md
    done/
  debt/
    DEBT-001-slug.md
    done/
  chores/
    CHORE-001-slug.md
    done/
```

### Roadmap

The roadmap mirrors the backlog structure — same file format, same per-type subdirectories, **same per-type `done/` convention.** `done/` lives inside each type directory, never as a flat bucket at the epic level. This keeps backlog and roadmap structurally identical so a single counter-recovery glob and a single health-check rule work for both.

```
docs/product/roadmap/
  INDEX.md                          ← milestone navigation manifest + sprint + milestone counters
  milestones/
    MS-001-platform-foundation/
      INDEX.md                      ← epic navigation manifest for this milestone + epic counter
      sprints/
        SPRINT-NNN-slug.md          ← milestone-level sprints (alternative to epic-level)
        done/
          SPRINT-OLD-slug.md
      epics/
        EP-001-auth/
          INDEX.md                  ← story table for this epic (same format as backlog INDEX.md, no counter frontmatter)
          stories/
            STORY-NNN-slug.md
            done/
              STORY-OLD-slug.md
          bugs/
            BUG-NNN-slug.md
            done/
          debt/
            done/
          chores/
            done/
          sprints/                  ← epic-level sprints (alternative to milestone-level)
            SPRINT-NNN-slug.md
            done/
        EP-MISC-general/
          INDEX.md
          stories/
            done/
```

**Roadmap INDEX.md** — milestone navigation manifest:
```markdown
# Roadmap

| Milestone | Status | Stories | Done |
|---|---|---|---|
| [MS-001 Platform Foundation](milestones/MS-001-platform-foundation/INDEX.md) | active | 12 | 3 |
```

**Milestone INDEX.md** — epic navigation manifest:
```markdown
# MS-001 Platform Foundation

| Epic | Stories | Done |
|---|---|---|
| [EP-001 Auth](epics/EP-001-auth/INDEX.md) | 5 | 1 |
| [EP-MISC-general — General / Misc](epics/EP-MISC-general/INDEX.md) | 2 | 0 |
```

**Epic INDEX.md** — story table, same format as backlog INDEX.md (frontmatter counters are backlog-level; epic INDEX.md has no counter frontmatter — it is a view only):
```markdown
# EP-001 Auth

| ID | Type | Status | Priority | Effort | Title |
|---|---|---|---|---|---|
| STORY-007 | story | active | next | m | Add OAuth login |
```

Stories live only in epic-level tables. Roadmap and milestone tables are navigation manifests only — they aggregate counts but do not duplicate rows.

**Note on the fallback epic:** When a user hasn't yet organized stories into named epics, the per-milestone fallback epic is `EP-MISC-general` (non-numeric prefix, deliberately reserved). This is distinct from the v3 `EP-999` "backlog holding epic" concept, which v4 removes entirely. The non-numeric prefix prevents collision with the EP-NNN counter namespace and signals to users and skills that this is a special-purpose slot, not a regular epic.

---

## Roadmap Rules

- A roadmap story **must** be in an epic — not directly on a milestone.
- If a user tries to add a story directly to a milestone, SweetClaude offers to create an epic.
- If no logical epic name exists, recommend **"General / Misc"** as a placeholder.
- In **Agile mode**: a story must be in a sprint. A sprint can live in a milestone or an epic. Hard enforced.

---

## Moving Stories: Git Tree Must Be Clean

When promoting a story from backlog to roadmap (physical file move), SweetClaude:

1. Checks the git working tree is clean
2. If dirty: refuses to move. Offers to commit **only the story file being moved** (leaving all other staged and unstaged changes untouched), or asks the user what to do. Never auto-stages the entire working tree — that would entangle unrelated changes with a story move.
3. Moves the file from `docs/product/backlog/{type}s/` to the target epic directory
4. Updates both INDEX.md files
5. Commits the move as a single atomic commit

---

## Story File Schema

**Canonical reference:** [`v4-story-schema.md`](v4-story-schema.md). All frontmatter fields, allowed values, the status state machine, the type→directory→prefix mapping, slug rules, and body section conventions are defined there.

The design doc does not duplicate the schema. If a value in the design doc appears to disagree with the schema reference, the schema reference wins — file a bug against the design doc.

**Quick summary** (full detail in the schema reference):
- All frontmatter fields are required. `null` is the only valid empty-value sentinel.
- `status: done` or `status: abandoned` files live under `<type>s/done/`; skills moving the file and writing the status do both in one operation.
- `epic` field uses qualified path `MS-NNN-slug/EP-NNN-slug`. `milestone` is the bare milestone slug. Both `null` for backlog stories.
- Slugs are immutable; uniqueness is checked across both backlog and roadmap before write.
- Body sections vary by type (see [`v4-story-template.md`](v4-story-template.md)).

---

## Sprint File Schema

**Canonical reference:** [`v4-story-schema.md`](v4-story-schema.md) §5 and [`v4-sprint-template.md`](v4-sprint-template.md).

Sprints are first-class entities in Agile mode. Each sprint is its own markdown file. Sprint IDs use `SPRINT-NNN` (full word, matching v4's full-word prefix convention for STORY, BUG, DEBT, CHORE). This is a breaking change from v3's `SP-NNN`; the migration handles the rename.

Sprint files live under the roadmap, either at the milestone level (`milestones/MS-NNN-slug/sprints/`) or at the epic level (`milestones/MS-NNN-slug/epics/EP-NNN-slug/sprints/`). Exactly one of `milestone` or `epic` is non-null in the sprint frontmatter — the field that's set must match the sprint's actual location.

The sprint counter is project-wide (single sequence across all milestones and epics). It is stored in `docs/product/roadmap/INDEX.md` under `counters.sprint`.

Sprint History on stories is generated by the sprint skill. Adding a story to a sprint writes both: a row in the story's Sprint History body table, and an entry in the sprint file's Committed Stories / Added / Removed sections. Both writes happen atomically — either both succeed or both are rolled back.

In Agile mode, story implementation is hard-blocked unless the story's `sprint:` field resolves to an existing sprint file with `status: active` or `status: planned`.

---

## Concurrency

v4 introduces per-type counters, INDEX.md as a counter store, and physical file moves on promotion. Each of these has concurrency implications that skills must respect.

### Counter increments are locked

Any operation that reads the counter, increments it, and writes a new file (story creation, sprint creation, milestone creation, epic creation) must acquire a counter lock for the entire read-modify-write cycle. The recommended mechanism is `mkdir`-based locking on a sibling of the INDEX.md being updated:

```bash
LOCKDIR="<INDEX-parent>/.counter.lock"
if mkdir "$LOCKDIR" 2>/dev/null; then
  trap "rmdir '$LOCKDIR'" EXIT
  # read INDEX.md → increment counter → write new file → write INDEX.md
else
  # another writer holds the lock — retry with backoff, or fail loudly
fi
```

Locks must be acquired and released within a single skill invocation. Skills do not hold locks across user interaction or across multiple tool calls — if a counter is needed for a multi-step operation, the counter is locked, increment is computed, lock is released, then the multi-step work proceeds with the assigned ID.

### Slug uniqueness is verified before write

Slug generation (lowercase, dash-collapse, truncate-at-word-boundary at 50 chars) is deterministic. But two stories with similar titles can produce the same slug. Before writing `<TYPE>-NNN-<slug>.md`, the creating skill scans both backlog and roadmap directories for any existing file with the same slug (any ID prefix). On collision, append `-2`, `-3`, etc. to the slug until unique.

### INDEX.md writes are atomic

Every INDEX.md update follows the temp-file + atomic-rename pattern: write to `INDEX.md.tmp` in the same directory, then `mv INDEX.md.tmp INDEX.md`. The mv is atomic on POSIX filesystems within the same filesystem volume.

### File moves on promotion roll back on failure

Promotion (backlog → roadmap) is: validate destination doesn't exist → write destination via temp + rename → update backlog INDEX.md → update roadmap epic INDEX.md → delete source → commit. If any step after writing the destination fails, the destination is deleted and the source is restored. The git commit is the final step and is the irreversibility point. The promotion is rejected upfront if the working tree is dirty (see Moving Stories section).

### Multi-session safety on the same project

Two Claude Code sessions on the same project directory (e.g. via git worktrees) can collide. The counter lock prevents duplicate-ID assignment but does not prevent concurrent modification of the same INDEX.md table rows. Skills that mutate INDEX.md should always re-read it within the lock window rather than relying on cached state.

---

## INDEX.md

**Canonical reference:** [`v4-story-schema.md`](v4-story-schema.md) §6.

In summary: the backlog INDEX.md owns story-type counters (`story`, `bug`, `debt`, `chore`). The roadmap INDEX.md owns the `sprint` and `milestone` counters. Each milestone's INDEX.md owns its `epic` counter. Counter recovery scans backlog and roadmap (including each `done/` subdirectory at every nesting level); duplicate IDs across locations halt recovery with a fatal error. Skills updating INDEX.md follow the write-protocol (temp file → atomic rename) and acquire a counter lock for any read-modify-write cycle. Details in the schema reference.

The table layout of INDEX.md:

```markdown
---
counters:
  story: 7
  bug: 3
  debt: 2
  chore: 4
---

# Backlog

| ID | Type | Status | Priority | Effort | Title |
|---|---|---|---|---|---|
| STORY-007 | story | active | next | m | Add OAuth login |
| BUG-003 | bug | new | sooner | s | Crash on empty input |
| DEBT-001 | debt | ready | soon | l | Remove legacy auth middleware |
| CHORE-004 | chore | new | later | xs | Update dependencies |

## Done

N stories · N bugs · N debt · N chores in their respective `done/` subdirectories
```

Default sort: active first, then ready, new, blocked, deferred — then by priority within each group.

---

## Tag vocabulary

Tags are free-form strings with no enforced registry — new components and subsystems emerge organically. Skills do case-insensitive matching when filtering by tag. The health check normalizes tags to lowercase on read. If a project wants a canonical tag list, it can define one in `docs/product/tags.md`; `project-backlog-triage` will suggest from that file if it exists.

---

## Mode Behaviors

### Flow Mode

Stories thrown into backlog **automatically, no prompting**. Vibe coding stories are often instant-history — created with `status: done` and immediately moved to `done/` in one step. SweetClaude tracks what was done, not what is planned.

### Kanban Mode

Works from the backlog. Before pulling next story, checks if triage is needed:
- More than 3 stories with priority `next` or `sooner`
- No visible force-ranking (many stories same priority)

If triage needed, warns user: unmet dependencies from unranked work can require rework.

WIP limit: **hard-enforced 3 active stories maximum.**

### Agile Mode

Stories must be in a sprint. Implementation hard-blocked without an active sprint. Epics are first-class — surfaced in status views and big-picture. Sprints can live in a milestone or an epic.

### Shape Up Mode

Deferred for v4 — included in this initiative. User is studying Shape Up methodology. Will use the existing backlog/roadmap structures with pitches as an additional layer. No implementation until Shape Up design is confirmed.

---

## Health Check / Lint Rules

Run automatically during `big-picture` and `project-backlog-triage`:

- All roadmap stories are in epics (none loose on milestones) — **gated: skip if `docs/product/roadmap/` does not exist**
- No story ID appears in both backlog and roadmap directories — **gated: skip if `docs/product/roadmap/` does not exist**
- All active and future stories have been migrated (v3 format not present at `.sweetclaude/product/backlog/BL-NNN-*.md`)
- Counter state in INDEX.md matches actual file count per type
- No story file exists outside the expected type subdirectory
- Any file under `done/` must have `status: done` or `status: abandoned`; any file with those statuses must be under `done/`

---

## .gitignore Handling

v4 places product data under `docs/product/`. Many repositories have an existing `.gitignore` policy on `docs/` (denylist or allowlist). The migration must handle both directions: detecting when product data would be silently hidden, and offering the choice to hide it intentionally.

### Detection (always runs, before migration writes anything)

The migration runs `git check-ignore docs/product/INDEX.md` (or equivalent for the project's git state) before any file is written.

- **If `docs/product/` would be ignored** by the current `.gitignore`: the migration **hard-stops** with a tailored message that includes a suggested patch (e.g. `!/docs/product/` to add to the existing allowlist). The user must edit `.gitignore` and re-run migration. Proceeding would silently hide their stories — including `MIGRATION-MAP.md`, the only record of the old → new ID mapping.
- **If `docs/product/` is not ignored** by the current `.gitignore`: migration proceeds. After successful migration, the user is asked whether they want planning data committed (Yes → no `.gitignore` change) or kept local (Add `docs/product/` to `.gitignore`).

This offer applies to all repos, not just open-source. Closed-source repos with cloud SCM hosting also have data-exposure concerns — backlog items describing security work, competitive strategy, debt tied to architecture vulnerabilities, and personnel-sensitive planning are all committable by default.

### The offer wording

```
v4 has migrated your stories to docs/product/.

This data is committable by default. Do you want it in version control?

[Yes — commit it]  → no .gitignore change; users see planning history in git log
[No — keep it local] → add /docs/product/ to .gitignore; data stays on your machine only
```

Default: present both options; do not pre-select. The framing ("Do you want it in version control?") avoids the prior wording's implication that ignoring is only for open-source repos.

---

## Roadmap Document Generation Skill

A new skill is needed to generate a human-readable roadmap document from the structured roadmap files. `big-picture` already shows a project overview; the new skill produces a standalone roadmap document suitable for sharing. **Not a v4 Phase 1 blocker** — Phase 2 work.

---

## artifact-privacy.yaml Change

Migration updates `categories.product.base_path` from `.sweetclaude/product` to `docs/product`. Applied automatically as part of Step 8 finalize (see migration spec).

---

## Documentation Plan

Per the C2 caucus finding, v4 docs are written per-skill (each skill's rewrite commit includes the corresponding doc update). This section makes that concrete.

### Per-skill doc rule

Every skill that ships in v4 must update its row in `docs/user-guide/skills-reference.md` as part of its v4 rewrite commit. The skill's name, slash command, and description column must reflect v4 reality. PRs are reviewed for both the skill change and the corresponding doc update.

### Documents that need updates for v4

| Document | Update needed | Phase |
|---|---|---|
| `docs/user-guide/skills-reference.md` | Updated rows for every rewritten skill; remove `I-NNN` references | Per-skill (Phase 1+) |
| `docs/user-guide/getting-started.md` | Replace v3 paths and ID examples with v4 | Phase 1 (before v4.0.0 ship) |
| `docs/user-guide/quickstart.md` | Same | Phase 1 (before v4.0.0 ship) |
| `docs/user-guide/state-and-memory.md` | Update product-data location | Phase 1 (before v4.0.0 ship) |
| `docs/user-guide/how-it-works.md` | Update story system description | Phase 1 (before v4.0.0 ship) |
| `docs/user-guide/phases-and-workflows.md` | Update where backlog/roadmap interact with phases | Phase 1 (before v4.0.0 ship) |
| `docs/user-guide/tdd.md` | Update branch naming example (BL-NNN → STORY-NNN) | Phase 1 |

### Documents that need to be created

| Document | Purpose | Release-gate priority |
|---|---|---|
| `docs/user-guide/v4-migration-guide.md` | User-facing migration walkthrough | **Required before v4.0.0 GitHub Release** |
| `docs/user-guide/planning-concepts.md` | Explain backlog vs roadmap, epics, milestones, sprints in v4 terms | **Required before v4.0.0 GitHub Release** |
| `CHANGELOG.md` | Net-new file; first entry is v4.0.0 | **Required before v4.0.0 GitHub Release** |

### v3 docs

v3 user-guide docs are rewritten in place. Git history preserves the v3 version. No archived `v3/` subdirectory is created.

### Release-gate blockers

These docs are blocking gates on the v4.0.0 GitHub Release (in the migration spec's Release Gates section):
- `docs/user-guide/v4-migration-guide.md` exists and links from the bootstrap hard-stop message
- `docs/user-guide/planning-concepts.md` exists and is referenced from `getting-started.md`
- `CHANGELOG.md` exists with a v4.0.0 entry that links to the migration guide
- `docs/user-guide/skills-reference.md` is up to date for every skill that v4 changes
