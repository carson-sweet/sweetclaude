---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:update
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

### 2a: Local repo (developer workflow)

Check if `~/dev/sweetclaude/package.json` exists AND the repo has a remote matching the repository URL.

If found, fetch from origin and use it as the source:

```bash
git -C ~/dev/sweetclaude fetch origin
git -C ~/dev/sweetclaude log --oneline -1
```

- If fetch succeeds: use `~/dev/sweetclaude` as SOURCE_DIR. The local repo may be ahead of GitHub (unpushed dev commits) — that is intentional and correct. Skip to Step 3.
- If fetch fails (network error): warn ("Could not reach GitHub to check for remote updates — proceeding with local repo state.") and use `~/dev/sweetclaude` as SOURCE_DIR. Skip to Step 3.

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
if [ "$SOURCE_DIR" = "$HOME/dev/sweetclaude" ]; then
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

# Skills → legacy install path (created by install.sh — must stay in sync)
if [ -d "$HOME/.claude/skills/sweetclaude" ]; then
  rsync -a --delete $SOURCE_DIR/skills/ ~/.claude/skills/sweetclaude/
fi

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
diff -rq $SOURCE_DIR/skills/ ~/.claude/skills/sweetclaude/ 2>/dev/null
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

**IMPORTANT: This step has two parts. Both parts must execute. Do not stop after 7a.**

### 7a: What's new in this update

Compare the installed hooks and config files (before sync) against the new version. Identify:

1. **New hooks** — files in `$SOURCE_DIR/hooks/` that did not exist in the previously installed `~/.claude/hooks/sweetclaude/`
2. **New skills** — skill directories in `$SOURCE_DIR/skills/` that did not exist in the previously installed `{installPath}/skills/`
3. **New config templates** — files in `$SOURCE_DIR/config/templates/` that are new

For each new item, check whether it requires per-project opt-in. Read the hook or skill to determine what config is needed.

If new items exist, present:
```
New in this update:
  → {skill-name}: {one-line description}
    Available as: /sweetclaude:{skill-name}
    Enable: {opt-in steps if required, else omit}
```

If nothing is new, show: "No new skills or hooks in this update."

**New skill onboarding:**

If any of these skills appear in the new skills list, after presenting them ask the user which to set up now:

| Keyword | Skill | What it does |
|---------|-------|--------------|
| `milestones` | `product-milestones` | Roadmap targets like "Exit Stealth" or "MVP Shipped" |
| `backlog` | `product-backlog` | Deferred work items with context |
| `sprint` | `product-sprint-plan` | Select stories from backlog into a sprint |
| `personas` | `product-user-personas` | Define who your users are and what they need |
| `stories` | `product-user-stories` | Write user stories for defined personas |
| `corpus` | `document-corpus` | Import and index your project documents |

Ask:
> "These skills are new and can import your existing data. Which would you like to set up now?
>
>   {list only the skills that are actually new, one per line with keyword and description}
>
> Enter keywords (e.g. "milestones backlog"), or "none" to skip."

For each skill the user enables, invoke it with argument `onboard`. Complete each onboard flow before starting the next. If the user says "none", continue.

**Then immediately continue to 7b. Do not stop here.**

### 7b: Full skill catalog

**This section always runs regardless of what 7a found.**

Read all skill directories from `$SOURCE_DIR/skills/`. For each, extract the `description` and `category` fields from `SKILL.md` frontmatter. Group by category. Infer category from directory name prefix if `category` is absent (`code-*` → Code, `design-*` → Design, `product-*` → Product, `documents-*` → Documents, everything else → Framework).

Present immediately after the 7a output:

```
All installed skills (v{new_version}):
═══════════════════════════════════════

PRODUCT
  /sweetclaude:product-backlog         — {description, truncated to ~80 chars}
  /sweetclaude:product-milestones      — ...
  ...

CODE
  /sweetclaude:code-feature            — ...
  ...

DESIGN
  /sweetclaude:design-architecture     — ...
  ...

DOCUMENTS
  /sweetclaude:document-corpus         — ...
  ...

FRAMEWORK
  /sweetclaude:go                      — ...
  /sweetclaude:status                  — ...
  ...
```

