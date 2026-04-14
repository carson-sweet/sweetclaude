# Corpus Management Design — 2026-04-14

**Version:** 1.0
**Status:** Approved design, not yet implemented
**Authors:** Carson Sweet, Claude (Claude Code instance), Claude (claude.ai instance)

---

## Problem

Projects accumulate strategic documents, brainstorming outputs, research files, meeting notes, and session exports across multiple directories, Claude.ai sessions, and external tools. These files are duplicated, unversioned, unorganized, and unsearchable. There is no clean separation between raw source material, work in progress, and approved canonical documents.

SweetClaude needs a structured corpus management layer that separates raw ingestion from reconciliation from canonical truth, with full provenance tracking and semantic search.

## Directory Structure

All corpus management lives under `corpus/` at the project root. This is the definitive layout.

```
~/dev/<project>/
├── [existing code — src/, tests/, package.json, whatever]
├── CLAUDE.md
├── .sweetclaude/                     # framework state ONLY — no content documents
│   ├── state/
│   │   ├── phase.yaml
│   │   ├── project.yaml
│   │   ├── corpus.yaml              # corpus policy, collection config, archive tracking
│   │   ├── decision-log.md
│   │   ├── assumption-register.md
│   │   ├── improvement-register.md
│   │   └── scope-changes.md
│   └── traceability/
│       ├── requirements-map.md
│       └── ripple-map.md
├── strategy/                         # active strategic workspace (skills write here)
│   ├── concept/
│   ├── pain-thesis/
│   ├── ideal-customer-profile/
│   ├── competitive-analysis/
│   ├── academic-research/
│   ├── meeting-prep/
│   ├── narrative-arc/
│   └── market-messaging/
├── corpus/                           # all corpus management lives here
│   ├── raw/                          # ingested, not yet processed
│   │   ├── inbox/                    # new arrivals, pre-triage
│   │   └── staged/                   # triaged, awaiting reconciliation
│   ├── working/                      # actively being reconciled — intermediate saves, drafts
│   ├── canonical/                    # approved, go-forward corpus
│   │   ├── strategic/                # promoted from strategy/ (not "strategy/" — different name)
│   │   ├── product/                  # product briefs, PRDs, success criteria, positioning
│   │   ├── design/                   # architecture, tech spec, data model, API design
│   │   ├── research/                 # academic papers, lit reviews, market research
│   │   └── operations/               # meeting outputs, debriefs, stakeholder profiles
│   ├── archive/                      # retired sources, reconciliation complete
│   │   └── <YYYY-MM-DD>-<source>/
│   │       ├── README.md             # per-source archive notice
│   │       └── [sidecars live here with archived files]
│   └── rag-system/                   # embeddings, db files, indexes — tracked in git, excluded from distribution
│       ├── canonical/                # default query target
│       └── raw/                      # opt-in for historical research or reconciliation work
└── docs/                             # project documentation (specs, stories, user-facing docs)
```

### Key Design Decisions

- **`corpus/` contains everything.** Raw, working, canonical, archive, and RAG all live under one root. No scattered directories.
- **`canonical/strategic/`** not `canonical/strategy/`. Differentiates from the active `strategy/` workspace at project root.
- **`.sweetclaude/` is state only.** No content documents — no specs/, stories/, brainstorm/. Framework state and traceability only.
- **`strategy/` is the active workspace.** SweetClaude skills write strategic working documents here. When approved, they promote to `corpus/canonical/strategic/`.
- **`docs/` is for project documentation.** Specs, stories, and user-facing docs during development. Promote to `corpus/canonical/product/` or `corpus/canonical/design/` when approved.
- **`rag-system/` is tracked in git for backup.** Not gitignored. Excluded from distribution packages via `.npmignore` or equivalent. A prominent warning during init tells the user to remove `.sweetclaude/`, `strategy/`, and `corpus/` before pushing to a public repo or deploying.
- **`strategy/reconciliation/` is gone.** File onboarding during init copies into `corpus/raw/inbox/` instead.

### State Tracking Hierarchy

