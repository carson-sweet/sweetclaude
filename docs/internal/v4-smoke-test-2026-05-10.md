# v4 Migration Smoke Test Plan

**Date:** 2026-05-12 (revised from 2026-05-10)
**Fixture base:** `tests/fixtures/migrate-smoke/`
**Goal:** Convert "manual verification" gates into automated tests so the release gates are auditable.

## Test scenarios

Each row is a test scenario that must be exercised before v4.0.0 ships. PASS/FAIL is determined by automated assertion. Manual verification is acceptable only for items marked `MANUAL`.

### Core migration

| # | Scenario | Implementation status | Expected result |
|---|---|---|---|
| 1 | Happy path: 5-story v3 fixture migrates cleanly | Existing fixture | All 5 files at expected v4 paths; INDEX.md counters correct; MIGRATION-MAP.md complete |
| 2 | INDEX.md counters match active file counts per type | Existing | story=2, bug=1, chore=1, debt=1 |
| 3 | MIGRATION-MAP.md exists at `docs/product/MIGRATION-MAP.md` (NOT in backlog/) | Per revised spec | File at root path; contains all 5 mappings |
| 4 | Status remap: `backlog → new`, `in_progress → active`, `in_review → active`, `cancelled → abandoned`, `done → done` | New | Fixture with one of each; each maps correctly |
| 5 | Type remap: `spike → story` | New | Fixture with a v3 spike; written as v4 story |
| 6 | Source → origin: `manual`, `inferred`, `generated → inferred`, `imported` | New | Each v3 value maps to correct v4 value |

### Preflight (Step 0)

| # | Scenario | Expected result |
|---|---|---|
| 7 | `.gitignore` excludes `/docs/*` with allowlist (sweetclaude pattern) | Step 0 hard-stops with the tailored fix message |
| 8 | `.gitignore` doesn't restrict `docs/product/` | Step 0 passes; migration proceeds |
| 9 | `.gitignore` doesn't exist | Step 0 passes; migration proceeds |

### Backup and integrity (Step 1)

| # | Scenario | Expected result |
|---|---|---|
| 10 | Both in-tree and off-tree backups created | Files exist at `~/.sweetclaude/backups/{project}/` AND `.sweetclaude/state/backups/` |
| 11 | Backup integrity (sample extraction) — corrupt the temp backup before copy | Migration aborts with "Backup integrity check failed" |
| 12 | Concurrent lock contention via `mkdir` — second migration attempts while first holds the lock | Second attempt sees existing lock dir, surfaces owner info |
| 13 | Backup retention prunes after verification, not before | Five backups exist + verified new one; oldest pruned only after new one validated |

### Pre-migration validation (Step 2)

| # | Scenario | Expected result |
|---|---|---|
| 14 | BOM-prefixed v3 file | Parses correctly after BOM strip |
| 15 | CRLF-ended v3 file | Parses correctly after normalization |
| 16 | No-frontmatter-delimiter v3 file | Reported as "no frontmatter delimiter" (not a generic parse error) |
| 17 | Filename↔frontmatter ID mismatch | Reported as validation failure |
| 18 | Duplicate IDs across two files | Each duplicate pair reported |
| 19 | Unknown v3 status value | Validation fails with specific value |
| 20 | Manifest accurately counts active vs done | Counts match the underlying fixture |

### Done items (Step 3)

| # | Scenario | Expected result |
|---|---|---|
| 21 | User skips done items | Done items remain in v3 location; MIGRATION-MAP.md "Skipped" section records each |
| 22 | User migrates done items | Done items written to `<type>s/done/` with `closed_date` set |

### Verification (Step 7)

| # | Scenario | Expected result |
|---|---|---|
| 23 | Per-file verification catches a planted post-write corruption | Migration fails; specific file reported; auto-restore fires |
| 24 | Content sampling (≥10 files or 10%): planted body truncation in a sampled file | Escalates to full audit; auto-restore fires |
| 25 | Input/output reconciliation: deliberately drop one source file during Step 5 | Reconciliation catches the shortfall; auto-restore fires |

### Finalize (Step 8)

