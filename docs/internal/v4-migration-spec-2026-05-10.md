# v4 Migration Spec
**Version:** 2.0
**Date:** 2026-05-12
**Status:** Implementation ready — caucus 3 findings resolved; A1/A3/A4/B1/B3/B4/D3 fixed 2026-05-13
**Canonical schema reference:** [`v4-story-schema.md`](v4-story-schema.md)
**Recovered from:** Session 41d83490 (00:20–14:10 UTC) after session crash
**Revision history:**
- v2.0 (2026-05-12) — caucus 3 findings incorporated: off-tree backup, gitignore detection, atomic finalize, input/output reconciliation, mkdir-based lock, status remap completeness, MIGRATION-MAP location, bootstrap state-flag detection, Phase 1 scope expansion, release gates strengthened
- v1.3 (2026-05-10) — renamed "Preflight" section to "Bootstrap Hard Stop"
- v1.2 (2026-05-10) — Step 7 to full verification, Promoting Stories auto-stage scope, added MIGRATION-MAP to finalize, synced release gates
- v1.1 (2026-05-10) — lock file, backup integrity, delete safety, "Not now" policy, hard stop message, ID map, scale guards, failure menu reframing
- v1.0 (2026-05-10) — two prior caucus rounds (C1–C38)

---

## Summary

v4 is a breaking change to how stories are stored. This document specifies the migration path from v3 to v4, the safety protocol, the failure handling flow, and the user-facing communication strategy.

---

## Core Principles

1. **No split upgrade.** "Upgrade framework now, migrate data later" is rejected. Migration happens project-by-project at first open.
2. **v4 hard-blocks on v3 artifacts.** Not a warning — a full stop.
3. **Create v3-final safety branch before any implementation.**
4. **Auto-restore on failure.** Backup → migrate → verify. Any failure rolls back automatically.
5. **Tell the user exactly what failed.** Specific file, specific field, specific value.
6. **Done items are optional to migrate. Active and future items must migrate.**
7. **Do not ship v4 publicly until all release gates pass.**

---

## Before Any Implementation: v3-Final Safety Branch

```bash
git checkout -b v3-final
git push origin v3-final
```

This is the rollback target for the entire initiative. Every v4 change is built off `main` in feature branches. `v3-final` is never touched after creation.

---

## Phased Implementation

Phases are scoped by what makes the day-one v4 experience work. Phase 1 includes everything required for "the user updates to v4, runs migration, and their orientation and backlog skills still function." Phase 2 adds roadmap operations. Phase 3 adds Shape Up and cleanup.

### Phase 1 — Backlog + Day-One Orientation

**Migration:**
- `sweetclaude:migrate` skill (steps 1–8 of this spec)
- `sweetclaude:migrate-diagnose` subskill
- Bootstrap hard-stop using state-flag detection (see Bootstrap section)

**Backlog skills (write-side):**
- `project-issues` — full rewrite, no sc-artifact dependency
- `project-backlog` — full rewrite
- `project-backlog-triage` — full rewrite
- `project-gh-import-issues` — rewrite description + behavior to produce v4 stories
- `project-gh-sync-issues` — rewrite description + behavior

**Orientation skills (read-side, day-one critical):**
- `status` — replace `BL-*.md` globs with v4 backlog scan
- `go` — replace `BL-*.md` globs; update git-log regex to detect both `BL-NNN` and `STORY-NNN`/`BUG-NNN`/etc.
- `big-picture` — replace `BL-\d+` regex throughout; read v4 INDEX.md
- `recap` — read from v4 location

**Branch/commit convention skills:**
- `code-feature` — branch naming uses new prefix (`STORY-NNN/`, `BUG-NNN/`)
- `code-issue` — detection supports both v3 (`BL-NNN/`, `issue-N/`) and v4 prefixes
- `code-tdd` — commit prefix uses new ID format

**Support skills:**
- `fix-sweetclaude` — update its path-ownership table to v4 layout

**Docs (per-skill rule):**
Every skill rewritten in Phase 1 ships with its `docs/user-guide/skills-reference.md` row updated in the same commit. Additionally, before Phase 1 closes:
- `docs/user-guide/getting-started.md` updated
- `docs/user-guide/quickstart.md` updated
- `docs/user-guide/state-and-memory.md` updated
- `docs/user-guide/v4-migration-guide.md` created
- `docs/user-guide/planning-concepts.md` created
- `CHANGELOG.md` created with v4.0.0 entry

### Phase 2 — Roadmap

- Roadmap directory structure (per design doc)
- Story promotion flow (backlog → roadmap)
- `project-epics` rewrite (no sc-artifact)
- `project-sprints` rewrite (no sc-artifact; uses new SPRINT-NNN schema)
- `product-milestones` rewrite
- `product-sprint-plan` rewrite
- `epic-design` rewrite (writes to new locations)
- Sprint file schema implementation (per `v4-story-schema.md` §5)
- Sprint-on-story sync (Sprint History body table maintenance)
- Documentation updates for all Phase 2 skills

### Phase 3 — Shape Up + Cleanup

