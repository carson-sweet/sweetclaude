---
name: sweetclaude:migrate
description: Migrate v3 BL-NNN stories to v4 docs/product/backlog/ layout. User-invocable as /sweetclaude:migrate. Builds backup, validates, previews, executes, verifies, finalizes.
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:migrate" 2>/dev/null || true`

This skill is a thin orchestrator. The deterministic migration operations
(validation, plan, execute, verify, finalize) are implemented in
`scripts/migrate/migrate-v3-to-v4.py` and tested end-to-end by
`tests/test-migrate-v3-to-v4.sh`. The skill owns: lock/backup, user prompts,
preview rendering, failure handling.

## Step 1: Lock & backup

```bash
SCRIPT=~/.claude/scripts/sweetclaude/migrate/migrate-v3-to-v4.py
if [ ! -f "$SCRIPT" ]; then
  SCRIPT=$(find ~/.claude/plugins/cache/sweetclaude -type f -name 'migrate-v3-to-v4.py' 2>/dev/null | head -1)
fi
if [ -z "$SCRIPT" ] || [ ! -f "$SCRIPT" ]; then
  echo "ERROR: migrate-v3-to-v4.py not found. Run /sweetclaude:update first."
  exit 1
fi

PRODUCT_BASE=$(python3 "$SCRIPT" resolve-base --project-dir . | python3 -c "import sys, json; print(json.load(sys.stdin)['product_base'])")
V3_BACKLOG="${PRODUCT_BASE}/backlog"

LOCK_FILE=".sweetclaude/state/migration.lock"
if [ -f "$LOCK_FILE" ]; then
  echo "ERROR: $LOCK_FILE exists. Previous migration may have crashed."
  echo "Inspect, then remove manually if safe: rm $LOCK_FILE"
  exit 1
fi
echo "$(date -u +%Y%m%dT%H%M%SZ) $$" > "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

BACKUP_DIR=".sweetclaude/state/backups"
mkdir -p "$BACKUP_DIR"
BACKUP_DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "nosha")
BACKUP_FILE="$BACKUP_DIR/pre-v4-${BACKUP_DATE}-${BACKUP_SHA}.tar.gz"

# Include v3 source files in backup. For .sweetclaude/product users they're already
# inside .sweetclaude/. For docs/product users they're outside it — add them explicitly.
case "$PRODUCT_BASE" in
  */.sweetclaude/product)
    tar -czf "$BACKUP_FILE" .sweetclaude/
    ;;
  *)
    tar -czf "$BACKUP_FILE" .sweetclaude/ "$V3_BACKLOG"/BL-*.md 2>/dev/null || \
      tar -czf "$BACKUP_FILE" .sweetclaude/
    ;;
esac
tar -tzf "$BACKUP_FILE" > /dev/null || { echo "ERROR: backup verification failed"; exit 1; }

# Retain last 5 — BSD-portable (no xargs -r):
ls -1t "$BACKUP_DIR"/pre-v4-*.tar.gz 2>/dev/null | tail -n +6 | while IFS= read -r f; do
  [ -n "$f" ] && rm -f "$f"
done
```

## Step 2: Validate

```bash
VALIDATE_OUT=$(python3 "$SCRIPT" validate --project-dir .)
echo "$VALIDATE_OUT"
FAILURE_COUNT=$(echo "$VALIDATE_OUT" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('failures', [])))")
```

If `FAILURE_COUNT > 0`: present **AskUserQuestion**:
- Question: `Validation found N problems in v3 BL files. Run /sweetclaude:migrate-diagnose to investigate?`
- Options: `Yes`, `No`
- On either choice: release lock (`rm $LOCK_FILE`) and stop. Do not proceed.

## Step 3: Done item choice

Count files where `status ∈ {done, cancelled, abandoned}` in the validate output. If count > 0, present **AskUserQuestion**:

- **Question:** `Found N completed stories. Migrate them too?`
- **Options:**
  1. `Migrate all` → set `INCLUDE_DONE=--include-done`
  2. `Skip done items` → set `INCLUDE_DONE=` (empty)

Store the user's choice as `$INCLUDE_DONE` for use in Steps 4 and 5.

If count is 0, set `INCLUDE_DONE=--include-done` (no-op — nothing to skip).

## Step 4: Preview

```bash
PLAN_OUT=$(python3 "$SCRIPT" plan --project-dir . $INCLUDE_DONE)
echo "$PLAN_OUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
items = d['plan_items']
print(f\"Migration preview — {len(items)} stories to migrate\")
print()
print('| v3 ID | v3 File | v4 ID | Type | Destination |')
print('|---|---|---|---|---|')
for it in items:
    import os
    v3_basename = os.path.basename(it['v3_file'])
    dest_relative = it['dest_path'].split('docs/product/backlog/', 1)[-1]
    print(f\"| {it['v3_id']} | {v3_basename} | {it['v4_id']} | {it['type']} | docs/product/backlog/{dest_relative} |\")
"
```

Then present **AskUserQuestion**:
- **Question:** `Proceed with migration?`
- **Options:**
  1. `Yes` → continue to Step 5
  2. `Cancel` → release the lock file (`rm $LOCK_FILE`), exit cleanly. No writes made.

