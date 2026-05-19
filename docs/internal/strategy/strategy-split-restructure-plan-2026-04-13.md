# SweetClaude Directory Restructure — Implementation Plan

> **SUPERSEDED** by `docs/plans/skill-reorganization-plan-2026-04-13.md` (5-bucket architecture). This plan was for the code/strategy dual-track split. The 5-bucket plan replaced it.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure SweetClaude from flat skill directory to code/strategy/shared split with orchestration skills at root.

**Architecture:** Move existing skills into code/ subdirectory, create strategy/ and shared/ directories, update all name references in frontmatter, config, phase-gates, and master SKILL.md. Clean break — no backward compatibility.

**Tech Stack:** Markdown skill files, YAML config, shell commands for file moves

**Spec:** `docs/superpowers/specs/2026-04-13-sweetclaude-strategy-split-design.md`

---

## Current State

```
~/.claude/skills/sweetclaude/
  SKILL.md                    name: sweetclaude
  auto-docs/SKILL.md          name: auto-docs
  discover-deep/SKILL.md      name: sweetclaude:discover-deep
  fix-issue/SKILL.md          name: sweetclaude-fix-issue
  gherkin-bridge/SKILL.md     name: gherkin-bridge
  hibernate/SKILL.md          name: sweetclaude-hibernate
  init/SKILL.md               name: sweetclaude-init
  mutation-testing/SKILL.md   name: mutation-testing
  notion-scaffold/SKILL.md    name: notion-scaffold
  pr-ready/SKILL.md           name: sweetclaude-pr-ready
  ripple/SKILL.md             name: ripple
  scope-tracker/SKILL.md      name: scope-tracker
  tdd/SKILL.md                name: sweetclaude-tdd
  work-router/SKILL.md        name: work-router
```

## Target State

```
~/.claude/skills/sweetclaude/
  SKILL.md                              name: sweetclaude (updated routing logic)
  discover-deep/SKILL.md                name: sweetclaude-discover-deep
  work-router/SKILL.md                  name: sweetclaude-work-router
  hibernate/SKILL.md                    name: sweetclaude-hibernate (unchanged)
  init/SKILL.md                         name: sweetclaude-init (unchanged)
  code/
    tdd/SKILL.md                        name: sweetclaude-code-tdd
    fix-issue/SKILL.md                  name: sweetclaude-code-fix-issue
    pr-ready/SKILL.md                   name: sweetclaude-code-pr-ready
    ripple/SKILL.md                     name: sweetclaude-code-ripple
    auto-docs/SKILL.md                  name: sweetclaude-code-auto-docs
    scope-tracker/SKILL.md              name: sweetclaude-code-scope-tracker
    gherkin-bridge/SKILL.md             name: sweetclaude-code-gherkin-bridge
    mutation-testing/SKILL.md           name: sweetclaude-code-mutation-testing
  strategy/                             (empty — skills added in later tasks)
  shared/                               (config and rules only — no skills)
  parked/
    notion-scaffold/SKILL.md            (WP-3, separate branch later)
```

## Config Files to Update

```
~/.claude/config/sweetclaude/phase-skills.yaml    — all skill references
~/.claude/rules/sweetclaude/phase-gates.md        — all "Available skills:" lines
~/.claude/skills/sweetclaude/SKILL.md             — master router routing logic
```

---

### Task 1: Create directory structure

**Files:**
- Create directories: `code/`, `strategy/`, `shared/`, `parked/`

- [ ] **Step 1: Create subdirectories**

```bash
mkdir -p ~/.claude/skills/sweetclaude/code
mkdir -p ~/.claude/skills/sweetclaude/strategy
mkdir -p ~/.claude/skills/sweetclaude/shared
mkdir -p ~/.claude/skills/sweetclaude/parked
```

- [ ] **Step 2: Verify**

```bash
ls -d ~/.claude/skills/sweetclaude/code ~/.claude/skills/sweetclaude/strategy ~/.claude/skills/sweetclaude/shared ~/.claude/skills/sweetclaude/parked
```

Expected: all four directories listed.

---

### Task 2: Move code skills into code/

**Files:**
- Move: `tdd/`, `fix-issue/`, `pr-ready/`, `ripple/`, `auto-docs/`, `scope-tracker/`, `gherkin-bridge/`, `mutation-testing/`

- [ ] **Step 1: Move all eight code skill directories**

