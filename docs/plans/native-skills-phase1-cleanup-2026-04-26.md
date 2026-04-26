# Native Skills Redesign — Phase 1: Cleanup

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove BMAD wrapper infrastructure — delete absorbed skills, rename misnamed skills, update all framework files to remove BMAD dependencies.

**Architecture:** Pure filesystem operations and targeted file edits. No new skill content in this phase — that is Phase 2. Phase 2 must not start until this plan is complete and committed.

**Tech Stack:** bash (mv, rm, rsync), Python 3 (YAML validation), git. Repo: `/Users/carsonsweet/dev/sweetclaude`. Installed plugin: `/Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0`.

---

## Pre-flight

Before any tasks, verify the environment:

```bash
# Correct repo
ls /Users/carsonsweet/dev/sweetclaude/skills/ | wc -l
# Expected: 61

# Installed plugin present
ls /Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/ | wc -l
# Expected: same count

# Python3 available
python3 --version
# Expected: Python 3.x.x

# Confirm skills to be deleted exist
ls /Users/carsonsweet/dev/sweetclaude/skills/ | grep -E "^(strategy-concept|strategy-pain-thesis|strategy-ideal-customer-profile|product-user-success-criteria|design-infra-design|design-services-design|product-feature-competitive|strategy-competitive-analysis)$"
# Expected: 8 lines
```

---

### Task 1: Delete absorbed skills

**Files:** Delete 8 skill directories from repo and installed location.

Skills being deleted (content absorbed into new native skills per design spec):
- `strategy-concept` → absorbed into `product-discovery` L1/L2
- `strategy-pain-thesis` → absorbed into `product-discovery` L3
- `strategy-ideal-customer-profile` → absorbed into `product-user-personas`
- `product-user-success-criteria` → absorbed into `product-user-personas`
- `design-infra-design` → absorbed into `design-tech-spec`
- `design-services-design` → absorbed into `design-architecture`
- `product-feature-competitive` → replaced by `product-competition`
- `strategy-competitive-analysis` → replaced by `product-competition`

- [ ] **Step 1: Delete from repo**

```bash
cd /Users/carsonsweet/dev/sweetclaude
rm -rf skills/strategy-concept
rm -rf skills/strategy-pain-thesis
rm -rf skills/strategy-ideal-customer-profile
rm -rf skills/product-user-success-criteria
rm -rf skills/design-infra-design
rm -rf skills/design-services-design
rm -rf skills/product-feature-competitive
rm -rf skills/strategy-competitive-analysis
```

- [ ] **Step 2: Verify deletions**

```bash
ls /Users/carsonsweet/dev/sweetclaude/skills/ | grep -E "^(strategy-concept|strategy-pain-thesis|strategy-ideal-customer-profile|product-user-success-criteria|design-infra-design|design-services-design|product-feature-competitive|strategy-competitive-analysis)$"
```

