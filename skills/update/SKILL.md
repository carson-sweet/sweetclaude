---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Update SweetClaude to the latest version from GitHub (or a local repo)."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:update" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# Update SweetClaude

Fetch the latest SweetClaude and sync it to all installed locations.

**This skill can be run from any project directory.**

---

## Step -1: Pre-flight

Ensure the versionless framework path is populated, clear any previous update decline (running `/sweetclaude:update` is explicit re-engagement), and emit the runner path for later steps.

```bash
if [ ! -f ~/.claude/scripts/sweetclaude/preflight.sh ]; then
  IP=$(python3 -c "
import json, os
try:
    d = json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
    entries = [e for versions in d.get('plugins', {}).values()
               for e in versions if e.get('scope') == 'user']
    entries.sort(key=lambda e: e.get('lastUpdated', ''), reverse=True)
    for e in entries:
        ip = e.get('installPath', '')
        if ip and os.path.isdir(os.path.join(ip, 'scripts')):
            print(ip)
            break
except Exception:
    pass
" 2>/dev/null)
  if [ -n "$IP" ] && [ -d "$IP/scripts" ]; then
    mkdir -p ~/.claude/scripts/sweetclaude
    rsync -a "$IP/scripts/" ~/.claude/scripts/sweetclaude/ 2>/dev/null || true
  fi
fi
eval "$(bash ~/.claude/scripts/sweetclaude/preflight.sh --from-update 2>/dev/null)"
```

`DECLINE_CLEARED=true` if the project's `framework.update.declined` was cleared. `RUNNER` is set for use in Step 6b. If the user picks "Not now" later, `declined` will be re-set to the specific version declined (per Gap #1's version-aware decline rule).

---

## Step 1: Read current install state

Read `~/.claude/plugins/installed_plugins.json` and find the `sweetclaude@sweetclaude` entry. Extract:
- `installPath` — the plugin cache directory
- `version` — current installed version
- `gitCommitSha` — the commit currently installed

Read `{installPath}/.claude-plugin/plugin.json` and extract:
- `repository` — the GitHub repo URL (fallback: `https://github.com/carson-sweet/sweetclaude`)

Present:
```
SweetClaude v{version}
═══════════════════════

Installed: {installPath}
Commit:    {gitCommitSha (short)}
Source:    {repository}
```

---

## Step 2: Get the latest source

### 2a: Local repo (developer workflow)

Read `~/.claude/sweetclaude-install.json` (written by `install.sh`) to find the local repo path:

```bash
REPO_PATH=$(python3 -c "
import json, os
try:
    d = json.load(open(os.path.expanduser('~/.claude/sweetclaude-install.json')))
    print(d.get('repo_path', ''))
except: print('')
" 2>/dev/null)
```

If `REPO_PATH` is non-empty AND `$REPO_PATH/package.json` exists AND the repo has a remote matching the repository URL, fetch from origin and use it as the source:

```bash
git -C "$REPO_PATH" fetch origin
git -C "$REPO_PATH" log --oneline -1
```

- If fetch succeeds: use `$REPO_PATH` as SOURCE_DIR. The local repo may be ahead of GitHub (unpushed dev commits) — that is intentional and correct. Skip to Step 3.
- If fetch fails (network error): warn ("Could not reach GitHub to check for remote updates — proceeding with local repo state.") and use `$REPO_PATH` as SOURCE_DIR. Skip to Step 3.

### 2b: GitHub (standard user workflow)

If no local repo found, clone a fresh shallow copy from GitHub. Use `gh` if available (handles private repos with existing auth), fall back to `git`.

```bash
TMPDIR=$(mktemp -d)

if command -v gh &>/dev/null; then
  gh repo clone {owner}/{repo} "$TMPDIR/sweetclaude" -- --depth 1
else
  git clone --depth 1 {repository_url} "$TMPDIR/sweetclaude"
fi
```

If clone fails with an auth error, tell the user:
> "The SweetClaude repo requires authentication. Run `! gh auth login` to authenticate with GitHub, then try again."

Do not retry. Do not ask for tokens. On any failure, stop.

Use `$TMPDIR/sweetclaude` as SOURCE_DIR.

---

## Step 3: Compare versions