1. **Filesystem location is primary.** A file in `corpus/raw/inbox/` is "ingested." In `corpus/raw/staged/` is "triaged." In `corpus/working/` is "being reconciled." In `corpus/archive/` with a sidecar is "done."
2. **Sidecars are the audit trail.** A `.reconciled.json` sidecar documents what happened to a file when it was processed. Sidecars live in `corpus/archive/` alongside the retired source files.
3. **`corpus.yaml` is collection-level config.** Which sources have been retired, reconciliation mode, RAG exclusions. Not per-file state.

If `corpus.yaml` disappears, rebuild it by walking the directory tree. If a sidecar goes missing, the file is still findable but provenance is lost for that file. Filesystem is the most durable layer.

---

## Four Skills

### 1. Consolidate (`/sweetclaude:consolidate`)

**Purpose:** Scan directories of messy files, deduplicate, classify, copy into `corpus/raw/inbox/`. Mechanical — no synthesis, no creative work.

**Input:** One or more directory paths containing source material.

**Process:**
1. Check preconditions (SweetClaude initialized, corpus/ exists or create it)
2. Scan and hash all files (exclude binary, large files, corpus/sweetclaude/strategy dirs)
3. Token estimation (optional — size_bytes/4 by default, precise counting on request)
4. Deduplication analysis (SHA-256 grouping, designate canonical copy per group)
5. Generate consolidation plan document at `.sweetclaude/state/consolidate-plan.md`
6. User reviews and approves the plan
7. Execute copy in batches of 500 files with progress reporting (originals untouched)
8. Offer RAG indexing into raw collection (opt-in, not automatic)
9. Update `corpus.yaml` and git commit

**Output:** Deduplicated files in `corpus/raw/inbox/<source_name>/`, preserving directory structure within each source. Plan document. Optional RAG index of raw collection.

**Key properties:**
- Non-destructive — copies, never moves or deletes source files
- Idempotent — re-running produces the same result
- Plan-as-gate — nothing moves without user approval
- Plan-as-recovery — if interrupted, the plan tells the next session what was intended
- Batched execution with progress reporting for large corpora

### 2. Triage (`/sweetclaude:triage`)

**Purpose:** Classify files in `corpus/raw/inbox/` for reconciliation. Lightweight batch review — no synthesis.

**Input:** Files in `corpus/raw/inbox/`.

**Process:**
1. For each file (or batch), classify as: keep-as-is / needs-reconciliation / discard / defer
2. Keep-as-is → move to `corpus/raw/staged/`
3. Discard → move to `corpus/archive/` with a discard sidecar (`action: discarded`, with rationale)
4. Defer → stays in `corpus/raw/inbox/` with a deferral note
5. Needs-reconciliation → move to `corpus/raw/staged/` with metadata indicating reconciliation needed

**Key properties:**
- Fast — most files classified in seconds because duplicates already collapsed by consolidate
- User-driven — human judgment required for classification
- Batch-friendly — can process many files per session
- Separate from reconcile because triage is a batch activity, reconcile is a per-topic deep activity

### 3. Reconcile (`/sweetclaude:reconcile`)

**Purpose:** Take staged files and work with the user to produce canonical documents. The heavy creative work.

**Input:** Files in `corpus/raw/staged/` (individually or as a related cluster).

**Process:**
1. Select a file or cluster of related files from `corpus/raw/staged/`
2. Move to `corpus/working/` for active work
3. Analyze content against existing canonical documents in `corpus/canonical/`
4. Work with the user to produce a canonical document (or update an existing one)
5. Write the canonical document to `corpus/canonical/<subdir>/`
6. Index into canonical RAG collection (incremental)
7. Write sidecars for each processed source file
8. Move processed source files + sidecars to `corpus/archive/<date>-<source>/`
9. Git commit

**Subagent contract per file:**
- Subagent: "Read this staged file and these canonical candidates. Propose an action (merge/supersede/copy/discard) with rationale. Return JSON: {source, action, target_canonical, rationale, conflicts: []}. Do nothing else."
- Main agent presents proposal to user, user approves or modifies, main agent applies.

**Key properties:**
- Per-topic, session-length activity (not batch)
- Produces canonical documents directly — no separate promotion step needed
- Full provenance via sidecars
- Supervised execution with scoped subagents

### 4. Promote (`/sweetclaude:promote`)

**Purpose:** Move a finished document from `strategy/` or `docs/` to `corpus/canonical/`. For net-new work that did not come from raw corpus reconciliation.

