# SweetClaude 4.x Beta User Guide

**Version:** 1.1
**Date:** 2026-05-25

Use this complete guide only if you intentionally installed the 4.x beta
marketplace or `/plugin list` shows `sweetclaude@sweetclaude-beta`.

4.x beta changes project maintenance behavior. Plugin update, framework sync,
project recovery, and taxonomy migration are separate safety-gated flows.

## Install And Update

```text
/plugin marketplace add carson-sweet/sweetclaude@beta-4.x
/plugin install sweetclaude@sweetclaude-beta
```

After plugin install or update, restart Claude Code before running SweetClaude
commands. To update beta:

```text
/plugin update sweetclaude@sweetclaude-beta
/sweetclaude:update
```

If `/plugin list` shows the legacy beta key `sweetclaude@sweetclaude`, update
that exact key first.

## Maintenance Front Door

For project problems after update, start with:

```text
/sweetclaude:doctor
```

Doctor routes to one of these outcomes:

| Route status | Next step |
|---|---|
| `recovery-available` | `/sweetclaude:recover` |
| `supported-migration-available` | `/sweetclaude:migrate` |
| `compatibility-mode` | Continue without migration prompt. |
| `no-migration-recommended` | Continue normal work. |

Do not start by running `/sweetclaude:migrate` on an unknown old project layout.

## Where To Begin

If you are new and want a working beta install, read [Getting Started](getting-started.md).

If you have an existing beta install that is stuck, noisy, or reporting confusing
migration advice, read [Beta Rescue](beta-rescue.md).

If you need to understand project-state and taxonomy migration behavior, read
[Migration and Recovery](migration-and-recovery.md).

If you have it installed and want to understand the design decisions, read
[How It Works](how-it-works.md).

## What Is In This Guide

| Page | What it is |
|---|---|
| [Install](install.md) | Beta install, update, optional integrations, and suspension. |
| [Quick Start](quickstart.md) | First commands after beta is installed. |
| [Getting Started](getting-started.md) | Install through first feature, beta channel included. |
| [New Project Cheatsheet](cheatsheet-new-project.md) | Fast path for starting from an empty folder. |
| [Existing Project Cheatsheet](cheatsheet-existing-project.md) | Fast path for adopting an existing codebase. |
| [Migration and Recovery](migration-and-recovery.md) | Doctor-first beta maintenance, supported migration, recovery, and compatibility mode. |
| [Beta Rescue](beta-rescue.md) | Recovery path for stuck or confusing beta installs. |
| [4.x Migration Guide](v4-migration.md) | Short migration route summary and doctor outcomes. |
| [How It Works](how-it-works.md) | Mental model and architecture. |
| [Walkthroughs](walkthroughs.md) | Six concrete scenarios end-to-end. |
| [Phases and Workflows](phases-and-workflows.md) | Reference for phases, work types, gates, and workflow shapes. |
| [Planning Concepts](planning-concepts.md) | Backlogs, stories/issues, milestones, epics, sprints, and priorities. |
| [Skills Reference](skills-reference.md) | 4.x beta skill surface, including doctor, recover, migrate, and hook repair. |
| [TDD Levels](tdd.md) | The four enforcement levels and hook-based discipline. |
| [State and Memory](state-and-memory.md) | 4.x beta state layout, product artifacts, doctor runs, and recovery runs. |
| [Hook Development](hook-development.md) | Hook repair and emergency recovery. |
| [Corpus and RAG](corpus-system.md) | Document pipeline and local semantic search. |
| [Platform Dependencies](platform-dependencies.md) | Claude Code dependency risks and contingency posture. |
| [Behavioral Contracts](behavioral-contracts.md) | Model behavior contracts and current status. |
| [FAQ](faq.md) | Honest answers and beta-specific troubleshooting. |
| [Glossary](glossary.md) | SweetClaude terminology. |

## Quick Reference

```text
/sweetclaude:go       Pick up where you left off
/sweetclaude:status   Project status
/sweetclaude:help     Conversational help
/sweetclaude:doctor   Maintenance front door
/sweetclaude:recover  Recovery for stuck beta states
/sweetclaude:migrate  Supported taxonomy migration only after preflight
```
