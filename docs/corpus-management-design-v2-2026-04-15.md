# Corpus Management Design — 2026-04-15

**Version:** 2.0
**Status:** Approved design, partially implemented
**Authors:** Carson Sweet, Claude (Claude Code instance)
**Supersedes:** corpus-management-design-v1-2026-04-14.md

---

## Changes from v1

- Pipeline state machine with enforced ordering
- Hard stop on out-of-order execution with explicit override protocol
- Reconcile split into creative work (reconcile) and mechanical finalization (promote)
- All project documents must go through the pipeline — no separate "net-new" path
- Promote is now the final pipeline step, not an independent operation
- Updated skill naming to `corpus-` prefix

---

## Pipeline

Four steps, strictly ordered:

```
consolidate → triage → reconcile → promote
```

**Consolidate.** Scan source directories, hash every file, deduplicate, copy unique files into `corpus/raw/inbox/`. Mechanical. No synthesis.

**Triage.** Classify files in `corpus/raw/inbox/` as keep-as-is, needs-reconciliation, discard, or defer. Move classified files to `corpus/raw/staged/` or `corpus/archive/`. User-driven batch decisions.

**Reconcile.** Take staged files and work with the user to produce canonical documents. Draft a canonical document, iterate until the user approves. Approved documents land in `corpus/working/`. This is the creative work — session-length, iterative, potentially multi-session.

**Promote.** Finalize an approved document from `corpus/working/`. Record provenance sidecars, archive source files, move canonical document to `corpus/canonical/`, index into RAG, update corpus.yaml, git commit. Mechanical, atomic. The audit trail step.

### Net-New Documents

Documents created directly in `strategy/` or `docs/` (not from raw corpus reconciliation) still go through the pipeline. When a user tries to promote a document that did not come through the raw pipeline, the skill asks:

> "This document was created outside the corpus pipeline. If it is a throwaway or draft, store it outside the project. If it is important enough to stay in the project, it should go through the pipeline. Add it to `corpus/raw/inbox/` and start from consolidate?"

The user can accept (file is copied to inbox, pipeline starts) or override (see Override Protocol below).

---

## Pipeline State

### State File: `.sweetclaude/state/corpus-pipeline.yaml`

```yaml
pipeline:
  step: idle | consolidating | triaging | reconciling | promoting
  active_since: null
  interrupted: false

consolidate:
  status: not-started | in-progress | complete
  last_run: null
  sources: []
  files_in_inbox: 0

triage:
  status: not-started | in-progress | complete
  last_run: null
  files_classified: 0
  files_remaining: 0

reconcile:
  status: not-started | in-progress | complete
  last_run: null
  active_cluster: null
  files_in_staged: 0
  files_in_working: 0

promote:
  status: not-started | in-progress | complete
  last_run: null
  files_in_working: 0
  files_promoted: 0
```

### Gating Rules

Each skill checks `corpus-pipeline.yaml` before running.

| Skill | Requires | Hard stop if |
|---|---|---|
| corpus-consolidate | Nothing — always the valid entry point | `pipeline.step` is not `idle` (another operation is active) |
| corpus-triage | `consolidate.status == complete` | `consolidate.status != complete` OR `pipeline.step` is not `idle` |
| corpus-reconcile | `triage.status == complete` | `triage.status != complete` OR `pipeline.step` is not `idle` |
| corpus-promote | `reconcile.status == complete` AND files exist in `corpus/working/` | `reconcile.status != complete` OR `pipeline.step` is not `idle` OR `corpus/working/` is empty |
| corpus-reindex | `pipeline.step == idle` | Any operation is active |
| corpus-status | Nothing — read-only, always allowed | Never |

### Hard Stop Protocol

When a skill is blocked by a gating rule:

**Step 1 — Error message:**

> "Cannot run {skill}. The corpus pipeline requires {prerequisite} to complete first. Current state: {step} is {status}."

**Step 2 — If the user insists (asks again or says to proceed anyway):**

> "Running {skill} out of order can corrupt the refined corpus. Original source files in `corpus/raw/inbox/` will be unaffected, but canonical documents, sidecars, and provenance records in `corpus/canonical/`, `corpus/working/`, and `corpus/archive/` may become inconsistent. Type 'I accept the risk of corpus corruption' to proceed."

**Step 3 — User must type the exact phrase.** Paraphrasing or abbreviating does not count. If they type it:

