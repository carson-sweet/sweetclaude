---
counters:
  story: 307
  bug: 10
  debt: 14
  chore: 13
updated: 2026-05-19
---

# Backlog INDEX

This file is the source of truth for backlog counter state and the visible table of unscheduled work.

## Stories
| ID | Title | Status | Priority | Effort | Tags |
|---|---|---|---|---|---|
| [STORY-001](stories/STORY-001-spike-caucus-as-live-reference-layer.md) | Spike — caucus as a live reference layer | new | soon | m | spike, caucus, knowledge, orchestration |
| [STORY-002](stories/STORY-002-status-consistency-and-roll-up-lint.md) | Status consistency — canonical vocabulary, roll-up lint, and propagation prompts | new | soon | l | health, big-picture, status, lint, hierarchy |
| [STORY-003](stories/STORY-003-plan-wave-sequencing-skill.md) | New skill: plan-wave-sequencing — design-first milestone resequencing | new | later | xl | skill, planning, milestones, dependency-graph, design-first |
| [STORY-004](stories/STORY-004-per-skill-model-requirements-declaration.md) | Per-skill model requirements declaration — reasoning level frontmatter for all skills | new | later | l | skills, model-routing, metadata, reasoning |
| [STORY-005](stories/STORY-005-spike-model-aware-skill-execution.md) | Spike: model-aware skill execution — automatic or assisted model switching per skill | new | later | m | spike, model-routing, cost, opus, sonnet |
| [STORY-006](stories/STORY-006-spike-token-efficiency-audit.md) | Spike: token efficiency audit — measure and reduce framework overhead per session | new | soon | m | spike, cost, tokens, prompt-cache, framework |
| [STORY-007](stories/STORY-007-structured-dependency-field.md) | Structured dependency field on backlog items, epics, and milestones | new | later | l | schema, dependencies, foundation, backlog, epics, milestones |
| [STORY-009](stories/STORY-009-aggregate-listings-from-structured-data.md) | Roadmap and aggregate listings consume sequence and dependency data | new | later | xl | rendering, aggregate-views, source-of-truth, big-picture, milestones, epics |
| [STORY-013](stories/STORY-013-mode-aware-behavior-enforcement.md) | Mode-aware behavior enforcement — Flow / Kanban / Shape Up / Agile rules in skills | new | soon | l | modes, flow, kanban, shape-up, agile, enforcement, v4-phase2 |
| [STORY-014](stories/STORY-014-native-skill-consolidation.md) | Native skill consolidation — replace wrapper-skills with v4-native implementations | new | later | xl | skills, native, wrapper, consolidation, v4-phase2 |
| [STORY-015](stories/STORY-015-planning-concepts-model-enforcement.md) | planning-concepts.md model enforcement — status state machine and hierarchy in skills | new | soon | m | planning-concepts, status, state-machine, enforcement, v4-phase2 |
| [STORY-016](stories/STORY-016-user-guide-for-v4-release.md) | User guide for v4.0.0 release — planning-concepts.md, skills-reference.md, migration guide | new | soon | m | docs, user-guide, planning-concepts, skills-reference, migration, v4-phase2 |
| [STORY-017](stories/STORY-017-document-changelog-tracking.md) | Document changelog — per-write metadata (datetime, skill, model, branch, summary) | new | soon | l | changelog, metadata, traceability, model-evaluation, auditing |
| [STORY-018](stories/STORY-018-story-status-by-phase.md) | Story phase-status table — per-phase status, blocking reason, and primary workfile | new | soon | m | stories, status, phases, traceability, developer-ux |
| [STORY-019](stories/STORY-019-adversarial-review-for-breaking-changes.md) | Adversarial review gate for breaking changes — breaking flag, mandatory code-reviewer pass | new | sooner | l | quality, tdd, code-review, caucus, breaking-changes, adversarial, safety |
| [STORY-020](stories/STORY-020-story-assessment-and-workflow-template-selection.md) | Upfront story assessment and workflow template selection — risk, complexity, breaking status, effort, blast radius | new | soon | xl | workflow, assessment, tdd, risk, breaking-changes, caucus, template-selection |
| [STORY-021](stories/STORY-021-spike-sqlite-state-storage.md) | Spike — SQLite as unified state store to replace drift-prone file/index system | new | soon | m | spike, sqlite, state, drift, architecture, indexes |
| [STORY-022](stories/STORY-022-spike-deterministic-logic-to-scripts.md) | Spike — move deterministic logic out of LLM skills and into scripts | new | soon | l | spike, architecture, scripts, skills, determinism, reliability |
| [STORY-024](stories/STORY-024-milestone-to-epic-migration-strategy.md) | Milestone-to-epic migration strategy for public launch | new | soon | l | roadmap, migration |
| [STORY-304](stories/STORY-304-hook-repair-recovery.md) | Bash-based hook repair recovery procedure | active | now | s | self-hosting, hooks, recovery |
| [STORY-305](stories/STORY-305-symlink-detection.md) | Session-start symlink detection | deferred | now | s | self-hosting, hooks, safety |
| [STORY-306](stories/STORY-306-hook-dev-workflow-docs.md) | Fixture-based hook development workflow documentation | deferred | now | s | self-hosting, hooks, documentation |
| [STORY-307](stories/STORY-307-spike-deference-enforcement.md) | Spike — enforce collaborative deference checkpoints via prompt engineering and/or subagent isolation | new | soon | m | spike, deference, prompt-engineering, subagents, safety, self-hosting |

