---
spdx-license: AGPL-3.0-or-later
description: "Manage the full document corpus pipeline — consolidate raw files, triage, reconcile into canonical documents, promote, set up semantic search (RAG), and reindex. Presents a menu at start."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Run `/sweetclaude:on` first." Then stop.
</preflight-guard>

# Document Corpus

Manage your project's documents — from a pile of raw files to a clean, indexed, searchable canonical corpus.

---

## Step 1: Read pipeline state and present menu

Read `.sweetclaude/state/corpus-pipeline.yaml` if it exists. Use it to show current status next to each option.

Check for existing RAG index:
```bash
ls .rag-index/lancedb/ 2>/dev/null | wc -l
cat .rag-index/.index-manifest.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('files',{})))" 2>/dev/null
```

If an index exists (lancedb directory has contents OR manifest has files), label option 6 as **"Update RAG"**. Otherwise label it **"Set up RAG"**.

Present:

```
Document Corpus
═══════════════

What do you want to do?

  1. Status          — see where the pipeline stands
  2. Consolidate     — scan directories, deduplicate, copy into inbox  {consolidate.status}
  3. Triage          — classify inbox files (keep / reconcile / discard / defer)  {triage.status}
  4. Reconcile       — draft canonical documents from staged files  {reconcile.status}
  5. Promote         — finalize, archive sources, index into RAG  {promote.status}
  6. {Set up RAG | Update RAG}  — {configure and run | check for changes and sync} semantic search
  7. Reindex RAG     — rebuild the search index from scratch (recovery)
```

If `$ARGUMENTS` is `onboard`, run the onboard flow below instead of showing the menu.

If `$ARGUMENTS` is `offboard`, run the offboard flow below instead of showing the menu.

If any other `$ARGUMENTS` was passed (e.g. `/sweetclaude:document-corpus triage`), skip the menu and route directly.

Parse the user's selection and jump to the named section below.

---

## Offboard — Export data and stop using this skill

Invoked with argument `offboard`.

1. **Inventory what exists:**

```bash
find corpus/ -type f 2>/dev/null | wc -l
find corpus/canonical/ -type f 2>/dev/null | wc -l
find corpus/raw/ -type f 2>/dev/null | grep -v '\.deferred\.json$\|\.triage\.json$' | wc -l
find .rag-index/ -type f 2>/dev/null | wc -l
```

Present a summary:
```
Corpus inventory:
  corpus/canonical/   {N} files  ← your finished documents
  corpus/raw/         {N} files  ← source and inbox files
  corpus/working/     {N} files  ← in-progress reconciliation
  corpus/archive/     {N} files  ← processed/discarded sources
  .rag-index/         {N} files  ← search index
```

If nothing exists, say: "No corpus data found. Nothing to export." Stop.

2. **Ask what to export:**

> "What do you want to export?
>   canonical   — export only `corpus/canonical/` (your finished documents)
>   all         — export the entire `corpus/` tree
>   none        — skip export, go straight to cleanup options"

3. **Ask export destination:**

If canonical or all: "Which directory should I copy the files to?"

