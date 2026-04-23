# Corpus Management System

**Version:** 1.1
**Date:** 2026-04-23

---

The corpus system manages the lifecycle of project documents — from messy scattered files to organized, searchable, canonical truth. It exists because real projects accumulate strategy docs, brainstorm exports, meeting notes, research, and session outputs across folders, Claude.ai sessions, and external tools. Without structure, valuable content gets buried, duplicated, or lost.

## The Problem It Solves

You have 500 files across three folders. Some are duplicates. Some are drafts superseded by later versions. Some contain a single paragraph worth keeping. Some are canonical. You need to figure out which is which, merge the best parts, and end up with a clean set of go-forward documents that you and your AI tools can actually search.

## The Pipeline

Four steps, strictly ordered, enforced by a state machine.

### 1. Consolidate (`/sweetclaude:corpus-consolidate`)

Point it at one or more directories. It scans every file, computes hashes, collapses duplicates, and copies unique files into `corpus/raw/inbox/`. Originals are never touched. You get a plan showing what it found before anything moves.

### 2. Triage (`/sweetclaude:corpus-triage`)

Classify each inbox file as keep (ready as-is), reconcile (needs merging with other files), discard (not useful), or defer (skip for now). Works in batch — you can classify by group, by file, or bulk. Classified files move to `corpus/raw/staged/`. Discards go to archive with a sidecar explaining why.

### 3. Reconcile (`/sweetclaude:corpus-reconcile`)

The creative step. Pick a cluster of related staged files. An AI subagent reads each file and proposes an action (merge, supersede, copy, discard) against existing canonical documents. You review the proposals, then work together to draft a merged canonical document. Iterate until you approve it. Approved documents land in `corpus/working/`.

### 4. Promote (`/sweetclaude:corpus-promote`)

The mechanical step. Takes approved documents from `corpus/working/` and finalizes them: writes provenance sidecars tracing every canonical document back to its source files, archives the source files, moves the canonical document to `corpus/canonical/`, indexes it into RAG for semantic search, and git commits everything. This is the audit trail.

## Pipeline Enforcement

You cannot run triage before consolidate completes. You cannot reconcile before triage completes. You cannot promote before reconcile completes. Attempting to skip a step produces a hard stop. If you insist, you must type an exact acknowledgment phrase accepting the risk of corpus corruption — and it gets logged.

## Where Things Live

| Directory | Contents |
|---|---|
| `corpus/raw/inbox/` | Deduplicated source files, not yet classified |
| `corpus/raw/staged/` | Classified files, ready for reconciliation |
| `corpus/working/` | Approved drafts, waiting for promotion |
| `corpus/canonical/` | Finalized documents (strategic, product, design, research, operations) |
| `corpus/archive/` | Retired source files with provenance sidecars |

## Utility Skills

**`/sweetclaude:corpus-reindex`** rebuilds RAG collections from the filesystem when embeddings are corrupted or the model changes.

**`/sweetclaude:corpus-status`** shows where the pipeline stands — file counts, step status, warnings, and what to do next. Status is always available, never gated.

## Key Properties

- **Non-destructive.** Originals are never deleted.
- **Resumable.** Every step can be paused and continued.
- **Crash-recoverable.** The state file detects interrupted operations.
- **Auditable.** Every canonical document traces back to source files via sidecars.
- **Filesystem is ground truth.** The state file coordinates, but if it disappears you can rebuild from the directory structure.

## Output Formatting

Corpus skills use a standardized symbol vocabulary in their output:

| Symbol | Meaning |
|---|---|
| `✓` | Completed / processed / in sync |
| `✗` | Failed / blocked |
| `⚠` | Warning / needs attention |
| `→` | Next action / recommendation |

Report headers use `═══` decorative lines for visual separation. Status and completion reports use these symbols consistently so you can scan results at a glance.
