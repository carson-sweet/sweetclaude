---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Update SweetClaude to the latest version from GitHub (or a local repo)."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# Update SweetClaude

Fetch the latest SweetClaude and sync it to all installed locations.

**This skill can be run from any project directory.**

---

## Step 0: Clear decline (Gap #8 manual reset)

Running `/sweetclaude:update` directly is interpreted as "I want updates again." Clear `framework.update.declined` before doing anything else. If the project doesn't have a `sweetclaude.yaml` (run from outside a SweetClaude project), this is a silent no-op.

```bash
if [ -f .sweetclaude/state/sweetclaude.yaml ]; then
  python3 - .sweetclaude/state/sweetclaude.yaml << 'PY'
import sys, yaml, tempfile, os
path = sys.argv[1]
try:
    with open(path) as f: d = yaml.safe_load(f) or {}
except Exception:
    sys.exit(0)
upd = d.setdefault('framework',{}).setdefault('update',{})
if upd.get('declined') not in (None, False):
    upd['declined'] = None
    with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
        yaml.dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
        tmp_name = tmp.name
    os.replace(tmp_name, path)
PY
fi
```

If the user picks "Not now" later in this update flow, `declined` will be re-set to the specific version they declined (per Gap #1's version-aware decline rule). This Step 0 is the explicit-re-engagement reset.

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

If EFFECTIVE_SHA matches the installed `gitCommitSha`: "Already up to date." Clean up temp dir if used. Stop.

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
| `product-milestones` | `{base_path}/milestones/MILESTONES-INDEX.md` |
| `product-parking-lot` or `product-backlog` | `{base_path}/backlog/BACKLOG-INDEX.md` |
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

## Step 4: Sync

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

# Scripts → plugin cache (contains migration scripts and other utilities)
if [ -d "$SOURCE_DIR/scripts" ]; then
  rsync -a --delete $SOURCE_DIR/scripts/ {installPath}/scripts/
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
```

---

## Step 5: Update plugin metadata

Update `~/.claude/plugins/installed_plugins.json`:

1. Read the HEAD SHA: `git -C $SOURCE_DIR rev-parse HEAD`
2. Read the version from `$SOURCE_DIR/package.json`
3. Update the `sweetclaude@sweetclaude` entry:
   - `lastUpdated` → current ISO timestamp
   - `gitCommitSha` → HEAD SHA
   - `version` → package.json version

---

## Step 6: Clean up and report

If a temp directory was used, remove it:
```bash
rm -rf "$TMPDIR"
```

Run a final diff to confirm sync:
```bash
diff -rq $SOURCE_DIR/skills/ {installPath}/skills/ 2>/dev/null
diff -rq $SOURCE_DIR/skills/ ~/.claude/skills/sweetclaude/ 2>/dev/null
diff -rq $SOURCE_DIR/scripts/ {installPath}/scripts/ 2>/dev/null
```

Report:

```
SweetClaude updated.
═══════════════════

✓ Version:    {old_version} → {new_version}  (or same if unchanged)
✓ Commit:     {old_sha_short} → {new_sha_short}
✓ Files:      {total count} synced across skills, rules, hooks, config, agents

→ New Claude Code sessions in any project will use the updated version.
  Current sessions keep the old version until restarted.
```

---

## Step 7: Surface capabilities

Read [capability-surface.md](capability-surface.md) and execute it in full.

It has two parts (7a and 7b) — both must run. 7a presents new items in this update, then runs a `skills.yaml` schema migration and an onboarding prompt for data-owning skills. 7b prints the full skill catalog grouped by category. Do not stop between 7a and 7b.


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

Ensure the plan directory exists and `plansDirectory` is set in both project settings files:

```bash
if [ -d ".sweetclaude" ]; then
  mkdir -p .sweetclaude/plans
  python3 - << 'PY'
import json, os, tempfile
os.makedirs('.claude', exist_ok=True)
for path in ['.claude/settings.json', '.claude/settings.local.json']:
    try:
        d = json.load(open(path))
    except:
        d = {}
    if d.get('plansDirectory') != '.sweetclaude/plans':
        d['plansDirectory'] = '.sweetclaude/plans'
        with tempfile.NamedTemporaryFile('w', dir='.claude', suffix='.tmp', delete=False) as tmp:
            json.dump(d, tmp, indent=2)
            tmp_name = tmp.name
        os.replace(tmp_name, path)
PY
fi
```

---

## Step 8: (removed)

Project-state migration is **not** part of the update flow. Update only syncs the framework. The current project (and any other v3 project the user opens) is migrated by `sweetclaude:bootstrap` on next session start, via the drift-detection scan now built into the runner.

Rationale (locked in `scratch/v3-upgrade-assessment-2026-05-11/DECISIONS.md`, Gap #7):

- Update success and project-migration success are independent — a failed migration no longer makes update look failed.
- Every v3 project migrates by the same mechanism: bootstrap detects drift, demands "Migrate now" or "Remove SweetClaude from this project."
- No "update the framework, defer migration" path — see Gap #7 hard demand rule.

If you want to migrate the current project immediately after this update completes, close this session and reopen it. Bootstrap will detect drift on entry and present the demand.

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
