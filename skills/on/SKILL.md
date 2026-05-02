---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:on
description: "Get started with SweetClaude on any project — new idea or existing codebase. Detects context automatically and walks you through setup, then hands off to the pipeline."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# SweetClaude Sherpa

One starting point. Works whether you have an empty folder or an existing project.

**Follow these steps in order. Do not skip.**

---

## Step 0: Detect context

Check four things in order:

1. **Disabled?** Does `.sweetclaude/disabled` exist?

   If yes:
   ```bash
   rm .sweetclaude/disabled
   ```

   Check for an available update:
   ```bash
   installed=$(cat ~/.claude/plugins/installed_plugins.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); e=[v for k,v in d.items() if 'sweetclaude' in k.lower()]; print(e[0].get('version','?') if e else '?')" 2>/dev/null)
   latest=$(cat ~/dev/sweetclaude/package.json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null)
   echo "installed=$installed latest=$latest"
   ```

   If `latest` differs from `installed` (and neither is `?`):
   > "SweetClaude reactivated. Update available: v{installed} → v{latest}. Run `/sweetclaude:update` to get the latest."

   Otherwise:
   > "SweetClaude reactivated. (v{installed}, up to date)"

   **RAG and MCP check:** Run these to detect existing infrastructure (a manifest is not the only signal):
   ```bash
   canonical_count=$(find corpus/canonical/ -type f 2>/dev/null | wc -l | tr -d ' ')
   manifest_files=$(cat .rag-index/.index-manifest.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('files',{})))" 2>/dev/null)
   lancedb_exists=$(ls .rag-index/lancedb/ 2>/dev/null | wc -l | tr -d ' ')
   rag_mcps=$(cat .mcp.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); servers=d.get('mcpServers',{}); rags=[k for k,v in servers.items() if 'rag' in k.lower() or 'rag' in str(v).lower()]; print('\n'.join(rags) if rags else 'none')" 2>/dev/null)
   ```

   - If `rag_mcps` is not `none` (RAG MCPs exist in `.mcp.json`): note them — the SOP may need updating.
   - If `lancedb_exists > 0` but `manifest_files` is empty or 0: RAG data exists without a manifest — offer to write the manifest via `/sweetclaude:document-corpus`.
   - If `canonical_count > 0` and no RAG at all: offer to index.
   - If RAG is indexed (manifest_files > 0): offer to check freshness.

   If `.sweetclaude/state/project-sop.md` does not exist but RAG MCPs or corpus were found: offer to create the SOP now so SweetClaude understands this project's tooling.

   Stop.

2. **Already configured?** Does `.sweetclaude/state/phase.yaml` exist?

   If yes:
   - Check if `CLAUDE.md` has the auto-fire instruction: look for the text `invoke \`sweetclaude:status\` automatically at session start`. If missing, patch the SweetClaude section of `CLAUDE.md`:
     - Find the line that reads `Read .sweetclaude/state/phase.yaml` (or similar)
     - Replace it with: `- Read \`.sweetclaude/state/phase.yaml\` and \`.sweetclaude/state/improvement-register.md\` at session start if they exist. If \`.sweetclaude/state/phase.yaml\` exists and \`.sweetclaude/disabled\` does not exist, invoke \`sweetclaude:status\` automatically at session start.`
     - Tell the user: "Also updated your CLAUDE.md with the auto-fire instruction."
   - **Artifact privacy check:** Run `ls .sweetclaude/artifact-privacy.yaml 2>/dev/null`. If the file does not exist:
     > "Artifact privacy is not yet configured for this project — this controls where planning documents (milestones, product briefs, strategy docs) are stored and whether they're tracked in git. Want to set that up now?"
     If yes: run Step 2.5-E inline (do not re-run the full on flow). If no: stop as normal.
   - Stop:
   > "SweetClaude is already set up here. Run `/sweetclaude:status` to see where things stand, or `/sweetclaude:help` for commands."

