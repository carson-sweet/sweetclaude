# SweetClaude 4.x Migration Guide

**Version:** 1.1
**Date:** 2026-10-21

This guide is for projects on a 4.x install that are moving to 5.x. The stable channel is now 5.x, tracked on `main`. The 4.x beta channel is retired: it no longer receives updates, and updating the beta plugin key stays on 4.x. The 3.x line is the `sweetclaude-legacy` channel (`carson-sweet/sweetclaude@stable-3.x`), and this guide does not apply to it.

The full migration and recovery guide lives here:

- [Migration and Recovery](migration-and-recovery.md)
- [Upgrading to 5.0](upgrading-to-5.md)
- [4.x Beta Rescue](beta-rescue.md)

## Short Version

Use this order:

1. Get onto 5.x.
   - Stable 4.x install: run the commands in [Upgrading to 5.0](upgrading-to-5.md): `/plugin marketplace update sweetclaude-stable`, then `/plugin update sweetclaude@sweetclaude-stable`.
   - Beta install: switch channels once, in this order, so you are never double-installed:

     ```text
     /plugin marketplace add carson-sweet/sweetclaude@main
     /plugin install sweetclaude@sweetclaude-stable
     /plugin marketplace remove sweetclaude-beta
     ```
2. Restart Claude Code.
3. Run `/sweetclaude:configure update` to sync framework files.
4. Run `/sweetclaude:configure doctor` in the project.
5. Follow doctor's maintenance route.

The `/sweetclaude:configure` commands are unknown until 5.x is installed and Claude Code has been restarted, so do not run any of them before step 2 is done.

Do not start by running `/sweetclaude:configure migrate` on an unknown old project layout.

## Routes

Doctor presents each route and offers to run the matching flow itself.

| Doctor route | Next step |
|---|---|
| `recovery-available` | Doctor offers to run safe recovery. |
| `supported-migration-available` | Doctor offers to start migration. |
| `compatibility-mode` | Continue without migration prompt. |
| `graduation-available` | Doctor offers to graduate the project from compatibility mode. |
| `graduation-blocked` | Doctor offers to fix the blockers, then graduate. |
| `migration-blocked` | Continue without migration; no files were changed. |
| `manual-review` | Review the findings doctor reports. |
| `no-maintenance-action` | Continue normal work. |

Typed legacy backlog layouts (`stories/`, `bugs/`, `debt/`, `chores/`) route to the taxonomy migrator, `scripts/migrate/migrate_taxonomy.py`. Duplicate work-item IDs are blockers that you resolve through `/sweetclaude:configure doctor` before migration.