- Shape Up mode design (deferred — user is studying Shape Up methodology)
- Roadmap document generation skill
- Full skill audit — remaining skills that touch product paths
- v3 artifact cleanup utilities

Each phase ships from a feature branch reviewed before merging to `main`. Phase 1 must be smoke-tested end-to-end (real project) before opening Phase 2's branch.

---

## Bootstrap Hard Stop on v3 Artifacts

### Detection

Bootstrap detects v3 → v4 migration need by reading **state**, not file presence. The migration-complete state lives in `.sweetclaude/state/sweetclaude.yaml` under `framework.v4.migration_complete: true`. This is set atomically as the final step of finalize (Step 8.2).

Detection logic:
1. Framework version is `4.x.x` (from `framework.installed_version` in `sweetclaude.yaml`)
2. AND `framework.v4.migration_complete` is missing or `false`
3. AND ANY of the following v3 story artifacts exist:
   - `.sweetclaude/product/backlog/` (directory exists, with or without `BL-NNN-*.md` files)
   - `.sweetclaude/product/issues/` (legacy v3 `I-NNN-*.md` location)
   - Any other story-bearing path listed in v3's `artifact-privacy.yaml` `categories.product.base_path` that contains markdown files

→ **full stop**.

**Sprint artifacts (`.sweetclaude/product/sprints/`) are NOT included in this detection** in Phase 1. v4 sprint schema is new and Phase 1 migration only handles stories. If a project has v3 sprint artifacts AND v3 stories, the story migration runs in Phase 1; sprint artifacts remain in v3 location and are recorded in MIGRATION-MAP.md `Skipped` section as `type: sprint, migrated: no, reason: deferred to Phase 2`. Phase 2 will add sprint migration with bootstrap detection extended to cover sprints.

If a project has ONLY v3 sprint artifacts and no stories: bootstrap does not hard-stop in Phase 1 (no stories to migrate). The sprint artifacts remain in their v3 location. Phase 2 will surface this state.

If the user kept v3 files after Step 8.4's cleanup offer, they are NOT re-prompted because `migration_complete: true` is set regardless of the cleanup decision.

If `migration_complete: true` is set but v3 files exist (declined cleanup): bootstrap proceeds normally. No hard stop.

### Message

The hard-stop message:

```
This project has v3 SweetClaude data that needs to migrate before v4 can run.

Found:
  - N stories in .sweetclaude/product/backlog/
  - N sprint artifacts (if any)
  - N issue artifacts (if any)

Migration creates an off-tree safety backup at ~/.sweetclaude/backups/{project}/
plus an in-tree backup. Your current work is not affected. A clean git working
tree is not required to migrate.

Migration is irreversible-ish: you can roll back to v3 from the backup, but
that means re-installing the v3 framework. See:
  docs/user-guide/v4-migration-guide.md

Run: /sweetclaude:migrate

To stay on v3: roll back the framework to the most recent v3.x.x release.
```

No skill executes. No workaround.

### Skill naming reconciliation

The public skill name is `sweetclaude:migrate` (no underscore). This is the user-facing entry point. Bootstrap invokes the internal `sweetclaude:_migrate` skill (with underscore) which actually executes the migration runner — this distinction is invisible to the user. The hard-stop message tells the user to run `/sweetclaude:migrate`; the public skill is a thin wrapper that invokes `_migrate` with v4-migration parameters.

---

## Update Skill: Pre-Upgrade Communication

`sweetclaude:update` surfaces this before installing v4:

```
SweetClaude v4 is available — this is a major release.

The biggest change: stories move from .sweetclaude/ to docs/product/ in a new
per-type directory structure with new IDs. Each project migrates independently
the first time you open it after updating.

Migration creates a safety backup and can be rolled back. Active and future 
stories must migrate. Done stories are optional.

Not ready? You can stay on v3: [Not now]

Update to v4? [Yes / Not now — I'll ask again when you run sweetclaude:update]
```

"Upgrade to v4, migrate later" is not offered — that path is rejected.

**"Not now" behavior:** The update skill sets `framework.update.declined: true` in `sweetclaude.yaml`. Bootstrap and session start do NOT re-offer the update. The update is only re-surfaced when the user explicitly runs `sweetclaude:update` again. This is the same behavior as any other declined update.

---

## Migration Flow

### Step 0: Preflight — `.gitignore` check

Before any backup or write, the migration must confirm that `docs/product/` will be visible to git. Many repositories use a `docs/` denylist pattern (e.g. `/docs/*` followed by allowlist entries for selected subdirectories). On such repos, v4 would silently gitignore product data including `MIGRATION-MAP.md` — the only mapping from v3 to v4 IDs.

```bash
# Probe the intended target path
PROBE_PATH="docs/product/INDEX.md"
if git check-ignore "$PROBE_PATH" >/dev/null 2>&1; then
  # The probe path would be ignored
  IGNORE_LINE=$(git check-ignore -v "$PROBE_PATH" 2>/dev/null | head -1)
  echo "ABORT: docs/product/ would be silently gitignored on this repo."
  echo "Ignore source: $IGNORE_LINE"
  echo ""
  echo "Suggested fix: add an allowlist line to your .gitignore:"
  echo "  !/docs/product/"
  echo ""
  echo "Without this, v4 migration would hide your stories AND MIGRATION-MAP.md"
  echo "(the only record of how BL-NNN IDs map to STORY-NNN/BUG-NNN/etc)."
  echo ""
  echo "Edit .gitignore, then re-run /sweetclaude:migrate."
  exit 1
fi
```