- Log the override in `.sweetclaude/state/decision-log.md` with timestamp, which gate was bypassed, and the user's acknowledgment
- Set `pipeline.step` to the requested operation
- Proceed with the skill

If they do not type the exact phrase, do not proceed.

### Lifecycle Hooks

**On skill entry:**
```yaml
pipeline:
  step: {skill name}
  active_since: {ISO 8601 timestamp}
  interrupted: false
```

**On skill exit (success):**
```yaml
pipeline:
  step: idle
  active_since: null
  interrupted: false
{skill_section}:
  status: complete
  last_run: {ISO 8601 timestamp}
  # ... update counts
```

**On skill exit (user cancelled or paused):**
```yaml
pipeline:
  step: idle
  active_since: null
  interrupted: false
{skill_section}:
  status: in-progress
  # ... preserve partial progress counts
```

Partial completion is valid for triage (some files classified, some not) and reconcile (some clusters processed, some not). The skill picks up where it left off on next run.

### Crash Recovery

If a session dies mid-operation, `pipeline.step` will be non-idle and `interrupted` will be false (it never got set to true because the session died).

**On next session start,** corpus preflight detects this:

1. Read `corpus-pipeline.yaml`
2. If `pipeline.step != idle` AND `pipeline.active_since` is more than 0 seconds ago (i.e., set):

> "The last corpus operation ({step}) did not complete. It started at {active_since}."

Ask the user:
- "Resume" — restart the skill, which reads its own recovery state (consolidate-plan.md, triage metadata, etc.)
- "Reset" — set `pipeline.step = idle`, mark the skill as `in-progress`, let the user decide what to do next

Do not auto-resume. Do not auto-reset. The user decides.

---

## Skill Specifications

### 1. Consolidate (`/sweetclaude:corpus-consolidate`)

**Status:** Implemented (skills/corpus-consolidate/SKILL.md)

**Purpose:** Scan directories, hash, deduplicate, copy unique files into `corpus/raw/inbox/`.

**Changes from v1:** Add pipeline state updates on entry and exit. Create `corpus-pipeline.yaml` if it does not exist (consolidate is always the valid entry point).

**Additions:**
- On entry: set `pipeline.step = consolidating`
- On exit: set `consolidate.status = complete`, update `consolidate.files_in_inbox`, set `pipeline.step = idle`
- If `corpus-pipeline.yaml` does not exist, create it with all statuses set to `not-started`

### 2. Triage (`/sweetclaude:corpus-triage`)

**Status:** Implemented (skills/corpus-triage/SKILL.md)

**Purpose:** Classify inbox files for reconciliation, archival, or deferral.

**Changes from v1:** Add pipeline gate check and state updates.

**Additions:**
- On entry: check gate, set `pipeline.step = triaging`
- On exit: set `triage.status = complete` (or `in-progress` if paused), update counts, set `pipeline.step = idle`
- Update `triage.files_remaining` after each batch so crash recovery knows where things stand

### 3. Reconcile (`/sweetclaude:corpus-reconcile`)

**Status:** Not implemented

**Purpose:** Take staged files and work with the user to produce approved canonical documents.

**Input:** Files in `corpus/raw/staged/`.

**Process:**

1. **Check gate.** Verify `triage.status == complete`. Hard stop if not.

2. **Set pipeline state.** `pipeline.step = reconciling`.

3. **Select cluster.** Present staged files grouped by topic or source. The user picks a file or cluster to work on. Move selected files to `corpus/working/`.

4. **Analyze.** Spawn a subagent per file:

   > Read this staged file and these existing canonical documents from `corpus/canonical/`. Propose an action with rationale. Return JSON:
   > ```json
   > {
   >   "source": "corpus/working/filename.md",
   >   "action": "merge | supersede | copy | discard",
   >   "target_canonical": "corpus/canonical/strategic/concept.md",
   >   "rationale": "Why this action",
   >   "conflicts": ["List of conflicts with existing canonical docs, if any"]
   > }
   > ```
   > Do nothing else.

5. **Present proposal.** Show the subagent's recommendation to the user. User approves, modifies, or rejects.

6. **Draft.** Based on the approved action:
   - **merge** — combine staged content into the target canonical document. Present the merged draft.
   - **supersede** — the staged file replaces the canonical document entirely. Present for confirmation.
   - **copy** — the staged file becomes a new canonical document as-is. Present for confirmation.
   - **discard** — the staged file has no canonical value. Confirm with user.

