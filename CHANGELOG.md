# Changelog

All notable changes to SweetClaude are documented here. SweetClaude has separate stable 3.x and 4.x beta channels, so this changelog calls out channel-specific changes explicitly.

---

## [Unreleased]

### Changed

- Added stable 3.x and 4.x beta user-guide tracks so beta users can follow channel-safe install, update, recovery, and migration guidance.
- Moved beta rescue guidance into the 4.x beta track while keeping a compatibility link at `docs/user-guide/beta-rescue.md`.
- Updated the 4.x migration guide to route through `/sweetclaude:doctor`, `/sweetclaude:recover`, and guarded `/sweetclaude:migrate` instead of blanket migrate-first advice.

---

## Stable 3.x Channel — current: 3.68.6

The stable branch did not previously carry its own `CHANGELOG.md`, so this
section summarizes the current stable-channel state from the `stable-3.x` branch.
Stable 3.x is the recommended channel for normal active project work.

### Changed

- Added explicit stable-channel install and update guidance: install from
  `carson-sweet/sweetclaude@stable-3.x`, update the Claude Code plugin package
  with `/plugin update sweetclaude@sweetclaude-stable`, restart Claude Code, then
  run `/sweetclaude:update` inside each project when framework files need
  syncing.
- Added a stable 3.x user-guide entry point and clarified that
  `/sweetclaude:update` does not move stable installs onto 4.x beta.
- Standardized docs and cheatsheets on `/sweetclaude:go` as the normal project
  entry point after stable install.

### Fixed

- Hardened stable install/update discovery so stable installs preserve the
  stable/beta channel boundary and do not prompt users into prerelease beta
  updates by default.
- Added deterministic plugin-state inspection for stable installs, including
  update-source detection, recorded plugin metadata, and preflight reporting.
- Aligned stable hook-maintenance and upgrade-path checks around
  `/sweetclaude:fix-sweetclaude`, Bash-blocking behavior, and plugin-native hook
  handling.

### Stable vs Beta

- Stable 3.x uses `/sweetclaude:fix-sweetclaude` for project repair.
- 4.x beta uses the newer `/sweetclaude:doctor`, `/sweetclaude:recover`, and
  guarded `/sweetclaude:migrate` maintenance front doors.
- Channel switching is explicit: install `sweetclaude@sweetclaude-beta` from
  `beta-4.x` if you intentionally want beta behavior.

## [4.1.12-beta] — 2026-05-25

### Fixed

- Added a stale beta plugin guard to bootstrap, update, and doctor so users on beta installs older than `4.1.9-beta` see the exact `/plugin update ...` command before any project maintenance runs.
- Extended plugin-state/preflight metadata with stale-beta detection, minimum safe beta version, exact plugin update command, and restart-required fields.
- Added regression coverage for stale legacy beta installs, preflight command emission, and front-door stale-beta stops in update/bootstrap/doctor.

---

## [4.1.11-beta] — 2026-05-25

### Changed

- Made `/sweetclaude:recover` the documented recovery entrypoint. Recovery now diagnoses first by default, then plans, snapshots, asks for approval, executes, verifies, and reports rollback instructions.
- Kept explicit recovery script subcommands for automation, but removed `recover diagnose` from user-facing beta rescue instructions.
- Made `scripts/recovery/recover_project.py` default to read-only diagnosis when run without a subcommand.

---

## [4.1.10-beta] — 2026-05-25

### Documentation

- Added a public 4.x beta rescue guide for users with stale beta installs or projects stuck after update, doctor, migrate, or repair failures.
- Clarified that existing beta users should run Claude Code's plugin update first, restart Claude Code, then run `/sweetclaude:update` from the repaired beta install.
- Updated install and skills-reference docs to distinguish stable updates, beta updates, legacy beta plugin keys, and project-state recovery.

---

## [4.1.9-beta] — 2026-05-25

### Fixed

- Hardened `/sweetclaude:update` for existing beta users with stale or legacy plugin metadata. Update now detects the installed SweetClaude channel, preserves the stable/beta branch boundary, ignores wrong-branch local repo sources, and repairs the recorded plugin version, commit SHA, and install path after sync.
- Added deterministic plugin install-state inspection and repair coverage for legacy `sweetclaude` beta installs.

---

## [4.1.8-beta] — 2026-05-25

### Fixed

- Hardened the release readiness gate so beta/stable release checks inspect the
  actual git checkout branch, upstream, tracked cleanliness, and tag-at-HEAD
  instead of trusting a supplied `--branch` argument alone.

---

## [4.1.7-beta] — 2026-05-25

### Fixed

- Added evidence receipts for high-stakes completion, ship, release, and
  external-close claims.