```bash
cd ~/.claude/skills/sweetclaude
mv tdd code/
mv fix-issue code/
mv pr-ready code/
mv ripple code/
mv auto-docs code/
mv scope-tracker code/
mv gherkin-bridge code/
mv mutation-testing code/
```

- [ ] **Step 2: Park notion-scaffold**

```bash
mv notion-scaffold parked/
```

- [ ] **Step 3: Verify directory structure**

```bash
ls ~/.claude/skills/sweetclaude/
# Expected: SKILL.md, code/, discover-deep/, hibernate/, init/, parked/, shared/, strategy/, work-router/

ls ~/.claude/skills/sweetclaude/code/
# Expected: auto-docs/, fix-issue/, gherkin-bridge/, mutation-testing/, pr-ready/, ripple/, scope-tracker/, tdd/
```

---

### Task 3: Update frontmatter name fields in moved code skills

**Files:**
- Modify: all 8 SKILL.md files under `code/`

- [ ] **Step 1: Update tdd**

In `~/.claude/skills/sweetclaude/code/tdd/SKILL.md`, change:
```
name: sweetclaude-tdd
```
to:
```
name: sweetclaude-code-tdd
```

- [ ] **Step 2: Update fix-issue**

In `~/.claude/skills/sweetclaude/code/fix-issue/SKILL.md`, change:
```
name: sweetclaude-fix-issue
```
to:
```
name: sweetclaude-code-fix-issue
```

- [ ] **Step 3: Update pr-ready**

In `~/.claude/skills/sweetclaude/code/pr-ready/SKILL.md`, change:
```
name: sweetclaude-pr-ready
```
to:
```
name: sweetclaude-code-pr-ready
```

- [ ] **Step 4: Update ripple**

In `~/.claude/skills/sweetclaude/code/ripple/SKILL.md`, change:
```
name: ripple
```
to:
```
name: sweetclaude-code-ripple
```

- [ ] **Step 5: Update auto-docs**

In `~/.claude/skills/sweetclaude/code/auto-docs/SKILL.md`, change:
```
name: auto-docs
```
to:
```
name: sweetclaude-code-auto-docs
```

- [ ] **Step 6: Update scope-tracker**

In `~/.claude/skills/sweetclaude/code/scope-tracker/SKILL.md`, change:
```
name: scope-tracker
```
to:
```
name: sweetclaude-code-scope-tracker
```

- [ ] **Step 7: Update gherkin-bridge**

In `~/.claude/skills/sweetclaude/code/gherkin-bridge/SKILL.md`, change:
```
name: gherkin-bridge
```
to:
```
name: sweetclaude-code-gherkin-bridge
```

- [ ] **Step 8: Update mutation-testing**

In `~/.claude/skills/sweetclaude/code/mutation-testing/SKILL.md`, change:
```
name: mutation-testing
```
to:
```
name: sweetclaude-code-mutation-testing
```

- [ ] **Step 9: Verify all names updated**

```bash
grep "^name:" ~/.claude/skills/sweetclaude/code/*/SKILL.md
```

Expected: all 8 show `sweetclaude-code-*` prefix.

---

### Task 4: Update frontmatter name fields for orchestration skills at root

**Files:**
- Modify: `discover-deep/SKILL.md`, `work-router/SKILL.md`

Note: `hibernate/SKILL.md` (sweetclaude-hibernate) and `init/SKILL.md` (sweetclaude-init) already have correct names — no change needed.

- [ ] **Step 1: Update discover-deep**

In `~/.claude/skills/sweetclaude/discover-deep/SKILL.md`, change:
```
name: sweetclaude:discover-deep
```
to:
```
name: sweetclaude-discover-deep
```

(Normalizes from colon notation to hyphen notation matching other skills.)

- [ ] **Step 2: Update work-router**

In `~/.claude/skills/sweetclaude/work-router/SKILL.md`, change:
```
name: work-router
```
to:
```
name: sweetclaude-work-router
```

- [ ] **Step 3: Verify all root-level skill names**

```bash
grep "^name:" ~/.claude/skills/sweetclaude/*/SKILL.md
```

Expected: `sweetclaude-discover-deep`, `sweetclaude-hibernate`, `sweetclaude-init`, `sweetclaude-work-router`.

---

### Task 5: Update phase-skills.yaml

**Files:**
- Modify: `~/.claude/config/sweetclaude/phase-skills.yaml`

- [ ] **Step 1: Read current file**

