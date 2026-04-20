---
description: "Rebuild RAG collections from source files. Recovery tool for corrupted embeddings, model changes, or index drift. Deletes and rebuilds from filesystem truth."
---

# SweetClaude Corpus Reindex

Rebuild RAG collections from source files. Use when embeddings are corrupted, lost, or when the embedding model changes.

**Follow these steps exactly as written. Do not skip steps. Do not fast-track.**

---

## Step 0: Preconditions (YOU check this)

**Check SweetClaude is initialized:**

Does `.sweetclaude/state/phase.yaml` exist?

If no:
> "SweetClaude is not set up for this project. Run `/sweetclaude:init` first."

Stop. Do not proceed.

**Check pipeline state:**

Read `.sweetclaude/state/corpus-pipeline.yaml`.

If it does not exist:
> "No corpus pipeline state found. Run `/sweetclaude:corpus-consolidate` first."

Stop.

If `pipeline.step` is not `idle`:
> "Cannot reindex while the pipeline is active. Current state: {pipeline.step} (started {pipeline.active_since}). Wait for it to finish first."

If the user insists:
> "Reindexing while {pipeline.step} is active can corrupt the refined corpus. Original source files will be unaffected, but canonical documents, sidecars, and provenance records may become inconsistent. Type 'I accept the risk of corpus corruption' to proceed."

The user must type the exact phrase. If they do, log the override in `.sweetclaude/state/decision-log.md` and proceed. If not, stop.

**Check RAG tooling is available:**

Check for MCP RAG server (mcp-local-rag or equivalent).

If not available:
> "MCP RAG server not configured. Run `/sweetclaude:rag-index` to set it up first."

Stop.

---

## Step 1: Choose Scope (YOU ask the user)

Use AskUserQuestion:
- "Canonical" — rebuild `{project}-canonical` from `corpus/canonical/`
- "Raw" — rebuild `{project}-raw` from `corpus/raw/inbox/`
- "All" — rebuild both collections

---

## Step 2: Execute Reindex

For each selected collection:

### 2a. Count files

```bash
find corpus/{source_dir}/ -type f | wc -l
```

Report:
> "Reindexing {collection}: {N} files in {source_dir}/. This will delete the existing index and rebuild from scratch."

Use AskUserQuestion:
- "Proceed" — delete and rebuild
- "Cancel" — skip this collection

### 2b. Delete existing collection

Delete the RAG collection via the MCP RAG server.

### 2c. Index all files

Walk the source directory recursively. For each file:
- Skip binary files and files larger than 1MB
- Index into the RAG collection

Report progress every 100 files:
> "Indexed {N}/{total} files..."

### 2d. Report

> "{collection} reindex complete. {N} files indexed from {source_dir}/."

---

## Step 3: Verify

After all selected collections are rebuilt:

> ```
> Reindex Complete
> ════════════════
>
> {collection}: {N} files indexed
> {collection}: {N} files indexed
> ```

---

## Error Handling

**RAG server connection fails:** Report the error. Do not partially index — the old collection was already deleted. The user needs to fix the RAG server and re-run.

**Individual file indexing fails:** Skip the file, report it, continue with remaining files. Log skipped files at the end.

**Large corpus (>1000 files):** Warn the user that this may take several minutes. Do not timeout — let it run.
