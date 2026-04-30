---
name: sweetclaude:on
description: "Get started with SweetClaude on any project — new idea or existing codebase. Detects context automatically and walks you through setup, then hands off to the pipeline."
---

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

   Stop.

2. **Already configured?** Does `.sweetclaude/state/phase.yaml` exist?

   If yes:
   - Check if `CLAUDE.md` has the auto-fire instruction: look for the text `invoke \`sweetclaude:status\` automatically at session start`. If missing, patch the SweetClaude section of `CLAUDE.md`:
     - Find the line that reads `Read .sweetclaude/state/phase.yaml` (or similar)
     - Replace it with: `- Read \`.sweetclaude/state/phase.yaml\` and \`.sweetclaude/state/improvement-register.md\` at session start if they exist. If \`.sweetclaude/state/phase.yaml\` exists and \`.sweetclaude/disabled\` does not exist, invoke \`sweetclaude:status\` automatically at session start.`
     - Tell the user: "Also updated your CLAUDE.md with the auto-fire instruction."
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
- `.sweetclaude/traceability/requirements-map.md` — empty table
- `.sweetclaude/traceability/ripple-map.md` — empty table

**2c. Strategy structure:** `mkdir -p strategy/{competitive-analysis,market-messaging,meeting-prep,narrative-arc,academic-research}`

**2d. CLAUDE.md:** Generate a CLAUDE.md using the user's one-line description from Step 1-N. Include: what this is, key directories, build/test commands (placeholder), project-specific rules placeholder, SweetClaude section, and distribution warning. Present to user before writing.

**2e. Existing strategy files:** Ask: "Do you have strategy documents to bring in — positioning docs, research, notes?" If yes, get the path and copy into `corpus/raw/inbox/`. Tell them to run `/sweetclaude:document-corpus` to organize them.

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
> "The strategic foundation is set. Next: product definition (product brief, PRD), then design, then implementation. Run `/sweetclaude:next-steps` to continue step by step, or pick a command from `/sweetclaude:help`."

Do not auto-invoke next-steps. The user decides when to continue.

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
> "Setup complete. Run `/sweetclaude:status` to see the full picture, `/sweetclaude:next-steps` to work through the pipeline, or `/sweetclaude:help` for all commands."

---

## Principles (Existing Project)

- Do not judge the existing code. You are an archaeologist, not a demolition crew.
- Do not propose rewriting anything unless the user raises it.
- Lock behavior before changing it. Tests before any refactoring.
- Respect existing docs, ADRs, and specs before proposing anything that might contradict them.

---

## Session continuity

If a session ends mid-setup, `.sweetclaude/state/phase.yaml` preserves state. The next session can check `/sweetclaude:status` to see what was done and what comes next.