Read `~/.claude/config/sweetclaude/phase-skills.yaml` to see exact current content.

- [ ] **Step 2: Rewrite with dual-track structure**

Replace the entire file with the new structure. All skill references update to new names:

**Name mapping (old → new):**
```
sweetclaude:tdd           → sweetclaude:code/tdd
sweetclaude:fix-issue     → sweetclaude:code/fix-issue
sweetclaude:ripple        → sweetclaude:code/ripple
sweetclaude:pr-ready      → sweetclaude:code/pr-ready
sweetclaude:auto-docs     → sweetclaude:code/auto-docs
sweetclaude:scope-tracker → sweetclaude:code/scope-tracker
sweetclaude:gherkin-bridge→ sweetclaude:code/gherkin-bridge
sweetclaude:discover-deep → sweetclaude:discover-deep (unchanged — root)
sweetclaude:work-router   → sweetclaude:work-router (unchanged — root)
sweetclaude:hibernate     → sweetclaude:hibernate (unchanged — root)
```

The new structure wraps existing phases under a `code:` key and adds a `strategy:` key (initially with placeholder skill lists that will be populated as strategy skills are built):

```yaml
always_loaded:
  skills:
    - sweetclaude
    - sweetclaude:work-router
    - sweetclaude:hibernate
    - hibernate-project
  rules:
    - sweetclaude/interaction-model.md
    - sweetclaude/phase-gates.md
    - sweetclaude/tdd-levels.md

code:
  discover:
    skills:
      - sweetclaude:discover-deep
      - [removed]
      - [removed]
      - caucus
      - reasoning-frameworks
    agents: []
    hooks: []

  define:
    skills:
      - [removed]
      - [removed]
      - sweetclaude:code/ripple
      - reconciling-documents
      - backlog-management
    agents: []
    hooks: []

  design:
    skills:
      - [removed]
      - [removed]
      - [removed]
      - [removed]
      - sweetclaude:code/ripple
      - caucus
      - reasoning-frameworks
    agents: []
    hooks: []

  plan:
    skills:
      - [removed]
      - [removed]
      - sweetclaude:code/gherkin-bridge
      - backlog-management
    agents: []
    hooks: []

  implement:
    skills:
      - sweetclaude:code/tdd
      - sweetclaude:code/fix-issue
      - sweetclaude:code/ripple
      - superpowers:writing-plans
      - superpowers:executing-plans
      - superpowers:using-git-worktrees
      - superpowers:systematic-debugging
      - superpowers:dispatching-parallel-agents
      - superpowers:subagent-driven-development
    agents:
      - sweetclaude:test-writer
      - sweetclaude:implementer
      - sweetclaude:qa-caucus-service
      - sweetclaude:qa-caucus-component
      - sweetclaude:qa-caucus-integration
    hooks:
      - test-guardian
      - auto-test-runner
      - git-checkpoint

  verify:
    skills:
      - sweetclaude:code/pr-ready
      - sweetclaude:code/ripple
      - sweetclaude:code/auto-docs
      - superpowers:requesting-code-review
      - superpowers:receiving-code-review
      - superpowers:verification-before-completion
      - superpowers:simplify
    agents:
      - sweetclaude:code-reviewer
      - sweetclaude:security-reviewer
      - sweetclaude:workflow-guardian
    hooks: []

  ship:
    skills:
      - superpowers:finishing-a-development-branch
      - sweetclaude:code/pr-ready
      - sweetclaude:hibernate
    agents: []
    hooks: []

strategy:
  discover:
    skills:
      - sweetclaude:discover-deep
      - caucus
      - reasoning-frameworks
    agents: []
    hooks: []

  define:
    skills:
      - sweetclaude:strategy/reconciliation
      - reconciling-documents
    agents: []
    hooks: []

  design:
    skills:
      - caucus
      - reasoning-frameworks
    agents: []
    hooks: []

  plan:
    skills: []
    agents: []
    hooks: []

  implement:
    skills:
      - superpowers:writing-plans
      - superpowers:executing-plans
    agents: []
    hooks: []

  verify:
    skills:
      - superpowers:verification-before-completion
    agents: []
    hooks: []

  ship:
    skills:
      - sweetclaude:hibernate
    agents: []
    hooks: []
```

- [ ] **Step 3: Validate YAML**