| # | Scenario | Expected result |
|---|---|---|
| 26 | Atomic finalize: `artifact-privacy.yaml.tmp` write fails | Both tmp files cleaned up; auto-restore fires |
| 27 | Atomic finalize: `sweetclaude.yaml` rename fails between two YAML writes | Migration retry detects the mismatch and re-runs Steps 5–8 idempotently |
| 28 | Delete-offer skipped (user keeps v3 files) | `framework.v4.migration_complete: true` set; bootstrap does not re-prompt on next session |
| 29 | Delete-offer accepted; offtree backup re-verified before deletion | Sample-extract passes before delete; delete proceeds |

### Auto-restore (Failure Handling)

| # | Scenario | Expected result |
|---|---|---|
| 30 | Auto-restore deletes orphan `docs/product/` if it did not pre-exist | `docs/product/` absent after restore |
| 31 | Auto-restore preserves pre-existing `docs/product/` content | Original pre-migration content restored |
| 32 | Option 2 ("Reset framework state") requires project-name confirmation | Refuses without exact match |
| 33 | Option 2 preserves decision-log.md, improvement-register.md, backups/ | Files exist after Option 2 |
| 34 | Option 2 removes sweetclaude.yaml, skills.yaml, session-state.yaml, artifact-privacy.yaml, .sweetclaude/product/ | Files absent after Option 2 |

### Counter recovery

| # | Scenario | Expected result |
|---|---|---|
| 35 | INDEX.md missing — recovery scans backlog and reconstructs counters | Counters match max(N) across scanned files |
| 36 | INDEX.md frontmatter malformed YAML — recovery treats as missing | Same as 35 |
| 37 | Same `TYPE-NNN` stem in backlog and roadmap — recovery halts | Fatal error, recovery does not silently resolve via max() |
| 38 | Roadmap has promoted stories with higher IDs than backlog — counter reflects max | Counter correct |

### Bootstrap hard-stop

| # | Scenario | Expected result |
|---|---|---|
| 39 | v4 framework + `framework.v4.migration_complete: false` + v3 backlog files exist | Hard-stop fires |
| 40 | v4 framework + `framework.v4.migration_complete: true` + v3 backlog files exist (user declined cleanup) | No hard-stop; session proceeds normally |
| 41 | v4 framework + no `.sweetclaude/product/` of any kind | No hard-stop; session proceeds normally |

### v3-ID lookup

| # | Scenario | Expected result |
|---|---|---|
| 42 | `project-issues view BL-001` after migration with BL-001 → STORY-001 | Auto-resolves, shows STORY-001 with note about the migration |
| 43 | `project-issues view BL-999` where BL-999 doesn't exist in MIGRATION-MAP.md | Clear "not found" message referencing MIGRATION-MAP.md |

---

## Fixtures required

`tests/fixtures/migrate-smoke/` — base 5-story fixture (already exists, may need to be created if missing)

`tests/fixtures/migrate-edge-bom/` — single file with `\xEF\xBB\xBF` BOM prefix
`tests/fixtures/migrate-edge-crlf/` — single file with CRLF line endings
`tests/fixtures/migrate-edge-no-delim/` — file lacking `---` frontmatter delimiter
`tests/fixtures/migrate-edge-id-mismatch/` — file with `BL-042` in filename, `id: BL-005` in frontmatter
`tests/fixtures/migrate-edge-dup-ids/` — two files with same `id: BL-001`
`tests/fixtures/migrate-stress-100/` — 100-story fixture (covers retention, pagination, time)
`tests/fixtures/migrate-gitignore-deny/` — project with `/docs/*` denylist gitignore
`tests/fixtures/migrate-corrupt-planted/` — script that runs migration, then corrupts one written file, then re-invokes verification
`tests/fixtures/migrate-drop-planted/` — script that runs migration but deliberately skips one Step-5 write

---

## Open items

- STORY-040 known ambiguity (carry-over from previous smoke test): the "no hits in non-historical files" grep for version `3.52.12` will match CHANGELOG entries. Resolution deferred to v4 implementation phase.
- Test fixture for sprint migration: not yet specified — v3 sprint artifacts exist but v4 sprint schema is new, so the migration mapping needs to be designed in Phase 2 work.
