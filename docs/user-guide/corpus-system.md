# Corpus Management and Semantic Search

**Version:** 2.1
**Date:** 2026-10-21

---

The corpus system manages the lifecycle of project documents — from messy scattered files to organized, searchable, canonical truth. It exists because real projects accumulate strategy docs, brainstorm exports, meeting notes, research, and session outputs across folders, Claude.ai sessions, and external tools. Without structure, valuable content gets buried, duplicated, or lost.

## Getting Started

Run from any SweetClaude-configured project:

```
/sweetclaude:utils document-corpus
```

A menu appears showing all available modes and the current pipeline status next to each. Pick one option. Each selection routes to exactly one sub-skill, and the menu offers **Set up RAG** until an index exists, then **Update RAG**.

## The Problem It Solves

You have 500 files across three folders. Some are duplicates. Some are drafts superseded by later versions. Some contain a single paragraph worth keeping. Some are canonical. You need to figure out which is which, merge the best parts, and end up with a clean set of go-forward documents that you and your AI tools can actually search.

## The Pipeline

Four steps in a fixed order. Each step checks the pipeline state before it runs and explains what is missing if an earlier step is incomplete. You can proceed anyway by typing the override phrase `I accept the risk of corpus corruption`, and the override is logged in the decision log.

### 1. Consolidate

Point it at one or more directories. It scans every file, computes hashes, collapses duplicates, and copies unique files into `corpus/raw/inbox/`. Originals are never touched. You get a plan showing what it found before anything moves.

### 2. Triage

Classify each inbox file as keep (ready as-is), reconcile (needs merging with other files), discard (not useful), or defer (skip for now). Works in batch — you can classify by group, by file, or bulk. Classified files move to `corpus/raw/staged/`. Discards go to archive with a sidecar explaining why.

### 3. Reconcile

The creative step. Pick a cluster of related staged files. An AI subagent reads each file and proposes an action (merge, supersede, copy, discard) against existing canonical documents. You review the proposals, then work together to draft a merged canonical document. Iterate until you approve it. Approved documents land in `corpus/working/`.

### 4. Promote

The mechanical step. Takes approved documents from `corpus/working/` and finalizes them: writes provenance sidecars tracing every canonical document back to its source files, archives the source files, moves the canonical document to `corpus/canonical/`, and git commits everything.

## Why the Steps Are Gated

The skill explains this at each gate if you try to skip ahead, and asks for the override phrase before it lets you continue. Here is the short version:

**Skipping consolidate:** You start triaging the same file multiple times under different names. Deduplication happens at consolidate — without it, you create duplicate canonical documents.

**Skipping triage:** Reconcile gets files it should have discarded. The AI tries to merge a discarded draft with a canonical document and produces something worse than either.

**Skipping reconcile and going straight to RAG:** You index raw, unreconciled files. RAG cannot distinguish a draft from an authoritative document — it returns whichever chunk matches the query embedding, regardless of quality. You get confident-sounding answers from stale or superseded content.

## Semantic Search (RAG)

### Set Up RAG

After promoting canonical documents, select **Set up RAG** from the menu. This:
- Installs [mcp-local-rag](https://www.npmjs.com/package/mcp-local-rag) if not already present
- Creates `.mcp.json` wiring the RAG server to your project
- Downloads the embedding model once (~90MB), then works offline
- Indexes every supported document type in the project into a per-project vector database

By default it indexes every `.pdf`, `.docx`, `.txt` and `.md` file in the project, minus default excludes such as `.git`, `node_modules`, virtual environments, build output, `scratch`, `archive`, `drafts`, backups and `corpus/raw/`. Choose the canonical-only option during setup to restrict indexing to `docs/`, `strategy/` and `corpus/canonical/`.

No external services, no API keys, no data leaving your machine.

### Reindex

Use **Reindex RAG** when embeddings are corrupted or the model changes. Asks you to choose a scope and rebuilds from scratch. The scopes are **Canonical** (rebuild the canonical collection from `corpus/canonical/`), **Raw** (rebuild the raw collection from `corpus/raw/inbox/`) or **All** (rebuild both). If the pipeline is not idle, reindex warns and requires the override phrase.

## Pipeline Status

Select **Status** from the menu at any time — it is never gated. Shows file counts per directory, step completion, any anomalies, and what to do next.

## Where Things Live

| Directory | Contents |
|---|---|
| `corpus/raw/inbox/` | Deduplicated source files, not yet classified |
| `corpus/raw/staged/` | Classified files, ready for reconciliation |
| `corpus/working/` | Approved drafts, waiting for promotion |
| `corpus/canonical/` | Finalized documents (strategic, product, design, research, operations) |
| `corpus/archive/` | Retired source files with provenance sidecars |

## Key Properties

- **Non-destructive.** Originals are never deleted.
- **Resumable.** Every step can be paused and continued.
- **Crash-recoverable.** The state file detects interrupted operations.
- **Auditable.** Every canonical document traces back to source files via sidecars.
- **Filesystem is ground truth.** The state file coordinates, but if it disappears you can rebuild from the directory structure.

## Output Formatting

Corpus operations use a standardized symbol vocabulary:

| Symbol | Meaning |
|---|---|
| `✓` | Completed / processed / in sync |
| `✗` | Failed / blocked |
| Warning triangle | Warning / needs attention |
| `→` | Next action / recommendation |
