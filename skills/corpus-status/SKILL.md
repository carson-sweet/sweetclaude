---
spdx-license: AGPL-3.0-or-later
name: corpus-status
user-invocable: true
description: "Show the current state of the document corpus pipeline — file counts in each stage, last-run timestamps per step, and recommended next action. Read-only. Part of the document-corpus pipeline; use /sweetclaude:document-corpus for the full menu."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Run `/sweetclaude:setup` first." Then stop.
</preflight-guard>

# Corpus Status

Show the current state of the corpus pipeline. Read-only — never modifies anything.

## Step S1: Read pipeline state

Read `.sweetclaude/state/corpus-pipeline.yaml`.

If it does not exist:
> "No corpus pipeline configured yet. Run `/sweetclaude:corpus-consolidate` to start, or `/sweetclaude:document-corpus` for the full menu."

Stop.

## Step S2: Count files (live from filesystem)

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

## Step S3: Present

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
- **Pipeline stuck:** `pipeline.step != idle` — "⚠ {step} did not complete. Run `/sweetclaude:corpus-{step}` to resume."
- **Working files not recently touched:** "⚠ {N} files in corpus/working/ may be from an abandoned reconciliation."
- **Staged files without triage metadata:** "⚠ {N} staged files have no triage metadata."
- **Canonical files not in RAG:** If RAG available, compare canonical count to RAG doc count — "⚠ {N} canonical files may not be indexed."

Suggest next action based on state:

| State | Recommendation |
|---|---|
| No pipeline state | "→ Run `/sweetclaude:corpus-consolidate` to start." |
| consolidate done, inbox has files, triage not started | "→ Run `/sweetclaude:corpus-triage` to classify {N} inbox files." |
| triage done, staged has files, reconcile not started | "→ Run `/sweetclaude:corpus-reconcile` to process {N} staged files." |
| reconcile done/in-progress, working has files | "→ Run `/sweetclaude:corpus-promote` to finalize {N} approved documents." |
| All steps complete | "✓ Pipeline complete. All files processed." |
| Pipeline stuck | "⚠ Resolve the interrupted {step} first." |
