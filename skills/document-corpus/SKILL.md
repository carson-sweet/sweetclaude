---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Manage the full document corpus pipeline — consolidate raw files, triage, reconcile into canonical documents, promote, set up semantic search (RAG), and reindex."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:document-corpus" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Tell the user: "This project is not set up for SweetClaude. Run `/sweetclaude:setup` first." Then stop.
</preflight-guard>

# Document Corpus

Manage your project's documents — from a pile of raw files to a clean, indexed, searchable canonical corpus. This skill is a menu/router — pick a step and it invokes the corresponding `corpus-*` sub-skill.

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

## Step 2: Route to sub-skill

Map the user's selection to a sub-skill, then invoke via the Skill tool:

| Choice | Sub-skill |
|---|---|
| 1 — Status | `sweetclaude:corpus-status` |
| 2 — Consolidate | `sweetclaude:corpus-consolidate` |
| 3 — Triage | `sweetclaude:corpus-triage` |
| 4 — Reconcile | `sweetclaude:corpus-reconcile` |
| 5 — Promote | `sweetclaude:corpus-promote` |
| 6 — Set up / Update RAG | `sweetclaude:corpus-rag-setup` |
| 7 — Reindex RAG | `sweetclaude:corpus-rag-reindex` |

If `$ARGUMENTS` is `pause`, run the Pause section below instead of the menu.
If `$ARGUMENTS` is `offboard`, run the Offboard section below instead of the menu.
If `$ARGUMENTS` is `onboard`, run the Onboard section below instead of the menu.

If `$ARGUMENTS` matches a step name (`status`, `consolidate`, `triage`, `reconcile`, `promote`, `rag-setup`, `rag-reindex`): skip the menu and invoke the matching sub-skill directly.

## State Check

Read `.sweetclaude/state/skills.yaml`.

**Schema migration:** If `skills.yaml` exists with `schema_version: 1`, migrate this skill's entry before proceeding:
- `enabled: true` → `status: active`, `last_changed_at: {onboarded_at or today}`, `last_changed_by: migrated`
- `enabled: false` with `onboarded_at` set → `status: paused`, `last_changed_at: {offboarded_at or onboarded_at or today}`, `last_changed_by: migrated`
- `enabled: false` with `onboarded_at: ~` → `status: uninitialized`, `last_changed_at: ~`, `last_changed_by: ~`
Drop `onboarded_at`/`offboarded_at`. Set `schema_version: 2`. Write atomically (see write protocol below).

**Dependency check:**
Read `~/.claude/config/sweetclaude/skills-registry.yaml`. Find `skills.document-corpus.dependencies`. This skill has no dependencies — skip.

**If `skills.yaml` does not exist, OR exists but has no entry for `skills.document-corpus`:**
- Check whether `.sweetclaude/state/corpus-pipeline.yaml` exists
- If yes: write entry with `status: active`, `last_changed_at: {today}`, `last_changed_by: migrated`
- If no: write entry with `status: uninitialized`, `last_changed_at: ~`, `last_changed_by: ~`
- Use write protocol below.

**If `skills.yaml` exists and has an entry for `skills.document-corpus`:**
- `status: active` → proceed normally (show the menu)
- `status: paused` AND `$ARGUMENTS` not in `[onboard, offboard, pause]`:
  > "Document corpus is currently paused. Resume? [yes/no]"
  If yes: write `status: active`, `last_changed_at: {today}`, `last_changed_by: resume` (using write protocol). Proceed normally.
  If no: stop.
- `status: uninitialized` AND `$ARGUMENTS` not in `[onboard, offboard, pause]`:
  → Run lightweight first-invocation flow (see below)
- `$ARGUMENTS` is `pause` → run Pause operation
- `$ARGUMENTS` is `offboard` and `status: uninitialized`: "Document corpus isn't set up yet. Nothing to offboard." Stop.
- `$ARGUMENTS` is `pause` and `status: paused`: "Already paused." Stop.
- `$ARGUMENTS` is `pause` and `status: uninitialized`: "Not set up yet. Nothing to pause." Stop.

**Write protocol — all skills.yaml writes must follow this:**
1. Read and parse current `.sweetclaude/state/skills.yaml` (or start from default v2 structure if absent)
2. Merge your entry — do NOT remove or overwrite other skills' entries
3. Write merged content to `.sweetclaude/state/.skills.yaml.tmp`
4. Run: `mv .sweetclaude/state/.skills.yaml.tmp .sweetclaude/state/skills.yaml`