3. **Existing project?** Does `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `Makefile`, `src/`, or a git repo with commits exist?

   If yes → take the **Existing Project** path (Step 1-E through Step 6-E below).

4. **Empty folder?** Nothing meaningful present (a README or .gitignore is fine).

   If yes → take the **New Project** path (Step 1-N through Step 6-N below).

---

## New Project Path

### Step 1-N: What do you want to build?

Ask:
> "What do you want to build?"

Listen. Do not structure. Do not correct. Let them talk. If the answer is very short, ask one follow-up:
> "What problem does it solve, and for whom?"

---

### Step 2-N: Initialize

Set up SweetClaude state for this project:

**2a. Git:** If no git repo exists, offer to initialize one. Get preferred branch name (main/master) and any gitignore exclusions. Initialize and make an initial commit.

**2b. State directory:** Create `.sweetclaude/state/` and `.sweetclaude/traceability/`. Create these files:

- `.sweetclaude/state/phase.yaml` — initial content:
  ```yaml
  # .sweetclaude/state/phase.yaml
  # SweetClaude phase state — schema version 2
  schema_version: 2

  version_stage: PROTOTYPE
  deference_level: ~
  project_type: new
  safety_snapshot: none
  last_work_item_id: ~

  active_work_item:
    id: ~
    type: net-new-feature
    workflow: []
    phase: DISCOVER
    title: ~
    started: ~
    entry_category: ~
  ```
- `.sweetclaude/state/decision-log.md` — empty table (Date / Phase / Decision / Rationale)
- `.sweetclaude/state/assumption-register.md` — empty table (Assumption / Status / Evidence)
- `.sweetclaude/state/improvement-register.md` — empty table (Date / Type / Learning)
- `.sweetclaude/state/scope-changes.md` — empty table (Date / Item / Direction / Phase / Rationale)
- `.sweetclaude/state/skills.yaml` — skill enablement state:
  ```yaml
  # .sweetclaude/state/skills.yaml
  # SweetClaude skill enablement state — schema version 2
  schema_version: 2

  skills:
    product-milestones:
      status: uninitialized
      last_changed_at: ~
      last_changed_by: ~
    product-backlog:
      status: uninitialized
      last_changed_at: ~
      last_changed_by: ~
    product-sprint-plan:
      status: uninitialized
      last_changed_at: ~
      last_changed_by: ~
    product-user-personas:
      status: uninitialized
      last_changed_at: ~
      last_changed_by: ~
    product-user-stories:
      status: uninitialized
      last_changed_at: ~
      last_changed_by: ~
    document-corpus:
      status: uninitialized
      last_changed_at: ~
      last_changed_by: ~
  ```
- `.sweetclaude/traceability/requirements-map.md` — empty table
- `.sweetclaude/traceability/ripple-map.md` — empty table

**2c. Strategy structure:** `mkdir -p strategy/{competitive-analysis,market-messaging,meeting-prep,narrative-arc,academic-research}`

**2d. CLAUDE.md:** Generate a CLAUDE.md using the user's one-line description from Step 1-N. Include: what this is, key directories, build/test commands (placeholder), project-specific rules placeholder, SweetClaude section, and distribution warning. Present to user before writing.

**2e. Existing strategy files:** Ask: "Do you have strategy documents to bring in — positioning docs, research, notes?" If yes, get the path and copy into `corpus/raw/inbox/`. Tell them to run `/sweetclaude:document-corpus` to organize them.

**2f. RAG offer:** After 2e, offer:
> "Once your docs are in place, I can index them into a searchable RAG corpus — lets you find design decisions, feature specs, and research by concept rather than by grep. Want to set that up now, or should I explain what it gives you?"

If the user says yes: create corpus directory structure and write integrity protection file, then invoke `/sweetclaude:document-corpus`:
```bash
mkdir -p corpus/canonical corpus/raw/inbox corpus/archive
```
Write `corpus/LLM_README.md`:
```markdown
# corpus/ — DO NOT MODIFY DIRECTLY

This directory is managed by `sweetclaude:document-corpus`. Modifying files here
directly corrupts the RAG index and causes stale search results downstream.

**To add documents:** Place them in `corpus/raw/inbox/` and run `/sweetclaude:document-corpus intake`
**To update canonical documents:** Run `/sweetclaude:document-corpus` and use the update flow
**To reindex after any manual change:** Run `/sweetclaude:document-corpus reindex`

