---
counters:
  story: 23
  bug: 6
  debt: 2
  chore: 11
updated: 2026-05-15
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
| [STORY-011](stories/STORY-011-roadmap-system-docs-product-roadmap.md) | Roadmap system — docs/product/roadmap/ structure and routing in go/big-picture/code-issue | new | soon | xl | roadmap, epics, sprints, big-picture, go, v4-phase2 |
| [STORY-012](stories/STORY-012-sweetclaude-milestones-skill.md) | sweetclaude:milestones skill — add/review/link/status/complete operations | new | soon | l | skill, milestones, roadmap, always-loaded, v4-phase2 |
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

## Bugs
| ID | Title | Status | Priority | Effort | Tags |
|---|---|---|---|---|---|

## Debt
| ID | Title | Status | Priority | Effort | Tags |
|---|---|---|---|---|---|
| [DEBT-001](debt/DEBT-001-verification-before-success-pattern-enforcement.md) | Architectural rule — every "✓ done" report must follow an explicit verification step | new | later | s | architecture, pattern, success-reporting, verification, framework-discipline |

## Chores
| ID | Title | Status | Priority | Effort | Tags |
|---|---|---|---|---|---|
| [CHORE-004](chores/CHORE-004-tighten-find-plugin-root-match.md) | Tighten find_plugin_root() plugin_key match to startswith("sweetclaude@") | new | later | s | hooks, maintenance, defensive |
| [CHORE-005](chores/CHORE-005-sort-plugin-cache-find-by-mtime.md) | Sort plugin-cache find results by mtime in fix-sweetclaude Step 7a | new | later | s | fix-sweetclaude, hooks, defensive |
| [CHORE-006](chores/CHORE-006-fsync-atomic-write.md) | Add fsync to ensure-global-hooks.py atomic write for crash safety | new | later | s | hooks, maintenance, durability |
| [CHORE-007](chores/CHORE-007-defer-case-wording-in-update-step-6c.md) | Distinguish Defer-case wording in update Step 6c from clean-state success | new | later | s | update, _migrate, ux, wording, defer |
| [CHORE-011](chores/CHORE-011-cutover-gate-enforcement-in-migration-runner.md) | CUTOVER gate enforcement in migration runner | new | later | s | migration, cutover, gate, enforcement |