Validate the directory exists (offer to create it if it doesn't). Copy files there with `rsync -a`. Report files copied.

4. **Confirm export complete** (if export ran):

> "Export complete. Confirm the files look correct at `{destination}` before proceeding. Ready to continue? (yes/cancel)"

If cancel, stop. Do not touch SweetClaude files.

5. **Ask what to delete** (separate question for each):

Ask each question independently. For each, require separate confirmation.

**corpus/ directory:**
> "⚠ IRREVERSIBLE DATA LOSS WARNING ⚠
>
> Delete the entire `corpus/` directory? This contains {N} files including your canonical documents, source files, and pipeline state.
> This cannot be undone.
>
> To confirm, type exactly: DELETE CORPUS
> To skip, type anything else."

**RAG index:**
> "⚠ IRREVERSIBLE DATA LOSS WARNING ⚠
>
> Delete the `.rag-index/` directory? This contains the search index ({N} files).
> The index can be rebuilt from `corpus/canonical/` if you keep those files.
> This cannot be undone.
>
> To confirm, type exactly: DELETE RAG INDEX
> To skip, type anything else."

**Pipeline state:**
> "⚠ IRREVERSIBLE DATA LOSS WARNING ⚠
>
> Delete pipeline state files (`.sweetclaude/state/corpus-pipeline.yaml`, `.sweetclaude/state/corpus.yaml`, `.sweetclaude/state/consolidate-plan.md`)?
> This cannot be undone.
>
> To confirm, type exactly: DELETE CORPUS STATE
> To skip, type anything else."

6. **Execute only confirmed deletions:**

```bash
# Only if DELETE CORPUS confirmed:
rm -rf corpus/

# Only if DELETE RAG INDEX confirmed:
rm -rf .rag-index/

# Only if DELETE CORPUS STATE confirmed:
rm -f .sweetclaude/state/corpus-pipeline.yaml .sweetclaude/state/corpus.yaml .sweetclaude/state/consolidate-plan.md
```

Report each deletion as it completes. Report anything skipped.

---

## Onboard — First-time setup

Invoked with argument `onboard` when this skill is newly installed.

1. **Scan for existing documents:**

```bash
# Count markdown and text files outside corpus/ and .sweetclaude/
find . -maxdepth 4 \( -name "*.md" -o -name "*.txt" -o -name "*.pdf" -o -name "*.docx" \) \
  ! -path "./.sweetclaude/*" ! -path "./corpus/*" ! -path "./.rag-index/*" \
  ! -path "./node_modules/*" ! -path "./.git/*" 2>/dev/null | wc -l

find . -maxdepth 4 \( -name "*.md" -o -name "*.txt" \) \
  ! -path "./.sweetclaude/*" ! -path "./corpus/*" ! -path "./.rag-index/*" \
  ! -path "./node_modules/*" ! -path "./.git/*" 2>/dev/null | head -10
```

2. **Present findings and ask:**

If documents found:
> "I found {N} documents in this project that could be imported into the corpus ({list of sample paths}).
>
> The Document Corpus pipeline consolidates, deduplicates, and indexes your docs into a clean searchable corpus. Want to start that pipeline now?
>   yes    — I'll start with Consolidate (you'll confirm before anything is copied)
>   later  — I'll skip for now; run `/sweetclaude:document-corpus` when ready"

If nothing found:
> "No existing documents found outside SweetClaude directories. The Document Corpus skill is ready — run `/sweetclaude:document-corpus` when you have documents to import."

3. **If yes:** Route to **Mode: Consolidate** with the discovered directories as suggested sources.

4. **If later / nothing found:** Stop.

---

## About the Pipeline (read this if you are tempted to skip steps)

The corpus pipeline has a strict order: **consolidate → triage → reconcile → promote**. Each step builds on the previous one. Skipping creates real problems:

**"Can I just RAG my documents right now without going through all this?"**

Yes, technically. But here is what happens: RAG cannot distinguish an authoritative spec from an abandoned draft, a final version from an early brainstorm, or a canonical document from a superseded one. A query for "the current architecture" will blend your latest design doc with the version from three pivots ago and the rough notes you typed at 2am. The results will look confident and be wrong in ways that are hard to notice. The pipeline exists to prevent exactly this failure mode.

**"Can I skip triage and go straight to reconcile?"**

Triage is where you decide what is worth keeping. Without it, reconcile has to process everything — including files you would have discarded in 30 seconds. It also means canonical documents may incorporate content you never intended to canonicalize.

**"Can I skip reconcile and go straight to promote?"**

Promote moves files from `corpus/working/` to `corpus/canonical/`. If reconcile has not run, there is nothing in `corpus/working/`. Promote requires approved documents — it does not create them.

**"I just need to reindex quickly."**

Reindex rebuilds the RAG collections from whatever is already in `corpus/canonical/` and `corpus/raw/inbox/`. If those directories are messy, the index will be messy. Reindex is a recovery tool, not a shortcut around the pipeline.

The pipeline is not bureaucracy. It is the difference between a search that answers your questions and one that confidently misleads you.

---

## Mode: Status

Show the current state of the corpus pipeline. Read-only — never modifies anything.

### Step S1: Read pipeline state

Read `.sweetclaude/state/corpus-pipeline.yaml`.

If it does not exist:
> "No corpus pipeline configured yet. Choose **Consolidate** to start."

Stop.

### Step S2: Count files (live from filesystem)

Do not trust cached counts — walk the directories:

```bash
find corpus/raw/inbox/ -type f 2>/dev/null | grep -v '\.deferred\.json$' | wc -l
find corpus/raw/staged/ -type f 2>/dev/null | grep -v '\.triage\.json$' | wc -l
find corpus/working/ -type f 2>/dev/null | wc -l
find corpus/canonical/ -type f 2>/dev/null | wc -l
find corpus/archive/ -type f 2>/dev/null | grep -v '\.reconciled\.json$' | wc -l
```

Count metadata files separately:
```bash
find corpus/raw/inbox/ -name '*.deferred.json' 2>/dev/null | wc -l
find corpus/raw/staged/ -name '*.triage.json' 2>/dev/null | wc -l
find corpus/archive/ -name '*.reconciled.json' 2>/dev/null | wc -l
```

