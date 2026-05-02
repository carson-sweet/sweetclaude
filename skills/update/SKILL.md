---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:update
description: Update SweetClaude to the latest version from GitHub (or a local repo). Syncs skills, rules, hooks, config, and agents across all projects.
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

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

**Skill state check and bootstrap:**

This runs unconditionally — regardless of whether any new skills were found.

Only run if `.sweetclaude/` exists in the current project directory.

Read `.sweetclaude/state/skills.yaml` if it exists.

**Step 1 — schema migration:** If `skills.yaml` exists with `schema_version: 1`, migrate to v2 now:
- `enabled: true` → `status: active`, `last_changed_at: {onboarded_at or today}`, `last_changed_by: migrated`
- `enabled: false` with `onboarded_at` set → `status: paused`, `last_changed_at: {offboarded_at or onboarded_at or today}`, `last_changed_by: migrated`
- `enabled: false` with `onboarded_at: ~` → `status: uninitialized`, `last_changed_at: ~`, `last_changed_by: ~`
- Drop `onboarded_at` and `offboarded_at` fields; update `schema_version: 2`
- Write atomically: write to `.sweetclaude/state/.skills.yaml.tmp`, then `mv .sweetclaude/state/.skills.yaml.tmp .sweetclaude/state/skills.yaml`
- Report: "Migrated skills.yaml to schema v2."

**Step 2 — fill missing entries:** For `base_path`: read `.sweetclaude/artifact-privacy.yaml` → `categories.product.base_path`. If absent, use `.sweetclaude/artifacts/product`.

For each of the six data-owning skills not already in `skills.yaml`, infer state from data files:

| Skill | Data file that indicates it was in use |
|---|---|
| `product-milestones` | `{base_path}/milestones/MILESTONES-INDEX.md` |
| `product-backlog` | `{base_path}/backlog/BACKLOG-INDEX.md` |
| `product-sprint-plan` | *(no inference — always `uninitialized` if absent)* |
| `product-user-personas` | `.sweetclaude/state/personas.yaml` |
| `product-user-stories` | any `US-*.md` under `{base_path}/stories/` |
| `document-corpus` | `.sweetclaude/state/corpus-pipeline.yaml` |

For each missing entry: data file exists → `status: active`, `last_changed_by: migrated`. Does not exist → `status: uninitialized`. Write atomically (temp file → rename). Do not remove existing entries.

**Skill onboarding prompt:**

After bootstrap, read `skills.yaml`. Build a list of all six data-owning skills where `status: uninitialized`. This list drives the onboarding prompt.

If the list is empty, skip the prompt and continue to 7b.

If non-empty, ask:

> "These skills aren't set up for this project yet. Which would you like to set up now?
>
>   {list only the skills with status: uninitialized, one per line with keyword and description}
>
> Enter keywords (e.g. "milestones backlog"), or "none" to skip."

| Keyword | Skill | What it does |
|---------|-------|--------------|
| `milestones` | `product-milestones` | Roadmap targets like "Exit Stealth" or "MVP Shipped" |
| `backlog` | `product-backlog` | Deferred work items with context |
| `sprint` | `product-sprint-plan` | Select stories from backlog into a sprint |
| `personas` | `product-user-personas` | Define who your users are and what they need |
| `stories` | `product-user-stories` | Write user stories for defined personas |
| `corpus` | `document-corpus` | Import and index your project documents |

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

### 8a: Pre-migration backup

Before running any migration, create a backup of the current state directory. Read `config/migration-registry.yaml` to determine which state files require backup (`backup_required: true`).

If any migration will run (detected in 8c/8d/8e), create the backup first:

```bash
BACKUP_DIR=".sweetclaude/state/backups"
mkdir -p "$BACKUP_DIR"
BACKUP_DATE=$(date +%Y%m%d)
BACKUP_SHA=$(git -C . rev-parse --short HEAD 2>/dev/null || echo "nosha")
BACKUP_FILE="$BACKUP_DIR/pre-migration-${BACKUP_DATE}-${BACKUP_SHA}.tar.gz"

tar -czf "$BACKUP_FILE" -C .sweetclaude/state \
  $(ls .sweetclaude/state/*.yaml .sweetclaude/state/*.md 2>/dev/null | xargs -I{} basename {})

echo "Pre-migration backup: $BACKUP_FILE"
```

Retain only the last 5 backups — remove older ones:

```bash
ls -t .sweetclaude/state/backups/pre-migration-*.tar.gz 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
```

If the backup fails (disk space, permission), warn and ask: "Could not create pre-migration backup. Proceed without backup? [yes/no]"

**Rollback instructions** (display at the end of migration if backup was created):

> "If migration produced unexpected results, restore with:
> `tar -xzf {BACKUP_FILE} -C .sweetclaude/state/`"

### 8b: Detect project state

Check for `.sweetclaude/state/phase.yaml`.

If `.sweetclaude/` does not exist:
> "This project has no SweetClaude state. Run `/sweetclaude:init` to set it up."
Stop.

If `phase.yaml` exists, read `schema_version`.

### 8c: Patch CLAUDE.md auto-fire instruction

Check if `CLAUDE.md` exists in the current project directory. If it has a `## SweetClaude` section, check whether it contains the text `invoke \`sweetclaude:status\` automatically at session start`.

If missing, find the line that reads `Read .sweetclaude/state/phase.yaml` (or similar) and replace it with:
```
- Read `.sweetclaude/state/phase.yaml` and `.sweetclaude/state/improvement-register.md` at session start if they exist. If `.sweetclaude/state/phase.yaml` exists and `.sweetclaude/disabled` does not exist, invoke `sweetclaude:status` automatically at session start.
```

Report whether the patch was applied or already up to date.

### 8d: Already on v2

If `schema_version: 2`: "Project state is current (schema v2). No migration needed." Stop.

### 8e: Migrate v1 → v2

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

### 8f: Migrate skills.yaml v1 → v2

After the phase.yaml migration (or if phase.yaml is already v2), check `.sweetclaude/state/skills.yaml`.

If `skills.yaml` does not exist: nothing to migrate. Continue.

If `skills.yaml` exists with `schema_version: 1`:

Map each entry:
- `enabled: true` → `status: active`, `last_changed_at: {onboarded_at or today}`, `last_changed_by: migrated`
- `enabled: false` with `onboarded_at` set → `status: paused`, `last_changed_at: {offboarded_at or onboarded_at or today}`, `last_changed_by: migrated`
- `enabled: false` with `onboarded_at: ~` → `status: uninitialized`, `last_changed_at: ~`, `last_changed_by: ~`
- Drop `onboarded_at` and `offboarded_at` fields
- Set `schema_version: 2`

Write atomically: write to `.sweetclaude/state/.skills.yaml.tmp`, then `mv .sweetclaude/state/.skills.yaml.tmp .sweetclaude/state/skills.yaml`.

Report: "skills.yaml migrated to schema v2."

If `skills.yaml` exists with `schema_version: 2`: "skills.yaml already on v2. No migration needed."

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