**Input:** Path to a document in `strategy/` or `docs/`.

**Process:**
1. Identify source document and validate it is in `strategy/` or `docs/`
2. Determine canonical target subdirectory (based on source path, user confirms)
3. Show promotion plan (source, target, action)
4. Execute move (git mv if tracked)
5. Index into canonical RAG collection (incremental)
6. Update `corpus.yaml` promotions list
7. Git commit

**Mapping:**

| Source | Canonical target |
|---|---|
| strategy/concept/ | corpus/canonical/strategic/ |
| strategy/pain-thesis/ | corpus/canonical/strategic/ |
| strategy/ideal-customer-profile/ | corpus/canonical/strategic/ |
| strategy/competitive-analysis/ | corpus/canonical/strategic/ |
| strategy/market-messaging/ | corpus/canonical/strategic/ |
| strategy/narrative-arc/ | corpus/canonical/strategic/ |
| strategy/academic-research/ | corpus/canonical/research/ |
| strategy/meeting-prep/ | corpus/canonical/operations/ |
| docs/specs/ | corpus/canonical/product/ or corpus/canonical/design/ |
| docs/architecture/ | corpus/canonical/design/ |
| docs/stories/ | corpus/canonical/product/ |

**Key properties:**
- Small, fast operation — single file
- Git mv preserves history
- Handles name collisions (backup existing, rename, or cancel)
- Logs promotion in corpus.yaml for auditability

---

## Supporting Infrastructure

### Corpus Configuration (`corpus.yaml`)

Lives at `.sweetclaude/state/corpus.yaml`.

```yaml
corpus_policy:
  default_collection: canonical
  raw_access: on_request           # on_request | open | blocked
  reconciliation_mode: active      # active | paused | complete

collections:
  canonical:
    path: corpus/canonical/
    rag_collection: <project>-canonical
  raw:
    path: corpus/raw/
    rag_collection: <project>-raw

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

archive_sources:
  - date: 2026-04-20
    source: syncog-archive
    original_path: /Users/carsonsweet/dev/syncog-archive
    reconciliation_complete: true

promotions:
  - timestamp: 2026-04-14T15:30:00Z
    source: strategy/concept/syncog-concept.md
    target: corpus/canonical/strategic/syncog-concept.md
    action: new
    indexed: true

last_consolidate:
  timestamp: 2026-04-14T12:00:00Z
  sources: [/Users/carsonsweet/dev/syncog-general, /Users/carsonsweet/dev/syncog-archive]
  files_copied: 847
  files_indexed: 812
  tokens_retained: 4200000
  plan_document: .sweetclaude/state/consolidate-plan.md
```

### Sidecar Format (`.reconciled.json`)

One sidecar per processed source file. Lives in `corpus/archive/` alongside the retired file.

```json
{
  "source_path": "corpus/archive/2026-04-20-syncog-general/prd-syncog-2026-04-08.md",
  "content_hash": "sha256:...",
  "reconciled_at": "2026-04-14T15:30:00Z",
  "reconciled_by": "carson",
  "canonical_documents": ["corpus/canonical/product/prd-syncog.md"],
  "action": "merged",
  "notes": "Sections 1-3 merged; section 4 (abandoned auth model) discarded."
}
```

Action enum: `merged` | `superseded` | `copied` | `discarded`

Discarded files still get a sidecar — the decision is auditable.

### Corpus Preflight Check

Runs on session start via the existing session-preflight hook. Checks for corpus health issues.

**Critical (halt session):**
1. `corpus.yaml` references files that do not exist (archive_sources pointing to missing dirs)
2. Uncommitted changes in `corpus/archive/` or `corpus/canonical/`

**Warning (report, continue):**
3. Files in `corpus/working/` older than 24 hours (abandoned reconciliation)
4. Sidecars pointing to nonexistent canonical documents
5. Canonical documents with no sidecar and no promotions entry (created outside workflow)
6. Files in `corpus/raw/staged/` with no triage metadata

**Info (verbose only):**
7. Raw RAG collection size vs. `corpus/raw/inbox/` file count mismatch
8. Canonical RAG collection size vs. `corpus/canonical/` file count mismatch