When SOURCE_DIR is the local repo (came from Step 2a), compare against `origin/HEAD` — not local `HEAD` — so commits on GitHub that haven't been pulled yet are detected. If origin is ahead of local HEAD, pull before syncing:

```bash
# Determine effective SHA to compare
CONFIGURED_REPO=$(python3 -c "import json,os; d=json.load(open(os.path.expanduser('~/.claude/sweetclaude-install.json'))); print(d.get('repo_path',''))" 2>/dev/null || echo "")
if [ "$SOURCE_DIR" = "$CONFIGURED_REPO" ]; then
  EFFECTIVE_SHA=$(git -C $SOURCE_DIR rev-parse origin/HEAD)
  LOCAL_SHA=$(git -C $SOURCE_DIR rev-parse HEAD)
  if [ "$EFFECTIVE_SHA" != "$LOCAL_SHA" ]; then
    git -C $SOURCE_DIR pull --ff-only origin
  fi
else
  EFFECTIVE_SHA=$(git -C $SOURCE_DIR rev-parse HEAD)
fi
git -C $SOURCE_DIR log --oneline -5
cat $SOURCE_DIR/package.json
```

If EFFECTIVE_SHA matches the installed `gitCommitSha`: "Already up to date." Clean up temp dir if used. **Then jump to Step 6b** — even when the framework is up to date, the current project may still have pending schema migrations from a previous update that wasn't completed (e.g., user updated in another project, then opened this one without restarting bootstrap). Do not stop.

Otherwise, show what changed since the installed version:

```bash
git -C $SOURCE_DIR log --oneline {installed_sha}..{EFFECTIVE_SHA}
```

Then diff against installed:

```bash
diff -rq $SOURCE_DIR/skills/ {installPath}/skills/ 2>/dev/null
diff -rq $SOURCE_DIR/skills/ ~/.claude/skills/sweetclaude/ 2>/dev/null
diff -rq $SOURCE_DIR/rules/ ~/.claude/rules/sweetclaude/ 2>/dev/null
diff -rq $SOURCE_DIR/hooks/ "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/hooks/sweetclaude}/" 2>/dev/null
diff -rq $SOURCE_DIR/config/ ~/.claude/config/sweetclaude/ 2>/dev/null
diff -rq $SOURCE_DIR/agents/ ~/.claude/agents/sweetclaude/ 2>/dev/null
diff -rq $SOURCE_DIR/scripts/ {installPath}/scripts/ 2>/dev/null
```

Present a summary:

```
Update available: {installed_sha_short} → {new_sha_short}
═══════════════════════════════════════════════════════════

Commits:
  {oneline log}

Changes:
  Skills:  {N} modified, {N} added, {N} removed
  Rules:   {N}
  Hooks:   {N}
  Config:  {N}
  Agents:  {N}
  Scripts: {N}
```

Wait for user confirmation before proceeding.

---

## Step 3b: Artifact safety check for removed skills

Before syncing, identify skills being removed — present in installed but absent in source:

```bash
diff -rq {installPath}/skills/ $SOURCE_DIR/skills/ 2>/dev/null \
  | grep "^Only in {installPath}/skills" \
  | sed 's|.*skills/||'
```

For each removed skill, check whether it owns live artifact content. Read `base_path` from session-state (`paths.product_base`) or fall back to `.sweetclaude/artifacts/product`.

| Skill | Artifact path |
|---|---|
| `product-milestones` | `{base_path}/milestones/MS-*.md` |
| `product-parking-lot` or `product-backlog` | `{base_path}/backlog/ISSUE-*.md` or `{base_path}/backlog/stories/*.md` |
| `product-sprint-plan` | `{base_path}/sprints/` (any files) |
| `user-personas` | `.sweetclaude/state/personas.yaml` |
| `product-user-stories` | `{base_path}/stories/US-*.md` (any files) |
| `document-corpus` | `.sweetclaude/state/corpus-pipeline.yaml` |

Only run this check if `.sweetclaude/` exists in the current project directory.

If any removed skill has matching live artifacts, pause and present:

```
⚠ Artifact safety check — removed skills with live content:
  {skill-name}: {artifact path} — {N} items found
  [repeat per affected skill]

  This content will become orphaned when these skills are removed.

  Options:
    1. Proceed anyway — I understand the content will be orphaned
    2. Cancel — I'll migrate the content before updating
    3. Skip removing these skills — sync everything else
```