### Step S3: Present

```
Corpus Status — {project name}
═══════════════════════════════

Pipeline:        {pipeline.step} {" (since {active_since})" if not idle}

                 Files    Metadata   Step Status
inbox/           {N}      {deferred} consolidate: {status}
staged/          {N}      {triage}   triage: {status}
working/         {N}      —          reconcile: {status}
canonical/       {N}      —          promote: {status}
archive/         {N}      {sidecars} —

Last consolidate: {date or "never"} — {sources summary}
Last triage:      {date or "never"} — {files_classified} classified
Last reconcile:   {date or "never"} — {cluster summary}
Last promote:     {date or "never"} — {files_promoted} promoted
```

Check for anomalies:
- **Pipeline stuck:** `pipeline.step != idle` — "⚠ {step} did not complete. Select that step to resume."
- **Working files not recently touched:** "⚠ {N} files in corpus/working/ may be from an abandoned reconciliation."
- **Staged files without triage metadata:** "⚠ {N} staged files have no triage metadata."
- **Canonical files not in RAG:** If RAG available, compare canonical count to RAG doc count — "⚠ {N} canonical files may not be indexed."

Suggest next action based on state:

| State | Recommendation |
|---|---|
| No pipeline state | "→ Select **Consolidate** to start the pipeline." |
| consolidate done, inbox has files, triage not started | "→ Select **Triage** to classify {N} inbox files." |
| triage done, staged has files, reconcile not started | "→ Select **Reconcile** to process {N} staged files." |
| reconcile done/in-progress, working has files | "→ Select **Promote** to finalize {N} approved documents." |
| All steps complete | "✓ Pipeline complete. All files processed." |
| Pipeline stuck | "⚠ Resolve the interrupted {step} first." |

---

## Mode: Consolidate

Scan source directories, deduplicate files, and copy unique files into `corpus/raw/inbox/`. Originals are never moved or deleted.

### Step C0: Preconditions

**Check pipeline state:**

Read `.sweetclaude/state/corpus-pipeline.yaml` if it exists.

If it does not exist, create it:
```yaml
pipeline:
  step: idle
  active_since: null
  interrupted: false
consolidate:
  status: not-started
  last_run: null
  sources: []
  files_in_inbox: 0
triage:
  status: not-started
  last_run: null
  files_classified: 0
  files_remaining: 0
reconcile:
  status: not-started
  last_run: null
  active_cluster: null
  files_in_staged: 0
  files_in_working: 0
promote:
  status: not-started
  last_run: null
  files_in_working: 0
  files_promoted: 0
```

If `pipeline.step` is not `idle`:
> "The pipeline is currently running {pipeline.step} (started {pipeline.active_since}). Wait for it to finish or resolve the interrupted operation."

If the user insists on overriding: require them to type `I accept the risk of corpus corruption`. If they do, log the override in `.sweetclaude/state/decision-log.md` and proceed. If not, stop.

**Set pipeline state:** `pipeline.step: consolidating`, `active_since: {now}`.

**Check for interrupted consolidation:**

Does `.sweetclaude/state/consolidate-plan.md` exist without a completion marker?

If yes, offer Resume (diff plan against actual inbox and copy what is missing) or Start over.

**Ensure corpus directory exists:** `mkdir -p {project-path}/corpus/raw/inbox`

### Step C1: Identify sources

If the user provided source directories as arguments, use those. Otherwise ask: "Which directories should I scan? Give me one or more paths."

Validate each path exists before proceeding.

### Step C2: Scan and hash (subagent)

Spawn a subagent:

> Scan these directories and catalog every file: {source paths}
>
> **Exclude:** binary files (.png, .jpg, .gif, .ico, .woff, .woff2, .ttf, .eot, .exe, .dll, .so, .zip, .tar, .gz, .jar, .pyc, .o, .a), files larger than 1MB, directories (node_modules/, .git/, __pycache__/, .venv/, venv/, dist/, build/, .next/, .rag-index/, corpus/, .sweetclaude/, strategy/), lock files (package-lock.json, yarn.lock, pnpm-lock.yaml, Pipfile.lock, poetry.lock, Cargo.lock, go.sum), .DS_Store
>
> For each included file, collect: relative path from source root, source directory, file size in bytes, SHA-256 hash.
>
> Report as JSON array: `[{"source": "...", "relative_path": "...", "size_bytes": N, "sha256": "..."}]`
>
> Also report: total files scanned, files excluded (with breakdown), files included, total size.
>
> Do nothing else. Do not copy, move, or modify any files.

Verify: subagent returned JSON array and stats, did not modify files.

Present: "Scanned {N} files across {M} sources. {excluded} excluded. {included} to process ({total_size})."

