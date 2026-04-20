---
description: "Finalize approved documents from corpus/working/. Record provenance sidecars, archive source files, move to corpus/canonical/, index into RAG. Mechanical, atomic — the audit trail step."
---

# SweetClaude Corpus Promote

Finalize approved documents from `corpus/working/`. Move them to `corpus/canonical/`, write provenance sidecars, archive source files, index into RAG, and commit. This is the mechanical finalization step — no creative decisions.

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

If `reconcile.status` is not `complete` and `reconcile.status` is not `in-progress`:
> "Cannot run corpus-promote. The corpus pipeline requires reconcile to complete first. Current state: reconcile is {reconcile.status}."

If the user insists:
> "Running corpus-promote before reconciliation is complete can corrupt the refined corpus. Original source files will be unaffected, but canonical documents, sidecars, and provenance records may become inconsistent. Type 'I accept the risk of corpus corruption' to proceed."

The user must type the exact phrase. If they do, log the override in `.sweetclaude/state/decision-log.md` and proceed. If not, stop.

If `pipeline.step` is not `idle`:
> "Cannot run corpus-promote. The pipeline is currently running {pipeline.step} (started {pipeline.active_since}). Wait for it to finish or resolve the interrupted operation."

Apply the same override protocol if the user insists.

**Check working directory has files:**

Does `corpus/working/` contain files?

If empty:
> "corpus/working/ is empty. No approved documents to promote. Run `/sweetclaude:corpus-reconcile` first."

Stop.

**Set pipeline state:**
```yaml
pipeline:
  step: promoting
  active_since: {ISO 8601 timestamp}
  interrupted: false
```

**Ensure canonical and archive directories exist:**
```bash
mkdir -p {project-path}/corpus/canonical/{strategic,product,design,research,operations}
mkdir -p {project-path}/corpus/archive
```

---

## Step 1: Inventory Working Documents (SUBAGENT)

Spawn a subagent:

> Scan `corpus/working/` for all files. For each file:
> - Full path
> - File size
> - First 10 lines of content
> - Content type (determine from content: strategy, product, design, research, operations)
>
> Also scan `corpus/raw/staged/` for any `.triage.json` metadata files that reference the source files that produced these working documents. Collect the source file paths from the metadata.
>
> Report for each working document:
> ```
> {filename}
>   Content type: {type}
>   Size: {size}
>   Suggested target: corpus/canonical/{subdir}/{name}
>   Source files: [{list of original staged/source files if traceable}]
> ```
>
> Do nothing else.

**Verify:** Subagent returned inventory. Did not modify any files.

---

## Step 2: Confirm Promotion Plan (YOU present to user)

Present the promotion plan:

```
Promotion Plan
══════════════

{filename} → corpus/canonical/{subdir}/{name}
  Sources: {list of original source files, or "created during reconciliation"}

{filename} → corpus/canonical/{subdir}/{name}
  Sources: {list}
```

**Canonical target mapping:**

| Content type | Target directory |
|---|---|
| Concept, positioning, vision, pain thesis, ICP, competitive analysis, market messaging, narrative arc | corpus/canonical/strategic/ |
| Academic research, publication strategy, research agenda | corpus/canonical/research/ |
| Meeting prep, debriefs, stakeholder profiles | corpus/canonical/operations/ |
| Product brief, PRD, user stories, success criteria | corpus/canonical/product/ |
| Architecture, tech spec, data model, API design, UX design | corpus/canonical/design/ |

Ask: "Confirm this promotion plan? You can adjust any target path."

Wait for the user. Incorporate adjustments.

---

## Step 3: Execute Promotion (YOU do this — one document at a time)

For each document in the approved plan, execute atomically:

### 3a. Check for collisions

Does a file already exist at the target path in `corpus/canonical/`?

If yes:

Use AskUserQuestion:
- "Replace" — overwrite the existing canonical document
- "Rename" — save the new document with a version suffix (e.g., `-v2`)
- "Skip" — do not promote this document
- "Cancel" — stop the entire promotion

