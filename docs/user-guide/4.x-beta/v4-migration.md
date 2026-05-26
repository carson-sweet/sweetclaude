# SweetClaude 4.x Migration Guide

This guide is for projects using the 4.x beta channel. If you are on stable 3.x,
do not follow 4.x migration instructions unless you intentionally installed the
4.x beta marketplace.

The full 4.x beta migration and recovery guide lives here:

- [4.x Migration and Recovery](migration-and-recovery.md)
- [4.x Beta Rescue](beta-rescue.md)

## Short Version

Use this order:

1. Update the Claude Code plugin package with `/plugin update`.
2. Restart Claude Code.
3. Run `/sweetclaude:update` to sync framework files.
4. Run `/sweetclaude:doctor` in the project.
5. Follow doctor's maintenance route.

Do not start by running `/sweetclaude:migrate` on an unknown old project layout.

## Routes

| Doctor route | Next step |
|---|---|
| `recovery-available` | `/sweetclaude:recover` |
| `supported-migration-available` | `/sweetclaude:migrate` |
| `compatibility-mode` | Continue without migration prompt. |
| `no-migration-recommended` | Continue normal work. |

`/sweetclaude:migrate` is only for layouts that pass preflight. Unsafe typed
legacy backlog directories and duplicate work-item IDs route to recovery instead
of blind migration.
