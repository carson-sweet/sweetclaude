# Work-Item Artifacts

**Version:** 1.1
**Date:** 2026-10-21

Work-item artifact directories are an opt-in feature that co-locates everything produced for a single work item — story, epic, or milestone — under one per-item directory. Design docs, plans, contracts, reports, and decision excerpts all live together, so finding everything about a work item means looking in one place instead of hunting across the project.

This page is reference. For the broader state model these artifacts live alongside, read [State and Memory](state-and-memory.md).

---

## The Directory

When the feature is active, artifacts are written to:

```
.sweetclaude/work/<ITEM-ID>/
```

`<ITEM-ID>` is the work item identifier — `ISSUE-170`, `EP-004`, `MS-002`, and so on. Each per-item directory holds a `manifest.yaml` plus a fixed set of category subdirectories:

```
.sweetclaude/work/ISSUE-170/
├── manifest.yaml   ← item metadata + backfill record
├── design/         ← design and technical docs
├── plans/          ← plan files
├── contracts/      ← success-criteria contracts
├── reports/        ← reports
├── decisions/      ← decision excerpts
└── scratch/        ← working notes
```

The `manifest.yaml` records the item ID, item type, title, the path to the item's definition file, any backfill links, cross-references, and an effort link if one exists.

---

## The Feature Flag

The feature is tracked in `.sweetclaude/state/sweetclaude.yaml` under `features.work_item_artifacts`. Like every optional feature it carries a status (`not_offered` until the feature is first offered, then `active` or `declined`).

You enable it the same way as any other optional feature — through feature configuration, which lists it as **Work-item artifact directories**:

> Co-locate all artifacts per story, epic, and milestone into `.sweetclaude/work/<ID>/` — find everything about a work item in one place.

When you turn it on for the first time, its onboarding flow runs automatically.

---

## The Skill

Everything is driven by `/sweetclaude:configure work-item-artifacts`. The argument you pass selects the flow.

### `onboard`

The setup flow, invoked automatically when the feature is newly enabled. It:

1. Explains what the feature does.
2. Runs the backfill scanner in dry-run mode to discover existing artifacts.
3. If nothing is found, confirms the feature is active — new artifacts will be written to per-item directories automatically — and stops.
4. If artifacts are found, shows a per-item breakdown and offers a choice: **Run backfill now** (create directories and symlink existing artifacts) or **Skip backfill** (activate without backfilling, so only new work items get directories).
5. If you choose to backfill, runs the scanner for real and reports how many directories were created.

Backfill creates symlinks — your existing files stay where they are.

### `backfill` (or no argument)

Runs the backfill scanner against the whole project, following the same dry-run → confirm → execute steps as onboard. Use this to re-run backfill later, after new items have accumulated artifacts.

### single item (e.g. `ISSUE-170`)

Scans for one item only. It runs a dry-run first, shows what it found, and — if there are artifacts — asks before linking them.

### `status`

Reports the current state: how many work-item directories exist in `.sweetclaude/work/` and how many broken symlinks they contain.

---

## Backfilling Existing Items

Backfill is handled by `${CLAUDE_PLUGIN_ROOT}/scripts/backfill_work_item_artifacts.py`. The script ships with the plugin, not in your project, so run it from the plugin root:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/backfill_work_item_artifacts.py" --project-dir . --dry-run
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/backfill_work_item_artifacts.py" --project-dir .
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/backfill_work_item_artifacts.py" --project-dir . --item ISSUE-170
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/backfill_work_item_artifacts.py" --project-dir . --json
```

`--dry-run` shows what would be created without making changes. `--item` limits the run to a single ID. `--json` prints the results as JSON. The skill flows above wrap these same commands, so most of the time you do not call the script yourself.

<!-- docs-claims: ignore path:docs/internal/ --><!-- docs-claims: ignore path:docs/plans/ -->
The scanner builds its list of work items from `work_history` and the active work item in `sweetclaude.yaml`, plus the issue, epic, and milestone files under `.sweetclaude/product/`. It then searches known artifact locations — `.sweetclaude/technical/`, `.sweetclaude/plans/`, `.sweetclaude/contracts/`, `.sweetclaude/reports/`, and the project's `docs/internal/` and `docs/plans/` — for files matching each item ID. It also resolves `STORY-NNN` aliases to their migrated `ISSUE-NNN` IDs and links any matching `.sweetclaude/efforts/` directory. Discovered files are sorted into the matching category subdirectory and symlinked in; the original files are never moved.

An item that already has a work directory is skipped, so re-running backfill is safe.

---

## Doctor Validation

When the feature is active, [Doctor](doctor.md) validates the work directories and reports issues as warnings:

- Feature active but `.sweetclaude/work/` does not exist.
- Work-item directories missing their `manifest.yaml`.
- Broken symlinks inside work-item directories (links whose targets no longer exist).

These are report-only findings — Doctor surfaces them so you can fix them, for example by re-running backfill.

---

## What to Read Next

- The state files these artifacts sit beside → [State and Memory](state-and-memory.md)
- Diagnosing and repairing project state, including the checks above → [Doctor](doctor.md)