If "Replace", back up the existing file:
```bash
cp corpus/canonical/{subdir}/{name} corpus/canonical/{subdir}/{name}.bak
```

### 3b. Write provenance sidecars

For each source file that was reconciled into this document, create a sidecar:

```json
{
  "source_path": "corpus/archive/{date}-reconcile/{original_filename}",
  "content_hash": "sha256:{compute hash of the source file}",
  "reconciled_at": "{ISO 8601 timestamp}",
  "reconciled_by": "{git user from git config}",
  "canonical_documents": ["corpus/canonical/{subdir}/{name}"],
  "action": "{merge|supersede|copy|discard — from reconcile session}",
  "notes": "{from reconcile session, or empty}"
}
```

Write sidecars to `corpus/archive/{date}-reconcile/`.

### 3c. Move canonical document

```bash
mv corpus/working/{name} corpus/canonical/{subdir}/{name}
```

### 3d. Archive source files

Move the original source files (from `corpus/raw/staged/` if they still exist there, or from wherever they are) alongside their sidecars:

```bash
mkdir -p corpus/archive/{date}-reconcile/
mv {source_files} corpus/archive/{date}-reconcile/
mv {triage_metadata_files} corpus/archive/{date}-reconcile/
```

### 3e. Git commit (per document)

```bash
git add corpus/canonical/{subdir}/{name} corpus/archive/{date}-reconcile/
git commit -m "promote: {name} → corpus/canonical/{subdir}/"
```

### 3f. Index into RAG

Index the canonical document into the `{project}-canonical` RAG collection (incremental).

If RAG tooling is not available:
> "RAG indexing skipped — MCP RAG server not configured. Run `/sweetclaude:corpus-reindex` later."

Continue with the next document regardless.

---

## Step 4: Update State (YOU do this)

**Update corpus.yaml promotions list:**

Append to the `promotions:` section in `.sweetclaude/state/corpus.yaml`:

```yaml
- timestamp: {ISO 8601}
  source: corpus/working/{name}
  target: corpus/canonical/{subdir}/{name}
  action: {action from reconcile}
  indexed: {true|false}
```

**Update pipeline state:**

```yaml
pipeline:
  step: idle
  active_since: null
  interrupted: false
promote:
  status: complete
  last_run: {ISO 8601 timestamp}
  files_in_working: 0
  files_promoted: {count}
```

**Git commit state:**

```bash
git add .sweetclaude/state/corpus-pipeline.yaml .sweetclaude/state/corpus.yaml
git commit -m "promote: update pipeline state and corpus.yaml"
```

---

## Step 5: Report

```
Promotion Complete
══════════════════

Documents promoted: {count}
  {name} → corpus/canonical/{subdir}/
  {name} → corpus/canonical/{subdir}/

Sources archived:   {count} files in corpus/archive/{date}-reconcile/
Sidecars written:   {count}
RAG indexed:        {count indexed} / {count total}

Pipeline status:    idle
```

If all pipeline steps are now complete (consolidate, triage, reconcile, promote):
> "Corpus pipeline complete. All source files have been processed into canonical documents with full provenance. Run `/sweetclaude:corpus-status` to see the full picture."

---

## Error Handling

**Move fails (permissions, disk):** Report the specific file and error. Do not continue with remaining documents — the atomic guarantee means partial state for one document is a problem. Ask the user to resolve and re-run.

**Sidecar write fails:** The canonical document move has not happened yet (sidecars are written first). Report and stop for this document. Skip to the next document if the user approves.

**Git commit fails:** The files are already in their final locations. Report the error. The commit can be retried manually. Continue with remaining documents.

**RAG indexing fails:** Not fatal. The canonical document is in place and committed. Report the failure. Corpus preflight will catch unindexed canonical documents on next session.

**Source files already archived (not in staged):** This can happen if reconcile archived them or if the pipeline was partially completed. Write the sidecar anyway with the archive path. Skip the archive move for that source file.

**Session dies mid-promote:** `pipeline.step` will be `promoting`. Some documents may be promoted, some may still be in `corpus/working/`. Next run of promote picks up the remaining files in `corpus/working/`.