---

## Step 8: Migrate existing project state

After syncing the framework, check whether the **current project** (the working directory where this skill was run) has `.sweetclaude/` state that needs migration.

### 8a: Detect project state

Check for `.sweetclaude/state/phase.yaml`.

If `.sweetclaude/` does not exist:
> "This project has no SweetClaude state. Run `/sweetclaude:init` to set it up."
Stop.

If `phase.yaml` exists, read `schema_version`.

### 8b: Patch CLAUDE.md auto-fire instruction

Check if `CLAUDE.md` exists in the current project directory. If it has a `## SweetClaude` section, check whether it contains the text `invoke \`sweetclaude:status\` automatically at session start`.

If missing, find the line that reads `Read .sweetclaude/state/phase.yaml` (or similar) and replace it with:
```
- Read `.sweetclaude/state/phase.yaml` and `.sweetclaude/state/improvement-register.md` at session start if they exist. If `.sweetclaude/state/phase.yaml` exists and `.sweetclaude/disabled` does not exist, invoke `sweetclaude:status` automatically at session start.
```

Report whether the patch was applied or already up to date.

### 8c: Already on v2

If `schema_version: 2`: "Project state is current (schema v2). No migration needed." Stop.

### 8d: Migrate v1 → v2

If `schema_version: 1`, map the old fields:

| v1 field | v2 destination | Notes |
|---|---|---|
| `phase` | `active_work_item.phase` | Carry forward unless value is `SHIP` or `DONE` → set to `~` |
| `work_type` | `active_work_item.type` | See mapping table below |
| `deference_level` | `deference_level` | Carry forward |
| `project_type` | `project_type` | Carry forward |
| `safety_snapshot` | `safety_snapshot` | Carry forward |
| `init_step` | *(drop)* | No v2 equivalent |

**`work_type` mapping:**

| v1 value | v2 value |
|---|---|
| `net-new` | `net-new-feature` |
| `bug-fix` | `bug-fix` |
| `enhancement` | `enhancement` |
| `refactor` | `tech-debt` |
| `security` | `security-patch` |
| `hotfix` | `hotfix` |
| `performance` | `performance-optimization` |
| anything else | `~` (find-skill will set it when work resumes) |

Show the user a preview before writing:

```
Schema migration: v1 → v2
═════════════════════════
Current (v1):
  phase:           {phase}
  work_type:       {work_type}
  deference_level: {deference_level}
  project_type:    {project_type}
  safety_snapshot: {safety_snapshot}

After migration (v2):
  version_stage:   (you'll set this below)
  deference_level: {deference_level}    [carried forward]
  project_type:    {project_type}       [carried forward]
  safety_snapshot: {safety_snapshot}    [carried forward]
  active_work_item:
    type:  {mapped_type or ~}
    phase: {phase or ~}
    (remaining fields: null — set by find-skill when work resumes)
```

Ask:
> "What version stage is this project at?
> PROTOTYPE | ALPHA | BETA | GA | SCALED | MAINTAINED
>
> PROTOTYPE = early exploration · ALPHA = working but rough · BETA = feature complete · GA = production-ready"

Wait for the user's answer. Then confirm:
> "Ready to write the migrated phase.yaml. Proceed?"

Write `.sweetclaude/state/phase.yaml`:

```yaml
# .sweetclaude/state/phase.yaml
# SweetClaude phase state — schema version 2
schema_version: 2

version_stage: {user_answer}
deference_level: {carried}
project_type: {carried}
safety_snapshot: {carried}
last_work_item_id: ~

active_work_item:
  id: ~
  type: {mapped_type or ~}
  workflow: []
  phase: {v1_phase or ~}
  title: ~
  started: ~
  entry_category: ~
```

Report: "phase.yaml migrated to schema v2. Use `/sweetclaude:find-skill` to resume work."

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