Wait for user choice before continuing.

If no removed skills have live artifacts, continue silently to Step 4.

---

## Step 3c: Major version gate (v3 → v4)

After determining the installed version and the incoming version, check for a v3→v4 major upgrade:

```python
import re

def major_version(v):
    m = re.match(r'^(\d+)', str(v or ''))
    return int(m.group(1)) if m else 0

current_major = major_version(installed_version)   # from Step 1
incoming_major = major_version(new_version)         # from Step 3 source package.json
```

If `current_major == 3` and `incoming_major >= 4`:

Present AskUserQuestion with this body block before any sync:

> **SweetClaude v4 is available — this is a major release.**
>
> All work items use the ISSUE-NNN prefix and are stored in `.sweetclaude/product/backlog/`. Each project migrates independently the first time you open it after updating.
>
> Migration creates a safety backup and can be rolled back. Active and future stories must migrate. Done stories are optional.

- **Options:** `Yes, update`, `Not now`
- On `Not now`:
  - Write `framework.update.declined: true` to `.sweetclaude/state/sweetclaude.yaml` (if it exists in the current project).
  - **Do NOT re-offer** in subsequent bootstrap runs until the user explicitly runs `/sweetclaude:update` again.
  - Clean up temp dir if used. Stop.
- On `Yes, update`: proceed to Step 4.

If it is not a v3→v4 transition (e.g. minor/patch updates), skip this step and proceed directly to Step 4.

## Step 4: Sync

Before syncing, capture which skills are new (present in source, absent in the currently installed path). Claude Code loads skills at session start, so new skills added during this update will not be available until the user restarts.

```bash
NEW_SKILLS=""
if [ -d "{installPath}/skills" ]; then
  for skill_dir in "$SOURCE_DIR/skills"/*/; do
    skill_name=$(basename "$skill_dir")
    if [ ! -d "{installPath}/skills/$skill_name" ]; then
      NEW_SKILLS="${NEW_SKILLS:+$NEW_SKILLS }$skill_name"
    fi
  done
fi
echo "NEW_SKILLS=${NEW_SKILLS}"
```

Save the value of `NEW_SKILLS` — it is used in the Step 6c success report.

Copy from SOURCE_DIR to installed locations. Use `rsync --delete` to remove files that no longer exist in the source.

```bash
# Skills → plugin cache
rsync -a --delete $SOURCE_DIR/skills/ {installPath}/skills/

# Hooks → plugin cache (hooks.json uses ${CLAUDE_PLUGIN_ROOT}/hooks/ — must stay current)
rsync -a --delete $SOURCE_DIR/hooks/ {installPath}/hooks/

# Top-level files → plugin cache
for f in CLAUDE.md package.json LICENSE; do
  [ -f "$SOURCE_DIR/$f" ] && cp "$SOURCE_DIR/$f" {installPath}/
done

# Plugin manifest
rsync -a $SOURCE_DIR/.claude-plugin/ {installPath}/.claude-plugin/

# Skills → legacy install path (created by install.sh — must stay in sync)
if [ -d "$HOME/.claude/skills/sweetclaude" ]; then
  rsync -a --delete $SOURCE_DIR/skills/ ~/.claude/skills/sweetclaude/
fi

# Scripts → plugin cache AND versionless ~/.claude/scripts/sweetclaude/.
# The versionless path is what skills reference (no installPath lookup needed).
if [ -d "$SOURCE_DIR/scripts" ]; then
  rsync -a --delete $SOURCE_DIR/scripts/ {installPath}/scripts/
  mkdir -p ~/.claude/scripts/sweetclaude
  rsync -a --delete $SOURCE_DIR/scripts/ ~/.claude/scripts/sweetclaude/
fi

# Framework dirs → ~/.claude/
rsync -a --delete $SOURCE_DIR/rules/ ~/.claude/rules/sweetclaude/
rsync -a --delete $SOURCE_DIR/hooks/ "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/hooks/sweetclaude}/"
rsync -a --delete $SOURCE_DIR/config/ ~/.claude/config/sweetclaude/
rsync -a --delete $SOURCE_DIR/agents/ ~/.claude/agents/sweetclaude/

# Ensure hooks are executable
chmod +x "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/hooks/sweetclaude}/"*.sh 2>/dev/null || true

# Verify registry file synced correctly
ls ~/.claude/config/sweetclaude/skills-registry.yaml 2>/dev/null || echo "WARNING: skills-registry.yaml not found after sync"

# Claude Code may load skills from a version-named directory (e.g. 4.0.6-beta/)
# rather than installPath (e.g. 3.52.14/) when they differ. Sync to both.
# Derive the version-named dir from the new package.json version.
NEW_VER=$(python3 -c "import json; print(json.load(open('$SOURCE_DIR/package.json'))['version'])" 2>/dev/null)
PLUGIN_CACHE_PARENT=$(dirname {installPath})
VERSION_DIR="$PLUGIN_CACHE_PARENT/$NEW_VER"
if [ -n "$NEW_VER" ] && [ "$VERSION_DIR" != "{installPath}" ]; then
  mkdir -p "$VERSION_DIR/skills" "$VERSION_DIR/hooks"
  rsync -a --delete $SOURCE_DIR/skills/ "$VERSION_DIR/skills/"
  rsync -a --delete $SOURCE_DIR/hooks/ "$VERSION_DIR/hooks/"
  rsync -a $SOURCE_DIR/.claude-plugin/ "$VERSION_DIR/.claude-plugin/"
  for f in CLAUDE.md package.json LICENSE; do
    [ -f "$SOURCE_DIR/$f" ] && cp "$SOURCE_DIR/$f" "$VERSION_DIR/"
  done
  echo "Synced to version-named dir: $VERSION_DIR"
fi
```