### Step C3: Token estimation

Estimate tokens: `size_bytes / 4`. Report: "Estimated corpus size: ~{N} tokens ({size_mb} MB)."

### Step C4: Deduplication analysis (subagent)

Spawn a subagent:

> Given this file catalog (JSON from Step C2), group files by SHA-256 hash. For each group with >1 file: designate the first alphabetically as canonical, mark others as duplicates.
>
> Report: total unique files, total duplicates, duplicate groups (hash, canonical path, duplicate paths), tokens saved by deduplication.
>
> Do nothing else.

Present: "{unique} unique files, {duplicates} duplicates found. Deduplication saves ~{tokens_saved} tokens."

### Step C5: Generate and approve consolidation plan

Write `.sweetclaude/state/consolidate-plan.md`:

```markdown
# Consolidation Plan — {date}

## Sources
{list each source directory}

## Scan Summary
- Files scanned: {total}
- Files excluded: {excluded}
- Files included: {included}
- Duplicates found: {duplicates}
- Unique files to copy: {unique}
- Estimated tokens: {tokens}

## Destination
corpus/raw/inbox/{source_name}/

## File Manifest
{for each unique file: source path, destination path, size, hash — one line per file}

## Duplicate Groups
{from Step C4}

## Execution
- Batch size: 500 files
- Status: PENDING
```

Present summary and use AskUserQuestion: Execute / Review plan / Cancel.

If "Review plan", show the document, then re-ask. If "Cancel", stop.

### Step C6: Execute copy (subagent — batched)

Destination for each source: `corpus/raw/inbox/{source_dir_name}/`. If two sources share a dir name, suffix: `old-project-2`.

Process in batches of 500. For each batch spawn a subagent:

> Copy these files to corpus/raw/inbox/. Preserve directory structure.
>
> Rules: copy only (never move or delete source). If destination exists with same hash, skip. If different hash, rename with `-{N}` suffix before extension. Create destination dirs with `mkdir -p`.
>
> Report: files copied, files skipped (same hash), files renamed (collision), errors.

After all batches: report totals. Update consolidate-plan.md with completion marker.

### Step C7: Update state and commit

Update `corpus-pipeline.yaml`:
```yaml
pipeline:
  step: idle
  active_since: null
  interrupted: false
consolidate:
  status: complete
  last_run: {now}
  sources: [{source paths}]
  files_in_inbox: {count}
```

Create or update `.sweetclaude/state/corpus.yaml` with `last_consolidate` details.

```bash
git add corpus/raw/inbox/ .sweetclaude/state/consolidate-plan.md .sweetclaude/state/corpus.yaml .sweetclaude/state/corpus-pipeline.yaml
git commit -m "consolidate: copy {N} files from {sources} into corpus/raw/inbox"
```

Report: "Done. Next: select **Triage** to classify the inbox files."

**Error handling:**
- Source disappears mid-run: skip missing files, continue, note in plan.
- Disk space: check before Step C6. If insufficient, stop before copying anything.
- Git commit fails: files are safe — commit can be retried manually. Do not delete copied files.

---

## Mode: Triage

Classify files in `corpus/raw/inbox/` as keep-as-is, needs-reconciliation, discard, or defer. Batch classification — fast decisions, no synthesis.

### Step T0: Preconditions

**Check pipeline gate:**

Read `corpus-pipeline.yaml`. If it does not exist, stop: "Run **Consolidate** first."

If `consolidate.status` is not `complete`, explain:
> "Triage requires consolidation to be complete first. Here is why: triage classifies the files that consolidation brought in. Without consolidation, triage has no defined inbox — it would be working on whatever happens to be in a directory, which may be your source files. Run **Consolidate** first."

If the user insists: require `I accept the risk of corpus corruption`. Log override if accepted.

If `pipeline.step` is not `idle`: same override protocol.

Set pipeline state: `step: triaging`.

Ensure `corpus/raw/staged/` and `corpus/archive/` directories exist.

### Step T1: Inventory (subagent)

Spawn a subagent:

> Scan `corpus/raw/inbox/` recursively. For each file: full path relative to project root, file size, first 5 lines of content.
>
> Group files by top-level subdirectory within `corpus/raw/inbox/`. Report as a table per group with: file number, relative path, size, preview.
>
> Also report: total files, total size, number of source groups.
>
> Do nothing else.

Present summary: "corpus/raw/inbox/ contains {N} files across {M} source groups ({total_size}). Ready to triage."

### Step T2: Choose triage mode

Use AskUserQuestion:
- "By group" — triage one source group at a time (recommended for large corpora)
- "By file" — triage individual files (for small corpora)
- "Bulk classify" — classify an entire source group with one decision

