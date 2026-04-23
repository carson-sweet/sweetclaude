---
description: "Show the current state of the corpus pipeline. Read-only — always allowed, never gated. Counts files, shows pipeline step, recommends next action."
---

# SweetClaude Corpus Status

Show the current state of the corpus pipeline. Read-only — never modifies anything, never gated.

---

## Process

### Step 1: Read pipeline state

Read `.sweetclaude/state/corpus-pipeline.yaml`.

If it does not exist:
> "No corpus pipeline configured. Run `/sweetclaude:corpus-consolidate` to start."

Stop.

### Step 2: Count files (live from filesystem)

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

### Step 3: Present status

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

### Step 4: Warnings

Check for anomalies and report:

- **Pipeline stuck:** `pipeline.step != idle` — "⚠ {step} did not complete. Run `/sweetclaude:corpus-{step}` to resume."
- **Working files older than 24 hours:** Files in `corpus/working/` that have not been modified recently — "⚠ {N} files in corpus/working/ may be from an abandoned reconciliation."
- **Staged files without triage metadata:** Files in `corpus/raw/staged/` with no `.triage.json` — "⚠ {N} staged files have no triage metadata."
- **Canonical files not in RAG:** If RAG is available, compare canonical file count to RAG document count — "⚠ {N} canonical files may not be indexed."

### Step 5: Recommend next action

Based on the current state, suggest one action:

| State | Recommendation |
|---|---|
| No pipeline state | "→ Run `/sweetclaude:corpus-consolidate` to start the pipeline." |
| consolidate complete, inbox has files, triage not started | "→ Run `/sweetclaude:corpus-triage` to classify {N} inbox files." |
| triage complete, staged has files, reconcile not started | "→ Run `/sweetclaude:corpus-reconcile` to process {N} staged files." |
| reconcile complete/in-progress, working has files | "→ Run `/sweetclaude:corpus-promote` to finalize {N} approved documents." |
| All steps complete, everything empty | "✓ Pipeline complete. All files processed." |
| Pipeline stuck | "⚠ Resolve the interrupted {step} first." |