This check is a **hard stop**. There is no override. The migration cannot proceed because the user's data would be invisible to source control without their informed consent.

Once the user adjusts `.gitignore` and re-runs migration, the check passes and migration proceeds.

After Step 8 finalize succeeds, the user is asked whether to add `/docs/product/` to `.gitignore` (commit planning data vs. keep local) — see `.gitignore Handling` in the design doc.

---

### Step 1: Pre-migration backup + lock

#### 1a. Acquire migration lock (atomic via `mkdir`)

The lock is a directory, not a file. Directory creation is atomic on POSIX filesystems — `mkdir` either succeeds (acquires the lock) or fails with `EEXIST` (lock held). No check-then-write race.

```bash
LOCK_DIR=".sweetclaude/state/migration.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  # Lock held — surface to user
  if [ -f "$LOCK_DIR/owner" ]; then
    OWNER_INFO=$(cat "$LOCK_DIR/owner")
    echo "Migration lock held by: $OWNER_INFO"
    echo "If this is a stale lock from a crashed session, remove it manually:"
    echo "  rm -rf '$LOCK_DIR'"
  else
    echo "Migration lock exists but has no owner record — likely stale"
    echo "Remove it manually with: rm -rf '$LOCK_DIR'"
  fi
  exit 1
fi
# Record owner info for stale-lock diagnosis
cat > "$LOCK_DIR/owner" <<EOF
started: $(date -u +%Y%m%dT%H%M%SZ)
pid: $$
user: $(whoami)
branch: $(git branch --show-current 2>/dev/null || echo unknown)
EOF
trap "rm -rf '$LOCK_DIR'" EXIT
```

The lock is released on every exit path (success, failure, crash) via the trap. Stale-lock detection cannot reliably check PID liveness from a Claude Code skill, so on EEXIST the user is shown the owner record and asked to remove the lock manually if they're confident the original session is dead.

#### 1b. Capture pre-migration `docs/product/` state

Auto-restore must return the project to its previous state on failure — including any pre-existing `docs/product/` content the user had. Capture both a boolean flag and (if the directory exists) a full snapshot tarball.

```bash
if [ -d docs/product ]; then
  echo "yes" > "$LOCK_DIR/docs-product-pre-existed"
  # Snapshot pre-existing content so auto-restore can return to this state
  tar -czf "$LOCK_DIR/docs-product-pre.tar.gz" docs/product/
  # Verify the snapshot is readable before proceeding
  if ! tar -tzf "$LOCK_DIR/docs-product-pre.tar.gz" >/dev/null 2>&1; then
    echo "Failed to snapshot pre-existing docs/product/ — aborting"
    rm -rf "$LOCK_DIR"
    exit 1
  fi
else
  echo "no" > "$LOCK_DIR/docs-product-pre-existed"
fi
```

The off-tree backup created in Step 1c does NOT cover `docs/product/` because the off-tree backup is rooted at `.sweetclaude/`. The pre-existing-`docs/product/` snapshot is its own tarball stored inside the lock directory. It is read by the auto-restore procedure (see Failure Handling) and discarded when migration succeeds and the lock directory is removed.

#### 1c. Create two backups: in-tree + off-tree

The in-tree backup is convenient. The off-tree backup is the **insurance policy** that survives even if the project directory itself is corrupted, wiped, or destroyed by Option 2 of the failure menu.

