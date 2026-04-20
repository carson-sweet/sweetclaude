---
description: "Classify files in corpus/raw/inbox/ for reconciliation. Lightweight batch review — no synthesis. User-driven classification into keep-as-is, needs-reconciliation, discard, or defer."
---

# SweetClaude Triage

Classify files in `corpus/raw/inbox/` so they can be reconciled, archived, or deferred. This is batch classification — fast decisions, no synthesis.

**Follow these steps exactly as written. Do not skip steps. Do not fast-track.**

---

## Step 0: Preconditions (YOU check this)

**Check SweetClaude is initialized:**

Does `.sweetclaude/state/phase.yaml` exist?

If no:
> "SweetClaude is not set up for this project. Run `/sweetclaude:init` first."

Stop. Do not proceed.

**Check pipeline gate:**

Read `.sweetclaude/state/corpus-pipeline.yaml`.

If it does not exist:
> "No corpus pipeline state found. Run `/sweetclaude:corpus-consolidate` first."

Stop.

If `consolidate.status` is not `complete`:
> "Cannot run corpus-triage. The corpus pipeline requires consolidate to complete first. Current state: consolidate is {consolidate.status}."

If the user insists:
> "Running corpus-triage before consolidation is complete can corrupt the refined corpus. Original source files will be unaffected, but canonical documents, sidecars, and provenance records may become inconsistent. Type 'I accept the risk of corpus corruption' to proceed."

The user must type the exact phrase. If they do, log the override in `.sweetclaude/state/decision-log.md` and proceed. If not, stop.

If `pipeline.step` is not `idle`:
> "Cannot run corpus-triage. The pipeline is currently running {pipeline.step} (started {pipeline.active_since}). Wait for it to finish or resolve the interrupted operation."

Apply the same override protocol if the user insists.

**Set pipeline state:**
```yaml
pipeline:
  step: triaging
  active_since: {ISO 8601 timestamp}
  interrupted: false
```

**Check corpus exists:**

Does `corpus/raw/inbox/` exist and contain files?

If the directory does not exist:
> "No corpus found. Run `/sweetclaude:corpus-consolidate` first to ingest files."

Stop.

If the directory exists but is empty:
> "corpus/raw/inbox/ is empty. Nothing to triage."

Stop.

**Ensure staging and archive directories exist:**

```bash
mkdir -p {project-path}/corpus/raw/staged
mkdir -p {project-path}/corpus/archive
```

---

## Step 1: Inventory (SUBAGENT)

Spawn a subagent:

> Scan `corpus/raw/inbox/` recursively. For each file:
> - Full path relative to project root
> - File size in bytes
> - First 5 lines of content (for classification context)
>
> Group files by top-level subdirectory within `corpus/raw/inbox/` (the source directory from consolidation). Report:
>
> ```
> ## {source_name}/ ({N} files, {total_size})
>
> | # | File | Size | Preview |
> |---|------|------|---------|
> | 1 | relative/path.md | 4.2 KB | First line of content... |
> ```
>
> Also report totals:
> - Total files in inbox
> - Total size
> - Number of source groups
>
> Do nothing else. Do not move, copy, or modify any files.

**Verify:** Subagent returned inventory. Did not modify any files.

Present summary:
> "corpus/raw/inbox/ contains {N} files across {M} source groups ({total_size}). Ready to triage."

---

## Step 2: Choose Triage Mode (YOU ask the user)

Use AskUserQuestion:
- "By group" — triage one source group at a time (recommended for large corpora)
- "By file" — triage individual files (for small corpora or targeted review)
- "Bulk classify" — classify an entire source group with one decision

---

## Step 3: Triage Loop

For each file or group (depending on mode chosen in Step 2), present the file(s) and ask for classification.

### By-Group Mode

For each source group from the inventory:

Present the group summary table from Step 1. Then for each file in the group, spawn a subagent to read it:

> Read this file and produce a one-paragraph summary (3-5 sentences). Identify:
> - What type of document this is (strategy, product spec, design doc, brainstorm, meeting notes, research, session export, code, config, other)
> - Whether it appears to be a draft, final version, or superseded version
> - Any version indicators (v1, v2, dates, "draft", "final")
> - Whether it overlaps with or duplicates content you have seen in other files (note which ones)
>
> Format:
> ```
> **{filename}** ({size})
> Type: {type} | Version: {version_indicator or "unknown"} | Status: {draft/final/superseded/unknown}
> Summary: {3-5 sentence summary}
> Overlaps: {list of similar files, or "none detected"}
> ```
>
> Do nothing else.

Present the summaries to the user in batches (10-20 files at a time for readability). For each batch, ask for classification using AskUserQuestion with free-text input:

> "Classify each file. Use the number and one of: **keep** (ready as-is), **reconcile** (needs merging or synthesis with other files), **discard** (not useful), **defer** (skip for now). You can classify multiple files at once, e.g., '1-5 keep, 6 discard, 7-8 reconcile, 9-10 defer'."

Parse the user's response. If any classification is ambiguous, ask for clarification on those specific files before proceeding.

### By-File Mode

