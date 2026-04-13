---
name: sweetclaude-strategy-reconciliation
description: "Onboard unstructured files into the strategy/ system. Inventory, categorize, version, and optionally synthesize canonical-draft documents from source materials. Use when starting a new strategy project with existing files, or when new files need to be incorporated into an organized corpus."
---

# Strategy File Reconciliation

Onboard unstructured files into `strategy/`, organize them, and optionally synthesize canonical-draft documents.

**This skill does NOT produce canonical documents.** It produces canonical-drafts that need user review, edits, and approval before promotion. Only the user can declare a document canonical.

---

## When to Use

- Starting a new project with existing strategy files (triggered by init)
- Incorporating new files received after initial setup (meeting notes, research, exports)
- Re-organizing after a batch of new materials arrives

---

## Process

### Step 1: Ensure Files Are in strategy/reconciliation/

If files are not already in `strategy/reconciliation/`:

> "I need the files in `strategy/reconciliation/` to work with them. Want me to copy them there? Originals stay untouched."

On confirmation, copy files. Do not move — never modify the source.

### Step 2: Create Inventory

**ENUMERATE EVERY FILE INDIVIDUALLY.** Do not categorize by directory. Do not generalize groups of files. Do not say "most of directory X is copies" without checking each file.

**Mandatory process:**
1. Run `find strategy/reconciliation/ -type f` to get a complete numbered list of every file (excluding archive/ and .DS_Store)
2. For EACH file — no exceptions — create a row in the inventory table
3. For files that appear to be duplicates, verify with a hash or diff. Do not assume based on filename.
4. After building the inventory, count the rows. The count MUST match the file count from step 1. If it doesn't, you missed files — go back and find them.

```markdown
# Reconciliation Inventory

Total files found: {N}
Total rows in inventory: {N} ← these MUST match

| # | File | Type | Topic | Category | Date | Summary | Recommendation |
|---|---|---|---|---|---|---|---|
| 1 | positioning-v2.md | markdown | SynCog architecture narrative | positioning | 2026-04-10 | Describes SynCog as graph of communicating state machines... | categorize |
| 2 | beat-3-defense.md | markdown | Defense Feeds the Attack section | academic | 2026-04-11 | Paper section on how defense mechanisms... | categorize |
| 3 | session-export.md | markdown | Claude session transcript | n/a | 2026-04-12 | Raw conversation about paper structure... | archive-only |
```

**Category** maps to strategy subdirectories:
- `positioning` → strategy/positioning/
- `competitive` → strategy/competitive/
- `market-messaging` → strategy/market-messaging/
- `biz-planning` → strategy/biz-planning/
- `academic` → strategy/academic/
- `meeting-prep` → strategy/meeting-prep/
- `narrative-arc` → strategy/narrative-arc/
- `decisions` → strategy/decisions/
- `n/a` → does not belong in any category (session exports, scratch files, duplicates)

**Recommendation** is one of:
- `categorize` — move to the appropriate category directory with versioned filename
- `merge-with: {target}` — content overlaps significantly with another file; merge during synthesis
- `archive-only` — useful for lineage but not worth synthesizing (raw transcripts, exports, superseded drafts)
- `discard` — duplicates, empty files, irrelevant content (requires user confirmation)

### Step 2.5: Self-Verify Inventory

Before presenting to the user, verify your own work:

1. Re-run the file count: `find strategy/reconciliation/ -type f | grep -v .DS_Store | grep -v '/archive/' | wc -l`
2. Count your inventory rows
3. If they don't match, find the missing files and add them
4. For every row marked `discard` (duplicate), confirm with `diff` or hash — not by filename alone
5. For every group you marked as "copies of what's in the repo," verify each file individually — mixed in among 20 copies there may be 2 unique files

**Do not present the inventory until the count matches.**

### Step 3: Present Inventory for Approval

Present the inventory table with the file count verification:

> "Found {N} files, inventoried {N} (verified match). Here's the breakdown. Review the categories and recommendations — I'll adjust anything you want to change before proceeding."

Wait for approval. Adjust as directed.

### Step 4: Reorganize

For each file with recommendation `categorize` or `merge-with`:

1. Determine a topic slug from the file's content (e.g., `syncog-architecture-description`, `cultivated-persona-paper-beat-3`)
2. Assign a version number based on file date ordering (earliest = lowest version)
3. Copy to the category directory with versioned filename:
   ```
   strategy/{category}/{topic-slug}-v{major}.{minor}.md
   ```
