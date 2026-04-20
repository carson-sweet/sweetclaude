---
description: "Take staged files and work with the user to produce approved canonical documents. Draft, iterate, and refine — the creative work. Per-cluster, session-length, iterative."
---

# SweetClaude Corpus Reconcile

Take staged files from `corpus/raw/staged/` and work with the user to produce approved canonical documents in `corpus/working/`. This is the creative work — drafting, merging, refining. The user controls pacing and approval.

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

If `triage.status` is not `complete`:
> "Cannot run corpus-reconcile. The corpus pipeline requires triage to complete first. Current state: triage is {triage.status}."

If the user insists:
> "Running corpus-reconcile before triage is complete can corrupt the refined corpus. Original source files will be unaffected, but canonical documents, sidecars, and provenance records may become inconsistent. Type 'I accept the risk of corpus corruption' to proceed."

The user must type the exact phrase. If they do, log the override in `.sweetclaude/state/decision-log.md` and proceed. If not, stop.

If `pipeline.step` is not `idle`:
> "Cannot run corpus-reconcile. The pipeline is currently running {pipeline.step} (started {pipeline.active_since}). Wait for it to finish or resolve the interrupted operation."

Apply the same override protocol if the user insists.

**Set pipeline state:**
```yaml
pipeline:
  step: reconciling
  active_since: {ISO 8601 timestamp}
  interrupted: false
```

**Check staged files exist:**

Does `corpus/raw/staged/` contain files?

If empty:
> "corpus/raw/staged/ is empty. Nothing to reconcile."

Set `pipeline.step = idle` and stop.

**Ensure working directory exists:**

```bash
mkdir -p {project-path}/corpus/working
```

**Check for active cluster from previous session:**

If `reconcile.active_cluster` is not null, files may be in `corpus/working/` from a previous session:

> "Found an active reconciliation cluster from a previous session: {active_cluster}. {N} files in corpus/working/."

Use AskUserQuestion:
- "Resume" — continue working on this cluster
- "Start fresh" — move working files back to staged and pick a new cluster

If resume, skip to Step 3 with the existing working files.

---

## Step 1: Inventory Staged Files (SUBAGENT)

Spawn a subagent:

> Scan `corpus/raw/staged/` recursively. For each file (skip `.triage.json` metadata files):
> - Full path relative to project root
> - File size in bytes
> - First 10 lines of content
> - Whether a `.triage.json` sidecar exists (and its classification if so)
>
> Group files by topic. Use these signals to cluster:
> - Filename similarity (same base name, different versions or dates)
> - Content overlap (similar titles, headings, or subject matter)
> - Source group (same subdirectory from consolidation)
> - Triage metadata (files flagged as needing reconciliation together)
>
> Present as clusters:
> ```
> ## Cluster: {topic name} ({N} files)
>
> | # | File | Size | Type | Version | Reconciliation needed |
> |---|------|------|------|---------|----------------------|
> | 1 | path/file.md | 4.2 KB | strategy | v2.1 | yes (from triage) |
> ```
>
> Also list any unclustered files separately.
>
> Do nothing else. Do not move, copy, or modify any files.

**Verify:** Subagent returned clusters. Did not modify any files.

Present summary:
> "corpus/raw/staged/ contains {N} files in {M} clusters. Pick a cluster to reconcile."

---

## Step 2: Select Cluster (YOU ask the user)

Present the cluster list. Ask: "Which cluster do you want to work on?"

Wait for the answer.

Move the selected cluster's files to `corpus/working/`:
```bash
mkdir -p corpus/working/
mv corpus/raw/staged/{selected_files} corpus/working/
```

Update pipeline state:
```yaml
reconcile:
  active_cluster: {cluster name}
  files_in_working: {count}
```

---

## Step 3: Analyze Cluster (SUBAGENT — one per file)

Also scan `corpus/canonical/` for existing documents that might be relevant.

For each file in the cluster, spawn a subagent:

> Read this staged file: `{file_path}`
>
> Also read these existing canonical documents (if any exist in `corpus/canonical/`):
> {list of potentially relevant canonical docs based on content type}
>
> Propose an action. Return JSON only:
> ```json
> {
>   "source": "corpus/working/{filename}",
>   "action": "merge | supersede | copy | discard",
>   "target_canonical": "corpus/canonical/{subdir}/{suggested_name}.md",
>   "rationale": "Why this action — be specific about what content is valuable and what overlaps",
>   "conflicts": ["List of conflicts with existing canonical docs, or empty"]
> }
> ```
>
> Action guide:
> - **merge** — this file has content that should be combined with an existing canonical doc or with other files in this cluster
> - **supersede** — this file is a newer/better version that should replace an existing canonical doc entirely
> - **copy** — this file stands alone as a new canonical document, no merging needed
> - **discard** — this file has no canonical value (outdated, duplicate of something already canonical, or low quality)
>
> Do nothing else.

