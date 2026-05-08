---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:corpus-consolidate
user-invocable: true
description: "Scan source directories, deduplicate files, copy unique files into corpus/raw/inbox/. Originals are never moved or deleted. First step of the document-corpus pipeline; precedes triage."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Run `/sweetclaude:setup` first." Then stop.
</preflight-guard>

# Corpus Consolidate

Scan source directories, deduplicate files, and copy unique files into `corpus/raw/inbox/`. Originals are never moved or deleted.

## Step C0: Preconditions

**Check pipeline state:**

Read `.sweetclaude/state/corpus-pipeline.yaml` if it exists.

If it does not exist, create it:
```yaml
pipeline:
  step: idle
  active_since: null
  interrupted: false
consolidate:
  status: not-started
  last_run: null
  sources: []
  files_in_inbox: 0
triage:
  status: not-started
  last_run: null
  files_classified: 0
  files_remaining: 0
reconcile:
  status: not-started
  last_run: null
  active_cluster: null
  files_in_staged: 0
  files_in_working: 0
promote:
  status: not-started
  last_run: null
  files_in_working: 0
  files_promoted: 0
```

If `pipeline.step` is not `idle`:
> "The pipeline is currently running {pipeline.step} (started {pipeline.active_since}). Wait for it to finish or resolve the interrupted operation."

If the user insists on overriding: require them to type `I accept the risk of corpus corruption`. If they do, log the override in `.sweetclaude/state/decision-log.md` and proceed. If not, stop.

**Set pipeline state:** `pipeline.step: consolidating`, `active_since: {now}`.

**Check for interrupted consolidation:**

Does `.sweetclaude/state/consolidate-plan.md` exist without a completion marker?

If yes, offer Resume (diff plan against actual inbox and copy what is missing) or Start over.

**Ensure corpus directory exists:** `mkdir -p {project-path}/corpus/raw/inbox`

## Step C1: Identify sources

If the user provided source directories as arguments, use those. Otherwise ask: "Which directories should I scan? Give me one or more paths."

Validate each path exists before proceeding.

## Step C2: Scan and hash (subagent)

Spawn a subagent:

> Scan these directories and catalog every file: {source paths}
>
> **Exclude:** binary files (.png, .jpg, .gif, .ico, .woff, .woff2, .ttf, .eot, .exe, .dll, .so, .zip, .tar, .gz, .jar, .pyc, .o, .a), files larger than 1MB, directories (node_modules/, .git/, __pycache__/, .venv/, venv/, dist/, build/, .next/, .rag-index/, corpus/, .sweetclaude/, strategy/), lock files (package-lock.json, yarn.lock, pnpm-lock.yaml, Pipfile.lock, poetry.lock, Cargo.lock, go.sum), .DS_Store
>
> For each included file, collect: relative path from source root, source directory, file size in bytes, SHA-256 hash.
>
> Report as JSON array: `[{"source": "...", "relative_path": "...", "size_bytes": N, "sha256": "..."}]`
>
> Also report: total files scanned, files excluded (with breakdown), files included, total size.
>
> Do nothing else. Do not copy, move, or modify any files.

Verify: subagent returned JSON array and stats, did not modify files.

Present: "Scanned {N} files across {M} sources. {excluded} excluded. {included} to process ({total_size})."

## Step C3: Token estimation

Estimate tokens: `size_bytes / 4`. Report: "Estimated corpus size: ~{N} tokens ({size_mb} MB)."

## Step C4: Deduplication analysis (subagent)

Spawn a subagent:

> Given this file catalog (JSON from Step C2), group files by SHA-256 hash. For each group with >1 file: designate the first alphabetically as canonical, mark others as duplicates.
>
> Report: total unique files, total duplicates, duplicate groups (hash, canonical path, duplicate paths), tokens saved by deduplication.
>
> Do nothing else.

Present: "{unique} unique files, {duplicates} duplicates found. Deduplication saves ~{tokens_saved} tokens."

## Step C5: Generate and approve consolidation plan

Write `.sweetclaude/state/consolidate-plan.md`:

```markdown
# Consolidation Plan — {date}

## Sources
{list each source directory}

## Scan Summary
- Files scanned: {total}
- Files excluded: {excluded}
- Files included: {included}
- Duplicates found: {duplicates}
- Unique files to copy: {unique}
- Estimated tokens: {tokens}

## Destination
corpus/raw/inbox/{source_name}/

## File Manifest
{for each unique file: source path, destination path, size, hash — one line per file}

## Duplicate Groups
{from Step C4}

## Execution
- Batch size: 500 files
- Status: PENDING
```

Present summary and use AskUserQuestion: Execute / Review plan / Cancel.

If "Review plan", show the document, then re-ask. If "Cancel", stop.

## Step C6: Execute copy (subagent — batched)

Destination for each source: `corpus/raw/inbox/{source_dir_name}/`. If two sources share a dir name, suffix: `old-project-2`.

Process in batches of 500. For each batch spawn a subagent:

> Copy these files to corpus/raw/inbox/. Preserve directory structure.
>
> Rules: copy only (never move or delete source). If destination exists with same hash, skip. If different hash, rename with `-{N}` suffix before extension. Create destination dirs with `mkdir -p`.
>
> Report: files copied, files skipped (same hash), files renamed (collision), errors.

After all batches: report totals. Update consolidate-plan.md with completion marker.

## Step C7: Update state and commit

Update `corpus-pipeline.yaml`:
```yaml
pipeline:
  step: idle
  active_since: null
  interrupted: false
consolidate:
  status: complete
  last_run: {now}
  sources: [{source paths}]
  files_in_inbox: {count}
```

Create or update `.sweetclaude/state/corpus.yaml` with `last_consolidate` details.

```bash
git add corpus/raw/inbox/ .sweetclaude/state/consolidate-plan.md .sweetclaude/state/corpus.yaml .sweetclaude/state/corpus-pipeline.yaml
git commit -m "consolidate: copy {N} files from {sources} into corpus/raw/inbox"
```

Report: "Done. Next: run `/sweetclaude:corpus-triage` to classify the inbox files."

**Error handling:**
- Source disappears mid-run: skip missing files, continue, note in plan.
- Disk space: check before Step C6. If insufficient, stop before copying anything.
- Git commit fails: files are safe — commit can be retried manually. Do not delete copied files.
