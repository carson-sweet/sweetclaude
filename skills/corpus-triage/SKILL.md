---
spdx-license: AGPL-3.0-or-later
name: corpus-triage
user-invocable: true
description: "Classify files in corpus/raw/inbox/ as keep-as-is, needs-reconciliation, discard, or defer. Batch classification — fast decisions, no synthesis. Second step of the document-corpus pipeline; requires consolidate complete."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Run `/sweetclaude:setup` first." Then stop.
</preflight-guard>

# Corpus Triage

Classify files in `corpus/raw/inbox/` as keep-as-is, needs-reconciliation, discard, or defer. Batch classification — fast decisions, no synthesis.

## Step T0: Preconditions

**Check pipeline gate:**

Read `corpus-pipeline.yaml`. If it does not exist, stop: "Run `/sweetclaude:corpus-consolidate` first."

If `consolidate.status` is not `complete`, explain:
> "Triage requires consolidation to be complete first. Here is why: triage classifies the files that consolidation brought in. Without consolidation, triage has no defined inbox — it would be working on whatever happens to be in a directory, which may be your source files. Run `/sweetclaude:corpus-consolidate` first."

If the user insists: require `I accept the risk of corpus corruption`. Log override if accepted.

If `pipeline.step` is not `idle`: same override protocol.

Set pipeline state: `step: triaging`.

Ensure `corpus/raw/staged/` and `corpus/archive/` directories exist.

## Step T1: Inventory (subagent)

Spawn a subagent:

> Scan `corpus/raw/inbox/` recursively. For each file: full path relative to project root, file size, first 5 lines of content.
>
> Group files by top-level subdirectory within `corpus/raw/inbox/`. Report as a table per group with: file number, relative path, size, preview.
>
> Also report: total files, total size, number of source groups.
>
> Do nothing else.

Present summary: "corpus/raw/inbox/ contains {N} files across {M} source groups ({total_size}). Ready to triage."

## Step T2: Choose triage mode

Use AskUserQuestion:
- "By group" — triage one source group at a time (recommended for large corpora)
- "By file" — triage individual files (for small corpora)
- "Bulk classify" — classify an entire source group with one decision

## Step T3: Triage loop

**By-group mode:** For each source group, spawn a subagent per file to produce a one-paragraph summary (type, draft/final/superseded, version indicators, overlaps). Present summaries in batches of 10-20. Ask user to classify each: **keep** (ready as-is) / **reconcile** (needs merging) / **discard** (not useful) / **defer** (skip for now). Accept batch input like "1-5 keep, 6 discard, 7-8 reconcile".

**By-file mode:** Present one file at a time with AskUserQuestion: Keep / Reconcile / Discard / Defer.

**Bulk classify mode:** Show the group summary. AskUserQuestion: Keep all / Discard all / Defer all / Mix (switch to by-group for this group).

## Step T4: Execute classifications (subagent — per batch)

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

## Step T5: Summary and commit

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

Report: "Done. Next: run `/sweetclaude:corpus-reconcile` to process staged files into canonical documents."

**Error handling:**
- File move fails: skip the specific file, continue, log in summary.
- User classification unparseable: ask again with examples. Do not guess.
- Mid-triage stop: set `triage.status: in-progress`, set pipeline to idle. Resume picks up remaining inbox files.
