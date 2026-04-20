---
description: "Scan directories of messy files, deduplicate, classify, copy into corpus/raw/inbox/. Mechanical — no synthesis, no creative work. Non-destructive, idempotent, plan-as-gate."
---

# SweetClaude Consolidate

Scan source directories, deduplicate files, and copy unique files into `corpus/raw/inbox/`. Originals are never moved or deleted.

**Follow these steps exactly as written. Do not skip steps. Do not fast-track.**

---

## Step 0: Preconditions (YOU check this)

**Check SweetClaude is initialized:**

Does `.sweetclaude/state/phase.yaml` exist?

If no:
> "SweetClaude is not set up for this project. Run `/sweetclaude:init` first."

Stop. Do not proceed.

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
> "Cannot run corpus-consolidate. The pipeline is currently running {pipeline.step} (started {pipeline.active_since}). Wait for it to finish or resolve the interrupted operation."

If the user insists:
> "Running corpus-consolidate while {pipeline.step} is active can corrupt the refined corpus. Original source files will be unaffected, but canonical documents, sidecars, and provenance records may become inconsistent. Type 'I accept the risk of corpus corruption' to proceed."

The user must type the exact phrase. If they do, log the override in `.sweetclaude/state/decision-log.md` and proceed. If not, stop.

**Set pipeline state:**
```yaml
pipeline:
  step: consolidating
  active_since: {ISO 8601 timestamp}
  interrupted: false
```

**Check for interrupted consolidation:**

Does `.sweetclaude/state/consolidate-plan.md` exist?

If yes, read it and check whether execution completed (look for a completion marker at the end). Tell the user:

> "Found an unfinished consolidation plan from a previous session. It planned to copy {N} files from {sources}."

Use AskUserQuestion:
- "Resume" — diff the plan against what actually landed in `corpus/raw/inbox/` and copy only what is missing
- "Start over" — discard the old plan and begin fresh

If resume, skip to Step 6 with the existing plan. If start over, delete the old plan and continue.

**Ensure corpus directory exists:**

```bash
mkdir -p {project-path}/corpus/raw/inbox
```

---

## Step 1: Identify Sources (YOU ask the user)

If the user provided source directories in the command arguments, use those.

If not, ask: "Which directories should I scan? Give me one or more paths."

Wait for the answer. Store the source paths.

Validate each path exists. If any path does not exist, report it and ask for correction. Do not proceed with invalid paths.

---

## Step 2: Scan and Hash (SUBAGENT)

Spawn a subagent:

> Scan the following directories and catalog every file:
> {source paths}
>
> **Exclude these patterns:**
> - Binary files (images, executables, compiled output, archives: .png, .jpg, .gif, .ico, .woff, .woff2, .ttf, .eot, .exe, .dll, .so, .dylib, .zip, .tar, .gz, .jar, .war, .pyc, .pyo, .o, .a)
> - Files larger than 1MB
> - Directories: node_modules/, .git/, __pycache__/, .venv/, venv/, dist/, build/, .next/, .rag-index/, corpus/, .sweetclaude/, strategy/
> - Lock files: package-lock.json, yarn.lock, pnpm-lock.yaml, Pipfile.lock, poetry.lock, Cargo.lock, go.sum
> - .DS_Store files
>
> For each included file, collect:
> - Relative path from source root
> - Source directory (which of the input directories it came from)
> - File size in bytes
> - SHA-256 hash of file contents
>
> Report as a JSON array:
> ```json
> [
>   {
>     "source": "/path/to/source-dir",
>     "relative_path": "subdir/file.md",
>     "size_bytes": 4521,
>     "sha256": "abc123..."
>   }
> ]
> ```
>
> Also report summary stats:
> - Total files scanned (before exclusions)
> - Files excluded (with breakdown by reason: binary, size, directory, lock, other)
> - Files included
> - Total size of included files
>
> Do nothing else. Do not copy, move, or modify any files.

**Verify:** Subagent returned JSON array and summary stats. Did not modify any files.

Present summary to user:
> "Scanned {N} files across {M} sources. {excluded} excluded (binary/large/lock/system). {included} files to process ({total_size})."

---

## Step 3: Token Estimation (YOU calculate this)

Estimate tokens for the included files using `size_bytes / 4` (rough approximation).

Report:
> "Estimated corpus size: ~{N} tokens ({size_mb} MB)."

If the user asks for precise token counting, note it but do not block on it — precise counting is expensive and optional.

---

## Step 4: Deduplication Analysis (SUBAGENT)

Spawn a subagent:

> Given this file catalog (JSON array from Step 2), identify duplicate groups.
>
> Group files by SHA-256 hash. For each group with more than one file:
> - Designate the first file (alphabetically by full path) as the canonical copy
> - Mark all others as duplicates
>
> Report:
> - Total unique files (files to copy)
> - Total duplicates found
> - Duplicate groups (hash, canonical file path, list of duplicate paths)
> - Tokens saved by deduplication (sum of duplicate file sizes / 4)
>
> Format duplicate groups as:
> ```
> ## Duplicate Group: {short_hash}
> Canonical: {source}/{relative_path} ({size} bytes)
> Duplicates:
>   - {source}/{relative_path}
>   - {source}/{relative_path}
> ```
>
> Do nothing else. Do not copy, move, or modify any files.

**Verify:** Subagent returned dedup analysis. Did not modify any files.

Present to user:
> "{unique} unique files, {duplicates} duplicates found. Deduplication saves ~{tokens_saved} tokens."

---

## Step 5: Generate Consolidation Plan (YOU write this)

Write the plan to `.sweetclaude/state/consolidate-plan.md`:

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
{For each unique file: source path, destination path, size, hash — one line per file}