```bash
BACKUP_DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "nosha")
PROJECT_SLUG=$(basename "$(pwd)")
BACKUP_NAME="pre-v4-${BACKUP_DATE}-${BACKUP_SHA}.tar.gz"

# Off-tree backup (primary insurance)
OFFTREE_BACKUP_DIR="$HOME/.sweetclaude/backups/$PROJECT_SLUG"
mkdir -p "$OFFTREE_BACKUP_DIR"
OFFTREE_BACKUP="$OFFTREE_BACKUP_DIR/$BACKUP_NAME"

# In-tree backup (convenience copy)
INTREE_BACKUP_DIR=".sweetclaude/state/backups"
mkdir -p "$INTREE_BACKUP_DIR"
INTREE_BACKUP="$INTREE_BACKUP_DIR/$BACKUP_NAME"

# Write the archive to a tmp location OUTSIDE .sweetclaude/ first so tar
# doesn't include its own destination in the archive
TMP_BACKUP=$(mktemp -t pre-v4-XXXXXX.tar.gz)
tar -czf "$TMP_BACKUP" --exclude='.sweetclaude/state/backups' .sweetclaude/

# Validate the tmp backup with actual extraction (not just header read)
TMP_VERIFY=$(mktemp -d -t verify-XXXXXX)
if ! tar -tzf "$TMP_BACKUP" >/dev/null 2>&1; then
  echo "Backup creation failed: archive header unreadable"
  rm -rf "$TMP_BACKUP" "$TMP_VERIFY"
  exit 1
fi
# Sample-extract 3 files to confirm data integrity, not just TOC.
# Paths from `tar -tzf` are relative to the tar root (e.g. ".sweetclaude/state/...").
# Extraction with -C "$TMP_VERIFY" reconstructs them under TMP_VERIFY using the
# same relative paths. We compare extracted-file size against source-file size
# (where source path == the tar entry path, since pwd is the project root).
SAMPLE_FILES=$(tar -tzf "$TMP_BACKUP" | grep -v '/$' | shuf -n 3 2>/dev/null || tar -tzf "$TMP_BACKUP" | grep -v '/$' | head -3)
for f in $SAMPLE_FILES; do
  if ! tar -xzf "$TMP_BACKUP" -C "$TMP_VERIFY" "$f" 2>/dev/null; then
    echo "Backup integrity check failed: cannot extract $f"
    rm -rf "$TMP_BACKUP" "$TMP_VERIFY"
    exit 1
  fi
  # The source path is $f (already relative to project root).
  # The extracted path is $TMP_VERIFY/$f.
  if [ -s "$f" ] && [ ! -s "$TMP_VERIFY/$f" ]; then
    echo "Backup integrity check failed: $f is non-empty in source but empty in archive"
    rm -rf "$TMP_BACKUP" "$TMP_VERIFY"
    exit 1
  fi
done
rm -rf "$TMP_VERIFY"

# Both backup copies (verified)
cp "$TMP_BACKUP" "$OFFTREE_BACKUP"
cp "$TMP_BACKUP" "$INTREE_BACKUP"
rm -f "$TMP_BACKUP"
```

If any backup or verification step fails: warn and ask before proceeding. Never continue without a verified backup.

#### 1d. Retention

Both locations retain the **last 5 backups**. Pruning happens after the new backup is verified, not before — so a verification failure never leaves the user with fewer backups than they had before.

```bash
for dir in "$OFFTREE_BACKUP_DIR" "$INTREE_BACKUP_DIR"; do
  ls -1t "$dir"/pre-v4-*.tar.gz 2>/dev/null | tail -n +6 | xargs -r rm -f
done
```

### Step 2: Pre-migration validation manifest

Before writing a single file, scan every v3 story file (in `.sweetclaude/product/backlog/BL-NNN-*.md`, `.sweetclaude/product/issues/I-NNN-*.md`, and any other v3 product paths listed in the v3 `artifact-privacy.yaml`) and validate each:

**Per-file checks:**
- File can be read (permissions, not corrupted)
- Strip UTF-8 BOM (`\xEF\xBB\xBF`) and normalize CRLF to LF before any parsing
- File has a `---` frontmatter delimiter (report "no frontmatter delimiter" as a named error, distinct from "frontmatter parse error")
- YAML frontmatter is parseable (after BOM strip and line-ending normalization)
- Required fields present: `id`, `type`, `title`, `status`
- `status` value is in the known v3 enum: `backlog`, `ready`, `in_progress`, `in_review`, `blocked`, `deferred`, `done`, `cancelled`, `active`
- `type` value is in the known v3 enum: `story`, `bug`, `chore`, `spike`
- Filename `id` component (e.g. `BL-042` in `BL-042-add-oauth.md`) matches the `id` field in frontmatter
- If `sprint_history` field is present in frontmatter, it parses as a list (the v3 sprint_history array shape)

**Cross-file checks:**
- No duplicate `id` values across all v3 story files (report each duplicate pair)

**Manifest output:**
The validation produces an in-memory or written manifest of:
- Total file count by source path
- Total file count by v3 type
- Total file count by v3 status (so the active vs done split is known before Step 3)
- Per-file: source path, v3 id, v3 type, v3 status, planned v4 type, planned v4 id

This manifest drives the preview (Step 4) and the input/output reconciliation (Step 7).

**If any file fails validation:** report all problems, stop. Do not migrate anything. Offer to run `sweetclaude:migrate-diagnose`.

This catches silent corruption before it happens — a failed migration that reports success is worse than one that stops loudly.

### Step 3: Done item choice

```
Found N completed stories (status: done or cancelled).

Migrate them too? They'll get new IDs and move to done/ subdirectories.
Or skip — they stay in v3 format as historical artifacts.

[Migrate all / Skip done items / Show me the list first]
```

**"Show me the list first"** displays done items paginated at 30 rows with title and current status. At each page: `[Migrate all shown / Skip all shown / Continue to next page]`. After reviewing all pages, the user returns to the Migrate all / Skip done items prompt.

### Step 4: Preview

Show the user: counts by type, field remappings, backup location.