- Made manual `status.py set-terminal --status done` fail closed unless a
  matching completion evidence receipt is provided.
- Hardened dashboard and orchestrator done transitions so active work is not
  silently cleared without completion evidence.
- Updated public closeout skills to validate and pass evidence receipts before
  marking work done.
- Added a release readiness gate that enforces beta/stable channel separation,
  matching package/plugin/changelog metadata, and release evidence receipts
  before tag preparation.

---

## [4.1.6-beta] — 2026-05-25

### Fixed

- Reduced `/sweetclaude:doctor` noise for accepted compatibility-mode legacy
  taxonomy projects. Doctor now collapses accepted legacy taxonomy findings
  into one info item while preserving real residual findings such as duplicate
  IDs, missing frontmatter, unknown statuses, missing milestone fields, stale
  derived statuses, and auto-fixable date fields.
- Made Doctor's stored run state compact and count-based. `last-doctor-run.json`
  now records severity counts, total finding count, and a bounded finding
  summary instead of unbounded full scan output.
- Hardened Doctor's pre-fix menu preference lookup so it reads only compact
  preference fields, does not print stale large Doctor run files, and does not
  skip the menu from a one-time prior `menu_preference`.

---

## [4.1.5-beta] — 2026-05-25

### Fixed

- Added a compact Doctor maintenance-route preflight so `/sweetclaude:doctor`
  presents recovery, supported migration, compatibility, or manual-review
  guidance before large full-scan reports can bury the maintenance decision.
- Improved Doctor's user-facing maintenance router so recoverable projects
  present `Run safe recovery`, supported flat migration candidates present
  `Start supported migration`, and accepted legacy taxonomy layouts clearly
  continue in compatibility mode with no migration recommendation.
- Added regression coverage for the route-only Doctor command and installed
  plugin smoke coverage on disposable llm-session-harness and SynCog copies.

---

## [4.1.4-beta] — 2026-05-25

### Fixed

- Made `/sweetclaude:migrate` fail closed on unsupported typed backlog layouts
  before creating locks, backups, converted files, or `MIGRATION-MAP.md`.
- Added a deterministic migration preflight command that blocks accepted
  compatibility-mode projects, typed legacy backlog folders, duplicate old
  work-item IDs, malformed SweetClaude state, and layouts with no flat
  `BL-NNN` files for the v3-to-v4 backlog migrator.
- Hardened `/sweetclaude:doctor` so taxonomy migration remains blocked in beta
  unless a future capability check proves the detected project layout is
  supported. Doctor no longer directly invokes `migrate_taxonomy.py` from the
  migration menu or prompted-fix delegation path.
- Decoupled `/sweetclaude:update` framework sync from project mutation. Update
  now treats project drift and taxonomy/orphan checks as read-only diagnostics
  and does not invoke `_migrate`, purge/adopt, feature setup, capability
  bootstrap, plan-directory writes, or doctor prompt marker writes inline.
- Added installed-plugin smoke coverage on disposable llm-session-harness and
  SynCog copies, proving recovery/compatibility routing, zero product artifact
  mutation during recovery, read-only update drift checks, and stable/beta
  prerelease isolation.

---

## [4.1.3-beta] — 2026-05-25

### New features

- Added `/sweetclaude:recover`, a manifest-backed recovery path for projects
  left in bad update, migration, doctor, or repair states. It diagnoses and
  plans read-only, snapshots before mutation, requires approval to execute,
  verifies doctor/update/migrate/fix safety, supports resume and rollback, and
  writes a recovery report.

### Fixed

- Recovered SynCog-class beta failure states by stabilizing unsupported typed
  backlog layouts without running taxonomy migration. The recovery route marks
  migration as deferred, records the accepted legacy layout, leaves product
  artifacts unchanged, and is idempotent after recovery.
- Hardened user-facing migration guards so status, go, bootstrap, doctor,
  backlog, issue, triage, and GitHub issue flows route unsafe legacy layouts to
  `/sweetclaude:recover` instead of telling users to run blind migration.
- Recovery guards now ignore normal time-based doctor checkup markers and only
  treat migration-related doctor prompts as recovery failures, preventing
  recovered projects from being routed back into recovery by routine checkups.
- New setup runs add `.sweetclaude/state/recovery-runs/` to `.gitignore` so
  recovery snapshots, manifests, and reports are not committed accidentally.

---

## [4.1.2-beta] — 2026-05-24

### Fixed