```bash
python3 -c "import yaml; yaml.safe_load(open('$HOME/.claude/config/sweetclaude/phase-skills.yaml')); print('YAML valid')"
```

---

### Task 6: Update phase-gates.md

**Files:**
- Modify: `~/.claude/rules/sweetclaude/phase-gates.md`

- [ ] **Step 1: Read current file**

Read `~/.claude/rules/sweetclaude/phase-gates.md`.

- [ ] **Step 2: Update all "Available skills:" lines**

Apply the name mapping from Task 5 to every phase's available skills list:

Phase 1 DISCOVER: `sweetclaude:discover-deep` (unchanged)
Phase 2 DEFINE: `sweetclaude:ripple` → `sweetclaude:code/ripple`
Phase 3 DESIGN: `sweetclaude:ripple` → `sweetclaude:code/ripple`
Phase 4 PLAN: `sweetclaude:gherkin-bridge` → `sweetclaude:code/gherkin-bridge`
Phase 5 IMPLEMENT: `sweetclaude:tdd` → `sweetclaude:code/tdd`, `sweetclaude:fix-issue` → `sweetclaude:code/fix-issue`, `sweetclaude:ripple` → `sweetclaude:code/ripple`
Phase 6 VERIFY: `sweetclaude:pr-ready` → `sweetclaude:code/pr-ready`, `sweetclaude:ripple` → `sweetclaude:code/ripple`, `sweetclaude:auto-docs` → `sweetclaude:code/auto-docs`
Phase 7 SHIP: `sweetclaude:pr-ready` → `sweetclaude:code/pr-ready`

- [ ] **Step 3: Add note that these are code-track defaults**

Add a header note after the intro text:
```
> These phase gates describe the default code-track skills. Strategy-track skills are listed in `phase-skills.yaml` under the `strategy:` key and will be documented here as they are built.
```

- [ ] **Step 4: Verify no old-format references remain**

```bash
grep -E "sweetclaude:(tdd|fix-issue|pr-ready|ripple|auto-docs|scope-tracker|gherkin-bridge)" ~/.claude/rules/sweetclaude/phase-gates.md
```

Expected: no matches.

---

### Task 7: Update master SKILL.md routing logic

**Files:**
- Modify: `~/.claude/skills/sweetclaude/SKILL.md`

- [ ] **Step 1: Read current master SKILL.md**

Read `~/.claude/skills/sweetclaude/SKILL.md`.

- [ ] **Step 2: Update skill references in Phase Pipeline section**

Update the phase pipeline listing to reflect the code/ prefix:

```
Phase 5: IMPLEMENT → SweetClaude TDD (levels 0-3), fix-issue, worktrees, debugging
```
becomes:
```
Phase 5: IMPLEMENT → code/tdd (levels 0-3), code/fix-issue, worktrees, debugging
```

- [ ] **Step 3: Update Skill Surfacing section**

The master SKILL.md's skill surfacing section reads `phase-skills.yaml`. Update the description to reflect the dual-track structure:

```markdown
## Skill Surfacing

Read `~/.claude/config/sweetclaude/phase-skills.yaml` to determine which skills are available. The config has two tracks:

- **`code:`** — skills for technical development (TDD, debugging, code review, deployment)
- **`strategy:`** — skills for strategic product development (research, positioning, meeting prep)

When the user asks to do something, the work router classifies it as code or strategy work. Surface skills from the appropriate track for the current phase. If a skill from the other track is requested, inform the user it's from a different track but offer to invoke it anyway (override).
```

- [ ] **Step 4: Update Delegation Depth section**

Update any skill references in the delegation depth section to use new names (e.g., `sweetclaude:discover-deep` stays the same, but check for any references to moved skills).

- [ ] **Step 5: Add work-type routing for strategy**

In the Work-type routing section, add strategy work types:

```markdown
**Work-type routing:**
- Net-new features → enter at DISCOVER (code track)
- Bug fixes → enter at DEFINE (code track)
- Feature enhancements → enter at DEFINE (code track)
- Iteration / tech debt → enter at DEFINE (code track)
- Research paper → enter at DISCOVER (strategy track)
- Strategic positioning → enter at DISCOVER (strategy track)
- Competitive analysis → enter at DISCOVER (strategy track)
- Meeting prep → enter at DEFINE (strategy track)
- Market messaging → enter at DEFINE (strategy track)
- Biz planning → enter at DISCOVER (strategy track)
- File reconciliation → enter at DEFINE (strategy track)
- Any type can escalate to DISCOVER if deeper issues surface
```