Expected: no output.

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add -A
git commit -m "chore: delete 8 absorbed skills (content folded into native replacements)"
```

---

### Task 2: Rename skill directories

**Files:**
- Rename: `skills/product-product-brief/` → `skills/product-brief/`
- Rename: `skills/product-user-story/` → `skills/product-user-stories/`
- Rename: `skills/product-user-workflows/` → `skills/design-user-flows/`
- Rename: `skills/code-code-review/` → `skills/code-review/`

Note: `product-brief`, `product-user-stories`, and `design-user-flows` will receive new SKILL.md content in Phase 2. `code-review` keeps its existing content — only the directory name and any name field need to change.

- [ ] **Step 1: Rename directories**

```bash
cd /Users/carsonsweet/dev/sweetclaude
mv skills/product-product-brief skills/product-brief
mv skills/product-user-story skills/product-user-stories
mv skills/product-user-workflows skills/design-user-flows
mv skills/code-code-review skills/code-review
```

- [ ] **Step 2: Check whether code-review/SKILL.md has a name field**

```bash
head -5 /Users/carsonsweet/dev/sweetclaude/skills/code-review/SKILL.md
```

If a `name:` field is present and says `sweetclaude:code-code-review`, update it to `sweetclaude:code-review`. If no `name:` field is present, the directory name is the canonical name — no edit needed.

- [ ] **Step 3: Verify renames**

```bash
ls /Users/carsonsweet/dev/sweetclaude/skills/ | grep -E "^(product-brief|product-user-stories|design-user-flows|code-review)$"
```

Expected: 4 lines.

```bash
ls /Users/carsonsweet/dev/sweetclaude/skills/ | grep -E "^(product-product-brief|product-user-story|product-user-workflows|code-code-review)$"
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add -A
git commit -m "chore: rename skills to fix bucket collisions and move design-user-flows to design phase"
```

---

### Task 3: Update phase-skills.yaml

**Files:**
- Modify: `config/phase-skills.yaml`

Changes:
- **strategy section:** Remove `concept`, `pain-thesis`, `ideal-customer-profile`, `competitive-analysis` (deleted skills). Keep remaining strategy skills.
- **product section:** Remove `product-brief` (old name), `user-story`, `user-success-criteria`, `user-workflows`, `feature-competitive`. Add: `product-brief` (new naming), `product-user-stories`, `product-user-personas`, `product-competition`, `design-user-flows` (moved here from design for pipeline order — actually no, it lives in design phase). Keep: `product-research`, `product-prd`, `positioning-statement`, and other product skills.
- **design section:** Remove `services-design`, `infra-design`. Add `design-user-flows` (moved from product).
- **code section:** Update `code/code-review` → `code/review`.

- [ ] **Step 1: Write the updated phase-skills.yaml**

```yaml
# SweetClaude Phase-Skill Mapping
# Five domain buckets: strategy, product, design, code, deploy.
# The new-task and auto-flow skills classify work into a bucket
# and surface appropriate skills.
schema_version: 1

always_loaded:
  skills:
    - sweetclaude
    - sweetclaude:new-task
    - sweetclaude:hibernate
    - sweetclaude:milestones
    - sweetclaude:metrics
    - hibernate-project
  rules:
    - sweetclaude/interaction-model.md
    - sweetclaude/phase-gates.md
    - sweetclaude/tdd-levels.md

strategy:
  skills:
    - sweetclaude:strategy/academic-research
    - sweetclaude:strategy/meeting-prep
    - sweetclaude:strategy/narrative-arc
    - sweetclaude:strategy/market-messaging
    - caucus
    - reasoning-frameworks
  agents: []
  hooks: []

product:
  skills:
    - sweetclaude:product/discovery
    - sweetclaude:product/research
    - sweetclaude:product/competition
    - sweetclaude:product/user-personas
    - sweetclaude:product/positioning-statement
    - sweetclaude:product/brief
    - sweetclaude:product/prd
    - sweetclaude:product/user-stories
    - sweetclaude:product/user-tdd-tests
    - sweetclaude:product/manage-scope
    - sweetclaude:product/backlog
    - sweetclaude:product/sprint-plan
    - reconciling-documents
  agents: []
  hooks: []

design:
  skills:
    - sweetclaude:design/user-flows
    - sweetclaude:design/architecture
    - sweetclaude:design/tech-spec
    - sweetclaude:design/ux
    - sweetclaude:design/solutioning-gate
    - sweetclaude:design/change-impact-analysis
    - sweetclaude:design/update-docs
    - sweetclaude:design/data-model
    - sweetclaude:design/api-design
    - sweetclaude:design/manage-decisions
    - caucus
    - reasoning-frameworks
  agents: []
  hooks: []

code:
  skills:
    - sweetclaude:code/tdd
    - sweetclaude:code/work-issue
    - sweetclaude:code/work-debt
    - sweetclaude:code/pr-precheck
    - sweetclaude:code/qa-testing
    - sweetclaude:code/mutation-testing
    - sweetclaude:code/security-testing
    - sweetclaude:code/review
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