## Step 5: Execute

```bash
EXEC_OUT=$(python3 "$SCRIPT" execute --project-dir . $INCLUDE_DONE)
echo "$EXEC_OUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f\"Wrote {len(d['created_paths'])} files. Counters: {d['counters']}.\")
"
# Save created_paths for Step 7 verify
echo "$EXEC_OUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
json.dump(d['created_paths'], open('.sweetclaude/state/.migrate-created-paths.json', 'w'))
"
```

The `execute` subcommand performs the per-file transformation and writes `MIGRATION-MAP.md`. After execution, the cache is rebuilt to reflect the new file layout.

## Step 6: Rebuild cache

```bash
python3 scripts/cache.py --project-dir . --rebuild 2>/dev/null
```

## Step 7: Verify

```bash
VERIFY_OUT=$(python3 "$SCRIPT" verify --project-dir . --created-paths-file .sweetclaude/state/.migrate-created-paths.json)
VERIFY_FAILURES=$(echo "$VERIFY_OUT" | python3 -c "import sys, json; print(len(json.load(sys.stdin).get('failures', [])))")
```

If `VERIFY_FAILURES > 0`: invoke Failure handling (below). Print the failures and offer the recovery menu.

If 0: continue to Step 8.

## Step 8: Finalize

```bash
python3 "$SCRIPT" finalize --project-dir . > /dev/null
rm -f .sweetclaude/state/.migrate-created-paths.json
rm -f "$LOCK_FILE"
```

The `finalize` subcommand sets `categories.product.base_path: docs/product` in `artifact-privacy.yaml` and `framework.installed_version: 4.0.0` in `sweetclaude.yaml`. This is the atomic commit point — only reached when validate + execute + verify all passed.

### Step 8 backup verification and delete

After successful finalize, verify the backup is valid and remove the v3 BL files. The backup tarball is the user's recovery path — keeping v3 files on disk after a completed migration creates a "stuck migration" state in bootstrap (v3 files present + project at 4.x triggers the hard-stop loop forever).

```bash
tar -tzf "$BACKUP_FILE" > /dev/null && BACKUP_OK=1 || BACKUP_OK=0

if [ "$BACKUP_OK" = "1" ]; then
  CLEANUP_OUT=$(python3 "$SCRIPT" cleanup-v3-files --project-dir .)
  V3_REMOVED_COUNT=$(echo "$CLEANUP_OUT" | python3 -c "import sys, json; print(json.load(sys.stdin)['count'])")
  echo "Removed $V3_REMOVED_COUNT v3 BL-*.md file(s)."
else
  echo "WARNING: backup verification failed — leaving v3 BL files in place. Inspect $BACKUP_FILE manually."
  V3_REMOVED_COUNT=0
fi
```

If the backup verification fails, v3 BL files are NOT removed (so the user can recover manually). The summary surfaces this so the user knows to address it.

### Step 8 summary

```
Migration complete.

  Created:       {count} files in docs/product/backlog/
  Counters:      story=X bug=Y debt=Z chore=W
  Skipped done:  {skipped_done if any}
  v3 BL files:   {removed | LEFT IN PLACE — backup invalid, see warning above}
  Backup:        $BACKUP_FILE
  Map:           docs/product/backlog/MIGRATION-MAP.md

To inspect the original v3 BL files, extract the backup:
  tar -xzf $BACKUP_FILE -C /tmp/v3-backup

Next session's bootstrap will run any remaining schema migrations
(e.g. sweetclaude.yaml v1->v2) via the registry-driven runner.
```

## Failure handling

Invoked by Step 2 (validation failures) or Step 7 (verify failures).

1. **Restore `.sweetclaude/`:**
   ```bash
   rm -rf .sweetclaude
   tar -xzf "$BACKUP_FILE"
   ```

2. **Remove created files:** Read the saved `.sweetclaude/state/.migrate-created-paths.json` (if Step 5 ran) and delete every path in it. Do not touch anything outside `docs/product/backlog/`.

   ```bash
   python3 -c "
   import json, os
   try:
       paths = json.load(open('.sweetclaude/state/.migrate-created-paths.json'))
       for p in paths:
           try: os.remove(p)
           except OSError: pass
   except FileNotFoundError:
       pass
   "
   ```

3. **Print failure details** from the JSON failure list (file path, problem).

4. **Present AskUserQuestion:**
   - Question: `What would you like to do?`
   - Options:
     1. `Work through it with me` → invoke `sweetclaude:migrate-diagnose`
     2. `Reset framework state` → clear `.sweetclaude/` state files only; `/docs/` is untouched. Stop and prompt user to re-run `/sweetclaude:migrate`.
     3. `Wait` → exit. Hard stop remains in effect until migration succeeds.

## Rules

- All deterministic work happens in `scripts/migrate/migrate-v3-to-v4.py`. The skill orchestrates only.
- The script is idempotent on validate/plan (read-only). `execute` and `finalize` are write operations and assume the lock file is held by the skill.
- If the script changes (new subcommand, schema bump), update `tests/test-migrate-v3-to-v4.sh` first, run it, and only then update this skill.
