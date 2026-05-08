---
spdx-license: AGPL-3.0-or-later
name: corpus-reconcile
user-invocable: true
description: "Take staged files and work with the user to produce approved canonical documents in corpus/working/. Drafting, merging, refining. Third step of the document-corpus pipeline; requires triage complete."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Run `/sweetclaude:setup` first." Then stop.
</preflight-guard>

# Corpus Reconcile

Take staged files and work with the user to produce approved canonical documents in `corpus/working/`. This is the creative work — drafting, merging, refining.

## Step R0: Preconditions

**Check pipeline gate:**

Read `corpus-pipeline.yaml`. If `triage.status` is not `complete`, explain:
> "Reconcile requires triage to be complete first. Here is why: triage decided which files are worth synthesizing. Running reconcile without triage means you would be trying to draft canonical documents from files you have not evaluated — including files you would have discarded in 30 seconds. Run `/sweetclaude:corpus-triage` first."

If the user insists: require `I accept the risk of corpus corruption`.

Set pipeline state: `step: reconciling`.

**Check for active cluster from previous session:** If `reconcile.active_cluster` is not null, offer Resume (continue that cluster) or Start fresh (move working files back to staged).

## Step R1: Inventory staged files (subagent)

Spawn a subagent:

> Scan `corpus/raw/staged/` recursively (skip `.triage.json` files). For each file: path, size, first 10 lines, triage classification if metadata exists.
>
> Group files into clusters by topic using: filename similarity, content overlap, source group, triage metadata.
>
> Present as clusters with a table per cluster. List unclustered files separately.
>
> Do nothing else.

Present: "corpus/raw/staged/ contains {N} files in {M} clusters. Pick a cluster to reconcile."

## Step R2: Select cluster

Present cluster list. Ask which to work on. Move selected files to `corpus/working/`. Update `reconcile.active_cluster`.

## Step R3: Analyze cluster (subagent per file)

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

## Step R4: Present proposals

For each file:
```
{filename}
  Action:    {action}
  Target:    {target_canonical}
  Rationale: {rationale}
  Conflicts: {conflicts or "none"}
```

Ask: "Approve these recommendations, or adjust? Change any by number."

## Step R5: Draft canonical documents

**copy:** File becomes canonical as-is. Present for confirmation.

**supersede:** File replaces existing canonical. Show what changes. Confirm.

**merge:** Read all files targeted at the same canonical document. Draft a merged document that preserves current and accurate content from each source, resolves conflicts (present conflicts to user for decision), and does not lose substantive content without approval. Present draft for review.

**discard:** Confirm with user, then archive with sidecar.

## Step R6: Refine

Iterate with the user until they approve each document. This may take multiple rounds. Present draft → accept feedback → produce updated draft → repeat.

**Do not push for approval. Do not ask "is this ready?" The user decides when a document is done.**

When approved, write to `corpus/working/{canonical-name}.md`.

## Step R7: Checkpoint per approved document

```bash
git add corpus/working/
git commit -m "reconcile: draft approved — {canonical-name}"
```

## Step R8: Continue or finish

If more clusters remain: offer to continue with another cluster or stop.

If stopping mid-way:
```yaml
pipeline:
  step: idle
reconcile:
  status: in-progress
  active_cluster: null
```

Report: "{N} approved documents in corpus/working/ ready for promotion. {M} files remain in staged. Run `/sweetclaude:corpus-promote` to finalize approved documents, or `/sweetclaude:corpus-reconcile` again to continue with staged files."

If all staged files processed, set `reconcile.status: complete`.

**Error handling:**
- Subagent returns invalid JSON: re-run once. If fails again, present file to user directly without recommendation.
- User wants to move a file back to staged: do it. This is normal.
- Merge has unresolvable conflicts: defer the cluster, move files back to staged.