7. **Refine.** Iterate with the user until they say the document is approved. This may take multiple rounds. The user controls pacing — do not push for approval.

8. **Save approved document.** Write the approved document to `corpus/working/{canonical-name}.md`. Do NOT move to `corpus/canonical/` — that is promote's job.

9. **Update state.** Set `reconcile.active_cluster` to the cluster name. Update `reconcile.files_in_working`.

10. **Repeat or finish.** If more staged files remain, ask if the user wants to continue with another cluster. If the user is done for this session, set `pipeline.step = idle` and `reconcile.status = in-progress`.

11. **When all staged files are processed:** Set `reconcile.status = complete`.

**Key properties:**
- Per-cluster, session-length activity (not batch)
- User controls pacing and approval — no pushing
- Approved documents stay in `corpus/working/` until promote
- Crash recovery via `reconcile.active_cluster` — next session can resume the cluster
- Git checkpoint after each approved document

### 4. Promote (`/sweetclaude:corpus-promote`)

**Status:** Not implemented

**Purpose:** Finalize approved documents from `corpus/working/`. Record provenance, archive sources, index into RAG.

**Input:** Approved documents in `corpus/working/`.

**Process:**

1. **Check gate.** Verify `reconcile.status == complete` AND `corpus/working/` contains files. Hard stop if not.

2. **Set pipeline state.** `pipeline.step = promoting`.

3. **Inventory working documents.** List all files in `corpus/working/`. For each, show:
   - Filename
   - Target canonical path (based on content type and mapping table)
   - Source files that were reconciled into it (from triage metadata)

4. **Confirm mapping.** Present the promotion plan to the user:

   > ```
   > Promotion Plan
   > ══════════════
   >
   > {filename} → corpus/canonical/{subdir}/{name}
   >   Sources: {list of original staged files}
   >
   > {filename} → corpus/canonical/{subdir}/{name}
   >   Sources: {list of original staged files}
   > ```

   User confirms or adjusts target paths.

5. **For each document, execute atomically:**

   a. **Write sidecar** for each source file:
   ```json
   {
     "source_path": "corpus/archive/{date}-reconcile/{original_filename}",
     "content_hash": "sha256:...",
     "reconciled_at": "{ISO 8601}",
     "reconciled_by": "{git user}",
     "canonical_documents": ["corpus/canonical/{subdir}/{name}"],
     "action": "{merge|supersede|copy|discard}",
     "notes": "{from reconcile session}"
   }
   ```

   b. **Move canonical document:**
   ```bash
   mv corpus/working/{name} corpus/canonical/{subdir}/{name}
   ```

   c. **Archive source files** with sidecars:
   ```bash
   mkdir -p corpus/archive/{date}-reconcile/
   mv corpus/raw/staged/{source_files} corpus/archive/{date}-reconcile/
   mv {sidecars} corpus/archive/{date}-reconcile/
   ```

   d. **Git commit** per document:
   ```bash
   git add corpus/canonical/ corpus/archive/
   git commit -m "promote: {name} → corpus/canonical/{subdir}/"
   ```

   e. **Index into RAG** (canonical collection, incremental).

6. **Update corpus.yaml.** Add entries to `promotions` list and `archive_sources`.

7. **Update pipeline state:**
   ```yaml
   promote:
     status: complete
     last_run: {timestamp}
     files_promoted: {count}
   pipeline:
     step: idle
   ```

8. **Report:**
   > "Promoted {N} documents to corpus/canonical/. Sources archived with provenance sidecars. RAG index updated."

**Canonical target mapping:**

| Source content type | Canonical target |
|---|---|
| Concept, positioning, vision | corpus/canonical/strategic/ |
| Pain thesis | corpus/canonical/strategic/ |
| ICP | corpus/canonical/strategic/ |
| Competitive analysis | corpus/canonical/strategic/ |
| Market messaging | corpus/canonical/strategic/ |
| Narrative arc | corpus/canonical/strategic/ |
| Academic research, publication strategy | corpus/canonical/research/ |
| Meeting prep, debriefs | corpus/canonical/operations/ |
| Product brief, PRD, user stories | corpus/canonical/product/ |
| Architecture, tech spec, data model, API design | corpus/canonical/design/ |