```
v4 Migration Preview
────────────────────
N active/future stories · N done stories (if included)

Changes:
  .sweetclaude/product/backlog/   →  docs/product/backlog/{type}s/
  BL-NNN IDs                      →  STORY-NNN / BUG-NNN / DEBT-NNN / CHORE-NNN
  status "backlog"                →  "new"
  status "cancelled"              →  "abandoned"
  source field                    →  origin field
  sprint_history (frontmatter)    →  Sprint History (body section)
  done stories                    →  docs/product/backlog/{type}s/done/

Unchanged: content, descriptions, acceptance criteria, priority, tags

Backup: {BACKUP_FILE}

Proceed? [Yes / Show me each story / Cancel]
```

**"Show me each story"** displays the full ID mapping table before the user confirms:

```
BL-001  →  STORY-001  add-oauth-login           (story)
BL-042  →  BUG-003    crash-on-empty-input       (bug)
BL-017  →  DEBT-001   remove-legacy-middleware   (debt, done)
...
```

Paginated at 30 rows. After reviewing, the user returns to the same Proceed / Cancel prompt.

### Step 5: Execute

For each v3 file in the validated manifest (active/future first, then done if included):

1. Read and parse (BOM stripped, CRLF normalized — done in Step 2)
2. Detect type from `type:` field. Apply v3→v4 type mapping (see [`v4-story-schema.md`](v4-story-schema.md) §7). Notably: v3 `spike` → v4 `story`.
3. Assign new per-type ID (increment counter — order-locked by the sort applied in Step 2)
4. Remap fields per [`v4-story-schema.md`](v4-story-schema.md) §7:
   - `status` mapping: full v3 enum (`backlog`, `in_progress`, `in_review`, `cancelled`, etc.) → v4 enum
   - `source` → `origin` (values: `generated` → `inferred`; others passed through)
   - `sprint_history` YAML array → Sprint History markdown table in body
   - `cancelled_at` or `done_at` → `closed_date`
   - Ensure all required v4 frontmatter fields are present; supply defaults for any missing
5. Write to `docs/product/backlog/{type}s/<TYPE>-NNN-<slug>.md`
   - done/abandoned → `docs/product/backlog/{type}s/done/` instead
   - Write via temp file + atomic rename
6. **Do not delete source files yet** (deletion only happens after Step 8.4 if user accepts cleanup offer)
7. Record per-file outcome in an in-memory results structure: `{source_path, v3_id, v4_id, v4_path, write_success}` — drives Step 7 reconciliation

### Step 6: Build INDEX.md and MIGRATION-MAP.md

Generate `docs/product/backlog/INDEX.md` with counter frontmatter and story table (format per [`v4-story-schema.md`](v4-story-schema.md) §6).

Generate `docs/product/MIGRATION-MAP.md` (note: at the product/ root, NOT inside backlog/). The MIGRATION-MAP is a migration artifact, not a backlog artifact — it doesn't belong alongside story files. Placing it at `docs/product/MIGRATION-MAP.md` keeps `docs/product/backlog/` clean of non-story content.

```markdown
# v3 → v4 ID Migration Map

**Migrated:** 2026-05-12
**Migration backup:** `~/.sweetclaude/backups/{project}/pre-v4-{date}-{sha}.tar.gz`

This file is the permanent record of how v3 IDs map to v4 IDs. Search for `BL-001`
in git history? Look it up here.

## Migrated

| v3 ID | v4 ID | Title | Type | Migrated |
|---|---|---|---|---|
| BL-001 | STORY-001 | Add OAuth login | story | yes |
| BL-042 | BUG-003 | Crash on empty input | bug | yes |

## Skipped (done items, kept in v3 format)

If the user chose "Skip done items" in Step 3, those items appear here with
`migrated: no` and their v3 path. v4 cannot read them, but this table preserves
the record of their existence and where they live.

| v3 ID | Title | Type | v3 status | v3 path | Migrated |
|---|---|---|---|---|---|
| BL-017 | Remove legacy middleware | debt | done | .sweetclaude/product/backlog/BL-017-…md | no |
```

Skills that take an ID argument (e.g. `project-issues view BL-001`) detect the v3-style prefix (`BL-`, `I-`, `SP-`) and consult `MIGRATION-MAP.md` to auto-resolve to the v4 ID. If found, the skill prints `BL-001 was migrated to STORY-001. Showing STORY-001.` and proceeds. If not found, the skill prints a clear "not found, check MIGRATION-MAP.md" message.

### Step 7: Post-migration verification

Three checks run, in order. Any failure → auto-restore immediately. Report the exact file path and field that failed.

#### 7a. Per-file verification (every written file)

Re-read **every file just written** — no sampling. For each:
- File exists at expected path
- Frontmatter parses without error
- All v4 required fields present with non-default values where appropriate
- `id`, `type`, `status`, `origin` match the remapped values (not the source values)
- Filename `id` component matches frontmatter `id`
- If `status` is `done` or `abandoned`, the file is under `done/`. If status is anything else, the file is NOT under `done/`.

#### 7b. Content sampling (N% sample, minimum 10 files)