---

## Step 4b: Reconcile SweetClaude hook entries in settings.json

Strip broken `${CLAUDE_PLUGIN_ROOT}` literals (from pre-3.68.2 installs) and stale plugin-version paths from `~/.claude/settings.json`. The three preflight hooks themselves are plugin-native (auto-loaded from `hooks/hooks.json`) and need no settings.json entry.

```bash
HOOK_RECONCILE_LOG=$(mktemp -t sc-hook-reconcile.XXXXXX) || HOOK_RECONCILE_LOG=/tmp/sc-hook-reconcile.log
if ! python3 ~/.claude/scripts/sweetclaude/maintenance/ensure-global-hooks.py >"$HOOK_RECONCILE_LOG" 2>&1; then
  echo "warning: hook reconciliation failed — see $HOOK_RECONCILE_LOG"
fi
cat "$HOOK_RECONCILE_LOG"
```

Read `$HOOK_RECONCILE_LOG`. If it contains any `cleaned:` line, sum the counts across buckets and include `✓ Hooks: reconciled N stale/broken entries in ~/.claude/settings.json` in the Step 6c success report (where N is the total). Also add this line to the report's tail:

> → Restart Claude Code to stop the in-session `${CLAUDE_PLUGIN_ROOT}` error from old settings.json entries. The hooks themselves load from the plugin's hooks.json and are unaffected.

If `$HOOK_RECONCILE_LOG` contains only `ok: hooks already up to date`, omit both lines entirely.

---

## Step 5: Update plugin metadata

Update `~/.claude/plugins/installed_plugins.json`:

1. Read the HEAD SHA: `git -C $SOURCE_DIR rev-parse HEAD`
2. Read the version from `$SOURCE_DIR/package.json`
3. Update the `sweetclaude@sweetclaude` entry:
   - `lastUpdated` → current ISO timestamp
   - `gitCommitSha` → HEAD SHA
   - `version` → package.json version
   - `installPath` → the version-named directory synced in Step 4 (`$VERSION_DIR`) if it was created; otherwise leave unchanged. This ensures Claude Code loads skills from the same directory that was just synced.

---

## Step 6: Clean up

If a temp directory was used, remove it:
```bash
rm -rf "$TMPDIR"
```

Run a final diff to confirm sync:
```bash
SYNC_TARGET="${VERSION_DIR:-{installPath}}"
diff -rq $SOURCE_DIR/skills/ "$SYNC_TARGET/skills/" 2>/dev/null
diff -rq $SOURCE_DIR/skills/ ~/.claude/skills/sweetclaude/ 2>/dev/null
diff -rq $SOURCE_DIR/scripts/ "$SYNC_TARGET/scripts/" 2>/dev/null
```