deploy:
  skills: []
  agents: []
  hooks: []
```

- [ ] **Step 2: Validate YAML**

```bash
python3 -c "import yaml; data = yaml.safe_load(open('/Users/carsonsweet/dev/sweetclaude/config/phase-skills.yaml')); print('OK — keys:', list(data.keys()))"
```

Expected: `OK — keys: ['schema_version', 'always_loaded', 'strategy', 'product', 'design', 'code', 'deploy']`

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add config/phase-skills.yaml
git commit -m "chore: update phase-skills.yaml — remove deleted skills, add new native skills"
```

---

### Task 4: Update master/SKILL.md — remove BMAD references

**Files:**
- Modify: `skills/master/SKILL.md`

Three BMAD references to replace (lines ~158–162):

Current text:
```
**For `bmad:product-brief`:** Conduct the full 11-section interview. One section at a time — never batch. Probe vague answers with follow-ups before moving to the next section. The interview is a discovery conversation, not a form to fill. After generating the document, run the BMAD validation checklist and present results before the phase gate.

**For `bmad:brainstorm`:** Run all selected techniques to completion. Do not abbreviate a technique because you "have enough." The brainstorm output should contain quantified results (idea count, category count, insight count).

**For `bmad:research`:** Answer every research question with evidence and sources. Identify research gaps explicitly. Do not present a research report with unanswered questions unless those gaps are flagged as open items.
```

Replace with:
```
**For `sweetclaude:product-brief`:** Present the outline first and get adjustment before writing. Ask about audience and NDA material. Sections scale to available input. Always end with "Additional Development" noting what wasn't covered. Follow the document production system (front matter, versioned naming, paragraph numbering in drafts).

**For `sweetclaude:product-research`:** Explain what the skill does and ask if the user wants it before running. Suggest depth based on project type. Document in the effort log if skipped. Output includes an initial competitive seed list that feeds `product-competition`.

**For `sweetclaude:product-discovery`:** Use depth levels — L1 for intent and boundaries, L2 for problem and success definition, L3 for full pain thesis. Challenge the framing at L2+. Never re-ask what was established at a prior level.
```

- [ ] **Step 1: Read current master SKILL.md to find exact line numbers**

```bash
grep -n "bmad:" /Users/carsonsweet/dev/sweetclaude/skills/master/SKILL.md
```

- [ ] **Step 2: Edit the file** — replace the three `bmad:` blocks with the new text above using the Edit tool. Replace each block individually to avoid mismatches.

- [ ] **Step 3: Verify no bmad references remain**

```bash
grep -i "bmad" /Users/carsonsweet/dev/sweetclaude/skills/master/SKILL.md
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/master/SKILL.md
git commit -m "fix: remove BMAD references from master skill, replace with native skill guidance"
```

---

### Task 5: Update phase-gates.md — remove BMAD checklist reference

**Files:**
- Modify: `rules/phase-gates.md`

Current text (line 33):
```
- BMAD validation checklist: the 9-item checklist has been run with all items passing or explicitly waived by the user with documented rationale
```

Replace with:
```
- Deliverable review: product brief outline was presented and adjusted before writing; audience and NDA were confirmed; "Additional Development" section is present
```

- [ ] **Step 1: Make the edit** using the Edit tool with the exact old and new strings above.

- [ ] **Step 2: Verify**

```bash
grep -i "bmad" /Users/carsonsweet/dev/sweetclaude/rules/phase-gates.md
```