4. Add reconciliation frontmatter to the copy:
   ```yaml
   ---
   source: strategy/reconciliation/{original-filename}
   category: {category}
   topic: {topic-slug}
   version: {version}
   reconciled_date: {date}
   ---
   ```

For files with recommendation `archive-only`:
- Move to `strategy/reconciliation/archive/` with deprecation frontmatter:
  ```yaml
  ---
  status: archived
  reason: {why — e.g., "raw session transcript", "superseded by v0.3"}
  original_source: {original path before onboarding}
  archived_date: {date}
  category: {category or "n/a"}
  ---
  ```

For files with recommendation `discard`:
- Confirm with user before any deletion
- If confirmed, move to `strategy/reconciliation/archive/` with `status: discarded` (never actually delete)

### Step 5: Report Reorganization

```
Reorganization complete.

Files categorized: {N}
  positioning: {N}
  academic: {N}
  biz-planning: {N}
  ...
Files archived: {N}
Files discarded: {N}

Topic areas identified: {list of unique topic slugs with category}
```

### Step 6: Offer Synthesis

> "Files are organized. Want me to synthesize canonical-draft documents per topic area? This will combine related files into a single current-state document for each topic. These are drafts — you'll review and approve before they become canonical."

If user declines, stop here. The files are organized and discoverable.

If user accepts, proceed to Step 7.

### Step 7: Synthesis (per topic area)

For each unique topic slug:

1. Gather all files for that topic (across versions)
2. Apply the reconciling-documents extraction pattern:
   - Create `scratch/extraction-{topic-slug}.md`
   - Read each file, extract key info to the extraction file
   - Note conflicts, version differences, evolution of thinking
3. Ask the user:
   > "For {topic}, do you have a template, example, or specific sections/topics you want? Otherwise I'll use a default outline."
   - If user provides guidance, follow it
   - If not, propose an outline based on the content and ask for approval
4. Draft the canonical-draft document
5. Write to: `strategy/{category}/{topic-slug}-v{next-version}-canonical-draft.md`
6. Add frontmatter:
   ```yaml
   ---
   status: canonical-draft
   topic: {topic-slug}
   category: {category}
   version: {version}
   synthesized_from:
     - strategy/{category}/{topic-slug}-v0.1.md
     - strategy/{category}/{topic-slug}-v0.2.md
   synthesized_date: {date}
   ---
   ```
7. Move source files to archive with deprecation frontmatter:
   ```yaml
   ---
   status: deprecated
   incorporated_into: strategy/{category}/{topic-slug}-v{version}-canonical-draft.md
   original_source: {original path}
   archived_date: {date}
   category: {category}
   ---
   ```
8. Present the draft to the user:
   > "Here's the canonical-draft for {topic}. Review and edit it. When you're satisfied, tell me to promote it to canonical."

### Step 8: Promote to Canonical (user-driven)

When the user says a canonical-draft is ready:

1. Rename: `{topic-slug}-v{N}-canonical-draft.md` → `{topic-slug}-v{N}-canonical.md`
2. Update frontmatter: `status: canonical-draft` → `status: canonical`
3. Update all archive frontmatter that referenced the draft to point to the canonical file
4. Report: "{topic} is now canonical at v{N}."

### Step 9: RAG Ingestion

After canonical documents are created (or after reorganization if user skipped synthesis):

- Invoke `rag-index` to index or update the strategy/ directory
- Canonical docs are indexed
- Archived/deprecated files are NOT indexed
- canonical-draft files ARE indexed (they're the best available until promoted)

---

## Versioning Rules

- All files have a version: `{topic-slug}-v{major}.{minor}.md`
- `-canonical-draft` suffix: synthesized, awaiting user approval
- `-canonical` suffix: user-approved current truth
- Only one `-canonical` file per topic at any time
- When canonical gets revised: version bumps (v1.0 → v1.1), old canonical moves to archive
- Version numbers are assigned chronologically within a topic

## What This Skill Does NOT Do

- Does not delete any files (moves to archive instead)
- Does not produce canonical documents (only canonical-drafts)
- Does not synthesize without explicit user opt-in
- Does not touch `docs/` — strategy/ only
- Does not modify source files outside strategy/reconciliation/

## Cleanup

After all synthesis is complete, `strategy/reconciliation/` should contain only:
- `archive/` — deprecated originals with lineage frontmatter
- Any files the user hasn't categorized yet

Delete `scratch/extraction-*.md` files after synthesis is complete.