Continue to Step 6b. The user-facing success report is deferred until Step 6b confirms project state is coherent — reporting "updated" before the drift verdict is what caused BUG-002.

---

## Step 6b: Project-state drift detection and migration

> **Future:** Steps 6b, 6b1, and 6b2 will be delegated to `sweetclaude:doctor` check categories (`migration_currency`, `file_diagnostics`, `storage_lint`) in a future version. The doctor skill provides a unified safety model (archive, backup, dry-run) that these inline checks lack.

Only run if `.sweetclaude/state/sweetclaude.yaml` exists in the current project directory — skip silently otherwise. (Update can be run from any directory; this step only applies when run from inside a SweetClaude project.)

After the framework sync, the registry on disk may declare schema versions newer than this project's state files. Surface it immediately — don't make the user bounce sessions.

Parse the runner's stdout directly. Do NOT read `pending-drift-decision.yaml` — that marker is written by `drift-gate.sh` at session start and represents pre-update state. The fresh stdout from the just-synced runner is authoritative for this step.

```bash
DRIFT_COUNT=0
CASE=A
DRIFT_MARKER=".sweetclaude/state/pending-drift-decision.yaml"
if [ -f .sweetclaude/state/sweetclaude.yaml ] && [ -n "$RUNNER" ] && [ -f "$RUNNER" ]; then
  DRIFT_OUTPUT=$(python3 "$RUNNER" --project-dir . --report-drift-for-skill 2>/dev/null)
  DRIFT_COUNT=$(printf '%s\n' "$DRIFT_OUTPUT" | grep '^DRIFT_COUNT=' | cut -d= -f2)
  [ -z "$DRIFT_COUNT" ] && DRIFT_COUNT=0
  if printf '%s\n' "$DRIFT_OUTPUT" | grep -q '|chain=broken'; then
    CASE=B
  fi
fi
echo "CASE=$CASE"
echo "DRIFT_COUNT=$DRIFT_COUNT"
```

If `DRIFT_COUNT` is 0: remove any stale marker left over from this session's earlier drift-gate scan, print the success report (Step 6c template below) with `✓ Project: clean` line, then continue to Step 7.

```bash
if [ "$DRIFT_COUNT" = "0" ]; then
  rm -f "$DRIFT_MARKER" 2>/dev/null || true
fi
```

If `DRIFT_COUNT > 0`: the framework update just bumped registry versions past the project's state. Migrate or remove — no "Not now," no silent proceed. This is the locked Gap #7 rule.

**Case A (CASE=A — all chains ok):** present via **AskUserQuestion** (single-select, no "Something else"):

> "Framework updated to v{new_version}. {DRIFT_COUNT} SweetClaude state file(s) in this project need migration before SweetClaude can continue. Would you like to do this now?"
>
> Options:
> - **Migrate now** — invoke `sweetclaude:_migrate` to bring this project up to current.
> - **Remove SweetClaude from this project (re-onboarding required to reactivate)** — invoke `sweetclaude:purge`.

**Case B (CASE=B — at least one chain broken):** present via **AskUserQuestion** (single-select):

> "Framework updated to v{new_version}, but this project's SweetClaude state files are too old for automatic migration (out of framework support window). How would you like to proceed?"
>
> Options:
> - **Re-onboard from scratch** — archive existing SweetClaude content and run `/sweetclaude:adopt` against a fresh state.
> - **Remove SweetClaude from this project (re-onboarding required to reactivate)** — invoke `sweetclaude:purge`.

If the user picks **Re-onboard from scratch** (Case B only):

```bash
TS=$(date -u +%Y%m%d-%H%M%S)
LEGACY=".sweetclaude.legacy/$TS"
mkdir -p ".sweetclaude.legacy"
if [ -d .sweetclaude ]; then
  mv .sweetclaude "$LEGACY"
fi
python3 ~/.claude/scripts/sweetclaude/maintenance/archive-sweetclaude-dir.py "$LEGACY"
echo "Moved existing SweetClaude content to $LEGACY/ — adopt will use it as reference, not auto-migrate."
```

Then invoke `sweetclaude:adopt`. Stop (adopt drives the next session itself). Do NOT continue to Step 6c — adopt owns the next session entirely.