### Step T3: Triage loop

**By-group mode:** For each source group, spawn a subagent per file to produce a one-paragraph summary (type, draft/final/superseded, version indicators, overlaps). Present summaries in batches of 10-20. Ask user to classify each: **keep** (ready as-is) / **reconcile** (needs merging) / **discard** (not useful) / **defer** (skip for now). Accept batch input like "1-5 keep, 6 discard, 7-8 reconcile".

**By-file mode:** Present one file at a time with AskUserQuestion: Keep / Reconcile / Discard / Defer.

**Bulk classify mode:** Show the group summary. AskUserQuestion: Keep all / Discard all / Defer all / Mix (switch to by-group for this group).

### Step T4: Execute classifications (subagent — per batch)

For each confirmed batch spawn a subagent:

> Execute these triage classifications:
> {classification list: file_path → action}
>
> **keep/reconcile:** `mv {source} corpus/raw/staged/{relative_path}`. For reconcile, also create `{path}.triage.json`: `{"triaged_at": "...", "classification": "needs-reconciliation", "source_path": "...", "notes": ""}`.
>
> **discard:** `mv {source} corpus/archive/{date}-triage/`. Create sidecar `{filename}.reconciled.json`: `{"source_path": "...", "action": "discarded", "notes": "..."}`.
>
> **defer:** Leave file in inbox. Create `{file_path}.deferred.json`: `{"deferred_at": "...", "reason": "..."}`.
>
> Report: files staged (keep), files staged (reconcile), files archived (discard), files deferred, errors.

### Step T5: Summary and commit

```
Triage Complete
═══════════════

✓ Staged (keep):          {count} files
✓ Staged (reconcile):     {count} files
✓ Archived (discard):     {count} files
  Deferred:               {count} files
  Remaining in inbox:     {count} files
```

Update `corpus-pipeline.yaml`: `triage.status: complete`.

```bash
git add corpus/raw/staged/ corpus/archive/ corpus/raw/inbox/ .sweetclaude/state/corpus-pipeline.yaml
git commit -m "triage: classify {N} files — {kept} staged, {discarded} archived, {deferred} deferred"
```

Report: "Done. Next: select **Reconcile** to process staged files into canonical documents."

**Error handling:**
- File move fails: skip the specific file, continue, log in summary.
- User classification unparseable: ask again with examples. Do not guess.
- Mid-triage stop: set `triage.status: in-progress`, set pipeline to idle. Resume picks up remaining inbox files.

---

## Mode: Reconcile

Take staged files and work with the user to produce approved canonical documents in `corpus/working/`. This is the creative work — drafting, merging, refining.

### Step R0: Preconditions

**Check pipeline gate:**

Read `corpus-pipeline.yaml`. If `triage.status` is not `complete`, explain:
> "Reconcile requires triage to be complete first. Here is why: triage decided which files are worth synthesizing. Running reconcile without triage means you would be trying to draft canonical documents from files you have not evaluated — including files you would have discarded in 30 seconds. Run **Triage** first."

If the user insists: require `I accept the risk of corpus corruption`.

Set pipeline state: `step: reconciling`.

**Check for active cluster from previous session:** If `reconcile.active_cluster` is not null, offer Resume (continue that cluster) or Start fresh (move working files back to staged).

### Step R1: Inventory staged files (subagent)

Spawn a subagent:

> Scan `corpus/raw/staged/` recursively (skip `.triage.json` files). For each file: path, size, first 10 lines, triage classification if metadata exists.
>
> Group files into clusters by topic using: filename similarity, content overlap, source group, triage metadata.
>
> Present as clusters with a table per cluster. List unclustered files separately.
>
> Do nothing else.

Present: "corpus/raw/staged/ contains {N} files in {M} clusters. Pick a cluster to reconcile."

### Step R2: Select cluster

Present cluster list. Ask which to work on. Move selected files to `corpus/working/`. Update `reconcile.active_cluster`.

### Step R3: Analyze cluster (subagent per file)

Also scan `corpus/canonical/` for existing docs that might be relevant.

For each file, spawn a subagent:

> Read `{file_path}`. Also read these potentially relevant canonical docs: {list}.
>
> Propose an action. Return JSON only:
> ```json
> {
>   "source": "corpus/working/{filename}",
>   "action": "merge | supersede | copy | discard",
>   "target_canonical": "corpus/canonical/{subdir}/{suggested_name}.md",
>   "rationale": "...",
>   "conflicts": ["..."]
> }
> ```
>
> merge = combine with existing or other cluster files. supersede = replace existing canonical entirely. copy = standalone new canonical doc. discard = no canonical value.
>
> Do nothing else.