Expected: no output.

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add rules/phase-gates.md
git commit -m "fix: replace BMAD validation checklist reference with native deliverable review criterion"
```

---

### Task 6: Update interaction-model.md — remove BMAD reference

**Files:**
- Modify: `rules/interaction-model.md`

Current text (line 108):
```
Strip or ignore duration estimates from upstream workflows (BMAD, Superpowers). Do not pass through time guidance when delegating to other frameworks.
```

Replace with:
```
Strip or ignore duration estimates from upstream workflows (Superpowers). Do not pass through time guidance when delegating to other frameworks.
```

- [ ] **Step 1: Make the edit** using the Edit tool.

- [ ] **Step 2: Verify**

```bash
grep -i "bmad" /Users/carsonsweet/dev/sweetclaude/rules/interaction-model.md
```

Expected: no output.

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add rules/interaction-model.md
git commit -m "fix: remove BMAD reference from interaction-model"
```

---

### Task 7: Extend update-sweetclaude/SKILL.md — Step 8 migration

**Files:**
- Modify: `skills/update-sweetclaude/SKILL.md`

Find the existing Step 8 section ("Check for project artifact migrations"). Replace the entire Step 8 with the expanded version below.

- [ ] **Step 1: Read current Step 8**

```bash
grep -n "Step 8\|## Step 8" /Users/carsonsweet/dev/sweetclaude/skills/update-sweetclaude/SKILL.md
```

- [ ] **Step 2: Replace Step 8** with the following content (use Edit tool):

```markdown
## Step 8: Migrate existing project artifacts

After syncing the framework, check whether the **current project** (the working directory where this skill was run) has `.sweetclaude/` artifacts that need migration.

### 8a: Detect project state

Check for `.sweetclaude/` directory. If it does not exist, this project has no SweetClaude state — skip this step.

If `.sweetclaude/` exists, check for:
- `.sweetclaude/state/phase.yaml` (old-format state)
- `.sweetclaude/log.md` (new-format effort log)
- `.sweetclaude/state/` directory
- Any `.md` files in `docs/` that look like deliverable artifacts

### 8b: Seed the effort log

If `.sweetclaude/log.md` does not exist but `phase.yaml` does:

1. Read `phase.yaml` and infer what phases were completed.
2. Create `.sweetclaude/log.md` with a migration entry:

```markdown
# SweetClaude Effort Log

## {current ISO datetime} — migration (n/a)

**Status:** completed
**Note:** Seeded from legacy phase.yaml during framework upgrade.
**Prior phase:** {phase value from phase.yaml}
**Key decisions:** Migrated from pre-1.9 SweetClaude. Prior artifacts registered below.
```

### 8c: Create state directory

```bash
mkdir -p .sweetclaude/state
```

### 8d: Register pre-existing deliverable documents

Scan `docs/` for `.md` files. For each one found, append a registration entry to `.sweetclaude/log.md`:

```markdown
## {current ISO datetime} — pre-existing artifact registration (n/a)

**Status:** completed
**Note:** Pre-existing documents found in docs/ before framework upgrade. Not modified.
**Produced:** {comma-separated list of filenames}
```

### 8e: Offer to update deliverable front matter and file naming

Identify `docs/` files that do not have the new front matter format. The new format requires these YAML fields at the top: `title`, `version`, `status`, `author`, `assisted_by`, `date`, `audience`, `nda`, `changes`, `previous_file`.

For each non-conforming file, determine:
- What the new filename would be: `{title}-{status}-v{version}-{yyyymmdd}.md`
- What the front matter block would look like with the available information

Present a preview table:

```
Files that would be updated:
  old-filename.md → whizbang-product-brief-draft-v1.0-20260426.md
    Front matter added: title, version, status, author, assisted_by, date
  ...
```

Ask: "Approve all changes at once, or review file by file?"

Apply approved changes. Never rename or reformat without explicit approval.

If no non-conforming files exist, skip this step and note "No document migration needed."
```

- [ ] **Step 3: Verify no syntax errors**