If the user picks **Remove SweetClaude** (either case): invoke `sweetclaude:purge`. Stop. Do NOT continue to Step 6c.

If the user picks **Migrate now** (Case A only): invoke `sweetclaude:_migrate`. When it returns, re-run the drift check:

```bash
POST_MIGRATE_COUNT=0
if [ -n "$RUNNER" ] && [ -f "$RUNNER" ]; then
  POST_OUTPUT=$(python3 "$RUNNER" --project-dir . --report-drift-for-skill 2>/dev/null)
  POST_MIGRATE_COUNT=$(printf '%s\n' "$POST_OUTPUT" | grep '^DRIFT_COUNT=' | cut -d= -f2)
  [ -z "$POST_MIGRATE_COUNT" ] && POST_MIGRATE_COUNT=0
fi
echo "POST_MIGRATE_COUNT=$POST_MIGRATE_COUNT"
```

If `POST_MIGRATE_COUNT` is 0: clean state. Print the success report (Step 6c template below) with `✓ Project: clean (verified post-migrate)` line, then continue to Step 7.

If `POST_MIGRATE_COUNT > 0`: do NOT print the success report. The framework files were synced, but the project is not in a coherent post-update state. Print the halt diagnostic instead:

```
SweetClaude update PARTIAL.
═══════════════════════════

✓ Version:    {old_version} → {new_version}  (framework synced)
✗ Project:    {POST_MIGRATE_COUNT} file(s) still drifted after _migrate

This usually means:
  (a) user picked Rollback or Leave-as-is in _migrate
  (b) a registered migration is missing its handler (chain broken)
  (c) a handler ran but didn't bump versions correctly

Files still drifted:
  {Print the FINDING lines from $POST_OUTPUT}

→ The framework is at v{new_version}. Project state is incomplete.
  The next session's drift-gate will surface this with full diagnostics.
```

Stop. Do NOT continue to Step 7.

---

## Step 6b1: Orphan file scan

Only run if `.sweetclaude/state/sweetclaude.yaml` exists in the current project directory — skip silently otherwise.

Scan for work item files that may have been lost, abandoned, or orphaned from previous SweetClaude versions — files in typed subdirectories (retired in 4.1.0), scratch/, or other locations the primary migration wouldn't find. Recovering them here means Step 6b2's taxonomy scan picks them up automatically.

```bash
ORPHAN_COUNT=0
MIGRATE_SCRIPT=~/.claude/scripts/sweetclaude/migrate/migrate-v3-to-v4.py
if [ ! -f "$MIGRATE_SCRIPT" ]; then
  MIGRATE_SCRIPT=$(find ~/.claude/plugins/cache/sweetclaude -type f -name 'migrate-v3-to-v4.py' 2>/dev/null | head -1)
fi
if [ -f .sweetclaude/state/sweetclaude.yaml ] && [ -n "$MIGRATE_SCRIPT" ] && [ -f "$MIGRATE_SCRIPT" ]; then
  ORPHAN_OUT=$(python3 "$MIGRATE_SCRIPT" scan-orphans --project-dir . 2>/dev/null)
  ORPHAN_COUNT=$(echo "$ORPHAN_OUT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('orphan_count', 0))" 2>/dev/null || echo 0)
fi
echo "ORPHAN_COUNT=$ORPHAN_COUNT"
```

If `ORPHAN_COUNT` is 0: continue silently to Step 6b2.

If `ORPHAN_COUNT > 0`: present findings grouped by category:

```
Found {N} orphaned work item files outside the primary backlog:

Typed subdirectories (retired in 4.1.0):
  {file} — {id} — {title} [{status}]

Scratch directory:
  {file} — {id} — {title} [{status}]

Stray files:
  {file} — {id} — {title} [{status}]
```

Then present **AskUserQuestion**:
- **Question:** `{N} orphaned files found during update. What should I do with them?`
- **Options:**
  1. `Include in migration` → copy each orphaned file into the primary backlog directory (`.sweetclaude/product/backlog/`) as `BL-{NNN}-{slug}.md` so Step 6b2's taxonomy scan picks them up. Assign sequential BL IDs starting after the highest existing BL number. For files without frontmatter, create minimal frontmatter from filename.
  2. `Show me each one` → present each file one at a time with **AskUserQuestion**: `Keep (include in migration)`, `Skip (leave where it is)`, `Delete`. Apply the user's choice per file.
  3. `Skip all` → proceed without recovering orphaned files. They stay where they are.