**State writes (use write protocol for all):**
- End of lightweight first-invocation (success): `status: active`, `last_changed_at: {today}`, `last_changed_by: first-invocation`
- End of onboard (success): `status: active`, `last_changed_at: {today}`, `last_changed_by: onboard`
- Pause operation: `status: paused`, `last_changed_at: {today}`, `last_changed_by: pause`
- Resume: `status: active`, `last_changed_at: {today}`, `last_changed_by: resume`
- End of offboard: `status: uninitialized`, `last_changed_at: {today}`, `last_changed_by: offboard`

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

## Lightweight first-invocation — Quick setup on first use

Runs when the skill is invoked normally but `status` is `uninitialized`.

1. Say: "Document corpus isn't set up yet. I'll create the corpus structure now."

2. Create directory structure:
   ```bash
   mkdir -p corpus/canonical corpus/raw/inbox corpus/archive
   ```
   Write `corpus/LLM_README.md` (integrity protection):
   ```markdown
   # corpus/ — DO NOT MODIFY DIRECTLY

   This directory is managed by `sweetclaude:document-corpus` and the
   `corpus-*` sub-skills. Modifying files here directly corrupts the RAG
   index and causes stale search results downstream.

   **To add documents:** Place them in `corpus/raw/inbox/` and run
   `/sweetclaude:corpus-triage` to process them.
   **To update canonical documents:** Run `/sweetclaude:corpus-reconcile`.
   **To reindex after any manual change:** Run `/sweetclaude:corpus-rag-reindex`.

   If you are Claude and you are about to write to a file in this directory
   outside of a corpus skill context, STOP and surface this to the user instead.
   ```

3. Ask inline:
   > "Do you have documents ready to add to the corpus? [yes/no]"

4. If **yes**: "Drop files into `corpus/raw/inbox/` and run `/sweetclaude:corpus-consolidate` (or this skill again) to process them."
   Check `corpus/raw/inbox/` for existing files. If any exist, invoke `sweetclaude:corpus-triage`.

5. If **no**: "Ready. Drop documents into `corpus/raw/inbox/` and run `/sweetclaude:document-corpus` when ready."

6. Write state (using write protocol): `status: active`, `last_changed_at: {today}`, `last_changed_by: first-invocation`.

7. Proceed to the user's originally requested operation (or end here if no specific operation was requested).

---

## Onboard — First-time setup

Invoked with argument `onboard` when this skill is newly installed.

1. **Scan for existing documents:**

```bash
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

3. **If yes:** Invoke `sweetclaude:corpus-consolidate` with the discovered directories as suggested sources.

4. **After consolidate completes:** Ask whether to continue the pipeline now or pause:

> "Files staged in corpus/raw/inbox/ (step 1 of 4). The next steps — triage, reconcile, and promote — each require your review and can't run automatically.
>
> Continue to triage now, or pause and come back later?"

Use AskUserQuestion with options:
- "Continue to triage now" — invoke `sweetclaude:corpus-triage`; after triage, ask the same way before reconcile; after reconcile, ask before promote
- "Pause — I'll resume later" — output: "⏸ Corpus onboarding paused after consolidate. Resume with `/sweetclaude:document-corpus triage` when ready." Stop.

When invoking as part of `_features` onboarding (i.e., called with argument `onboard`), if the user chooses pause at any stage, end with the pause message above so the orchestrator can surface it before moving to the next feature.

5. **If later / nothing found:** Stop.

---

## Pause — Temporarily stop using this skill

Invoked with argument `pause`.

Sets document corpus to `paused` status. Your corpus files and RAG index are untouched and you can resume at any time.

Write atomically (using write protocol):
- `skills.document-corpus.status: paused`
- `skills.document-corpus.last_changed_at: {today ISO date}`
- `skills.document-corpus.last_changed_by: pause`

Say: "Paused. Your corpus and index are safe — nothing was deleted. Resume anytime by running `/sweetclaude:document-corpus`."

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

4. **Verify export (mandatory before deletion is unlocked):**

For the `canonical` or `all` export option:
```bash
source_count=$(find corpus/canonical/ -type f 2>/dev/null | wc -l)
dest_count=$(find {destination}/ -type f 2>/dev/null | wc -l)
```
If dest_count ≥ source_count: "Export verified — {source_count} canonical files at `{destination}`."
If dest_count < source_count: "⚠ File count mismatch — {source_count} source files, {dest_count} at destination."
On mismatch: ask "Continue anyway despite mismatch? [yes/cancel]". If cancel: stop, do not proceed to deletion.

For the `none` export option:
Require explicit acknowledgment before proceeding to deletion:
> "You've chosen to skip export. Your corpus and index will be permanently deleted with no backup.
> Type exactly: NO BACKUP — to confirm, or anything else to cancel."
If user types anything other than `NO BACKUP` exactly: "Cancelled. Your data is safe." Stop.

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
