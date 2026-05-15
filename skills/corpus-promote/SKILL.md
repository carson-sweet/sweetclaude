---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Finalize approved documents from corpus/working/."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:corpus-promote" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Run `/sweetclaude:setup` first." Then stop.
</preflight-guard>

# Corpus Promote

Finalize approved documents from `corpus/working/`. Move to `corpus/canonical/`, write provenance sidecars, archive source files, index into RAG, commit. No creative decisions — pure finalization.

## Step P0: Preconditions

**Check pipeline gate:**

Read `corpus-pipeline.yaml`. If `reconcile.status` is not `complete` and not `in-progress`, explain:
> "Promote finalizes documents that reconcile approved. Without reconcile, there is nothing in corpus/working/ to promote — promote does not create canonical documents, it only moves already-approved ones into place. Run `/sweetclaude:corpus-reconcile` first."

If the user insists: require `I accept the risk of corpus corruption`.

Check `corpus/working/` has files. If empty: "Nothing to promote. Run `/sweetclaude:corpus-reconcile` first to create approved documents."

Set pipeline state: `step: promoting`.

Ensure `corpus/canonical/{strategic,product,design,research,operations}/` and `corpus/archive/` exist.

## Step P1: Inventory working documents (subagent)

Spawn a subagent:

> Scan `corpus/working/`. For each file: path, size, first 10 lines, content type (strategy / product / design / research / operations).
>
> Also scan `corpus/raw/staged/` for `.triage.json` metadata referencing the source files. Collect source file paths.
>
> Report for each: `{filename}`, content type, size, suggested target in `corpus/canonical/{subdir}/`, source files if traceable.
>
> Do nothing else.

## Step P2: Confirm promotion plan

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

## Step P3: Execute promotion (one document at a time, atomic)

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

## Step P4: Update state and report

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