After the user's choice is applied, continue to Step 6b2.

---

## Step 6b2: Taxonomy migration detection

Only run if `.sweetclaude/state/sweetclaude.yaml` exists in the current project directory — skip silently otherwise.

Check for old-taxonomy files that need migration to the ISSUE-NNN format:

```bash
OLD_TAXONOMY=0
if [ -d .sweetclaude/product/backlog ]; then
  BL_COUNT=$(find .sweetclaude/product/backlog -maxdepth 1 -name 'BL-*.md' 2>/dev/null | wc -l | tr -d ' ')
  STORY_COUNT=$(find .sweetclaude/product/backlog -maxdepth 2 -name 'STORY-*.md' 2>/dev/null | wc -l | tr -d ' ')
  BUG_COUNT=$(find .sweetclaude/product/backlog -maxdepth 2 -name 'BUG-*.md' 2>/dev/null | wc -l | tr -d ' ')
  DEBT_COUNT=$(find .sweetclaude/product/backlog -maxdepth 2 -name 'DEBT-*.md' 2>/dev/null | wc -l | tr -d ' ')
  CHORE_COUNT=$(find .sweetclaude/product/backlog -maxdepth 2 -name 'CHORE-*.md' 2>/dev/null | wc -l | tr -d ' ')
  OLD_TAXONOMY=$((BL_COUNT + STORY_COUNT + BUG_COUNT + DEBT_COUNT + CHORE_COUNT))
fi
echo "OLD_TAXONOMY=$OLD_TAXONOMY"
```

If `OLD_TAXONOMY` is 0: skip — project is already on the new taxonomy.

If `OLD_TAXONOMY > 0`: present via **AskUserQuestion**:

> "Found {OLD_TAXONOMY} work item(s) using the old taxonomy (BL-/STORY-/BUG-/DEBT-/CHORE- prefixes). These need to be migrated to the ISSUE-NNN format."
>
> Options:
> - **Migrate now** — run taxonomy migration with dry-run preview and safety snapshot
> - **Skip for now** — migrate later with `/sweetclaude:migrate`

If **Migrate now**: run `python3 scripts/migrate/migrate_taxonomy.py --project-dir . --dry-run` first to preview, then on confirmation run without `--dry-run`. Report results. After successful migration, write the doctor prompt marker:

```bash
python3 -c "
import json, os, tempfile
from datetime import datetime, timezone
marker = {
    'trigger': 'migration',
    'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds')
}
path = '.sweetclaude/state/doctor-prompt-pending.json'
os.makedirs(os.path.dirname(path), exist_ok=True)
with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
    json.dump(marker, tmp, indent=2)
    tmp_name = tmp.name
os.replace(tmp_name, path)
" 2>/dev/null || true
```

If **Skip for now**: continue to Step 6c. The migration guard in skills will prompt the user when they next invoke a skill that reads work items.

---

## Step 6c: Success report (only reached when project state is verified clean)

```
SweetClaude updated.
═══════════════════

✓ Version:    {old_version} → {new_version}  (or same if unchanged)
✓ Commit:     {old_sha_short} → {new_sha_short}
✓ Files:      {total count} synced across skills, rules, hooks, config, agents
✓ Hooks:      {only include this line if Step 4b reported cleaned: entries}
✓ Project:    {clean | clean (verified post-migrate)}

→ Restart Claude Code to use this update — skills are loaded at session start
  and are not updated in the current session.
```

The `✓ Project:` line wording depends on which Step 6b exit path was taken:
- DRIFT_COUNT=0 on first check → `clean`
- _migrate ran and POST_MIGRATE_COUNT=0 → `clean (verified post-migrate)`

Print exactly one of those two; do not print the literal text `clean OR clean (verified post-migrate)`.

If `NEW_SKILLS` (from Step 4) is non-empty, append this block after the success report — one line per new skill:

```
New skills added (not available until restart):
  {list each name from NEW_SKILLS, one per line, prefixed with /sweetclaude:}
```

Do not mention any `/sweetclaude:` command as something the user can run now. Do not ask "Want to run it?" or offer to invoke any skill. The current session does not have the updated skill set.

