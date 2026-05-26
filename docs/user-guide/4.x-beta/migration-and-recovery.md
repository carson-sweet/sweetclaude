# SweetClaude 4.x Migration and Recovery

This page replaces the older "run migrate first" guidance. In 4.x beta, project
maintenance is routed through doctor and recovery before any taxonomy migration
runs.

## Safe Order

1. Update the Claude Code plugin package.
2. Restart Claude Code.
3. Run `/sweetclaude:update` to sync framework files.
4. Run `/sweetclaude:doctor` in the project.
5. Follow doctor's maintenance route.

Do not start by running `/sweetclaude:migrate` on an unknown project layout.

## What Doctor Decides

Doctor reads a deterministic maintenance route:

```text
python3 ~/.claude/scripts/sweetclaude/doctor.py maintenance-route --project-dir .
```

The route determines the next user-facing command:

| Route status | What it means | Next command |
|---|---|---|
| `recovery-available` | The project has an unsafe or stuck layout that should be stabilized before migration. | `/sweetclaude:recover` |
| `supported-migration-available` | The flat v3 `BL-*.md` layout passed preflight. | `/sweetclaude:migrate` |
| `compatibility-mode` | Recovery already accepted a legacy taxonomy layout without migration. | Continue; no migration prompt. |
| `no-migration-recommended` | No supported migration is needed. | Continue normal work. |

## What Migrate Supports

`/sweetclaude:migrate` is for the supported flat v3 backlog layout:

```text
.sweetclaude/product/backlog/BL-001-example.md
```

It runs a read-only preflight before creating locks, backups, copied files, or
migration maps:

```text
python3 ~/.claude/scripts/sweetclaude/migrate/migrate-v3-to-v4.py preflight --project-dir .
```

Migration is blocked when preflight finds typed legacy backlog directories or
duplicate work-item IDs. Blocked projects route to recovery.

## What Recovery Does

`/sweetclaude:recover` diagnoses first, plans second, snapshots before mutation,
and asks before execution. For unsafe typed legacy layouts, recovery stabilizes
state so SweetClaude stops repeatedly prompting blind migration. It does not move,
rename, delete, or normalize product artifacts manually.

Recovery run data lives under:

```text
.sweetclaude/state/recovery-runs/
```

Keep that directory out of source control. Recovery reports a rollback command in
its run report.

## Accepted Legacy Compatibility Mode

Some projects contain old typed backlog directories such as `stories/`, `bugs/`,
`debt/`, and `chores/`. Until a layout-specific migrator exists for those shapes,
recovery can mark the taxonomy as accepted legacy state:

```yaml
recovery:
  taxonomy:
    status: stabilized-without-migration
    migration_required: false
    blind_taxonomy_migration_allowed: false
```

When doctor sees that state, it collapses accepted legacy taxonomy noise and does
not show a migration prompt.

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