**Key properties:**
- Atomic per document — if one fails, others already promoted are safe
- Full provenance via sidecars — every canonical document traces back to source files
- Git commit per document — granular history
- RAG indexing at the end — if it fails, corpus preflight catches it next session

### 5. Reindex (`/sweetclaude:corpus-reindex`)

**Status:** Not implemented

**Purpose:** Rebuild RAG collections from source files. Recovery tool for when embeddings are corrupted, lost, or when the embedding model changes.

**Gate:** `pipeline.step == idle`. Cannot run while any operation is active.

**Process:**

1. **Check gate.** Hard stop if pipeline is not idle.

2. **Choose scope.** Use AskUserQuestion:
   - "Canonical" — rebuild `{project}-canonical` from `corpus/canonical/`
   - "Raw" — rebuild `{project}-raw` from `corpus/raw/inbox/`
   - "All" — both

3. **For each collection:**
   a. Delete the existing RAG collection
   b. Walk the source directory recursively
   c. Index every file
   d. Report: "{N} files indexed into {collection}"

4. **If RAG tooling is not available:**
   > "MCP RAG server not configured. Run `/sweetclaude:rag-index` to set it up first."

### 6. Corpus Status (`/sweetclaude:corpus-status`)

**Status:** Not implemented

**Purpose:** Show the current state of the corpus pipeline. Read-only — always allowed, never gated.

**Process:**

1. Read `corpus-pipeline.yaml`.
2. Walk corpus directories to get live counts (do not trust cached counts alone).
3. Present:

```
Corpus Status — {project name}
═══════════════════════════════

Pipeline:        {step} {since active_since, if not idle}

                 Files    Status
inbox/           {N}      {consolidate.status}
staged/          {N}      {triage.status}
working/         {N}      {reconcile.status}
canonical/       {N}      {promote.status}
archive/         {N}      —

Last consolidate: {date or "never"}
Last triage:      {date or "never"}
Last reconcile:   {date or "never"}
Last promote:     {date or "never"}

Next step: {recommendation based on current state}
```

4. If `pipeline.interrupted` or `pipeline.step != idle`:
   > "Warning: {step} did not complete. Run `/sweetclaude:corpus-{step}` to resume or `/sweetclaude:corpus-status` for details."

---

## Pipeline Reset

If the pipeline gets stuck or the user wants to start over:

There is no reset skill. The user deletes `corpus-pipeline.yaml` and the next corpus skill creates a fresh one. This is intentionally manual — resetting pipeline state should require deliberate action, not a convenient command that could be invoked by accident.

---

## Directory Structure

Unchanged from v1:

```
corpus/
  raw/
    inbox/          # consolidate writes here
    staged/         # triage moves files here
  working/          # reconcile drafts here, promote reads from here
  canonical/        # promote writes here (final destination)
    strategic/
    product/
    design/
    research/
    operations/
  archive/          # promote archives source files here
    {date}-{source}/
      {files}
      {sidecars}
  rag-system/       # RAG embeddings and indexes
    canonical/
    raw/
```

---

## Failure Recovery

### Per-Skill Recovery

Each skill has its own recovery mechanism:

- **Consolidate:** `consolidate-plan.md` survives session death. Next run diffs plan against inbox.
- **Triage:** Partially classified files are already moved. Next run inventories whatever remains in inbox.
- **Reconcile:** `reconcile.active_cluster` in pipeline state. Next run offers to resume the cluster. Approved documents in `corpus/working/` are safe.
- **Promote:** Atomic per document. Partially promoted sets are valid — some documents in canonical, some still in working. Next run promotes the remainder.

### Pipeline-Level Recovery

`corpus-pipeline.yaml` with `pipeline.step != idle` on session start triggers the crash recovery protocol (see Crash Recovery section above).

### Nuclear Recovery

If everything is broken:
1. Delete `corpus-pipeline.yaml`
2. `corpus/raw/inbox/` still has the deduplicated source files
3. `corpus/raw/staged/` has classified files
4. `corpus/working/` has approved drafts
5. `corpus/canonical/` has promoted documents
6. Filesystem location is always the ground truth — the state file is a coordination tool, not the source of truth

---

## Implementation Order

1. Update corpus-consolidate to write `corpus-pipeline.yaml` on entry/exit
2. Update corpus-triage to check gate and write pipeline state on entry/exit
3. Build corpus-reconcile
4. Build corpus-promote
5. Build corpus-reindex
6. Build corpus-status
7. Add pipeline state check to corpus preflight hook
