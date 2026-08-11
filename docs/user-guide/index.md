# SweetClaude 4.x User Guide

**Version:** 1.4
**Date:** 2026-08-11

SweetClaude 4.x is the stable channel, tracked on `main`. Plugin update,
framework sync, project recovery, and taxonomy migration are separate
safety-gated flows.

**The beta channel is retired.** If `/plugin list` shows
`sweetclaude@sweetclaude-beta`, see [Installing SweetClaude](install.md) for
the one-time switch to stable.

## Install And Update

```text
/plugin marketplace add carson-sweet/sweetclaude@main
/plugin install sweetclaude@sweetclaude-stable
```

After plugin install or update, restart Claude Code before running SweetClaude
commands. To update:

```text
/plugin update sweetclaude@sweetclaude-stable
/sweetclaude:update
```

If `/plugin list` shows the legacy key `sweetclaude@sweetclaude`, update
that exact key first.

## Maintenance Front Door

For project problems after update, start with:

```text
/sweetclaude:doctor
```

Doctor scans read-only, then routes to one of these outcomes (see
[Doctor](doctor.md) for the full scan, fix, and rollback model):

| Route status | Next step |
|---|---|
| `recovery-available` | `/sweetclaude:recover` |
| `supported-migration-available` | `/sweetclaude:migrate` |
| `compatibility-mode` | Continue without migration prompt. |
| `no-migration-recommended` | Continue normal work. |

Do not start by running `/sweetclaude:migrate` on an unknown old project layout.

## Where To Begin

If you are new, read [Getting Started](getting-started.md).

If you have a former beta install that is stuck, noisy, or reporting confusing
migration advice, read [Beta Rescue](beta-rescue.md).

If you need to understand project-state and taxonomy migration behavior, read
[Migration and Recovery](migration-and-recovery.md).

If you have it installed and want to understand the design decisions, read
[How It Works](how-it-works.md).

## What Is In This Guide

| Page | What it is |
|---|---|
| [Install](install.md) | Beta install, update, optional integrations, and suspension. |
| [Quick Start](quickstart.md) | First commands after SweetClaude is installed. |
| [Getting Started](getting-started.md) | Install through first feature. |
| [New Project Cheatsheet](cheatsheet-new-project.md) | Fast path for starting from an empty folder. |
| [Existing Project Cheatsheet](cheatsheet-existing-project.md) | Fast path for adopting an existing codebase. |
| [Migration and Recovery](migration-and-recovery.md) | Doctor-first maintenance, supported migration, recovery, and compatibility mode. |
| [Doctor](doctor.md) | The maintenance front door: read-only scan, safe and reversible fixes, rollback, and routing. |
| [Beta Rescue](beta-rescue.md) | Recovery path for stuck installs from the retired beta channel. |
| [4.x Migration Guide](v4-migration.md) | Short migration route summary and doctor outcomes. |
| [How It Works](how-it-works.md) | Mental model and architecture. |
| [Walkthroughs](walkthroughs.md) | Seven concrete scenarios end-to-end. |
| [Phases and Workflows](phases-and-workflows.md) | Reference for phases, work types, gates, and workflow shapes. |
| [Large-Story and Small-Story Workflows](large-story-workflow.md) | Controller-gated, evidence-based workflows for large and bounded work items. |
| [Planning Concepts](planning-concepts.md) | Backlogs, stories/issues, milestones, epics, sprints, and priorities. |
| [Skills Reference](skills-reference.md) | 4.x skill surface, including doctor, recover, migrate, and hook repair. |
| [TDD Levels](tdd.md) | The four enforcement levels and hook-based discipline. |
| [State and Memory](state-and-memory.md) | 4.x state layout, product artifacts, doctor runs, and recovery runs. |
| [Work-Item Artifacts](work-item-artifacts.md) | Opt-in per-work-item artifact directories, and how to enable and backfill them. |
| [Hook Development](hook-development.md) | Hook repair and emergency recovery. |
| [Corpus and RAG](corpus-system.md) | Document pipeline and local semantic search. |
| [Platform Dependencies](platform-dependencies.md) | Claude Code dependency risks and contingency posture. |
| [Capability Ledger](capability-ledger.md) | How every capability is classified as works, compromised, broken, or not mechanically verifiable. |
| [Capability Ledger — Current Table](capability-ledger-table.md) | The generated truth table: which capabilities work right now, and why the others do not. |
| [Behavioral Contracts](behavioral-contracts.md) | Model behavior contracts and current status. |
| [Evidence and Success-Criteria Contracts](evidence-and-contracts.md) | Frozen success-criteria contracts, implementation evidence, and the fail-closed verify gate. |
| [FAQ](faq.md) | Honest answers and troubleshooting. |
| [Glossary](glossary.md) | SweetClaude terminology. |

## Quick Reference

```text
/sweetclaude:go       Pick up where you left off
/sweetclaude:status   Project status
/sweetclaude:help     Conversational help
/sweetclaude:doctor   Maintenance front door
/sweetclaude:recover  Recovery for stuck project states
/sweetclaude:migrate  Supported taxonomy migration only after preflight
```
