# Changelog

All notable changes to SweetClaude are documented here.

---

## [Unreleased] — targeting 4.0.10-beta

### New features

**Bash-based hook repair recovery (EP-010, STORY-304)**
- `scripts/emergency-hook-restore.sh` — zero-dependency emergency hook restore script. Resolves install path via `installed_plugins.json` (with `find` fallback), restores from `hooks.bak/` (with `repo/hooks/` fallback), validates each backup with `bash -n` before accepting. Supports `--dry-run` and an optional `[hook-name.sh]` argument to restore a single hook. Uses Bash only — works when Write/Edit hooks are blocked.
- `tests/test-emergency-restore.sh` — behavioral test suite for the recovery script (eight tests passing, one documented SKIP).
- `sweetclaude:hook-repair` skill — invocable as `/sweetclaude:hook-repair`. Diagnoses broken installed hooks via `bash -n`, proposes restoration via AskUserQuestion, verifies after restore. Falls through to `bash scripts/emergency-hook-restore.sh` if the backup is missing or itself broken.
- `docs/user-guide/hook-development.md` — new user-guide page with Recovery, Emergency Recovery (Break Glass), and What to Read Next sections.

### Changed

- `README.md` — "Housekeeping" table heading renamed to "Maintenance & Troubleshooting"; new `hook-repair` row added.
- `docs/user-guide/skills-reference.md` — System table grew from 14 to 15 skills; total count bumped from 103 to 104.

---

## [4.0.9-beta] — 2026-05-19

### New features

**Roadmap cache (SQLite)**
- `scripts/cache.py` — SQLite-backed cache built from roadmap markdown frontmatter. Supports `--rebuild`, `--query releases`, `--query summary`, `--query backlog`.
- `sweetclaude:epics` skill — browse, filter, and link epics interactively.
- `sweetclaude:big-picture` now renders the full release → epic → story pipeline from the cache instead of milestones.
- `sweetclaude:go` routes P3 (find next story from active epic) via cache.
- 16 skills decoupled from `INDEX.md`; cache is the source of truth for aggregate queries.

**Self-hosting infrastructure (EP-010, STORY-300–303)**
- `scripts/sync-to-installed.sh` — canonical sync wrapper with phase gate (blocks on `implement`), backup (`hooks.bak/` before overwrite), test gate (`tests/test-hooks.sh` must pass), and atomic rollback on failure. Flags: `--dry-run`, `--force`.
- `sweetclaude:feature-setup` — replaces `sweetclaude:experimental-feature-setup`. Thin wrapper around `sync-to-installed.sh` + cache rebuild. Enforces same phase and test gates.
- `tests/test-hooks.sh` extended from 10 to 22 tests. New coverage: `test-guardian.sh` code paths (phase inactive, blocked, non-test file, non-implement tdd_phase, uppercase IMPLEMENT), `auto-test-runner.sh` code paths (phase inactive, source → triggers, test file → skip, non-Write/Edit → skip), and syntax validation (fail-closed check).

### Changed

- `sweetclaude:experimental-feature-setup` removed; use `sweetclaude:feature-setup` instead.
- `auto-test-runner.sh` TEST_PATTERNS array now matches `test-guardian.sh` exactly, including a separate `*.feature` suffix check (was using substring match, which incorrectly matched `.feature-flags/` directories).

### Deferred to 4.0.10

STORY-305 (session-start symlink detection), STORY-306 (hook development workflow documentation). STORY-304 (Bash-based hook repair recovery) was completed post-release — see [Unreleased] above.

---

## [4.0.0] — 2026-05-10

### Breaking

Story storage moved from `.sweetclaude/product/backlog/BL-NNN.md` to `docs/product/backlog/<type>s/<TYPE>-NNN-<slug>.md`. ID scheme is now per-type (`STORY-NNN`, `BUG-NNN`, `DEBT-NNN`, `CHORE-NNN`). The legacy `BL-NNN` scheme is retired. v4 cannot run against v3 storage — the bootstrap hard stop blocks every v4 skill in a v3 project until migration completes.

### Migration

`/sweetclaude:migrate` runs once per project; a safety backup is created automatically. See [docs/user-guide/v4-migration.md](docs/user-guide/v4-migration.md) for the full migration walkthrough.

### New features

- Per-type subdirectories (`stories/`, `bugs/`, `debt/`, `chores/`) with `done/` archive subdirectory.
- `MIGRATION-MAP.md` for v3↔v4 ID lookups at `docs/product/backlog/MIGRATION-MAP.md`.
- `_health` lint rules for v4 storage invariants: counter drift detection, done/status placement invariant, v3 file detection.
- `fix-sweetclaude` auto-repair recipes for lint findings.

### Removed

The EP-999 backlog-holding-epic concept is replaced by the `docs/product/backlog/INDEX.md` source of truth for counters and the visible table of unscheduled work.