Randomly select `max(10, ceil(0.10 * total))` files (or all files if total ≤ 10). For each:
- Read the source v3 file from the in-tree backup tarball at `.sweetclaude/state/backups/pre-v4-{date}-{sha}.tar.gz`. The migration skill does NOT hold full file content in memory during Step 5 (this would not scale for projects with many large stories). Sample verification extracts each sampled file's source content from the backup on demand using `tar -xzf {backup} -O {path-in-archive}`.
- Read the written v4 file from disk.
- Compare body sections that were preserved verbatim (Description, Acceptance Criteria for stories; the type-specific sections — all of them except Sprint History which is transformed).
- Compare frontmatter fields that were preserved verbatim (`title`, `priority`, `effort`, `tags`, `created`).
- Verify Sprint History body table contains entries derived from the v3 `sprint_history` array (if any) — count match, sprint names match.

A single sample failure escalates to a full content audit (read every file from the backup, compare against every written file). The escalation produces a complete diff report before triggering auto-restore.

The backup-as-source-of-truth design means the in-tree backup must remain valid through Step 7. If the in-tree backup is unreadable mid-verification (e.g. disk pressure caused it to be evicted, or it was tampered with), fall back to the off-tree backup. If neither is readable, verification cannot proceed — surface this loudly and ask the user to abort or accept (auto-restore is impossible without a backup, so accepting is at the user's risk).

#### 7c. Input/output reconciliation

Compare the Step 2 validation manifest against the Step 5 results structure:
- `source_count == written_count` per type (story/bug/debt/chore)
- `source_count == written_count` per scope (active/future vs done; "done count" applies only if user chose to migrate done items)
- Every entry in the manifest has a corresponding entry in the results structure with `write_success: true`

Any shortfall — even one source file with no corresponding output — triggers auto-restore. This catches silent file drops that would otherwise pass per-file verification (which only sees the files that were written, not the ones that weren't).

### Step 8: Finalize

Finalize is the **single atomic commit point** for the migration. The migration is "committed" when `sweetclaude.yaml` is updated with `framework.installed_version: 4.x.x` and `framework.v4.migration_complete: true`. Both flags are written together.

#### 8a. Build the finalize payload (no writes yet)

Construct the updated content for both YAML files in memory:
- New `artifact-privacy.yaml` with `categories.product.base_path: docs/product`
- New `sweetclaude.yaml` with `framework.installed_version: 4.x.x` and `framework.v4.migration_complete: true` (plus `framework.v4.migrated_at: <ISO timestamp>` and `framework.v4.skipped_done_count: N` for record-keeping)

#### 8b. Atomic two-file write

Write both via temp + rename. **Rename order matters** because bootstrap uses `sweetclaude.yaml` to decide whether migration is needed (the `framework.v4.migration_complete: true` flag lives there). The `sweetclaude.yaml` rename is the irreversibility point — after it, bootstrap will NOT re-trigger migration on next session.

To keep "fail safely" semantics — partial completion should leave the project in a state where bootstrap re-triggers migration, not in a state where bootstrap thinks migration succeeded — `artifact-privacy.yaml` is renamed FIRST and `sweetclaude.yaml` is renamed LAST.

1. Write `artifact-privacy.yaml.tmp` (don't rename yet)
2. Write `sweetclaude.yaml.tmp` (don't rename yet)
3. Verify both tmp files parse correctly (read them back, parse as YAML)
4. Rename `artifact-privacy.yaml.tmp` → `artifact-privacy.yaml`
5. Rename `sweetclaude.yaml.tmp` → `sweetclaude.yaml` ← **commit point** (also the bootstrap-state flag)

If any step 1–4 fails: delete both tmp files, trigger auto-restore. Only step 5 has partial-completion semantics — if rename 4 succeeds and rename 5 fails:
- `artifact-privacy.yaml` says `docs/product` (matches the data already written in Step 5)
- `sweetclaude.yaml` still says old version AND lacks `migration_complete: true`
- Bootstrap detection (v3 artifacts AND `migration_complete` missing/false) re-triggers migration on next session
- The `artifact-privacy.yaml` change is harmless because product data has already been written to `docs/product/` — re-running migration finds nothing new to write and falls through to the finalize step that previously failed.

Re-running migration in this state is safe: the lock prevents concurrent runs; Step 1's gitignore preflight, backup creation, and validation are idempotent; Step 5 detects that all source files have already been migrated; finalize retries the rename.

#### 8c. Release lock and offer cleanup

After 8b succeeds:

```bash
rm -rf "$LOCK_DIR"
```

Offer to delete v3 source files:

```
Migration complete. Backups retained:
  Off-tree:  ~/.sweetclaude/backups/{project}/pre-v4-{date}-{sha}.tar.gz
  In-tree:   .sweetclaude/state/backups/pre-v4-{date}-{sha}.tar.gz

Both backups verified by sample extraction. Both will be kept (retention: last 5).

Delete the v3 source files at .sweetclaude/product/ now?

[Yes, delete] — irreversible without backup restore; ~/.sweetclaude/backups/ survives.
[Keep them] — v3 files remain on disk; v4 ignores them.
```

If the user chooses Keep: v3 files stay. Bootstrap does not re-prompt because `framework.v4.migration_complete: true` is already set. The next session will run normally.

If the user chooses Delete:
1. Re-verify the off-tree backup passes header read AND sample extraction (per Step 1c). If verification fails, refuse the delete and surface the warning.
2. Delete the v3 product paths recorded in Step 2's manifest (only those paths — do not delete unrelated `.sweetclaude/` content).
3. Confirm: "Deleted N files from v3 product paths. Backups retained at: {paths}."

#### 8d. Final report

```
Migration complete.

Summary:
  N stories migrated (X active/future, Y done)
  Z done items skipped (recorded in MIGRATION-MAP.md)
  Counters initialized: story={N}, bug={N}, debt={N}, chore={N}

Files written:
  docs/product/backlog/INDEX.md
  docs/product/MIGRATION-MAP.md
  docs/product/backlog/{stories,bugs,debt,chores}/

Backups:
  ~/.sweetclaude/backups/{project}/pre-v4-{date}-{sha}.tar.gz
  .sweetclaude/state/backups/pre-v4-{date}-{sha}.tar.gz

State:
  framework.installed_version: 4.x.x
  framework.v4.migration_complete: true

Next: open any file under docs/product/ to see your v4 backlog. Run /sweetclaude:status for a project overview.
```

---

## Promoting Stories (Backlog → Roadmap)

After migration, when a user promotes a story from backlog to roadmap:

1. SweetClaude checks: **git working tree must be clean**
2. If dirty: refuse. Offer to commit only the story file being moved (not the full working tree — other staged or unstaged changes are left untouched), or ask the user what to do.
3. Move file from `docs/product/backlog/{type}s/` to target epic directory in roadmap
4. Update backlog INDEX.md (remove row)
5. Update roadmap epic INDEX.md (add row)
6. Commit the move as a single atomic commit with a conventional commit message

No story ID ever appears in both backlog and roadmap simultaneously.

---

## Failure Handling

### Auto-restore-first-then-menu

If migration fails at any point — during preflight, validation, write, or verification:

1. **Auto-restore from backup.** Sequenced precisely to avoid losing the pre-existence flag during the `.sweetclaude/` restore:
   - **First, snapshot pre-existence flag and pre-existing tarball into local variables** — `$LOCK_DIR/docs-product-pre-existed` and (if `yes`) `$LOCK_DIR/docs-product-pre.tar.gz` are inside `.sweetclaude/state/migration.lock/`, and the next step may overwrite that directory. Read both into local variables BEFORE the next step.
   - **Restore `.sweetclaude/`**: extract the in-tree backup to a tmp directory, atomically rename to replace the live `.sweetclaude/`. If in-tree backup is unreadable, fall back to off-tree backup at `~/.sweetclaude/backups/{project}/`.
   - **Clean up `docs/product/` orphans** using the snapshotted flag:
     - If `no` (didn't exist before migration): delete `docs/product/` entirely.
     - If `yes` (existed before — e.g. the user had unrelated `docs/product/` content): the pre-migration snapshot tarball captured in Step 1b is referenced from the snapshotted variable. Delete the current `docs/product/`, then extract the snapshot tarball into the project root.
   - The spec claim "project has been restored to its previous state" must hold true — including outside `.sweetclaude/`.
2. Report exactly what failed: file path, field name, value found, value expected.
3. Offer post-restore re-run: "Re-run migration?" (skip the option to re-run against partial `docs/product/` because Step 1c capture + clean-up guarantees a clean slate)
4. Present failure menu.

If auto-restore itself fails or is interrupted (power loss, session kill), the spec cannot guarantee state. The recovery path is documented in the failure menu's emergency-recovery item:

> "If auto-restore was interrupted, manually run: `tar -xzf ~/.sweetclaude/backups/{project}/{backup}.tar.gz -C /` and `rm -rf docs/product/` if it was created by migration."

The restore uses extract-to-tmp + atomic-rename where possible to keep the partial-overwrite window as small as feasible, but cross-tmpfs operations cannot guarantee atomicity.

### Failure menu

```
Migration failed — project has been restored to its previous state.

Problem: [exact file path] — field "[field]" had value "[found]", expected "[expected]"

What would you like to do?

  1. Work through it with me
     I'll diagnose the problem, explain it, and we'll resolve it together.
     Then re-run migration.

  2. Reset framework state (DESTRUCTIVE)
     Read carefully before choosing — see "Option 2 details" below.

  3. Wait
     Exit migration for now. SweetClaude will continue blocking this project
     until migration completes. Come back when ready and run /sweetclaude:migrate.

  4. Emergency recovery
     If auto-restore did not fully complete, show the manual recovery commands.
```

### Option 2 details (DESTRUCTIVE — full file manifest required)

Option 2 is a re-onboarding flow that assumes your durable deliverables are in `/docs/`. It does NOT touch `/docs/`. But it DOES delete the following from `.sweetclaude/`:

```
.sweetclaude/state/sweetclaude.yaml          → removed (will be regenerated by bootstrap)
.sweetclaude/state/skills.yaml               → removed (will be regenerated)
.sweetclaude/state/session-state.yaml        → removed (will be regenerated)
.sweetclaude/state/artifact-privacy.yaml     → removed (will be regenerated)
.sweetclaude/product/                        → removed (the v3 data being migrated)
```

The following are explicitly **preserved**:

```
.sweetclaude/state/decision-log.md           → KEPT
.sweetclaude/state/improvement-register.md   → KEPT
.sweetclaude/state/assumption-register.md    → KEPT
.sweetclaude/state/scope-changes.md          → KEPT
.sweetclaude/state/backups/                  → KEPT (your backup is here)
.sweetclaude/plans/                          → KEPT
.sweetclaude/traceability/                   → KEPT
```

After Option 2 runs, bootstrap re-onboards the project against the preserved state and the durable `/docs/` content.

**Confirmation prompt:**
```
Option 2 will delete the files listed above and keep the files listed.

This will discard your v3 product/backlog data. Your only recovery is the
backup at ~/.sweetclaude/backups/{project}/pre-v4-{date}-{sha}.tar.gz.

Type the project name to confirm: ____
```

Require exact project name match before proceeding.

---

## Migration Diagnosis Subskill

**`sweetclaude:migrate-diagnose`**

- **Not user-invocable directly** — under-the-hood, called by other skills
- Called by: `sweetclaude:migrate` (failure menu option 1), `sweetclaude:bootstrap` (optional offer at hard stop)

Responsibilities:
- Scan all BL-NNN files, report all anomalies
- Identify which files will fail validation and why
- Propose fixes for common issues (missing `type`, unrecognized `status`, corrupt frontmatter)
- Apply fixes with user approval, then trigger re-migration

---

## Release Gates (Public Repo)

Do not publish v4 publicly until all of these are green. Each item must produce an evidence artifact (test log, screenshot, commit hash, or doc link) committed under `docs/internal/v4-release-evidence/` so the gate is auditable.

### Build & test gates

- [ ] `v3-final` branch created and pushed
- [ ] `sweetclaude:migrate` skill built and tested (automated test, not just smoke)
- [ ] `sweetclaude:migrate-diagnose` subskill built and tested
- [ ] Bootstrap hard-stop implemented and tested (covers all detection paths)
- [ ] `sweetclaude:update` v4 messaging written and tested
- [ ] Phase 1 complete and end-to-end smoke-tested

### Migration coverage gates

- [ ] Migration tested on **at least three** real v3 projects, drawn from distinct contexts:
  - One author-owned project (e.g. `sweetclaude` itself, dogfood)
  - One external/non-author project (volunteer or test fixture mirroring a different usage pattern)
  - One stress-test project (≥ 100 stories OR includes `sprint_history` arrays OR mixed `spike`/`story`/`bug` types)
- [ ] Migration tested against a `/docs/*` denylist gitignore pattern (sweetclaude is the canonical example) — Step 0 hard-stop fires correctly
- [ ] Migration tested with `.gitignore` that does NOT exclude `docs/product/` — Step 0 passes, Step 8c offer presented
- [ ] Auto-restore tested by deliberately corrupting one written file after Step 5 (planted-corruption fixture)
- [ ] Input/output reconciliation tested by deliberately dropping one source file during Step 5 (silent-drop fixture)
- [ ] Counter recovery tested from a state where INDEX.md is missing
- [ ] Counter recovery tested from a state where INDEX.md frontmatter is malformed
- [ ] Per-project evidence log committed: file count, type breakdown, time elapsed, any anomalies

### Documentation gates

- [ ] `docs/user-guide/v4-migration-guide.md` exists, links from bootstrap hard-stop message
- [ ] `docs/user-guide/planning-concepts.md` exists, referenced from `getting-started.md`
- [ ] `CHANGELOG.md` exists with v4.0.0 entry (breaking changes, migration steps, new features); links to migration guide
- [ ] `docs/user-guide/skills-reference.md` updated for every skill changed in v4
- [ ] `docs/user-guide/getting-started.md`, `quickstart.md`, `state-and-memory.md` updated for v4 paths
- [ ] Docs written per-skill (each skill's rewrite commit includes its corresponding doc row update)

### Release artifact gates

- [ ] Version bumped to v4.0.0 in framework config (`package.json`, `.claude-plugin/plugin.json`)
- [ ] GitHub Release v4.0.0 created and published; release notes link to migration guide AND changelog
- [ ] Public release-notes message drafted (for project's communication channels) with v4 install path and one-paragraph migration summary

---

## Caucus Concerns (C1–C3)

Identified by the 10-expert, 4-round caucus at 13:42 UTC.

### C1: Migration validation manifest

Silent corruption is more dangerous than noisy failure. Two-pass guard: pre-write validation manifest + post-write verification. Any discrepancy triggers auto-restore — not a warning.

### C2: Documentation as phase deliverable

Docs written per-skill during implementation, not batched in a final phase. Every skill change ships with its documentation update in the same commit. A "Phase 8: write all the docs" approach was explicitly flagged as a doc/skill divergence risk.

### C3: Pre-v4 communication

Users surprised by a hard stop write angry issues. `sweetclaude:update` must set expectations clearly before the user upgrades. The hard stop message in bootstrap must be specific, calm, and tell the user exactly what to do next.
