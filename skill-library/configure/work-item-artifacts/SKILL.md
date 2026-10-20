---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Co-locate all artifacts per story, epic, and milestone into .sweetclaude/work/<ID>/. Manages onboarding, backfill, and per-item directory creation."
---



# Work-Item Artifact Directories

## Onboard

If invoked with argument `onboard`:

### Step 1: Explain

> "Work-item artifact directories group all artifacts produced for each story, epic, and milestone into `.sweetclaude/work/<ITEM-ID>/`. Design docs, plans, contracts, reports, and decision excerpts all live together — finding everything about a work item means looking in one place."

### Step 2: Backfill scan

Run the backfill scanner in dry-run mode to discover existing artifacts:

```bash
python3 scripts/backfill_work_item_artifacts.py --project-dir . --dry-run
```

Present the results to the user. If no artifacts were found:

> "No existing artifacts found to backfill. The feature is active — new artifacts will be written to per-item directories automatically."

Stop here.

If artifacts were found, present a summary:

> "I found artifacts for {N} work items that can be linked into per-item directories. This creates symlinks — your existing files stay where they are."

Then show the per-item breakdown from the script output.

### Step 3: Confirm backfill

Use **AskUserQuestion** (multiSelect: false):
- **label**: "Run backfill now"
- **description**: "Create work-item directories and symlink existing artifacts"
- **label**: "Skip backfill"
- **description**: "Activate the feature without backfilling — only new work items will get directories"

### Step 4: Execute backfill

If the user chose to run the backfill:

```bash
python3 scripts/backfill_work_item_artifacts.py --project-dir .
```

Present the results:

> "{N} work-item directories created in `.sweetclaude/work/`."

### Step 5: Confirm

> "Work-item artifact directories are active. New artifacts will be written to `.sweetclaude/work/<ITEM-ID>/` automatically."

---

## Manual backfill

If invoked without arguments or with argument `backfill`:

Run the backfill scanner. Follow the same Steps 2-4 from the onboard flow above.

## Single-item backfill

If invoked with a specific item ID (e.g., `ISSUE-170`):

```bash
python3 scripts/backfill_work_item_artifacts.py --project-dir . --item {ITEM-ID} --dry-run
```

Show results. If artifacts found, ask to proceed, then run without `--dry-run`.

## Status

If invoked with argument `status`:

```bash
python3 - << 'PY'
import os, yaml

work_dir = '.sweetclaude/work'
if not os.path.isdir(work_dir):
    print("NONE")
else:
    dirs = [d for d in os.listdir(work_dir) if os.path.isdir(os.path.join(work_dir, d))]
    total = len(dirs)
    broken = 0
    for d in dirs:
        for root, _, files in os.walk(os.path.join(work_dir, d)):
            for f in files:
                fpath = os.path.join(root, f)
                if os.path.islink(fpath) and not os.path.exists(fpath):
                    broken += 1
    print(f"TOTAL:{total}")
    print(f"BROKEN_LINKS:{broken}")
PY
```

Present:
> "{TOTAL} work-item directories in `.sweetclaude/work/`. {BROKEN_LINKS} broken symlinks."