Same as by-group but present one file at a time. Use AskUserQuestion with options:
- "Keep" — ready as-is, move to staged
- "Reconcile" — needs merging, move to staged with reconciliation flag
- "Discard" — not useful, archive with discard sidecar
- "Defer" — skip for now, stays in inbox

### Bulk Classify Mode

Present the group summary. Use AskUserQuestion with options:
- "Keep all" — move entire group to staged
- "Discard all" — archive entire group with discard sidecars
- "Defer all" — leave entire group in inbox
- "Mix" — switch to by-group mode for this group

---

## Step 4: Execute Classifications (SUBAGENT — per batch)

After each batch of classifications is confirmed, spawn a subagent to execute:

> Execute these triage classifications in `{project-path}`:
>
> {classification list: file_path → action}
>
> **For each "keep" file:**
> ```bash
> mkdir -p {destination_dir}
> mv {source_path} corpus/raw/staged/{relative_path}
> ```
> Preserve the directory structure within the source group.
>
> **For each "reconcile" file:**
> ```bash
> mkdir -p {destination_dir}
> mv {source_path} corpus/raw/staged/{relative_path}
> ```
> After moving, create a metadata file at `corpus/raw/staged/{relative_path}.triage.json`:
> ```json
> {
>   "triaged_at": "{ISO 8601 timestamp}",
>   "classification": "needs-reconciliation",
>   "source_path": "{original inbox path}",
>   "notes": ""
> }
> ```
>
> **For each "discard" file:**
> ```bash
> mkdir -p corpus/archive/{date}-triage/
> mv {source_path} corpus/archive/{date}-triage/
> ```
> Create a sidecar at `corpus/archive/{date}-triage/{filename}.reconciled.json`:
> ```json
> {
>   "source_path": "{original inbox path}",
>   "content_hash": "sha256:{hash if available, or 'not computed'}",
>   "reconciled_at": "{ISO 8601 timestamp}",
>   "reconciled_by": "{git user}",
>   "canonical_documents": [],
>   "action": "discarded",
>   "notes": "Discarded during triage — {user's rationale if provided, or 'no rationale given'}"
> }
> ```
>
> **For each "defer" file:**
> Leave the file in `corpus/raw/inbox/`. Create a metadata file at `{file_path}.deferred.json`:
> ```json
> {
>   "deferred_at": "{ISO 8601 timestamp}",
>   "reason": "{user's reason if provided, or 'deferred without reason'}"
> }
> ```
>
> Report:
> - Files staged (keep): {count}
> - Files staged (reconcile): {count}
> - Files archived (discard): {count}
> - Files deferred: {count}
> - Errors: {count with details}
>
> Do nothing else.

**Verify:** Subagent reported counts matching the classifications. No unexpected errors.

Report progress to user:
> "Batch complete: {kept} staged, {reconcile} staged for reconciliation, {discarded} archived, {deferred} deferred."

---

## Step 5: Repeat or Finish

If there are more files or groups to triage, return to Step 3.

If all files have been triaged (or the user wants to stop), proceed to Step 6.

If the user wants to stop mid-triage:

Update pipeline state:
```yaml
pipeline:
  step: idle
  active_since: null
  interrupted: false
triage:
  status: in-progress
  files_classified: {count so far}
  files_remaining: {count remaining in inbox}
```

> "Triage paused. {N} files classified, {M} remaining in inbox. Run `/sweetclaude:corpus-triage` to continue."

---

## Step 6: Summary and Commit (YOU do this)

Present the triage summary:

```
Triage Complete
═══════════════

Staged (keep):          {count} files
Staged (reconcile):     {count} files
Archived (discard):     {count} files
Deferred:               {count} files
Remaining in inbox:     {count} files

Staged files are in corpus/raw/staged/ ready for reconciliation.
Archived files are in corpus/archive/{date}-triage/ with sidecars.
```

**Update pipeline state:**

```yaml
pipeline:
  step: idle
  active_since: null
  interrupted: false
triage:
  status: complete
  last_run: {ISO 8601 timestamp}
  files_classified: {total count}
  files_remaining: 0
```

**Git commit:**

```bash
git add corpus/raw/staged/ corpus/archive/ corpus/raw/inbox/ .sweetclaude/state/corpus-pipeline.yaml
git commit -m "triage: classify {N} files — {kept} staged, {discarded} archived, {deferred} deferred"
```

Report:
> "Triage committed. Next step: run `/sweetclaude:corpus-reconcile` to process staged files into canonical documents."

---

## Error Handling

**File move fails (permissions, disk):** Report the specific file and error. Skip it, continue with remaining files. Log in the triage summary.

**Metadata write fails:** The file move is still valid. Report the missing metadata. The corpus preflight will flag staged files without triage metadata on next session.

**User classification is unparseable:** Ask again with examples. Do not guess.

**Empty source groups:** Skip groups with no files. Report: "Skipping {group} — empty (all files may have been previously triaged)."

**Git commit fails:** Report the error. Files are already moved — the commit can be retried manually. Do not undo file moves on commit failure.

**Interrupted mid-triage:** Files already classified and moved stay moved. Unclassified files stay in inbox. Next run of `/sweetclaude:corpus-triage` picks up where things left off since it inventories whatever is currently in inbox.
