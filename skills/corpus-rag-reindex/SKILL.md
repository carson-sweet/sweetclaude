---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:corpus-rag-reindex
user-invocable: true
description: "Rebuild RAG collections from source files. Use when embeddings are corrupted, lost, or when the embedding model changes. Recovery tool, not a shortcut around the pipeline — if your source files are messy, the rebuilt index will be messy."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Run `/sweetclaude:setup` first." Then stop.
</preflight-guard>

# Reindex RAG

Rebuild RAG collections from source files. Use when embeddings are corrupted, lost, or when the embedding model changes. This is a recovery tool, not a shortcut around the pipeline — if your source files are messy, the rebuilt index will be messy.

## Step X0: Preconditions

Read `corpus-pipeline.yaml`. If `pipeline.step` is not `idle`: warn and require override phrase.

Check RAG tooling is available. If not: "MCP RAG server not configured. Run `/sweetclaude:corpus-rag-setup` first."

## Step X1: Choose scope

AskUserQuestion:
- "Canonical" — rebuild `{project}-canonical` from `corpus/canonical/`
- "Raw" — rebuild `{project}-raw` from `corpus/raw/inbox/`
- "All" — rebuild both

## Step X2: Execute reindex

For each selected collection:

Count files: `find corpus/{source_dir}/ -type f | wc -l`

Warn: "This will delete the existing index and rebuild from scratch. {N} files." AskUserQuestion: Proceed / Cancel.

Delete existing collection via MCP RAG server. Walk source directory recursively, skip binaries and files >1MB, index each file. Report progress every 100 files.

## Step X3: Report

```
Reindex Complete
════════════════

✓ {collection}: {N} files indexed
✓ {collection}: {N} files indexed
```

**Error handling:**
- RAG server connection fails: report and stop. The old collection was already deleted — the user must fix the RAG server and re-run.
- Individual file indexing fails: skip the file, continue, list skipped files at the end.