## Bugs
| ID | Title | Status | Priority | Effort | Tags |
|---|---|---|---|---|---|
| [BUG-007](bugs/BUG-007-migrate-step-8-atomicity-gap.md) | Migrate Step 8 (finalize) is not atomic — crash mid-finalize can leave half-state | new | soon | m | migrate, atomicity, data-integrity, recovery |
| [BUG-008](bugs/BUG-008-missing-migration-guards-in-gh-skills.md) | project-gh-import-issues and project-gh-sync-issues missing v4 migration guards | new | soon | s | v4, skills, migration-guard, ep-008-5 |
| [BUG-009](bugs/BUG-009-epic-criteria-not-in-frontmatter.md) | Epic completion criteria only in body text — cache renders Criteria 0/0 | new | now | s | cache, big-picture, roadmap, epic |
| [BUG-010](bugs/BUG-010-cache-rebuild-overwrites-source-files.md) | Cache rebuild modifies source markdown files | new | now | — | — |

## Debt
| ID | Title | Status | Priority | Effort | Tags |
|---|---|---|---|---|---|
| [DEBT-001](debt/DEBT-001-verification-before-success-pattern-enforcement.md) | Architectural rule — every "✓ done" report must follow an explicit verification step | new | later | s | architecture, pattern, success-reporting, verification, framework-discipline |
| [DEBT-003](debt/DEBT-003-sync-exit-code-hygiene.md) | Sync script exit code hygiene | new | later | s | self-hosting, sync, code-quality |
| [DEBT-004](debt/DEBT-004-decision-log-append-robustness.md) | Decision-log append robustness | new | later | s | self-hosting, sync, code-quality |
| [DEBT-005](debt/DEBT-005-dry-run-output-completeness.md) | Dry-run output completeness | new | later | s | self-hosting, sync |
| [DEBT-006](debt/DEBT-006-version-extraction-python-spawn.md) | Replace Python spawn for version extraction | new | someday | s | self-hosting, sync, performance |
| [DEBT-007](debt/DEBT-007-version-dir-accumulation.md) | Version-dir accumulation without cleanup | new | soon | s | self-hosting, sync, disk-usage |
| [DEBT-008](debt/DEBT-008-sync-script-structural-cleanup.md) | Sync script structural cleanup | new | later | s | self-hosting, sync, code-quality |
| [DEBT-009](debt/DEBT-009-grep-fallback-ambiguity.md) | grep fallback for sweetclaude.yaml is ambiguous | new | later | s | self-hosting, sync, correctness |
| [DEBT-010](debt/DEBT-010-backup-validation-partial-copy.md) | Backup validation should compare source and destination file counts | new | later | xs | sync, backup, validation |
| [DEBT-011](debt/DEBT-011-version-dir-no-backup.md) | Version-dir hooks sync bypasses backup and rollback | new | later | s | sync, backup, version-dir |
| [DEBT-012](debt/DEBT-012-hooks-failed-accumulation.md) | hooks.failed/ artifact not cleaned on subsequent syncs | new | later | xs | sync, rollback, cleanup |
| [DEBT-013](debt/DEBT-013-empty-hooks-bootstrap.md) | First sync to fresh install fails on empty hooks/ validation | new | soon | xs | sync, backup, bootstrap |
| [DEBT-014](debt/DEBT-014-sync-error-messages.md) | Sync script error messages not actionable | new | later | xs | sync, ux, error-messages |

## Chores
| ID | Title | Status | Priority | Effort | Tags |
|---|---|---|---|---|---|
| [CHORE-004](chores/CHORE-004-tighten-find-plugin-root-match.md) | Tighten find_plugin_root() plugin_key match to startswith("sweetclaude@") | new | later | s | hooks, maintenance, defensive |
| [CHORE-005](chores/CHORE-005-sort-plugin-cache-find-by-mtime.md) | Sort plugin-cache find results by mtime in fix-sweetclaude Step 7a | new | later | s | fix-sweetclaude, hooks, defensive |
| [CHORE-006](chores/CHORE-006-fsync-atomic-write.md) | Add fsync to ensure-global-hooks.py atomic write for crash safety | new | later | s | hooks, maintenance, durability |
| [CHORE-007](chores/CHORE-007-defer-case-wording-in-update-step-6c.md) | Distinguish Defer-case wording in update Step 6c from clean-state success | new | later | s | update, _migrate, ux, wording, defer |
| [CHORE-011](chores/CHORE-011-cutover-gate-enforcement-in-migration-runner.md) | CUTOVER gate enforcement in migration runner | new | later | s | migration, cutover, gate, enforcement |
| [CHORE-012](chores/CHORE-012-force-flag-audit-logging.md) | --force decision-log on non-implement phases | new | later | s | self-hosting, sync, audit |
| [CHORE-013](chores/CHORE-013-wire-hooks-tests-into-sync-gate.md) | Wire tests/hooks/*.sh into the pre-sync test gate | new | later | s | self-hosting, sync, testing, gate |