After printing the template (and the new-skills block if applicable), write the doctor prompt marker so the next session offers a post-update checkup:

```bash
if [ -f .sweetclaude/state/sweetclaude.yaml ]; then
  python3 -c "
import json, os, tempfile
from datetime import datetime, timezone
marker = {
    'trigger': 'update',
    'version': '${NEW_VERSION}',
    'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds')
}
path = '.sweetclaude/state/doctor-prompt-pending.json'
os.makedirs(os.path.dirname(path), exist_ok=True)
with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
    json.dump(marker, tmp, indent=2)
    tmp_name = tmp.name
os.replace(tmp_name, path)
" 2>/dev/null || true
fi
```

Continue to Step 7.

---

## Step 7: Surface capabilities

Read [capability-surface.md](capability-surface.md) and execute it in full.


---

## Step 7b: Feature configuration check

Only run this step if `.sweetclaude/state/sweetclaude.yaml` exists in the current project directory — skip silently otherwise.

```bash
python3 - << 'PY'
import yaml, os

sc_path = '.sweetclaude/state/sweetclaude.yaml'
if not os.path.exists(sc_path):
    print("NO_SC")
    exit()

try:
    d = yaml.safe_load(open(sc_path)) or {}
except:
    print("NO_SC")
    exit()

features = d.get('features', {})
keys = ['product_milestones', 'product_backlog', 'product_personas',
        'product_stories', 'document_corpus', 'usage_tracking', 'behavioral_regression']

enabled = sum(1 for k in keys
              if isinstance(features.get(k), dict) and features[k].get('status') == 'active')
unconfigured = sum(1 for k in keys
                   if not isinstance(features.get(k), dict)
                   or features[k].get('status') not in ('active', 'declined'))

try:
    mc = yaml.safe_load(open('.sweetclaude/metrics/config.yaml'))
    if mc.get('enabled', False) and features.get('usage_tracking', {}).get('status') != 'active':
        enabled += 1
        unconfigured = max(0, unconfigured - 1)
except:
    pass

print(f"ENABLED:{enabled}")
print(f"TOTAL:{len(keys)}")
print(f"UNCONFIGURED:{unconfigured}")
PY
```

If output is `NO_SC`, skip. Otherwise, if `UNCONFIGURED` > 0 or `ENABLED` < `TOTAL`:

Use **AskUserQuestion** (single-select):
> "This project has {ENABLED} of {TOTAL} features enabled. Want to review the feature setup?"
- **Yes** → invoke `sweetclaude:_features`
- **No** → continue

---

## Step 7c: Configure plan directory

Only run if `.sweetclaude/` exists in the current project directory — skip silently otherwise.

Ensure the plan directory exists and `plansDirectory` is set in both project settings files. Logic lives in a helper script (same reason as Step 0's `clear-decline.py` — no nested heredocs):

```bash
python3 ~/.claude/scripts/sweetclaude/maintenance/configure-plan-dir.py .
```

---

## Step 8: Project-state migration is run inline (see Step 6b)

The current project is migrated inline by Step 6b right after the framework sync — no session bounce required. Other projects the user opens will hit the same hard demand via `bootstrap` Step 5b on their next entry.

Rationale (Gap #7, locked in `scratch/v3-upgrade-assessment-2026-05-11/DECISIONS.md`):

- Framework sync and project-state migration remain logically independent — if migration fails, the framework sync stays successful (the user can still open other projects on the new framework).
- Every project migrates by the same mechanism — Step 6b here, Step 5b in bootstrap — both routing through `_migrate`.
- No "update the framework, defer migration" path. Migrate or remove.

---

## Rules

- **Always show the diff preview and wait for confirmation before syncing.**
- **Use rsync --delete.** Removed files in the source should be removed from installed locations.
- **Prefer `gh` over `git` for cloning.** It handles private repo auth transparently.
- **Never ask for tokens or credentials.** If auth fails, tell the user to run `gh auth login`.
- **Always clean up temp directories**, even on failure.
- **Do not touch ~/.claude/settings.json.** Hook wiring is handled by install.sh.
- **Do not modify ~/CLAUDE.md.** Also handled by install.sh.
- **This does not affect per-project .sweetclaude/ directories.** Only the global framework.
