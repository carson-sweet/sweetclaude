# Doctor — The Maintenance Front Door

**Version:** 1.0
**Date:** 2026-06-10

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
4. **Your choice.** You pick what to do — proceed, review, dry-run, or stop.
5. **Execute (only after approval).** Auto-fixes run; prompted fixes ask you to
   choose first. Each change is recorded to the run archive.
6. **Persist & summarize.** Doctor writes a run summary and, when needed, offers
   to re-scan.

## How findings get resolved

Every finding maps to a resolution — there are no dead-end "here's a problem,
good luck" reports:

- **Auto-fix** — safe, unambiguous repairs (e.g. a stale derived value). Applied
  automatically *after you approve the batch*, backed up and reversible.
- **Prompted fix** — the fix is clear but the right value depends on your intent,
  so Doctor presents a bounded set of choices (pick a valid value, supply a
  value, resolve a config conflict, repair YAML, restore a missing hook, move a
  misfiled file, renumber a duplicate, or exit compatibility mode). You choose;
  Doctor executes through the same backed-up pipeline.
- **Delegate** — problems owned by another flow (taxonomy migration, project
  recovery) are handed off to `/sweetclaude:configure migrate` or `/sweetclaude:configure recover`,
  which run their own preflight, approval, and rollback. Doctor re-scans after.
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
- **Rollback is always possible.** Any run can be fully reversed from its
  archive — see below.

## Rolling back a run

If a run did something you didn't want, you can restore the project to its
pre-run state. Run `/sweetclaude:configure doctor` and choose the rollback option (it lists
recent runs and the files each one changed), or tell Doctor you want to undo the
last run. Restore rewrites each changed file from its archived before-image and
reverses any moves.

## Routes from a scan

When the scan determines a specialist flow is needed, Doctor points you to it
rather than acting outside its lane:

| Route status | Next step |
|---|---|
| `recovery-available` | `/sweetclaude:configure recover` |
| `supported-migration-available` | `/sweetclaude:configure migrate` |
| `compatibility-mode` | Continue without the migration prompt. |
| `no-migration-recommended` | Continue normal work. |

Do not start by running `/sweetclaude:configure migrate` on an unknown old layout — start
with Doctor.

## Related

- [Migration and Recovery](migration-and-recovery.md) — the migration and
  recovery flows Doctor routes to.
- [Work-Item Artifacts](work-item-artifacts.md) — one of the things Doctor
  validates.
- [State and Memory](state-and-memory.md) — where doctor runs and archives live.
