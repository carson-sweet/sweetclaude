---
name: sweetclaude:update-skills
description: Update SweetClaude to the latest version from GitHub (or a local repo). Syncs skills, rules, hooks, config, and agents across all projects.
---

# Update SweetClaude

Fetch the latest SweetClaude and sync it to all installed locations.

**This skill can be run from any project directory.**

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

Try sources in this order:

### 2a: Local repo (developer workflow)

Check if `~/dev/sweetclaude/package.json` exists AND is a git repo with remote matching the repository URL.

If found:
```bash
git -C ~/dev/sweetclaude log --oneline -1
```
Use `~/dev/sweetclaude` as SOURCE_DIR. Skip to Step 3.

### 2b: GitHub (standard user workflow)

Clone a shallow copy to a temp directory. Use `gh` if available (handles private repos with existing auth), fall back to `git`.

```bash
TMPDIR=$(mktemp -d)

# Prefer gh — it uses the user's existing GitHub auth (handles private repos)
if command -v gh &>/dev/null; then
  gh repo clone {owner}/{repo} "$TMPDIR/sweetclaude" -- --depth 1
else
  git clone --depth 1 {repository_url} "$TMPDIR/sweetclaude"
fi
```

If clone fails with an auth error, tell the user:
> "The SweetClaude repo requires authentication. Run `! gh auth login` to authenticate with GitHub, then try again."

Do not retry. Do not ask for tokens.

Use `$TMPDIR/sweetclaude` as SOURCE_DIR.

---

## Step 3: Compare versions

```bash
# Get latest commit and version from source
git -C $SOURCE_DIR rev-parse HEAD
git -C $SOURCE_DIR log --oneline -5
cat $SOURCE_DIR/package.json
```

If the source HEAD SHA matches the installed `gitCommitSha`: "Already up to date." Clean up temp dir if used. Stop.

Otherwise, show what changed since the installed version:

```bash
git -C $SOURCE_DIR log --oneline {installed_sha}..HEAD
```

Then diff against installed:

```bash
diff -rq $SOURCE_DIR/skills/ {installPath}/skills/ 2>/dev/null
diff -rq $SOURCE_DIR/rules/ ~/.claude/rules/sweetclaude/ 2>/dev/null
diff -rq $SOURCE_DIR/hooks/ ~/.claude/hooks/sweetclaude/ 2>/dev/null
diff -rq $SOURCE_DIR/config/ ~/.claude/config/sweetclaude/ 2>/dev/null
diff -rq $SOURCE_DIR/agents/ ~/.claude/agents/sweetclaude/ 2>/dev/null
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
```

Wait for user confirmation before proceeding.

---

## Step 4: Sync

Copy from SOURCE_DIR to installed locations. Use `rsync --delete` to remove files that no longer exist in the source.

```bash
# Skills → plugin cache
rsync -a --delete $SOURCE_DIR/skills/ {installPath}/skills/

# Top-level files → plugin cache
for f in CLAUDE.md package.json LICENSE; do
  [ -f "$SOURCE_DIR/$f" ] && cp "$SOURCE_DIR/$f" {installPath}/
done

# Plugin manifest
rsync -a $SOURCE_DIR/.claude-plugin/ {installPath}/.claude-plugin/

# Framework dirs → ~/.claude/
rsync -a --delete $SOURCE_DIR/rules/ ~/.claude/rules/sweetclaude/
rsync -a --delete $SOURCE_DIR/hooks/ ~/.claude/hooks/sweetclaude/
rsync -a --delete $SOURCE_DIR/config/ ~/.claude/config/sweetclaude/
rsync -a --delete $SOURCE_DIR/agents/ ~/.claude/agents/sweetclaude/

# Ensure hooks are executable
chmod +x ~/.claude/hooks/sweetclaude/*.sh 2>/dev/null || true
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

## Step 7: Surface new capabilities

Compare the installed hooks and config files (before sync) against the new version. Identify:

1. **New hooks** — files in `$SOURCE_DIR/hooks/` that did not exist in the previously installed `~/.claude/hooks/sweetclaude/`
2. **New skills** — skill directories in `$SOURCE_DIR/skills/` that did not exist in the previously installed `{installPath}/skills/`
3. **New config templates** — files in `$SOURCE_DIR/config/templates/` that are new

For each new capability, check whether it requires per-project opt-in (e.g., a config file in `.sweetclaude/`). Read the hook or skill to determine what config is needed.

Present after the update report:

```
New in this update:
  → {capability name}: {one-line description}
    Enable: {what the user needs to do, e.g. "create .sweetclaude/version-bump.yaml"}

  → {capability name}: {one-line description}
    Available as: /sweetclaude:{skill-name}
```

If no new capabilities, omit this section.

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
