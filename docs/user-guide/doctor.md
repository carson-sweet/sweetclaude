# Doctor — The Maintenance Front Door

**Version:** 1.1
**Date:** 2026-10-21

`/sweetclaude:configure doctor` is the single place to start whenever a project feels
wrong after an update, a migration, or a long gap: noisy prompts, confusing
state, broken hooks, half-finished migrations, or files in the wrong place.
Doctor scans the project, tells you exactly what it found, and — only with your
approval — fixes what it safely can, routing everything else to the right
specialist flow.

Doctor is built to be **safe by construction**. Scanning and planning never
touch your files; only the execute phase changes anything, and every change it
makes is backed up first and fully reversible.

## When to run it

- After `/plugin update` or `/sweetclaude:configure update`.
- When SweetClaude gives confusing migration advice or won't pick up your work.
- When prompts repeat, hooks misbehave, or status looks inconsistent.
- Any time you're unsure whether the project is healthy — it's read-only until
  you say otherwise.

```text
/sweetclaude:configure doctor
```

## What it checks

A scan runs every check category and collects findings; it writes nothing. The
categories cover:

| Area | Checks |
|---|---|
| Project state & integrity | Core state files, derived/cached status freshness, onboarding completeness. |
| Hooks & environment | Installed hooks against the manifest (missing/broken), environment wiring. |
| Version & migration | Plugin/version currency, taxonomy and schema migration currency. |
| Storage & files | Duplicate IDs, misfiled work items, counter drift, frontmatter and format problems, orphaned index entries. |
| Planning artifacts | Per-work-item artifact directories, epic completion criteria, config compatibility. |

## How a run works

1. **Plugin guard.** Doctor refuses to run on a retired-channel or stale beta plugin and tells you
   how to update first.
2. **Route preflight + scan (read-only).** Doctor decides whether recovery,
   migration, or compatibility mode applies, then runs the full scan.
3. **Report.** Every finding is shown with its severity and how it will be
   resolved. Nothing has changed yet.
4. **Your choice.** You pick what to do — proceed, review, dry-run, or stop. If you have chosen `proceed` as your remembered default, Doctor skips this menu and says it is using the stored preference; pass `--interactive` to bring the menu back for that run.
5. **Execute.** Auto-fixes run once you have chosen proceed, either at the menu or through the remembered default; prompted fixes ask you to choose first. Each change is recorded to the run archive.
6. **Persist & summarize.** Doctor writes a run summary and, when needed, offers
   to re-scan.

## How findings get resolved

Every finding maps to a resolution — there are no dead-end "here's a problem,
good luck" reports:

- **Auto-fix** — safe, unambiguous repairs (e.g. a stale derived value). Applied after you choose proceed at the menu, or straight away when a remembered `proceed` default skips the menu (`--interactive` restores the menu). Backed up and reversible.
- **Prompted fix** — the fix is clear but the right value depends on your intent,
  so Doctor presents a bounded set of choices (pick a valid value, supply a
  value, resolve a config conflict, repair YAML, restore a missing hook, move a
  misfiled file, renumber a duplicate, or exit compatibility mode). You choose;
  Doctor executes through the same backed-up pipeline.
- **Delegate** — problems owned by another flow (taxonomy migration, project
  recovery) are presented by Doctor itself, which offers to run recovery or migration for you.
  Those flows run their own preflight, approval, and rollback, and Doctor re-scans after.
- **Accepted / report-only** — informational findings that need no action are reported and
  marked accepted. Doctor lists them so the picture is complete, but changes nothing.
- **Terminal fallback** — if a project is too far gone for in-place repair,
  Doctor surfaces the last-resort options: re-onboard from a clean state, or
  remove SweetClaude from the project. These are always explicit, never silent.

## Safety model

- **Read before write.** Scanning and planning are read-only. Only the execute
  phase changes files, and only after your approval for prompted fixes.
- **Every change is backed up.** Each run creates an archive at
  `.sweetclaude/state/doctor-runs/<timestamp>/` containing a before-image and a
  unified diff for every file it touches.
- **Safety branch offered.** Before making changes, Doctor offers to create a
  git restore point.
- **Archived changes are reversible.** Restore puts back every file that has an
  archived before-image. An action with no before-image is not reversible; restore
  lists it as skipped, and the git safety branch, when one was created for that run,
  is the fallback. See below.

## Rolling back a run

If a run did something you didn't want, you can restore the project to its
pre-run state. Run `/sweetclaude:configure doctor` and choose the rollback option (it lists
recent runs and the files each one changed), or tell Doctor you want to undo the
last run. Restore rewrites each changed file from its archived before-image and
reverses any moves. The result lists the files restored and any actions skipped because they had no archived before-image.

## Routes from a scan

Before the full scan, Doctor reads a compact maintenance route. When a specialist flow applies, Doctor presents it and offers to run recovery or migration itself, so you do not have to pick an internal command. You can decline and continue to the other fixes.

| Route status | What Doctor does |
|---|---|
| `recovery-available` | Offers to run safe recovery, the snapshot-backed flow, then re-scans. |
| `supported-migration-available` | Offers to start the migration flow for the supported flat `BL-NNN` or typed legacy layout, then re-scans. Migration runs its own preflight. |
| `compatibility-mode` | Prints the route message and continues. No migration is recommended while compatibility mode is active. |
| `graduation-available` | Offers to graduate the project from compatibility mode. This is a state-only change; no work-item files are modified. |
| `graduation-blocked` | Lists the fixable blockers and offers to fix them through Doctor's archived executor, then graduate. |
| `migration-blocked` | Prints the route message and continues. The migration capability did not prove the layout safe, and no files were changed. |
| `manual-review` | Prints the route message and continues to the scan, which carries the manual-review findings. |
| `no-maintenance-action` | Nothing to route. Continue normal work. |

Do not start by running `/sweetclaude:configure migrate` on an unknown old layout. Start with Doctor.

## Related

- [Migration and Recovery](migration-and-recovery.md) — the migration and
  recovery flows Doctor routes to.
- [Work-Item Artifacts](work-item-artifacts.md) — one of the things Doctor
  validates.
- [State and Memory](state-and-memory.md) — where doctor runs and archives live.