### Step R4: Present proposals

For each file:
```
{filename}
  Action:    {action}
  Target:    {target_canonical}
  Rationale: {rationale}
  Conflicts: {conflicts or "none"}
```

Ask: "Approve these recommendations, or adjust? Change any by number."

### Step R5: Draft canonical documents

**copy:** File becomes canonical as-is. Present for confirmation.

**supersede:** File replaces existing canonical. Show what changes. Confirm.

**merge:** Read all files targeted at the same canonical document. Draft a merged document that preserves current and accurate content from each source, resolves conflicts (present conflicts to user for decision), and does not lose substantive content without approval. Present draft for review.

**discard:** Confirm with user, then archive with sidecar.

### Step R6: Refine

Iterate with the user until they approve each document. This may take multiple rounds. Present draft → accept feedback → produce updated draft → repeat.

**Do not push for approval. Do not ask "is this ready?" The user decides when a document is done.**

When approved, write to `corpus/working/{canonical-name}.md`.

### Step R7: Checkpoint per approved document

```bash
git add corpus/working/
git commit -m "reconcile: draft approved — {canonical-name}"
```

### Step R8: Continue or finish

If more clusters remain: offer to continue with another cluster or stop.

If stopping mid-way:
```yaml
pipeline:
  step: idle
reconcile:
  status: in-progress
  active_cluster: null
```

Report: "{N} approved documents in corpus/working/ ready for promotion. {M} files remain in staged. Select **Promote** to finalize approved documents, or **Reconcile** to continue with staged files."

If all staged files processed, set `reconcile.status: complete`.

**Error handling:**
- Subagent returns invalid JSON: re-run once. If fails again, present file to user directly without recommendation.
- User wants to move a file back to staged: do it. This is normal.
- Merge has unresolvable conflicts: defer the cluster, move files back to staged.

---

## Mode: Promote

Finalize approved documents from `corpus/working/`. Move to `corpus/canonical/`, write provenance sidecars, archive source files, index into RAG, commit. No creative decisions — pure finalization.

### Step P0: Preconditions

**Check pipeline gate:**

Read `corpus-pipeline.yaml`. If `reconcile.status` is not `complete` and not `in-progress`, explain:
> "Promote finalizes documents that reconcile approved. Without reconcile, there is nothing in corpus/working/ to promote — promote does not create canonical documents, it only moves already-approved ones into place. Run **Reconcile** first."

If the user insists: require `I accept the risk of corpus corruption`.

Check `corpus/working/` has files. If empty: "Nothing to promote. Run **Reconcile** first to create approved documents."

Set pipeline state: `step: promoting`.

Ensure `corpus/canonical/{strategic,product,design,research,operations}/` and `corpus/archive/` exist.

### Step P1: Inventory working documents (subagent)

Spawn a subagent:

> Scan `corpus/working/`. For each file: path, size, first 10 lines, content type (strategy / product / design / research / operations).
>
> Also scan `corpus/raw/staged/` for `.triage.json` metadata referencing the source files. Collect source file paths.
>
> Report for each: `{filename}`, content type, size, suggested target in `corpus/canonical/{subdir}/`, source files if traceable.
>
> Do nothing else.

### Step P2: Confirm promotion plan

Present:
```
Promotion Plan
══════════════

{filename} → corpus/canonical/{subdir}/{name}
  Sources: {list or "created during reconciliation"}
```

Content type → canonical directory:
- Concept, positioning, vision, pain thesis, ICP, competitive analysis, market messaging, narrative arc → `canonical/strategic/`
- Academic research, publication strategy → `canonical/research/`
- Meeting prep, debriefs, stakeholder profiles → `canonical/operations/`
- Product brief, PRD, user stories, success criteria → `canonical/product/`
- Architecture, tech spec, data model, API design, UX → `canonical/design/`

Ask: "Confirm this plan? You can adjust any target path."

### Step P3: Execute promotion (one document at a time, atomic)

For each document:

**P3a. Check for collision:** If a file exists at the target, offer Replace (with backup) / Rename (add version suffix) / Skip / Cancel.

**P3b. Write provenance sidecars:** For each source file, create `corpus/archive/{date}-reconcile/{filename}.reconciled.json`:
```json
{
  "source_path": "...",
  "content_hash": "sha256:{hash}",
  "reconciled_at": "{ISO 8601}",
  "reconciled_by": "{git user}",
  "canonical_documents": ["corpus/canonical/{subdir}/{name}"],
  "action": "{merge|supersede|copy|discard}",
  "notes": "..."
}
```

**P3c. Move canonical document:** `mv corpus/working/{name} corpus/canonical/{subdir}/{name}`