If you are Claude and you are about to write to a file in this directory outside of
a corpus skill context, STOP and surface this to the user instead.
```
Then invoke `/sweetclaude:document-corpus`.

If they ask for explanation: explain that RAG lets Claude search documentation semantically — e.g., "what did we decide about auth?" surfaces the right ADR even if it doesn't contain those exact words. Then offer to proceed. Do not auto-invoke without consent.

**2g. MCP discovery + project SOP:** Read `.mcp.json` if it exists. For each configured MCP server:
- Identify its type by name and config: `rag` (name or env contains "rag", or DB_PATH points to lancedb), `database`, `filesystem`, `api`, or `custom`.
- For RAG servers: run `ls {DB_PATH}/ 2>/dev/null | wc -l` to check if the index has data. Note scope if determinable from BASE_DIR.
- For unrecognized non-RAG servers: ask the user one question per server: "I see `{name}` is configured — what is it for, and how should I use it in this project?"

Create `.sweetclaude/state/project-sop.md`:

```markdown
---
updated: {today}
---

# SweetClaude Project SOP

What is here and how to use it — project-specific tool knowledge for Claude.

## MCP Tools

| Name | Type | Purpose | Notes |
|------|------|---------|-------|
{one row per MCP from .mcp.json, type from detection, purpose from user answers or inference}

## RAG Indexes

| MCP Name | Base Dir | Scope | Last Indexed | Notes |
|----------|----------|-------|-------------|-------|
{one row per RAG MCP — scope = what directories are indexed; "unknown" if not yet run}

## Corpus & Docs Structure

{If corpus/ exists: describe canonical/, raw/, archive/ and their purpose.}
{If docs/ exists: note what belongs here vs corpus.}
{If neither: "Not yet configured."}

## Project Conventions

{Empty — populated as conventions are established.}
```

Tell the user: "I've created `.sweetclaude/state/project-sop.md` to track this project's tools and conventions. I'll keep it updated as things change."

---

### Step 2.5-N: Artifact privacy setup

Determine where SweetClaude stores planning artifacts. **Assess the environment first. Do not ask questions before looking.**

**Check for existing manifest first:**
Run: `ls .sweetclaude/artifact-privacy.yaml 2>/dev/null`

If it exists: ask "You already have artifact privacy settings configured — want to update them?" If no, skip to Step 3-N. If yes, proceed below and overwrite both manifest files.

**Phase 1: Environment assessment — run all of these, ask nothing yet**

```bash
# Actual repo visibility
gh repo view --json visibility,name 2>/dev/null || echo "NO_GH_REMOTE"

# What is gitignored
cat .gitignore 2>/dev/null

# Where planning artifacts currently exist
find docs/ -maxdepth 3 -name "*.md" 2>/dev/null | head -20
find strategy/ -maxdepth 3 -name "*.md" 2>/dev/null | head -20
find .sweetclaude/ -name "*.md" 2>/dev/null | grep -v "/state/" | head -20