- [ ] **Step 6: Verify no old-format references remain in master SKILL.md**

```bash
grep -E "sweetclaude:(tdd|fix-issue|pr-ready|ripple|auto-docs|gherkin-bridge)" ~/.claude/skills/sweetclaude/SKILL.md
```

Expected: no matches.

---

### Task 8: Update internal cross-references in skill files

**Files:**
- Modify: any skill SKILL.md files that reference other skills by old names

- [ ] **Step 1: Search for old-format references across all skill files**

```bash
grep -r "sweetclaude:tdd\|sweetclaude:fix-issue\|sweetclaude:pr-ready\|sweetclaude:ripple\|sweetclaude:auto-docs\|sweetclaude:gherkin-bridge\|sweetclaude:scope-tracker\|sweetclaude:mutation-testing" ~/.claude/skills/sweetclaude/
```

- [ ] **Step 2: Update each reference found**

For each file with old references, update to the new `sweetclaude:code/X` format. Read each file first, then make targeted edits.

- [ ] **Step 3: Verify no old references remain**

```bash
grep -r "sweetclaude:tdd\|sweetclaude:fix-issue\|sweetclaude:pr-ready\|sweetclaude:ripple\|sweetclaude:auto-docs\|sweetclaude:gherkin-bridge\|sweetclaude:scope-tracker\|sweetclaude:mutation-testing" ~/.claude/skills/sweetclaude/
```

Expected: no matches.

---

### Task 9: Move shared config and rules

**Files:**
- Move: config and rules into `shared/` conceptual grouping

- [ ] **Step 1: Assess current config/rules locations**

Config lives at `~/.claude/config/sweetclaude/` and rules at `~/.claude/rules/sweetclaude/`. These are already separate from skills. The `shared/` directory in the skills tree is for documentation/reference only — we do NOT move config and rules files, as Claude Code expects them at their current paths.

- [ ] **Step 2: Add a README to shared/**

Create `~/.claude/skills/sweetclaude/shared/README.md`:

```markdown
# Shared Infrastructure

Config and rules that apply to both code and strategy tracks live at:

- `~/.claude/config/sweetclaude/phase-skills.yaml` — phase → skill mapping
- `~/.claude/config/sweetclaude/defaults.yaml` — user defaults
- `~/.claude/config/sweetclaude/model-routing.yaml` — model selection
- `~/.claude/rules/sweetclaude/phase-gates.md` — entry/exit criteria
- `~/.claude/rules/sweetclaude/interaction-model.md` — behavioral rules
- `~/.claude/rules/sweetclaude/tdd-levels.md` — TDD enforcement levels

These files are NOT moved into this directory because Claude Code expects them at their current paths.
```

---

### Task 10: Smoke test

- [ ] **Step 1: Verify all skill names are discoverable**

Start a fresh Claude Code session or check the skill list. Confirm:
- `sweetclaude` (master) appears
- `sweetclaude-code-tdd` appears (or however Claude lists it)
- `sweetclaude-hibernate` appears
- `sweetclaude-discover-deep` appears
- No orphaned old-name skills appear

- [ ] **Step 2: Verify phase-skills.yaml loads without error**

```bash
python3 -c "import yaml; d = yaml.safe_load(open('$HOME/.claude/config/sweetclaude/phase-skills.yaml')); print('code phases:', list(d['code'].keys())); print('strategy phases:', list(d['strategy'].keys()))"
```

Expected: both `code` and `strategy` keys present with 7 phases each.

- [ ] **Step 3: Spot-check a code skill invocation**

Invoke `/sweetclaude:code/tdd` or reference it — confirm it loads the TDD skill correctly.

---

## Summary

| Task | What | Files Changed |
|---|---|---|
| 1 | Create directories | 4 new dirs |
| 2 | Move code skills + park notion-scaffold | 9 directories moved |
| 3 | Update code skill name frontmatter | 8 SKILL.md files |
| 4 | Update orchestration skill name frontmatter | 2 SKILL.md files |
| 5 | Rewrite phase-skills.yaml | 1 config file |
| 6 | Update phase-gates.md | 1 rules file |
| 7 | Update master SKILL.md | 1 skill file |
| 8 | Update cross-references in skill files | TBD (grep to find) |
| 9 | Add shared/ README | 1 new file |
| 10 | Smoke test | 0 files |