**P3d. Archive source files:** `mv {source_files} corpus/archive/{date}-reconcile/`

**P3e. Commit:**
```bash
git add corpus/canonical/{subdir}/{name} corpus/archive/{date}-reconcile/
git commit -m "promote: {name} → corpus/canonical/{subdir}/"
```

**P3f. Index into RAG:** Index `corpus/canonical/{subdir}/{name}` into `{project}-canonical` collection. If RAG unavailable, note it and continue.

### Step P4: Update state and report

Update `corpus-pipeline.yaml`: `promote.status: complete`, `files_promoted: {count}`. Update `corpus.yaml` promotions list. Commit state.

```
Promotion Complete
══════════════════

✓ Documents promoted: {count}
✓ Sources archived:   {count} files
✓ Sidecars written:   {count}
✓ RAG indexed:        {indexed}/{total}

→ Pipeline: idle
```

**Error handling:**
- Move fails: do not continue with remaining documents for this file. Ask user to resolve and re-run.
- Sidecar write fails: sidecars are written before the move. Report and skip this document. Continue with next.
- RAG indexing fails: not fatal. Document is safely promoted. Note for reindex.

---

## Mode: Set Up RAG

Configure and run local semantic search on your project documents using `mcp-local-rag`.

### Step G0: Reconciliation gate

**Run on first indexing and any time new noise has appeared. Never skip on a first run.**

Indexing raw project contents blends authoritative documents with scratch notes, abandoned pivots, and versioned duplicates. RAG cannot distinguish them. The corpus pipeline exists to prevent this failure. This gate checks whether your content is clean enough to index usefully.

**G0a: Scan for noise indicators:**

```bash
noise_dirs=$(find . -maxdepth 4 -type d \( \
  -name "scratch" -o -name "attached_assets" -o -name "archive" \
  -o -name "drafts" -o -name "_old" -o -name "old" -o -name "backup" \
  -o -path "*/corpus/raw/inbox" \
  \) ! -path "*/.git/*" ! -path "*/node_modules/*" ! -path "*/.rag-index/*" 2>/dev/null | sort)

versioned_files=$(find . -type f \( -iname "*-v[0-9]*.*" -o -iname "*_v[0-9]*.*" \) \
  ! -path "./.rag-index/*" ! -path "./.git/*" ! -path "*/node_modules/*" 2>/dev/null | sort)
```

**G0b: If both are empty** — content is clean. Skip the gate. Proceed to G1 with default excludes.

**G0c: If noise was found**, check `.rag-index/.index-manifest.json` for a prior `noise_scan` decision:
- No manifest or no `noise_scan` → first-run, present the gate (G0d).
- Prior choice was **B (canonical-only)** → re-apply silently. Note to user.
- Prior choice was **C (proceed anyway)** → compare current scan to recorded one. If unchanged, re-apply silently. If new noise appeared, re-present the gate with a warning.

**G0d: Present the gate:**

```
⚠ Unreconciled content detected

Found:
- Directories: {list from noise_dirs}
- Versioned files: {first 10 from versioned_files}

If indexed raw, RAG treats all of these as equally authoritative.
A query for "the current design" blends an abandoned pivot, an
outdated draft, and the current spec with no distinction.

Three options:

  (A) RECONCILE FIRST — run the corpus pipeline (Consolidate →
      Triage → Reconcile → Promote), then return here. This is
      the right answer unless you have a specific reason not to.

  (B) CANONICAL-ONLY — index only docs/, strategy/, and
      corpus/canonical/. Skip everything else. Safe if those
      dirs are already clean.

  (C) PROCEED ANYWAY — index raw contents with default excludes.
      Logged as a decision. Only use if you explicitly want raw
      search across all drafts.
```

- **(A):** Stop. Tell the user to select **Consolidate** and run the pipeline. Do not record `noise_scan`.
- **(B):** Set `CANONICAL_ONLY=true`. Record choice in manifest. Proceed to G1.
- **(C):** Ask for one-sentence rationale. Log in decision-log if it exists. Record choice in manifest. Proceed to G1 with default excludes.

### Step G1: Check mcp-local-rag installation

```bash
npm list -g mcp-local-rag 2>/dev/null || echo "NOT_INSTALLED"
```

If not installed: `npm install -g mcp-local-rag`. If global install fails, note that `npx -y mcp-local-rag` works without it — `.mcp.json` uses `npx`.

### Step G2: Determine project root

Use current working directory. Confirm if ambiguous.

### Step G3: Create or verify `.mcp.json`

