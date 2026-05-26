# Corpus Management and Semantic Search

**Version:** 2.0
**Date:** 2026-04-27

---

The corpus system manages the lifecycle of project documents — from messy scattered files to organized, searchable, canonical truth. It exists because real projects accumulate strategy docs, brainstorm exports, meeting notes, research, and session outputs across folders, Claude.ai sessions, and external tools. Without structure, valuable content gets buried, duplicated, or lost.

## Getting Started

Run from any SweetClaude-configured project:

```
/sweetclaude:document-corpus
```

A menu appears showing all available modes and the current pipeline status next to each. Pick one or more.

## The Problem It Solves

You have 500 files across three folders. Some are duplicates. Some are drafts superseded by later versions. Some contain a single paragraph worth keeping. Some are canonical. You need to figure out which is which, merge the best parts, and end up with a clean set of go-forward documents that you and your AI tools can actually search.

## The Pipeline

Four steps, strictly ordered, enforced by a state machine.

### 1. Consolidate

Point it at one or more directories. It scans every file, computes hashes, collapses duplicates, and copies unique files into `corpus/raw/inbox/`. Originals are never touched. You get a plan showing what it found before anything moves.

### 2. Triage

Classify each inbox file as keep (ready as-is), reconcile (needs merging with other files), discard (not useful), or defer (skip for now). Works in batch — you can classify by group, by file, or bulk. Classified files move to `corpus/raw/staged/`. Discards go to archive with a sidecar explaining why.

### 3. Reconcile

The creative step. Pick a cluster of related staged files. An AI subagent reads each file and proposes an action (merge, supersede, copy, discard) against existing canonical documents. You review the proposals, then work together to draft a merged canonical document. Iterate until you approve it. Approved documents land in `corpus/working/`.

### 4. Promote

The mechanical step. Takes approved documents from `corpus/working/` and finalizes them: writes provenance sidecars tracing every canonical document back to its source files, archives the source files, moves the canonical document to `corpus/canonical/`, and git commits everything.

## Why You Cannot Skip Steps

The skill explains this at each gate if you try to skip, but here is the short version:

**Skipping consolidate:** You start triaging the same file multiple times under different names. Deduplication happens at consolidate — without it, you create duplicate canonical documents.

**Skipping triage:** Reconcile gets files it should have discarded. The AI tries to merge a discarded draft with a canonical document and produces something worse than either.

**Skipping reconcile and going straight to RAG:** You index raw, unreconciled files. RAG cannot distinguish a draft from an authoritative document — it returns whichever chunk matches the query embedding, regardless of quality. You get confident-sounding answers from stale or superseded content.

## Semantic Search (RAG)

### Set Up RAG

After promoting canonical documents, select **Set up RAG** from the menu. This:
- Installs [mcp-local-rag](https://www.npmjs.com/package/mcp-local-rag) if not already present
- Creates `.mcp.json` wiring the RAG server to your project
- Downloads the embedding model once (~90MB), then works offline
- Indexes your canonical documents into a per-project vector database

No external services, no API keys, no data leaving your machine. Supports PDF, Word (.docx), markdown, and text files.

### Reindex

Use **Reindex RAG** when embeddings are corrupted or the model changes. Lets you scope the rebuild (one collection, several, or everything) and rebuilds from scratch.

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
| `⚠` | Warning / needs attention |
| `→` | Next action / recommendation |