## Duplicate Groups
{From Step 4 output — which files are duplicates of which}

## Execution
- Batch size: 500 files
- Estimated batches: {ceil(unique / 500)}
- Status: PENDING
```

Present the plan summary to the user:

> "Consolidation plan written to `.sweetclaude/state/consolidate-plan.md`. {unique} files will be copied to `corpus/raw/inbox/` from {N} sources. Review the plan?"

Use AskUserQuestion:
- "Execute" — proceed with copying
- "Review plan" — show the full plan document
- "Cancel" — stop without copying

If "Review plan", show the document, then re-ask Execute or Cancel.

If "Cancel":
> "Plan saved but not executed. Run `/sweetclaude:corpus-consolidate` again to resume."

Stop.

---

## Step 6: Execute Copy (SUBAGENT — batched)

Read the plan from `.sweetclaude/state/consolidate-plan.md`.

The destination for each source is `corpus/raw/inbox/{source_name}/` where `source_name` is the directory name of the source path (e.g., `/Users/me/dev/old-project` → `old-project`).

If two sources have the same directory name, append a numeric suffix: `old-project`, `old-project-2`.

**Process in batches of 500 files.** For each batch, spawn a subagent:

> Copy these files to `corpus/raw/inbox/`. Preserve the directory structure within each source.
>
> {batch file list: source_path → destination_path}
>
> Rules:
> - Copy only. Never move or delete source files.
> - If destination file already exists with the same SHA-256 hash, skip it (idempotent).
> - If destination file exists with a different hash, rename the new file with a `-{N}` suffix before the extension.
> - Create destination directories as needed with `mkdir -p`.
>
> Report:
> - Files copied: {count}
> - Files skipped (already exist, same hash): {count}
> - Files renamed (collision, different hash): {count with new names}
> - Errors: {count with details}
>
> Do nothing else.

**Verify** each batch: subagent reported counts, no errors (or errors are explained).

After each batch, report progress to user:
> "Batch {N}/{total}: {copied} copied, {skipped} skipped, {errors} errors."

After all batches complete, report totals:
> "Consolidation complete. {total_copied} files copied to `corpus/raw/inbox/`. {total_skipped} skipped (already present). {total_errors} errors."

Update the plan document — append at the end:

```markdown
## Execution Complete
- Date: {date}
- Files copied: {total_copied}
- Files skipped: {total_skipped}
- Files renamed: {total_renamed}
- Errors: {total_errors}
- Status: COMPLETE
```

---

## Step 7: Offer RAG Indexing (YOU ask the user)

Use AskUserQuestion:
- "Index" — index the copied files into the raw RAG collection
- "Skip" — do not index now

If "Index":
> "Indexing `corpus/raw/inbox/` into the raw RAG collection. This may take a moment for large corpora."

Invoke the RAG indexing tool (mcp-local-rag or equivalent) to index all files in `corpus/raw/inbox/` into the `{project}-raw` collection.

If RAG tooling is not available:
> "RAG indexing not available — MCP RAG server not configured. Run `/sweetclaude:rag-index` to set it up, then re-run indexing."

If "Skip":
> "Skipping RAG indexing. Run `/sweetclaude:rag-index` later to index the raw corpus."

---

## Step 8: Update State and Commit (YOU do this)

**Update or create `corpus.yaml`:**

If `.sweetclaude/state/corpus.yaml` exists, update the `last_consolidate` section. If it does not exist, create it:

```yaml
corpus_policy:
  default_collection: canonical
  raw_access: on_request
  reconciliation_mode: active

collections:
  canonical:
    path: corpus/canonical/
    rag_collection: {project_name}-canonical
  raw:
    path: corpus/raw/
    rag_collection: {project_name}-raw

rag_exclusions:
  - "**/node_modules/**"
  - "**/.git/**"
  - "**/__pycache__/**"
  - "**/.venv/**"
  - "**/dist/**"
  - "**/build/**"
  - "**/corpus/**"
  - "**/.sweetclaude/**"
  - "**/strategy/**"

last_consolidate:
  timestamp: {ISO 8601 timestamp}
  sources: [{source paths}]
  files_copied: {count}
  files_skipped: {count}
  tokens_retained: {estimated tokens of copied files}
  plan_document: .sweetclaude/state/consolidate-plan.md
```

**Update pipeline state:**

```yaml
pipeline:
  step: idle
  active_since: null
  interrupted: false
consolidate:
  status: complete
  last_run: {ISO 8601 timestamp}
  sources: [{source paths}]
  files_in_inbox: {count of files now in corpus/raw/inbox/}
```

**Git commit:**

```bash
git add corpus/raw/inbox/ .sweetclaude/state/consolidate-plan.md .sweetclaude/state/corpus.yaml .sweetclaude/state/corpus-pipeline.yaml
git commit -m "consolidate: copy {N} files from {sources} into corpus/raw/inbox"
```

If the commit is too large (more than 5000 files staged), split into multiple commits by source directory.

Report:
> "State updated and committed. Next step: run `/sweetclaude:corpus-triage` to classify the files for reconciliation."

---

## Error Handling

**Source directory disappeared mid-run:** Skip missing files, report which were skipped, continue with remaining batches. Note in plan document.

**Disk space:** Before starting Step 6, check available disk space vs. total size to copy. If insufficient:
> "Not enough disk space. Need {required}, have {available}. Free space and retry."

Stop. Do not partially copy.

**Git commit fails:** Report the error. The files are already copied — the commit can be retried manually. Do not delete copied files on commit failure.

**Hash computation fails on a file:** Skip the file, log it in the plan document under an Errors section, continue with remaining files.