- Disabled unsafe update-time taxonomy/orphan migration prompts. `sweetclaude:update` now reports legacy taxonomy and orphan findings without moving, copying, deleting, or normalizing project files.
- `sweetclaude:doctor` no longer recommends taxonomy migration unless `migrate_taxonomy.py` is actually executable as a CLI entry point.
- Corrected doctor routing guidance so taxonomy migration no longer delegates to the v3-to-v4 backlog migration skill.
- Stable 3.x installs no longer get automatic prerelease prompts for 4.x beta tags; beta users still get prompted for newer beta/RC tags.

---

## [4.1.1-beta] — 2026-05-24

### New features

**Doctor diagnostic skill (EP-001, ISSUE-177–181)**
- `sweetclaude:doctor` — unified diagnostic scan and repair skill across 8 categories: state integrity, hooks, storage, migration, config, files, onboarding, environment. 257 tests.
- `validate_frontmatter()` used for all schema checks — consistent validation across all doctor categories.
- Category filter support — run specific diagnostic categories instead of full scan.
- Health delegation — `_health` delegates to doctor for consistency checks.
- `fix-sweetclaude`, `migrate-diagnose`, and `claude-config-audit` replaced with thin wrappers that redirect to `doctor`.

**Dashboard (ISSUE-188–190)**
- `sweetclaude:dashboard` — local web dashboard showing roadmap, releases, epics, backlog, dependencies, git history, and skill activity.
- Detail panel UX with sidebar navigation.
- Drag-and-drop reorder and cross-priority moves for backlog issues.
- Write-back API — changes in the dashboard persist to issue files.
- Source flag, datetime fields, and story drag-and-drop support.

**Status system overhaul (EP-002a/b, ISSUE-182–186)**
- EP-002a: status integrity — canonical validation, derived status computation, consistency checks.
- EP-002b: status visibility — derived status, view scopes, dashboard integration.
- Milestone auto-close and auto-reopen with `source:auto` tracking.
- Consolidated status views — single `/sweetclaude:status` command with dynamic view selection.

**DateTime normalization (ISSUE-192)**
- All timestamps normalized to full ISO 8601 with timezone across all state files and skill output.

### Fixed

- All script paths resolved to `~/.claude/scripts/sweetclaude/` for consistent cross-platform operation.
- Auto-close bug fixes — false closure of items prevented.
- Migration output now uses `ISSUE-NNN` format with flat backlog structure; orphan scan added.

---

## [4.1.0-beta] — 2026-05-22

### New features

**Bash-based hook repair recovery (EP-010, STORY-304)**
- `scripts/emergency-hook-restore.sh` — zero-dependency emergency hook restore script. Resolves install path via `installed_plugins.json` (with `find` fallback), restores from `hooks.bak/` (with `repo/hooks/` fallback), validates each backup with `bash -n` before accepting. Supports `--dry-run` and an optional `[hook-name.sh]` argument to restore a single hook. Uses Bash only — works when Write/Edit hooks are blocked.
- `tests/test-emergency-restore.sh` — behavioral test suite for the recovery script (eight tests passing, one documented SKIP).
- `sweetclaude:hook-repair` skill — invocable as `/sweetclaude:hook-repair`. Diagnoses broken installed hooks via `bash -n`, proposes restoration via AskUserQuestion, verifies after restore. Falls through to `bash scripts/emergency-hook-restore.sh` if the backup is missing or itself broken.
- `docs/user-guide/hook-development.md` — new user-guide page with Recovery, Emergency Recovery (Break Glass), and What to Read Next sections.

### Changed

**Artifact taxonomy rationalization (EP-001)**
- All work item prefixes unified to `ISSUE-NNN`. The per-type prefixes (`STORY-NNN`, `BUG-NNN`, `DEBT-NNN`, `CHORE-NNN`) and the legacy `BL-NNN` scheme are retired. Item type is now a frontmatter field, not an ID prefix.
- Flat `backlog/` directory replaces typed subdirectories (`stories/`, `bugs/`, `debt/`, `chores/`).
- Two-directory lifecycle: `backlog/` (untriaged) and `roadmap/issues/` (committed to an epic). Three moves: triage, complete, discard.
- 11 statuses: new, ready, active, in-review, blocked, on-hold, deferred, done, declined, abandoned, superseded.
- `sweetclaude:update` detects old-format files and offers migration. `/sweetclaude:migrate` handles the conversion with backup, preview, and verify steps.
- If you are already on v4 with `ISSUE-NNN` files, this change is transparent — no action needed.

**Version bumping is now explicit (ISSUE-069)**
- Removed `auto-version-bump` hook. Version bumps are now manual via `scripts/bump-version.sh`.
- Updated CONTRIBUTING.md and GOVERNANCE.md to reflect the explicit bump workflow.

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

### Deferred to 4.1.0

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
