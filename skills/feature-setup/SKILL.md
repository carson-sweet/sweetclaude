---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Deploy local repo to installed locations and rebuild the project cache."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:feature-setup" 2>/dev/null || true`

# Feature Setup

Sync the local SweetClaude repo to all installed locations and rebuild the project cache. Delegates all sync work (including phase gate, test gate, backup, and rollback) to `scripts/sync-to-installed.sh`.

## Step 1: Locate the repo

```bash
REPO_PATH=$(python3 -c "
import json, os
try:
    d = json.load(open(os.path.expanduser('~/.claude/sweetclaude-install.json')))
    print(d.get('repo_path', ''))
except Exception: print('')
" 2>/dev/null)

if [ -z "$REPO_PATH" ] || [ ! -f "$REPO_PATH/scripts/sync-to-installed.sh" ]; then
  if [ -f "scripts/sync-to-installed.sh" ] && python3 -c "
import json, sys
try:
    d = json.load(open('package.json'))
    sys.exit(0 if d.get('name') == 'sweetclaude' else 1)
except Exception: sys.exit(1)
" 2>/dev/null; then
    REPO_PATH="$PWD"
  fi
fi

if [ -z "$REPO_PATH" ] || [ ! -f "$REPO_PATH/scripts/sync-to-installed.sh" ]; then
  echo "REPO_NOT_FOUND"
else
  echo "REPO_PATH=$REPO_PATH"
fi
```

If `REPO_NOT_FOUND`: stop with:
> "Could not find the SweetClaude repo. Run this from inside the repo, or ensure `~/.claude/sweetclaude-install.json` has the correct `repo_path`."

## Step 2: Run sync-to-installed.sh

```bash
bash "$REPO_PATH/scripts/sync-to-installed.sh"
SYNC_EXIT=$?
echo "SYNC_EXIT=$SYNC_EXIT"
```

If `SYNC_EXIT` is non-zero, stop. The sync script prints its own error messages. Common exit codes:
- 1: phase is IMPLEMENT (sync blocked)
- 2: hook tests failed (sync blocked)
- 3: backup failed
- 4: sync failed (rolled back from backup)
- 5: path resolution failed

## Step 3: Verify project structure

Steps 3–5 operate on the current working directory (the user's project), not `$REPO_PATH`.

```bash
[ -f .sweetclaude/state/sweetclaude.yaml ] || echo "NO_SWEETCLAUDE"
[ -d docs/product/backlog ] || echo "NO_BACKLOG_DIR"
```

If `NO_SWEETCLAUDE`: stop with:
> "No SweetClaude state found in this project. Run `/sweetclaude:setup` first."

If `NO_BACKLOG_DIR`: create the v4 directory tree:

```bash
for subdir in stories/done bugs/done debt/done chores/done; do
  mkdir -p "docs/product/backlog/$subdir"
done
```

Always create the roadmap directory structure (idempotent):

```bash
mkdir -p docs/product/roadmap/epics/done
mkdir -p docs/product/roadmap/releases
echo "ROADMAP_DIRS_READY"
```

## Step 4: Build the cache

```bash
mkdir -p .sweetclaude/cache
python3 ~/.claude/scripts/sweetclaude/cache.py --project-dir . --rebuild 2>&1
```

## Step 5: Report

Query the cache:

```bash
python3 ~/.claude/scripts/sweetclaude/cache.py --project-dir . --query item-count 2>/dev/null
python3 ~/.claude/scripts/sweetclaude/cache.py --project-dir . --query releases 2>/dev/null
python3 ~/.claude/scripts/sweetclaude/cache.py --project-dir . --query active-epic 2>/dev/null
```

Present:

```
Local repo deployed.

  Scripts:   ~/.claude/scripts/sweetclaude/
  Cache:     .sweetclaude/cache/roadmap.db

  Items indexed:  {item_count}
  Releases:       {release count, or "none"}
  Active epic:    {EP-NNN title, or "none"}
```

If item count is 0 and backlog files exist, warn:
> "Cache is empty but backlog files exist. Check that files have valid YAML frontmatter with `---` delimiters."

If releases and active epic are both "none", show getting-started guidance:
> "The roadmap system is ready. Your existing backlog ({item_count} items) is indexed. To start using epics and releases:"
> - `/sweetclaude:epics add` — create your first epic
> - `/sweetclaude:epics link STORY-NNN EP-NNN` — link existing backlog items to an epic
> - `/sweetclaude:big-picture` — see the full project at a glance

Check `.gitignore`:

```bash
git check-ignore -q .sweetclaude/cache/roadmap.db 2>/dev/null && echo "CACHE_IGNORED" || echo "CACHE_NOT_IGNORED"
```

If `CACHE_NOT_IGNORED`:
> "Add `.sweetclaude/cache/` to your `.gitignore` — the cache is derived data and should not be committed."

Final note:
> "Restart Claude Code to pick up the updated skills."

## Rules

- Idempotent. Safe to run repeatedly.
- All sync safety (phase gate, test gate, backup, rollback) is handled by `sync-to-installed.sh`.
- Never modifies markdown source files.