**Verify:** Each subagent returned valid JSON. Did not modify any files.

---

## Step 4: Present Proposals (YOU do this)

For each file, present the subagent's recommendation:

```
{filename}
  Action:    {action}
  Target:    {target_canonical}
  Rationale: {rationale}
  Conflicts: {conflicts or "none"}
```

After presenting all proposals, ask: "Approve these recommendations, or adjust? You can change any file's action by number."

Wait for the user. Incorporate any adjustments.

---

## Step 5: Draft Canonical Documents (YOU do this)

Group files by their approved action and target:

**For "copy" files:** The file becomes the canonical document as-is. Present it to the user for confirmation:
> "This file will become `{target_canonical}` as-is. Confirm?"

**For "supersede" files:** The file replaces the existing canonical document. Present both side by side (or a diff if they are similar):
> "This file will replace `{existing_canonical}`. Here is what changes. Confirm?"

**For "merge" files:** This is where the creative work happens. Read all files targeted at the same canonical document. Draft a merged document that:
- Preserves the most current and accurate content from each source
- Resolves conflicts between sources (present conflicts to the user for decision)
- Maintains a coherent structure and voice
- Does not lose substantive content without the user's approval

Present the draft:
> "Here is the merged draft for `{target_canonical}`. It combines content from {list of source files}. Review and refine."

**For "discard" files:** Confirm with the user:
> "Discard `{filename}`? Reason: {rationale}. It will be archived with a sidecar."

---

## Step 6: Refine (YOU and the user)

For each merged or superseded document, iterate with the user until they approve. This may take multiple rounds.

- Present the draft
- Accept feedback and revisions
- Produce updated draft
- Repeat until the user says it is approved

**Do not push for approval. Do not ask "is this ready?" The user decides when a document is done.**

When the user approves a document, write it to `corpus/working/{canonical-name}.md`.

---

## Step 7: Save and Checkpoint

After each approved document:

```bash
git add corpus/working/
git commit -m "reconcile: draft approved — {canonical-name}"
```

After all files in the cluster are processed (approved, discarded, or deferred within the cluster):

Update pipeline state:
```yaml
reconcile:
  files_in_staged: {remaining count in corpus/raw/staged/}
  files_in_working: {count in corpus/working/}
```

---

## Step 8: Continue or Finish

If more clusters remain in `corpus/raw/staged/`:

> "{N} clusters remaining in staged. Continue with another cluster?"

If the user wants to continue, return to Step 1.

If the user wants to stop:

Update pipeline state:
```yaml
pipeline:
  step: idle
  active_since: null
  interrupted: false
reconcile:
  status: in-progress
  active_cluster: null
  files_in_staged: {count}
  files_in_working: {count}
```

> "Reconciliation paused. {N} approved documents in corpus/working/ ready for promotion. {M} files remain in staged. Run `/sweetclaude:corpus-reconcile` to continue, or `/sweetclaude:corpus-promote` to finalize approved documents."

If ALL staged files have been processed:

Update pipeline state:
```yaml
pipeline:
  step: idle
  active_since: null
  interrupted: false
reconcile:
  status: complete
  last_run: {ISO 8601 timestamp}
  active_cluster: null
  files_in_staged: 0
  files_in_working: {count of approved documents}
```

```bash
git add .sweetclaude/state/corpus-pipeline.yaml
git commit -m "reconcile: all staged files processed"
```

> "Reconciliation complete. {N} approved documents in corpus/working/ ready for promotion. Run `/sweetclaude:corpus-promote` to finalize them."

---

## Error Handling

**Subagent returns invalid JSON:** Re-run the subagent for that file. If it fails twice, present the file to the user directly without a recommendation.

**File in working/ has no corresponding staged source:** Flag it. It may be from a previous interrupted session. Ask the user what to do.

**User wants to move a file back to staged (change their mind):** Move it back. Update counts. This is normal.

**Merge produces conflicts the user cannot resolve:** Defer the cluster. Move files back to `corpus/raw/staged/`. Set `reconcile.active_cluster = null`.

**Session dies mid-reconcile:** `pipeline.step` will be `reconciling` and `reconcile.active_cluster` will identify the cluster. Files in `corpus/working/` are safe. Next session offers resume or start fresh (Step 0).

**Git commit fails:** Report the error. Approved documents in `corpus/working/` are safe. The commit can be retried manually.
