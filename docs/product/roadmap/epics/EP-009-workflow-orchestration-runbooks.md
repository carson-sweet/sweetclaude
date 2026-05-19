---
id: EP-009
type: epic
title: Workflow Orchestration Runbooks
status: proposed
release: REL-003
milestones: [MS-007, MS-008, MS-009, MS-010, MS-011, MS-012, MS-013, MS-014, MS-015]
source: BL-082
depends_on: [EP-010]
created: 2026-05-18
updated: 2026-05-19
---

# EP-009: Workflow Orchestration Runbooks

**Release:** v4.1 (Execution Workflows)
**Source:** BL-082 — Structured, state-tracked development workflows per work type
**Milestones:** MS-007 through MS-015 (MS-006 discovery already done)

## Summary

Build structured, state-tracked workflow runbooks for every development effort type. Each workflow is a defined sequence of prompts with enforced completion, artifact persistence, crash recovery, and quality gates. The user is the decision-maker and reviewer — SweetClaude is the orchestrator.

## Problem

SweetClaude has strong individual skills (caucus, TDD, code review, spec drafting) but no enforced structure governing the sequence in which they're invoked. Steps get skipped, artifacts get lost in conversation context instead of persisted to disk, and session crashes leave no recovery state. Quality is seriously impacted: stray branches, uncommitted files, incomplete work, missing tests, skipped code reviews.

## Workflow Types

1. **Epic** — multi-story efforts with nested planning/execution/finalization loops
2. **Large Story** — full spec, architect caucus, TDD Level 3, adversarial completion
3. **Bug Fix / Security Patch / Performance** — symptom-first diagnostic track
4. **Chore** — dependency updates, config changes, small refactors
5. **Minor Enhancement** — small feature additions with clear acceptance criteria
6. **Documentation** — content creation and updates

## Key Capabilities

- **Session state persistence and crash recovery** — state file updated after every prompt completion
- **Artifact persistence enforcement** — workflow does not advance if output artifact is not on disk
- **Prompt runbook execution** — self-contained prompts with orchestrator tracking position
- **Phase exit gates with user approval** — orchestrator waits at defined boundaries
- **Caucus integration at defined points** — correct caucus type with correct documents
- **Decision point routing** — specific return-to-phase when quality gates fail
- **Escalation between workflow tracks** — small effort promotes to large without losing work

## Milestone Mapping

| Milestone | Scope |
|---|---|
| MS-006 | Discovery complete (done) |
| MS-007 | Workflow taxonomy finalized |
| MS-008 | State model designed |
| MS-009 | Design consensus reached |
| MS-010 | Technical spec approved |
| MS-011 | Workflow state infrastructure implemented |
| MS-012 | All 12 execution workflow types implemented |
| MS-013 | Code and security review complete |
| MS-014 | Behavioral regression suite passing |
| MS-015 | Docs and changelog updated — release ready |

## Design Considerations

- Skill, mode, or orchestration layer?
- Interaction with existing workflow shapes (full-pipeline, abbreviated, diagnostic, etc.)
- Reconciliation with existing phase gates in effective-gates.yaml
- Automation level tied to deference level
- Hook-based enforcement (judiciously)
- Second LLM provider for independent gate judging
- John Wick integration / replacement

## Full Feature Request

See BL-082 for the complete feature request document including all prompt runbook appendices (Epic, Large Story, Small Effort tracks A-D).
