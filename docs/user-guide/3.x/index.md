# SweetClaude 3.x Stable User Guide

**Version:** 1.1
**Date:** 2026-05-25

Use this complete guide if you installed SweetClaude from `stable-3.x` or
`/plugin list` shows `sweetclaude@sweetclaude-stable`.

3.x is the recommended channel for normal active project work. Stay on this track
unless you are intentionally testing 4.x beta project maintenance and taxonomy
changes.

## Install And Update

```text
/plugin marketplace add carson-sweet/sweetclaude@stable-3.x
/plugin install sweetclaude@sweetclaude-stable
```

To update stable:

```text
/plugin update sweetclaude@sweetclaude-stable
```

Restart Claude Code so the new plugin package is loaded. Then run this inside a
SweetClaude project when framework files need syncing:

```text
/sweetclaude:update
```

Do not use `/sweetclaude:update` to move a stable install onto 4.x beta. Beta is
a separate marketplace channel.

## Where To Begin

If you are new and want a working stable install, read [Getting Started](getting-started.md).

If you already installed stable and want the fastest operational path, read
[Quick Start](quickstart.md).

If you have it installed and want to understand the design decisions, read
[How It Works](how-it-works.md).

If you are considering beta, read [Moving From 3.x Stable To 4.x Beta](v4-migration.md).

## What Is In This Guide

| Page | What it is |
|---|---|
| [Install](install.md) | Stable install, update, legacy install keys, optional integrations, and suspension. |
| [Quick Start](quickstart.md) | First commands after stable is installed. |
| [Getting Started](getting-started.md) | Install through first feature on the stable channel. |
| [New Project Cheatsheet](cheatsheet-new-project.md) | Fast path for starting from an empty folder. |
| [Existing Project Cheatsheet](cheatsheet-existing-project.md) | Fast path for adopting an existing codebase. |
| [How It Works](how-it-works.md) | Mental model and architecture. |
| [Walkthroughs](walkthroughs.md) | Six concrete scenarios end-to-end. |
| [Phases and Workflows](phases-and-workflows.md) | Reference for phases, work types, gates, and workflow shapes. |
| [Planning Concepts](planning-concepts.md) | Backlogs, stories, milestones, epics, sprints, and priorities. |
| [Skills Reference](skills-reference.md) | Stable 3.x skill surface. |
| [TDD Levels](tdd.md) | The four enforcement levels and hook-based discipline. |
| [State and Memory](state-and-memory.md) | Stable 3.x project state, decision logs, assumptions, plans, and traceability. |
| [Hook Development](hook-development.md) | Stable 3.x hook diagnosis and manual repair. |
| [Corpus and RAG](corpus-system.md) | Document pipeline and local semantic search. |
| [Platform Dependencies](platform-dependencies.md) | Claude Code dependency risks and contingency posture. |
| [Behavioral Contracts](behavioral-contracts.md) | Model behavior contracts and current status. |
| [FAQ](faq.md) | Honest answers for stable users. |
| [Glossary](glossary.md) | SweetClaude terminology. |
| [Moving To 4.x Beta](v4-migration.md) | Safe channel-switch guidance. |

## Quick Reference

```text
/sweetclaude:go     Pick up where you left off
/sweetclaude:status Project status
/sweetclaude:help   Conversational help
/sweetclaude:update Sync framework files after plugin update
```