Output is compact by default:
```
SweetClaude corpus preflight:
  Critical: 0
  Warning:  2
  Info:     1
```

Details available via `/sweetclaude:corpus-status`.

### Reindex Utility (`/sweetclaude:reindex`)

Rebuilds RAG collections from source files. For recovery when embeddings are corrupted, lost, or when the embedding model changes.

- `/sweetclaude:reindex canonical` — walks `corpus/canonical/`, rebuilds canonical collection
- `/sweetclaude:reindex raw` — walks `corpus/raw/inbox/`, rebuilds raw collection
- `/sweetclaude:reindex all` — both

### RAG Collections

Two physical collections, always. Never one collection with metadata filtering.

- `<project>-canonical` — default query target. Contains approved, go-forward documents.
- `<project>-raw` — opt-in for historical research or reconciliation work. Contains raw ingested files.

Physical separation prevents accidentally mixing historical raw material with canonical truth.

Collections created lazily on first write. The MCP RAG server creates the collection on first ingest call.

### Canonical RAG Population Points

Three skills write to the canonical RAG collection:
1. **Reconcile** — when a reconciliation session completes and produces a canonical doc
2. **Promote** — when a draft is promoted from strategy/ or docs/
3. **Reindex** — manual rebuild of the entire collection

Each write is incremental (single doc) except reindex which is a full rebuild.

Write order: file to disk → git commit → RAG index. If indexing fails, the file exists and the preflight catches the missing index on next session.

---

## Failure Recovery

### Atomic Operations

Every state transition follows dependency order so partial failure leaves a recoverable state:

1. Write sidecar in `corpus/working/` next to the file
2. Write canonical document to `corpus/canonical/`
3. Git add sidecar + canonical
4. Git commit
5. Move source file + sidecar to `corpus/archive/`
6. Git add the move
7. Git commit
8. Index canonical doc into RAG

If interrupted between steps 4 and 7: reconciliation is committed but archive move is pending. Sidecar says "done" but file is still in working/. Recovery: finish the move.

If interrupted between steps 7 and 8: file is archived and committed but not indexed. Preflight catches canonical docs not in RAG.

### Session-Start Recovery

The corpus preflight hook scans for orphans and half-done transitions. Reports issues, does not auto-fix. User decides.

### Plan-as-Recovery

The consolidation plan document (`.sweetclaude/state/consolidate-plan.md`) survives session death. Next session can diff the plan against what actually landed in `corpus/raw/inbox/` and offer to resume.

### Git Checkpoints

Extended git-checkpoint hook commits at corpus state transitions (not just phase transitions):
- Per consolidation run
- Per batch triage session
- Per reconciliation session
- Per promotion

Recovery via `git log` and `git reset` for any committed state.

---

## Distribution Warning

During init, SweetClaude creates a `.npmignore` (or equivalent for the project ecosystem) that excludes:
- `.sweetclaude/`
- `strategy/`
- `corpus/`

A prominent warning is shown:

> "These directories contain project strategy and corpus data. Remove `.sweetclaude/`, `strategy/`, and `corpus/` before pushing to a public repo or deploying to production."

The RAG system (`corpus/rag-system/`) is tracked in git for backup but must not ship in releases.

---

## Cross-Project Corpus

Each project is an island for now. If shared content matters later, add `~/dev/_shared/canonical/` with its own RAG collection queried alongside project canonical on opt-in. Not designed now — room left for it.

---

## Implementation Order

1. Integrate consolidate skill (with five modifications: optional token estimation, opt-in RAG, corpus/sweetclaude/strategy exclusions, batched copies, plan-as-recovery)
2. Integrate promote skill
3. Add corpus preflight to session-preflight hook
4. Update init skill to create `corpus/` structure and warn about distribution
5. Test consolidate on SynCog (98M raw tokens, ~22K files)
6. Iterate on triage and reconcile based on what consolidate produces
7. Add reindex utility skill
8. Add corpus-status detail skill

---

## Open Items (Deferred)

- Triage skill detailed design (after consolidate tested)
- Reconcile skill detailed design (after triage tested)
- Corpus-status display skill
- Reindex utility skill
- Archive-retire skill (moves entire original source directories to corpus/archive/ after full reconciliation)
- Cross-project shared canonical