```bash
python3 -c "
content = open('/Users/carsonsweet/dev/sweetclaude/skills/update-sweetclaude/SKILL.md').read()
fm = content.split('---')[1]
import yaml
data = yaml.safe_load(fm)
print('Frontmatter OK:', data.get('name', '(no name field)'))
"
```

- [ ] **Step 4: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/update-sweetclaude/SKILL.md
git commit -m "feat: extend update-sweetclaude Step 8 with project artifact migration"
```

---

### Task 8: Sync all changes to installed location

**Files:** Sync repo → installed plugin cache.

- [ ] **Step 1: Sync skills directory**

```bash
rsync -a --delete \
  /Users/carsonsweet/dev/sweetclaude/skills/ \
  /Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/
```

- [ ] **Step 2: Sync config directory**

```bash
rsync -a --delete \
  /Users/carsonsweet/dev/sweetclaude/config/ \
  /Users/carsonsweet/.claude/config/sweetclaude/
```

- [ ] **Step 3: Sync rules directory**

```bash
rsync -a --delete \
  /Users/carsonsweet/dev/sweetclaude/rules/ \
  /Users/carsonsweet/.claude/rules/sweetclaude/
```

- [ ] **Step 4: Verify deleted skills are gone from installed location**

```bash
ls /Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/ | grep -E "^(strategy-concept|strategy-pain-thesis|strategy-ideal-customer-profile|product-user-success-criteria|design-infra-design|design-services-design|product-feature-competitive|strategy-competitive-analysis)$"
```

Expected: no output.

- [ ] **Step 5: Verify renamed skills are present in installed location**

```bash
ls /Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/ | grep -E "^(product-brief|product-user-stories|design-user-flows|code-review)$"
```

Expected: 4 lines.

- [ ] **Step 6: Commit sync confirmation**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add -A
git commit -m "chore: sync phase 1 changes to installed plugin location" 2>/dev/null || echo "Nothing to commit — repo already clean"
```

---

### Task 9: Final validation

- [ ] **Step 1: Confirm total skill count**

```bash
ls /Users/carsonsweet/dev/sweetclaude/skills/ | wc -l
```

Expected: 53 (61 - 8 deleted = 53; renames don't change count). Note: Phase 2 will add 2 new skills (product-user-personas, product-competition) to reach 53 in the repo, then 55 after Phase 2 additions. Wait — let me recalculate: 61 - 8 deleted = 53. Phase 2 writes new content to existing dirs + creates 2 new dirs = 55. This task should show 53.

- [ ] **Step 2: Confirm no BMAD references remain in framework files**

```bash
grep -ri "bmad" \
  /Users/carsonsweet/dev/sweetclaude/skills/master/SKILL.md \
  /Users/carsonsweet/dev/sweetclaude/rules/phase-gates.md \
  /Users/carsonsweet/dev/sweetclaude/rules/interaction-model.md \
  /Users/carsonsweet/dev/sweetclaude/config/phase-skills.yaml
```

Expected: no output.

- [ ] **Step 3: Validate all remaining SKILL.md frontmatter**

```bash
python3 << 'EOF'
import os, yaml, sys
errors = []
skills_dir = "/Users/carsonsweet/dev/sweetclaude/skills"
for skill in os.listdir(skills_dir):
    path = os.path.join(skills_dir, skill, "SKILL.md")
    if not os.path.exists(path):
        continue
    content = open(path).read()
    parts = content.split("---")
    if len(parts) < 3:
        errors.append(f"{skill}: no valid frontmatter delimiters")
        continue
    try:
        yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        errors.append(f"{skill}: YAML error — {e}")
if errors:
    print("ERRORS:")
    for e in errors:
        print(" ", e)
    sys.exit(1)
else:
    print(f"OK — {len(os.listdir(skills_dir))} skills validated")
EOF
```

Expected: `OK — 53 skills validated`

- [ ] **Step 4: Final commit if anything remains uncommitted**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git status --short
```

If clean: Phase 1 complete. Proceed to Phase 2 plan.
