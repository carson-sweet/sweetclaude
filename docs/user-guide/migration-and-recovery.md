# SweetClaude Migration and Recovery

**Version:** 1.1
**Date:** 2026-10-21

This page replaces the older "run migrate first" guidance. Project maintenance is routed through doctor and recovery before any taxonomy migration runs.

## Safe Order

1. Get onto 5.x first. The 5.x configure commands do not exist on a 4.x install, so follow [Upgrading to 5.0](upgrading-to-5.md):
   - Stable 4.x install: `/plugin marketplace update sweetclaude-stable`, then `/plugin update sweetclaude@sweetclaude-stable`.
   - Beta install: the beta channel is retired and `/plugin update` on it stays on 4.x, so switch channels with `/plugin marketplace add carson-sweet/sweetclaude@main`, `/plugin install sweetclaude@sweetclaude-stable`, then `/plugin marketplace remove sweetclaude-beta`.
2. Restart Claude Code.
3. Run `/sweetclaude:configure update` to sync framework files. Update does not migrate project data.
4. Run `/sweetclaude:configure doctor` in the project.
5. Follow doctor's maintenance route.

Do not start by running `/sweetclaude:configure migrate` on an unknown project layout.

## What Doctor Decides

Doctor reads a deterministic maintenance route:

```text
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py" maintenance-route --project-dir .
```

Doctor presents the route and offers to run the matching flow itself. The statuses it can report are:

| Route status | What it means | Next step |
|---|---|---|
| `recovery-available` | The project has an unsafe or stuck layout that should be stabilized before migration. | Doctor offers to run safe recovery. |
| `supported-migration-available` | The project is a flat v3 `BL-NNN` layout that passed preflight, or a typed legacy layout (`stories/`, `bugs/`, `debt/`, `chores/`) that the taxonomy migrator handles. | Doctor offers to start migration. |
| `compatibility-mode` | Recovery already accepted a legacy taxonomy layout without migration. | Continue; no migration prompt. |
| `graduation-available` | The accepted legacy state is v4-compliant and no old prefixes remain. | Doctor offers to graduate the project from compatibility mode. |
| `graduation-blocked` | The project could graduate, but fixable validation blockers stand in the way. | Doctor offers to fix the blockers, then graduate. |
| `migration-blocked` | Old-format work items exist, but the migration capability did not prove the layout safe. No files were changed. | Continue without migration. |
| `manual-review` | The layout needs a human look before any automated step. | Review the findings doctor reports. |
| `no-maintenance-action` | Nothing needs maintenance. | Continue normal work. |

## What Migrate Supports

`/sweetclaude:configure migrate` dispatches to one of two migrators by project shape.

The flat v3 backlog layout goes to `scripts/migrate/migrate-v3-to-v4.py`:

```text
.sweetclaude/product/backlog/BL-001-example.md
```

It runs a read-only preflight before creating locks, backups, copied files, or migration maps:

```text
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/migrate/migrate-v3-to-v4.py" preflight --project-dir .
```

Typed legacy layouts (`stories/`, `bugs/`, `debt/`, `chores/`) and other multi-prefix layouts go to the taxonomy migrator, `scripts/migrate/migrate_taxonomy.py`, which supports `--dry-run` for a preview.

Duplicate work-item IDs appear as `duplicate-ids` blockers. Resolve them through `/sweetclaude:configure doctor` before migration; doctor's fix renumbers the non-canonical copy, and you can choose which copy is renumbered.

## What Recovery Does

`/sweetclaude:configure recover` diagnoses first, plans second, snapshots before mutation, and asks before execution. For unsafe layouts, recovery stabilizes state so SweetClaude stops repeatedly prompting blind migration. It does not move, rename, delete, or normalize product artifacts manually.

Recovery run data lives under:

```text
.sweetclaude/state/recovery-runs/
```

Keep that directory out of source control. Recovery reports a rollback command in its run report.

## Accepted Legacy Compatibility Mode

Some projects contain old typed backlog directories such as `stories/`, `bugs/`, `debt/`, and `chores/`. Recovery can mark the taxonomy as accepted legacy state:

```yaml
recovery:
  taxonomy:
    status: stabilized-without-migration
    migration_required: false
    blind_taxonomy_migration_allowed: false
```

What doctor does with accepted legacy state depends on what is still on disk:

- Old prefixes remain: doctor routes to `supported-migration-available` and shows a migration prompt for the taxonomy migrator.
- No old prefixes remain and the project passes the graduation check: doctor offers to graduate the project from compatibility mode.
- Otherwise, the project stays in compatibility mode, and doctor collapses the accepted legacy taxonomy noise without a migration prompt.

## Current 4.x Taxonomy

Current 4.x issue files use the unified taxonomy:

```text
.sweetclaude/product/backlog/ISSUE-001-example.md
.sweetclaude/product/backlog/done/ISSUE-002-completed.md
.sweetclaude/product/roadmap/issues/ISSUE-003-linked-to-epic.md
```

Item type is frontmatter, not an ID prefix:

```yaml
id: ISSUE-001
type: bug
status: new
```