If `.mcp.json` does not exist, create:
```json
{
  "mcpServers": {
    "local-rag": {
      "command": "npx",
      "args": ["-y", "mcp-local-rag"],
      "env": {
        "BASE_DIR": ".",
        "DB_PATH": "./.rag-index/lancedb",
        "CACHE_DIR": "./.rag-index/models"
      }
    }
  }
}
```

If `.mcp.json` exists: check for `local-rag` entry. If present, leave alone. If absent, merge the entry without disturbing other servers.

### Step G4: Update `.gitignore`

If `.gitignore` does not contain `.rag-index/`, append:
```
# Local RAG index (mcp-local-rag)
.rag-index/
```

### Step G5: Discover indexable files

If `CANONICAL_ONLY=true` (from Step G0): restrict to `docs/`, `strategy/`, `corpus/canonical/` only.

Otherwise (default):
```bash
find . -type f \( -iname "*.pdf" -o -iname "*.docx" -o -iname "*.txt" -o -iname "*.md" \) \
  ! -path "./.rag-index/*" ! -path "./.git/*" ! -path "*/node_modules/*" \
  ! -path "*/.venv/*" ! -path "*/venv/*" ! -path "*/__pycache__/*" \
  ! -path "*/dist/*" ! -path "*/build/*" ! -path "*/scratch/*" \
  ! -path "*/attached_assets/*" ! -path "*/archive/*" ! -path "*/drafts/*" \
  ! -path "*/_old/*" ! -path "*/old/*" ! -path "*/backup/*" \
  ! -path "*/corpus/raw/*" | sort
```

Report file count and which default excludes applied before proceeding.

### Step G6: Check existing index state

Read `.rag-index/.index-manifest.json` if it exists.

- No manifest (first run): all discovered files need ingestion.
- Manifest exists (update run): compare — new files (ingest), modified files (re-ingest), deleted files (delete from index via `delete_file` MCP tool), unchanged files (skip). Report: "X new, Y modified, Z deleted, N unchanged."

If nothing changed: "Index is up to date." Stop.

### Step G7: Ingest files

For each file needing ingestion, call `ingest_file` MCP tool with absolute path. Process sequentially. Report progress every 10 files. If a file fails, log the error and continue.

The embedding model (~90MB) downloads on first use — warn the user.

### Step G8: Write manifest

Write `.rag-index/.index-manifest.json` with indexed files (paths, mtime, size) and `noise_scan` block if Step G0 produced one.

### Step G9: Confirm

Report:
- Files indexed
- Index location (`.rag-index/`)
- If first run: "Restart Claude Code for the MCP server to become active."
- How to search: "Ask questions naturally once the MCP server connects. The index supports semantic search — query by meaning, not just keywords."
- How to update: "Run `/sweetclaude:document-corpus` and select **Set up RAG** again to update the index when files change."

**Update project SOP:** After reporting, update `.sweetclaude/state/project-sop.md` — find the RAG Indexes table and update (or add) the row for this MCP with the scope used (canonical-only or full), today's date as Last Indexed, and a note if this was a canonical-only build. If `project-sop.md` does not exist, create it with just the RAG Indexes section populated — the MCP Tools and Corpus sections can be filled in by running `/sweetclaude:on`.

**Supported formats:** PDF, DOCX, TXT, Markdown. Excel and PowerPoint are not supported.

---

## Mode: Reindex RAG

Rebuild RAG collections from source files. Use when embeddings are corrupted, lost, or when the embedding model changes. This is a recovery tool, not a shortcut around the pipeline — if your source files are messy, the rebuilt index will be messy.

### Step X0: Preconditions

Read `corpus-pipeline.yaml`. If `pipeline.step` is not `idle`: warn and require override phrase.

Check RAG tooling is available. If not: "MCP RAG server not configured. Select **Set up RAG** first."

### Step X1: Choose scope

AskUserQuestion:
- "Canonical" — rebuild `{project}-canonical` from `corpus/canonical/`
- "Raw" — rebuild `{project}-raw` from `corpus/raw/inbox/`
- "All" — rebuild both

### Step X2: Execute reindex

For each selected collection:

Count files: `find corpus/{source_dir}/ -type f | wc -l`

Warn: "This will delete the existing index and rebuild from scratch. {N} files." AskUserQuestion: Proceed / Cancel.

Delete existing collection via MCP RAG server. Walk source directory recursively, skip binaries and files >1MB, index each file. Report progress every 100 files.

### Step X3: Report

```
Reindex Complete
════════════════

✓ {collection}: {N} files indexed
✓ {collection}: {N} files indexed
```

**Error handling:**
- RAG server connection fails: report and stop. The old collection was already deleted — the user must fix the RAG server and re-run.
- Individual file indexing fails: skip the file, continue, list skipped files at the end.