# What is already tracked in git vs untracked
git ls-files docs/ strategy/ 2>/dev/null | head -30
git ls-files --others --exclude-standard docs/ strategy/ 2>/dev/null | head -10
```

**Phase 2: Present what you found — before asking anything**

Report in plain language:
> "Here's what I found:
> - Repo: {private | public | no remote detected}
> - Existing planning docs: {locations where docs already exist, or 'none found'}
> - Gitignored: {relevant ignored paths}
> - Already tracked in git: {any docs/strategy files committed, or 'none'}"

**Phase 3: Ask only what the scan could not determine — one question at a time**

**Visibility intent** — only ask if the repo is currently private:
> "The repo is currently private. Do you plan to make it public?"
Accept: yes / no / not sure yet. Record verbatim.
If the repo is already public: note it, skip this question entirely.

**Per category — one at a time. Lead with what was found; don't ask as if starting from scratch:**

**Strategy** (competitive analysis, market messaging, positioning, research):
> "Strategy documents. [If found: I see these at {location}.] Should these be tracked in the repo or kept private?"
If public: "Where should they live? [Suggest found location if applicable, otherwise default `strategy/`.]" Store confirmed path.
If private: location is `.sweetclaude/strategy/` — no question needed.

**Product** (brief, PRD, milestones, roadmap, backlog, user stories):
> "Product definition documents. [If found: I see these at {location}.] Tracked or private?"
If public: "Where? [Suggest found location or default `docs/`.]" Store confirmed path.
If private: location is `.sweetclaude/product/` — no question needed.

**Technical** (architecture, tech spec, data model, API design):
> "Technical documents. [If found: I see these at {location}.] Tracked or private?"
If public: "Where? [Suggest found location or default `docs/`.]" Store confirmed path.
If private: location is `.sweetclaude/technical/` — no question needed.

**Design** (UX flows, wireframes):
> "Design artifacts. [If found: I see these at {location}.] Tracked or private?"
If public: "Where? [Suggest found location or default `docs/design/`.]" Store confirmed path.
If private: location is `.sweetclaude/design/` — no question needed.

For each: ask for one-sentence rationale. Record decision, location, and rationale.

**Write both manifest files after all four questions are answered:**

`.sweetclaude/artifact-privacy.yaml`:
```yaml
schema_version: 1
recorded: {today's date}

repo:
  current_visibility: "{Q1 answer}"
  future_intent: "{verbatim answer}"

categories:
  strategy:
    privacy: public | private
    base_path: "{confirmed path}"
  product:
    privacy: public | private
    base_path: "{confirmed path}"
  technical:
    privacy: public | private
    base_path: "{confirmed path}"
  design:
    privacy: public | private
    base_path: "{confirmed path}"
```

`.sweetclaude/artifact-privacy.md`:
```markdown
# Artifact Privacy Manifest
**Recorded:** {today's date}
**Schema:** 1

This document records where SweetClaude stores planning artifacts for this project.
Review and update if repo visibility changes — run `/sweetclaude:on` and choose to update settings.

## Repository Visibility

**Current:** {Q1 answer}
**Future intent:** {verbatim answer}

## Category Decisions

### Strategy Documents
*Competitive analysis, market messaging, positioning, research*
**Decision:** {Public|Private}
**Rationale:** {user's rationale}
**Location:** `{base_path}/`

### Product Definition
*Product brief, PRD, milestones, roadmap, backlog, user stories*
**Decision:** {Public|Private}
**Rationale:** {user's rationale}
**Location:** `{base_path}/`

### Technical Documents
*Architecture, tech spec, data model, API design*
**Decision:** {Public|Private}
**Rationale:** {user's rationale}
**Location:** `{base_path}/`

### Design Artifacts
*UX flows, wireframes*
**Decision:** {Public|Private}
**Rationale:** {user's rationale}
**Location:** `{base_path}/`

## Internal State
*Phase tracking, decision logs, improvement register, assumption register*
Always private — stored in `.sweetclaude/state/` (gitignored). No decision required.

## Changelog
| Date | Change |
|------|--------|
| {today's date} | Initial manifest created during /sweetclaude:on |
```

**Confirm and warn after writing:**
Tell the user:
> "Artifact privacy configured. {N} categories private, {M} public. Recorded in `.sweetclaude/artifact-privacy.md`."

For each public category in a repo that is/will be public, confirm:
> "Note: {category} documents at `{path}` will be publicly visible — that's what you chose. Confirmed."

Check whether any confirmed public path appears to be gitignored. If so:
> "The path `{path}` appears to be gitignored. Documents there won't be tracked until you add a gitignore exception. Want me to add one now?"

---

### Step 3-N: Product discovery

Run `/sweetclaude:product-discovery` using the idea from Step 1-N as starting input.

Before starting, offer three depth levels:
- **L1 — Intent and boundaries:** What you're building, for whom, and what's out of scope. Good for utilities and hobby projects.
- **L2 — Problem and success:** Adds concrete problem definition, audience refinement, success framing, and a challenge of the framing. Good for internal tools and significant projects.
- **L3 — Full pain thesis:** Adds pain measurement, market context, accountability analysis, escalation chains, and a validation rubric. For commercial products.

Let the user choose depth or ask for a recommendation.

Wait for the user to be satisfied before proceeding.

---

### Step 4-N: User personas

Run `/sweetclaude:product-user-personas`.

Wait for completion.

---

### Step 5-N: Competitive landscape (optional)

Offer:
> "Want to map the competitive landscape before moving to product definition? I can run a survey (L1), comparison matrix (L2), or feature-deep analysis (L3) via `/sweetclaude:product-competition`."

Run if the user wants it. Otherwise proceed.

---

### Step 6-N: Hand off

Tell the user:
> "The strategic foundation is set. Next: product definition (product brief, PRD), then design, then implementation. Run `/sweetclaude:go` to continue, or `/sweetclaude:help` to see what's possible."

Do not auto-invoke anything. The user decides when to continue.

---

## Existing Project Path

### Step 1-E: Safety snapshot

Before touching anything, create a safety branch:

```bash
git stash --include-untracked -m "pre-sweetclaude: stash uncommitted changes" 2>/dev/null
git branch pre-sweetclaude 2>/dev/null || git branch pre-sweetclaude-$(date +%Y%m%d)
git stash pop 2>/dev/null
```

Tell the user: "Created `pre-sweetclaude` branch. If you ever want to undo everything SweetClaude added, check out that branch."

If the project has no git: offer to initialize one (same as Step 2-N 2a). The initial commit serves as the snapshot.

---

### Step 2-E: Initialize

Same as Step 2-N (2b through 2e) — create state directory, strategy structure, CLAUDE.md, optionally onboard files.

For CLAUDE.md generation: scan the project for language, framework, package manager, test runner, and build commands first. Use those in the CLAUDE.md instead of placeholders.

**skills.yaml override for existing projects:** When creating `.sweetclaude/state/skills.yaml` in Step 2b, use schema v2 and bootstrap from data files. Read `artifact-privacy.yaml` → `categories.product.base_path` (fallback: `.sweetclaude/artifacts/product`). For each skill, check the data file signal:

| Skill | Data file signal |
|---|---|
| `product-milestones` | `{base_path}/milestones/MILESTONES-INDEX.md` exists |
| `product-backlog` | `{base_path}/backlog/BACKLOG-INDEX.md` exists |
| `product-sprint-plan` | *(no signal — always `uninitialized`)* |
| `product-user-personas` | `.sweetclaude/state/personas.yaml` exists |
| `product-user-stories` | any `US-*.md` under `{base_path}/stories/` |
| `document-corpus` | `.sweetclaude/state/corpus-pipeline.yaml` exists |

If data file exists → `status: active`, `last_changed_at: {today}`, `last_changed_by: migrated`. Otherwise → `status: uninitialized`, `last_changed_at: ~`, `last_changed_by: ~`.

Write atomically: write to `.sweetclaude/state/.skills.yaml.tmp`, then `mv .sweetclaude/state/.skills.yaml.tmp .sweetclaude/state/skills.yaml`.

Note: `artifact-privacy.yaml` may not exist yet when this step runs (it is created in Step 2.5-E). Use the fallback path if it is absent.

---

### Step 2.5-E: Artifact privacy setup

Determine where SweetClaude stores planning artifacts. **Assess the environment first. Do not ask questions before looking.**

**Check for existing manifest first:**
Run: `ls .sweetclaude/artifact-privacy.yaml 2>/dev/null`

If it exists: ask "You already have artifact privacy settings configured — want to update them?" If no, skip to Step 3-E. If yes, proceed below and overwrite both manifest files.

**Phase 1: Environment assessment — run all of these, ask nothing yet**

```bash
# Actual repo visibility
gh repo view --json visibility,name 2>/dev/null || echo "NO_GH_REMOTE"

# What is gitignored
cat .gitignore 2>/dev/null

# Where planning artifacts currently exist
find docs/ -maxdepth 3 -name "*.md" 2>/dev/null | head -20
find strategy/ -maxdepth 3 -name "*.md" 2>/dev/null | head -20
find .sweetclaude/ -name "*.md" 2>/dev/null | grep -v "/state/" | head -20

# What is already tracked in git vs untracked
git ls-files docs/ strategy/ 2>/dev/null | head -30
git ls-files --others --exclude-standard docs/ strategy/ 2>/dev/null | head -10
```

**Phase 2: Present what you found — before asking anything**

Report in plain language:
> "Here's what I found:
> - Repo: {private | public | no remote detected}
> - Existing planning docs: {locations where docs already exist, or 'none found'}
> - Gitignored: {relevant ignored paths}
> - Already tracked in git: {any docs/strategy files committed, or 'none'}"

**Phase 3: Ask only what the scan could not determine — one question at a time**

**Visibility intent** — only ask if the repo is currently private:
> "The repo is currently private. Do you plan to make it public?"
Accept: yes / no / not sure yet. Record verbatim.
If the repo is already public: note it, skip this question entirely.

**Per category — one at a time. Lead with what was found; don't ask as if starting from scratch:**

**Strategy** (competitive analysis, market messaging, positioning, research):
> "Strategy documents. [If found: I see these at {location}.] Should these be tracked in the repo or kept private?"
If public: "Where should they live? [Suggest found location if applicable, otherwise default `strategy/`.]" Store confirmed path.
If private: location is `.sweetclaude/strategy/` — no question needed.

**Product** (brief, PRD, milestones, roadmap, backlog, user stories):
> "Product definition documents. [If found: I see these at {location}.] Tracked or private?"
If public: "Where? [Suggest found location or default `docs/`.]" Store confirmed path.
If private: location is `.sweetclaude/product/` — no question needed.

**Technical** (architecture, tech spec, data model, API design):
> "Technical documents. [If found: I see these at {location}.] Tracked or private?"
If public: "Where? [Suggest found location or default `docs/`.]" Store confirmed path.
If private: location is `.sweetclaude/technical/` — no question needed.

**Design** (UX flows, wireframes):
> "Design artifacts. [If found: I see these at {location}.] Tracked or private?"
If public: "Where? [Suggest found location or default `docs/design/`.]" Store confirmed path.
If private: location is `.sweetclaude/design/` — no question needed.

For each: ask for one-sentence rationale. Record decision, location, and rationale.

**Write both manifest files after all four questions are answered:**

`.sweetclaude/artifact-privacy.yaml`:
```yaml
schema_version: 1
recorded: {today's date}

repo:
  current_visibility: "{Q1 answer}"
  future_intent: "{verbatim answer}"

categories:
  strategy:
    privacy: public | private
    base_path: "{confirmed path}"
  product:
    privacy: public | private
    base_path: "{confirmed path}"
  technical:
    privacy: public | private
    base_path: "{confirmed path}"
  design:
    privacy: public | private
    base_path: "{confirmed path}"
```

`.sweetclaude/artifact-privacy.md`:
```markdown
# Artifact Privacy Manifest
**Recorded:** {today's date}
**Schema:** 1

This document records where SweetClaude stores planning artifacts for this project.
Review and update if repo visibility changes — run `/sweetclaude:on` and choose to update settings.

## Repository Visibility

**Current:** {Q1 answer}
**Future intent:** {verbatim answer}

## Category Decisions

### Strategy Documents
*Competitive analysis, market messaging, positioning, research*
**Decision:** {Public|Private}
**Rationale:** {user's rationale}
**Location:** `{base_path}/`

### Product Definition
*Product brief, PRD, milestones, roadmap, backlog, user stories*
**Decision:** {Public|Private}
**Rationale:** {user's rationale}
**Location:** `{base_path}/`

### Technical Documents
*Architecture, tech spec, data model, API design*
**Decision:** {Public|Private}
**Rationale:** {user's rationale}
**Location:** `{base_path}/`

### Design Artifacts
*UX flows, wireframes*
**Decision:** {Public|Private}
**Rationale:** {user's rationale}
**Location:** `{base_path}/`

## Internal State
*Phase tracking, decision logs, improvement register, assumption register*
Always private — stored in `.sweetclaude/state/` (gitignored). No decision required.

## Changelog
| Date | Change |
|------|--------|
| {today's date} | Initial manifest created during /sweetclaude:on |
```

**Confirm and warn after writing:**
Tell the user:
> "Artifact privacy configured. {N} categories private, {M} public. Recorded in `.sweetclaude/artifact-privacy.md`."

For each public category in a repo that is/will be public, confirm:
> "Note: {category} documents at `{path}` will be publicly visible — that's what you chose. Confirmed."

Check whether any confirmed public path appears to be gitignored. If so:
> "The path `{path}` appears to be gitignored. Documents there won't be tracked until you add a gitignore exception. Want me to add one now?"

---

### Step 3-E: Scan what exists

Spawn a subagent to survey the project:

> Scan this project and report what exists, organized by category:
>
> **Code:** languages, frameworks, file count, test framework and rough coverage, CI/CD scripts
>
> **Docs:** README (does it exist, is it substantive?), CLAUDE.md, docs/ directory contents, ADRs, specs
>
> **Project management:** open GitHub issues (`gh issue list`), open PRs (`gh pr list`), backlog files, user stories
>
> **Strategy:** strategy/ directory contents, positioning docs, competitive analysis, research
>
> Be factual — count files, list what exists. Do not editorialize. Do nothing else.

Present the survey to the user.

---

### Step 4-E: Understand the current state

Ask these questions ONE AT A TIME. Wait for each answer before asking the next.

1. "Is this project early, mid-build, or mature?"
2. "What needs to happen next?"
3. "What is the biggest problem or frustration with the project right now?"
4. "Is anything in the codebase messy, undocumented, or worrying you?"

---

### Step 5-E: Position in pipeline

Based on the scan and answers, propose which phase this project is in:

| Project state | Recommended phase |
|---|---|
| Just an idea, no code | DISCOVER |
| Has specs/PRD but no code | PLAN or DESIGN |
| Actively building | IMPLEMENT |
| Code exists but untested | IMPLEMENT (lock behavior with tests first) |
| Feature-complete, needs polish | VERIFY |
| Shipping/maintaining | SHIP or find-skill cycle |

Present:
> "This project is in the {phase} phase. {Reasoning}. Does that match?"

Let the user confirm or adjust. Update `phase.yaml` with the agreed phase. Ask deference level (Collaborative / Guided / Autonomous) and save to `phase.yaml`.

---

### Step 6-E: First action

If the user mentioned a problem in Step 4-E, propose a first action:
> "You mentioned {concern}. First step: {specific action with a specific command}. Start there?"

If no specific concern:
> "Setup complete. Run `/sweetclaude:go` to start working, `/sweetclaude:status` to see the full picture, or `/sweetclaude:help` to learn what's possible."

**RAG offer (existing projects):** After the above, check doc volume: count files in `docs/`, `corpus/`, `strategy/`, and any `.md` files in the root. If total is 5 or more, offer:
> "You have a meaningful amount of documentation. Want to index it into a searchable RAG corpus so I can find design decisions, specs, and research by concept rather than by text search? (`/sweetclaude:document-corpus`)"

Do not offer if doc count is below 5 — not worth it yet.

**MCP discovery + project SOP (existing projects):** Step 2-E runs 2b–2g from the New Project path. For existing projects, 2g is especially important — existing projects often have MCPs, RAG indexes, or corpus infrastructure that was set up before SweetClaude. The discovery step surfaces all of it and records it in `project-sop.md` so SweetClaude isn't working blind.

After creating the SOP, also note the corpus/docs philosophy if relevant:
- If this project has a `corpus/canonical/` alongside `docs/`: record in the SOP that `corpus/canonical/` is what Claude reasons from and `docs/` is for human navigation / content needed outside the dev cycle.
- If ADRs, design docs, or strategy docs live in `docs/` rather than `corpus/`: note this as a potential migration candidate in the SOP's Project Conventions section.

---

## Principles (Existing Project)

- Do not judge the existing code. You are an archaeologist, not a demolition crew.
- Do not propose rewriting anything unless the user raises it.
- Lock behavior before changing it. Tests before any refactoring.
- Respect existing docs, ADRs, and specs before proposing anything that might contradict them.

---

## Session continuity

If a session ends mid-setup, `.sweetclaude/state/phase.yaml` preserves state. The next session can check `/sweetclaude:status` to see what was done and what comes next.
