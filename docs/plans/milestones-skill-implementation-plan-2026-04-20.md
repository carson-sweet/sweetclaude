# Milestones Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `sweetclaude:milestones` skill — a cross-cutting, always-loaded SweetClaude skill that manages roadmap-target milestones with bidirectional links to product work items and one-way references to canonical strategy artifacts.

**Architecture:** New `skills/milestones/SKILL.md` file containing the full operations spec (add, review, link, status, blockers, complete, unassigned). `config/phase-skills.yaml` updated to add the skill to `always_loaded.skills`. Three existing skill files updated to add milestone-awareness protocol: `skills/product-user-story/SKILL.md`, `skills/product-sprint-plan/SKILL.md`, `skills/status/SKILL.md`. No code — all content is Markdown and YAML. Strategy skills are unchanged.

**Tech Stack:** Markdown (SKILL.md authoring), YAML (phase-skills config), bash (file validation, plugin sync), Python (YAML parse check). Plugin install target: `~/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/`.

**Reference spec:** `/Users/carsonsweet/dev/sweetclaude/docs/milestones-skill-design-v1-2026-04-20.md`

---

## Pre-flight

Before starting tasks, verify environment:

```bash
# Verify repo location
ls /Users/carsonsweet/dev/sweetclaude/skills/ | head -5
# Expected: at least one existing skill dir, e.g. auto-flow

# Verify installed plugin location
ls /Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/ | head -5
# Expected: the same skills list (installed copies)

# Verify phase-skills.yaml is parseable
python3 -c "import yaml; yaml.safe_load(open('/Users/carsonsweet/dev/sweetclaude/config/phase-skills.yaml'))"
# Expected: no output (success). If error, stop and fix first.
```

---

## Task 1: Create skill directory and skeleton SKILL.md

**Files:**
- Create: `/Users/carsonsweet/dev/sweetclaude/skills/milestones/SKILL.md`

- [ ] **Step 1: Create the skill directory**

```bash
mkdir -p /Users/carsonsweet/dev/sweetclaude/skills/milestones
```

- [ ] **Step 2: Write the skeleton with frontmatter, preflight, header, and routing table**

Write this exact content to `/Users/carsonsweet/dev/sweetclaude/skills/milestones/SKILL.md`:

````markdown
---
description: "Manage roadmap targets (milestones) that span strategy and product work. Create, review, link work items to, and track completion of outcome-driven milestones like 'Exit Stealth' or 'Paid Pilot Live'."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Milestones

Manage milestones: $ARGUMENTS

A milestone is a **roadmap target** — a named strategic outcome the project is driving toward. Not a release, not a sprint, not an epic. Examples: "Exit Stealth", "Paid Pilot Live", "Series A Readiness", "MVP Shipped".

## Routing

Classify the invocation by the first word of `$ARGUMENTS`:

| First word | Operation |
|------------|-----------|
| `add` | Create a new milestone |
| `review` | List milestones grouped by Now / Next / Later |
| `link <item> <MS-XXX>` | Attach a product work item to a milestone |
| `status <MS-XXX>` | Detail view of one milestone |
| `blockers <MS-XXX>` | List what's unfinished on a milestone |
| `complete <MS-XXX>` | Mark a milestone achieved + chain follow-ups |
| `unassigned` | Find work items with no milestone |

If `$ARGUMENTS` is empty or doesn't match, default to `review`.
````

- [ ] **Step 3: Verify the file exists and frontmatter parses**

```bash
test -f /Users/carsonsweet/dev/sweetclaude/skills/milestones/SKILL.md && echo "OK"
head -3 /Users/carsonsweet/dev/sweetclaude/skills/milestones/SKILL.md
```

Expected: `OK` followed by the `---` frontmatter delimiter and description line.

- [ ] **Step 4: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/milestones/SKILL.md
git commit -m "feat: add milestones skill skeleton (frontmatter, preflight, routing)"
```

---

## Task 2: Add storage layout and milestone file template

**Files:**
- Modify: `skills/milestones/SKILL.md` (append)

- [ ] **Step 1: Append storage and template sections**

Append the following to `skills/milestones/SKILL.md`:

````markdown

## Storage

```
docs/milestones/
  MILESTONES-INDEX.md       Master index (one row per milestone)
  MS-001-short-name.md      One file per milestone
  MS-002-short-name.md
  ...
```

- IDs are `MS-XXX`. Read the index, find the highest number, increment by 1.
- IDs are permanent. Never renumber. Gaps are fine.

## Milestone file template

```markdown
# MS-XXX: Title

**Status:** proposed | active | achieved | dropped | superseded
**Owner:** [name/role]
**Depends on:** (other MS-XXX refs, if any)

## Outcome
One paragraph describing what this milestone represents and why it matters.

## Measuring success
- [ ] Criterion 1 (each evaluable as true/false)
- [ ] Criterion 2
- [ ] Criterion linked to artifact: `strategy/narrative-arc.md` finalized

## Non-goals
- What this milestone is explicitly NOT
- Second explicit exclusion

## Contributing work items
- US-012 — Landing page redesign
- BL-007 — Analytics tracking

## Notes
Free-form log of decisions, scope changes, blockers encountered.

---

## Changelog
| Version | Date       | Change summary       |
|---------|------------|----------------------|
| 1.0     | YYYY-MM-DD | Initial draft        |
```

## Status taxonomy

| Status       | Meaning                                                                  |
|--------------|--------------------------------------------------------------------------|
| `proposed`   | Drafted, not yet committed. Appears in "Later".                          |
| `active`     | Currently being driven. Appears in "Now". Can be multiple.               |
| `achieved`   | All criteria met; user confirmed. Terminal state.                        |
| `dropped`    | Abandoned with rationale in Notes. Terminal state.                       |
| `superseded` | Replaced by a newer milestone. Links to successor in Notes. Terminal.    |
````

- [ ] **Step 2: Verify content appended**

```bash
grep -c "^## Storage\|^## Milestone file template\|^## Status taxonomy" /Users/carsonsweet/dev/sweetclaude/skills/milestones/SKILL.md
```

Expected: `3`

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/milestones/SKILL.md
git commit -m "feat(milestones): document storage layout and milestone file template"
```

---

## Task 3: Add the `add` operation

**Files:**
- Modify: `skills/milestones/SKILL.md` (append)

- [ ] **Step 1: Append the Operations heading and the `add` subsection**

Append this exact content:

````markdown

## Operations

### `add` — Create a new milestone

1. Read `docs/milestones/MILESTONES-INDEX.md`. If it does not exist, create it with this header:

```markdown
# Milestones Index

| ID | Title | Status | Owner | Short summary |
|----|-------|--------|-------|---------------|
```

2. Find the highest existing `MS-XXX` in the index. Increment by 1. If the index is empty, start at `MS-001`.
3. Ask the user (one question at a time, per SweetClaude interaction model):
   - Title (short, descriptive, 2-5 words)
   - Outcome (one paragraph — what "achieved" looks like)
   - Measuring success criteria: ask for a list. For each criterion, offer: "Link this to a canonical artifact path? (optional, e.g. `strategy/narrative-arc.md`)"
   - Non-goals: require at least one. If the user offers none, prompt: "What is this milestone explicitly NOT? A non-goals list with zero items is a scope red flag."
   - Depends on: list of other MS-XXX refs (optional)
   - Owner: default to the value of `owner` in `.sweetclaude/state/phase.yaml` if present; otherwise prompt.
4. Default `Status:` to `proposed`. Ask the user only if they indicate otherwise.
5. Write the file at `docs/milestones/MS-XXX-<slug>.md` using the milestone template from the previous section, filling in all fields. `<slug>` is a dash-lowercased version of the title (e.g., "Exit Stealth" → `exit-stealth`).
6. Append a row to `MILESTONES-INDEX.md`:

```
| MS-XXX | [Title](MS-XXX-slug.md) | proposed | Owner | One-sentence outcome summary |
```

7. Tell the user: "Added MS-XXX: {title}. Status: proposed. File: docs/milestones/MS-XXX-{slug}.md"
````

- [ ] **Step 2: Verify append**

```bash
grep -c "^### \`add\` —" /Users/carsonsweet/dev/sweetclaude/skills/milestones/SKILL.md
```

Expected: `1`

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/milestones/SKILL.md
git commit -m "feat(milestones): add 'add' operation"
```

---

## Task 4: Add the `review` operation

**Files:**
- Modify: `skills/milestones/SKILL.md` (append)

- [ ] **Step 1: Append the `review` operation**

Append this exact content:

````markdown

### `review` — List milestones by commitment level

1. Scan `docs/milestones/` for all files matching `MS-*.md` (exclude `MILESTONES-INDEX.md`).
2. Read each file's `**Status:**` field.
3. Group:
   - **Now**: `active`
   - **Next**: (see Open Items — default empty; promotion mechanism is an open design question in the spec)
   - **Later**: `proposed`
   - Terminal states (`achieved`, `dropped`, `superseded`): hidden unless `review --all` was invoked.
4. For each displayed milestone, compute a progress snapshot:
   - Count `- [x]` and `- [ ]` lines under the `## Measuring success` heading.
   - For criteria that reference an artifact path, note whether the path is populated vs. a bare text criterion. (Artifact finalization check — see Open Items for the canonical convention.)
5. Present in this format:

```
Milestones

Now (active):
  MS-001 Exit Stealth         3/5 criteria met
  MS-003 MVP Shipped          4/4 criteria met — ready to complete

Later (proposed):
  MS-004 Paid Pilot Live
  MS-005 Series A Readiness
```

6. If `--all` was passed, append terminal-state milestones after Later:

```
Achieved:
  MS-002 Private Alpha        (2026-03-15)

Dropped:
  MS-006 Desktop App          (2026-02-01 — rationale: see Notes)
```

7. If no milestones exist, say: "No milestones yet. Run `/sweetclaude:milestones add` to create one."
````

- [ ] **Step 2: Verify append**

```bash
grep -c "^### \`review\` —" /Users/carsonsweet/dev/sweetclaude/skills/milestones/SKILL.md
```

Expected: `1`

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/milestones/SKILL.md
git commit -m "feat(milestones): add 'review' operation with Now/Next/Later grouping"
```

---

## Task 5: Add the `link` operation

**Files:**
- Modify: `skills/milestones/SKILL.md` (append)

- [ ] **Step 1: Append the `link` operation**

Append this exact content:

````markdown

### `link <work-item> <MS-XXX>` — Bidirectional attach

1. Validate the work-item ref: must match `^(US|BL)-\d+$`. If not, tell the user the expected format and stop.
2. Locate the work-item file:
   - `US-XXX` → search `stories/**/US-XXX-*.md` then `.sweetclaude/stories/**/US-XXX-*.md`.
   - `BL-XXX` → search `docs/backlog/BL-XXX-*.md`.
   - If not found, tell the user and stop.
3. Validate `docs/milestones/MS-XXX-*.md` exists. If not, tell the user and stop.
4. Read the work item. Check for an existing `**Milestone:**` header (exact match: line starting with `**Milestone:**`).
   - If present and equals the requested MS: no-op. Say "Already linked."
   - If present but different: ask "This work item is currently linked to {old MS}. Replace with {new MS}? (yes/no)" — require explicit yes. If no, stop.
5. Write/update the work item's `**Milestone:**` header:
   - If no header exists, insert `**Milestone:** MS-XXX` immediately after the H1 title line.
   - If a header exists, replace its value.
6. Read `docs/milestones/MS-XXX-*.md`. In the `## Contributing work items` section:
   - If the item is not already listed, add `- {work-item-ref} — {title from work item's H1}`.
   - If the section does not exist, create it before `## Notes`.
7. If the work item was previously linked to a different milestone:
   - Read that old milestone file.
   - Remove the work item from its Contributing work items section.
   - Append a Changelog row: "{date} — Removed {work-item-ref} (relinked to {new MS})."
8. Append a Changelog row to the new milestone file: "{date} — Linked {work-item-ref}."
9. Tell the user: "Linked {work-item-ref} to MS-XXX. {if relinked: 'Removed from {old MS}.'}"
````

- [ ] **Step 2: Verify append**

```bash
grep -c "^### \`link " /Users/carsonsweet/dev/sweetclaude/skills/milestones/SKILL.md
```

Expected: `1`

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/milestones/SKILL.md
git commit -m "feat(milestones): add 'link' operation with bidirectional attach"
```

---

## Task 6: Add the `status` operation

**Files:**
- Modify: `skills/milestones/SKILL.md` (append)

- [ ] **Step 1: Append the `status` operation**

Append this exact content:

````markdown

### `status <MS-XXX>` — Detail view

1. Read `docs/milestones/MS-XXX-*.md`. If missing, tell user and stop.
2. For each item in `## Measuring success`:
   - If the item references an artifact path (pattern: backtick-wrapped path like `` `strategy/narrative-arc.md` ``), read that file. Determine "met" using the finalization convention (see Open Items — default: file exists and its first heading is not `# DRAFT`).
   - Otherwise, use the checkbox state directly (`- [x]` met, `- [ ]` not met).
3. For each item in `## Contributing work items`, read the work-item file and classify:
   - **done**: work item's own status marker says completed/done/merged.
   - **in-progress**: marker says active/in-progress.
   - **pending**: no active marker.
   - **unknown**: file missing or no marker — flag with `?`.
4. Render:

```
MS-001: Exit Stealth
Status: active  |  Owner: Carson
Depends on: (none)

Outcome:
One paragraph...

Measuring success:
  [x] Criterion 1
  [ ] Criterion 2
  [x] strategy/narrative-arc.md finalized
  [ ] strategy/market-messaging.md finalized

Non-goals:
  - Not a self-serve launch
  - Not a pricing change

Contributing work items:
  US-012  (done)        Landing page redesign
  US-015  (in-progress) Press kit generator
  BL-007  (pending)     Analytics tracking

Recent notes:
  2026-04-18 — Narrative arc finalized.
  2026-04-10 — Decided to split press kit from landing page.
```

5. "Recent notes" shows the last 3 Notes entries (by date if dated, otherwise by file order).
````

- [ ] **Step 2: Verify append**

```bash
grep -c "^### \`status " /Users/carsonsweet/dev/sweetclaude/skills/milestones/SKILL.md
```

Expected: `1`

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/milestones/SKILL.md
git commit -m "feat(milestones): add 'status' detail view operation"
```

---

## Task 7: Add the `blockers` operation

**Files:**
- Modify: `skills/milestones/SKILL.md` (append)

- [ ] **Step 1: Append the `blockers` operation**

Append this exact content:

````markdown

### `blockers <MS-XXX>` — What is stopping us

1. Read the milestone file. If missing, tell user and stop.
2. Compute:
   - **Unmet criteria:** each `- [ ]` line under Measuring success, and each artifact-reference criterion where the artifact is not finalized.
   - **Open work items:** each item under Contributing work items that is not in `done` state (same classification as `status`).
   - **Unmet dependencies:** each MS-XXX in Depends on whose Status is not `achieved`.
3. Render:

```
Blockers for MS-001 Exit Stealth:

Unmet criteria (2):
  - Criterion 2
  - strategy/market-messaging.md finalized

Open work items (2):
  US-015  (in-progress) Press kit generator
  BL-007  (pending)     Analytics tracking

Dependencies not met (1):
  MS-000  Company name finalized  (status: proposed)
```

4. If nothing is blocking, say: "Nothing is blocking MS-XXX. All criteria met, all contributing work items done, all dependencies achieved. Run `/sweetclaude:milestones complete MS-XXX` to mark it achieved."
````

- [ ] **Step 2: Verify append**

```bash
grep -c "^### \`blockers " /Users/carsonsweet/dev/sweetclaude/skills/milestones/SKILL.md
```

Expected: `1`

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/milestones/SKILL.md
git commit -m "feat(milestones): add 'blockers' operation"
```

---

## Task 8: Add the `complete` operation with follow-up chain

**Files:**
- Modify: `skills/milestones/SKILL.md` (append)

- [ ] **Step 1: Append the `complete` operation**

Append this exact content:

````markdown

### `complete <MS-XXX>` — Mark achieved and chain follow-ups

1. Read the milestone file. If missing, tell user and stop.
2. If current Status is already terminal (`achieved`, `dropped`, `superseded`), tell the user and stop. Do not transition from a terminal state.
3. Evaluate criteria (same logic as `status`):
   - If any criterion is unmet, list them.
   - Ask: "These criteria are not met: {list}. Proceed with explicit waiver?"
   - If the user declines, stop without changes.
   - If the user accepts, prompt: "Waiver rationale?" Append to `## Notes`: `{date} — Completion waiver: {rationale}. Unmet at completion: {list}.`
4. Evaluate contributing work items:
   - If any are not in `done` state, list them.
   - Ask: "These contributing work items are not done: {list}. Continue?"
   - If no, stop. If yes, proceed.
5. Set `**Status:**` to `achieved`.
6. Append Changelog row: `{date} — Marked achieved. {if waived: 'Waived N criteria — see Notes.'}`
7. Update `MILESTONES-INDEX.md`: change the status column for this milestone to `achieved`.
8. **Follow-up chain.** Ask the user:

```
Milestone achieved. Any follow-ups to capture?

Categories:
  - incomplete_scope — parts deferred from this milestone
  - next_steps      — what users will want next
  - tech_debt       — shortcuts taken that should be paid back
  - test_gaps       — missing test coverage uncovered during the work

List each follow-up as: "<category>: <short title>". Enter blank line when done.
```

9. For each follow-up entered, invoke `sweetclaude:product/backlog` with arguments that route to its `add` flow. Pass the category as context. Do not inline the backlog-add logic — delegate. If the user indicated a strategic item, the backlog skill's existing router will redirect to `strategy/`.
10. Tell the user: "MS-XXX marked achieved. {N} follow-ups filed."
````

- [ ] **Step 2: Verify append**

```bash
grep -c "^### \`complete " /Users/carsonsweet/dev/sweetclaude/skills/milestones/SKILL.md
```

Expected: `1`

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/milestones/SKILL.md
git commit -m "feat(milestones): add 'complete' operation with follow-up chain"
```

---

## Task 9: Add the `unassigned` operation

**Files:**
- Modify: `skills/milestones/SKILL.md` (append)

- [ ] **Step 1: Append the `unassigned` operation**

Append this exact content:

````markdown

### `unassigned` — Hygiene check

1. Scan work-item files:
   - Stories: `stories/**/US-*.md` and `.sweetclaude/stories/**/US-*.md`.
   - Backlog: `docs/backlog/BL-*.md`.
2. For each file, check for a `**Milestone:**` header line.
3. Group items with no header by type:

```
Unassigned work items (5):

Stories (2):
  US-008  Onboarding email flow
  US-011  Usage dashboard

Backlog (3):
  BL-003  Migrate to Postgres
  BL-005  Add rate limiting
  BL-009  Vendor management page
```

4. Tell the user: "These have no milestone. Either link them to a milestone (`/sweetclaude:milestones link <item> <MS-XXX>`) or confirm they are distractions / out of roadmap. Not doing anything is also fine — this check is advisory."
5. Do not force action. Do not modify files. Surface only.
````

- [ ] **Step 2: Verify append**

```bash
grep -c "^### \`unassigned\`" /Users/carsonsweet/dev/sweetclaude/skills/milestones/SKILL.md
```

Expected: `1`

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/milestones/SKILL.md
git commit -m "feat(milestones): add 'unassigned' hygiene operation"
```

---

## Task 10: Add integration protocol and invariants sections

**Files:**
- Modify: `skills/milestones/SKILL.md` (append)

- [ ] **Step 1: Append the final sections**

Append this exact content:

````markdown

## Integration protocol

The milestones skill is the single source of truth for milestone data. Other skills should follow this protocol rather than writing their own milestone logic:

- **`sweetclaude:product/user-story`**: after creating a story, prompt "Assign this story to a milestone? [list of active + proposed milestones, or 'none / later']". On user selection, invoke `sweetclaude:milestones link <US-XXX> <MS-XXX>`.
- **`sweetclaude:product/sprint-plan`**: after stories are chosen for a sprint, read each story's `**Milestone:**` header. Report which milestones the sprint advances and count unassigned stories. If > 50% of sprint stories are unassigned, flag it as a scope concern.
- **`sweetclaude:status`**: in the orient view, include an "Active milestones" section showing each `active` milestone with its criterion-met count.

Strategy skills (`strategy/narrative-arc`, `strategy/market-messaging`, etc.) are **not modified**. Milestones reference their canonical artifacts by path as Measuring-success criteria; the milestones skill reads those files directly.

The `product/backlog` skill is not modified, but is invoked indirectly by the `complete` operation's follow-up chain.

## Rules / Invariants

- Every milestone has its own file under `docs/milestones/`. The index is an index only.
- `MS-XXX` IDs are permanent. Never renumber. Gaps are fine.
- Bidirectional links must stay consistent. `link` updates both sides. Any skill that adds or removes a work item from a milestone must do the same.
- Terminal states (`achieved`, `dropped`, `superseded`) are never edited back to non-terminal. To re-activate a deprecated goal, create a new milestone that references the old one in its Notes.
- No derived state file. Progress is recomputed on every read by scanning files.
- Non-goals are not optional. Every milestone must have at least one explicit exclusion under `## Non-goals`.
- No time estimates. Status taxonomy and Now/Next/Later bucketing replace date-based roadmapping.

## Open items (tracked in design spec)

These are documented in `docs/milestones-skill-design-v1-2026-04-20.md` as open for a follow-up iteration:

- Canonical-artifact finalization convention (front-matter field vs path vs registry).
- Next-bucket promotion mechanism for `proposed` milestones.
- Bulk-link operation (defer until single-item link proves tedious).
- Whether to archive `achieved` milestones to `docs/milestones/archive/`.
````

- [ ] **Step 2: Verify full skill file structure**

```bash
grep -c "^## " /Users/carsonsweet/dev/sweetclaude/skills/milestones/SKILL.md
```

Expected: at least `9` (Routing, Storage, Milestone file template, Status taxonomy, Operations, Integration protocol, Rules / Invariants, Open items, plus the file-internal `## Notes`, `## Measuring success`, etc. inside the template block).

```bash
wc -l /Users/carsonsweet/dev/sweetclaude/skills/milestones/SKILL.md
```

Expected: approximately 250-300 lines.

- [ ] **Step 3: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/milestones/SKILL.md
git commit -m "feat(milestones): document integration protocol, invariants, and open items"
```

---

## Task 11: Add milestones skill to phase-skills.yaml always_loaded

**Files:**
- Modify: `/Users/carsonsweet/dev/sweetclaude/config/phase-skills.yaml:6-15`

- [ ] **Step 1: Read the current always_loaded block**

```bash
sed -n '6,15p' /Users/carsonsweet/dev/sweetclaude/config/phase-skills.yaml
```

Expected current content:

```yaml
always_loaded:
  skills:
    - sweetclaude
    - sweetclaude:new-task
    - sweetclaude:hibernate
    - hibernate-project
  rules:
    - sweetclaude/interaction-model.md
    - sweetclaude/phase-gates.md
    - sweetclaude/tdd-levels.md
```

- [ ] **Step 2: Insert the new skill entry using an Edit operation**

Replace this exact block:

```yaml
always_loaded:
  skills:
    - sweetclaude
    - sweetclaude:new-task
    - sweetclaude:hibernate
    - hibernate-project
```

With:

```yaml
always_loaded:
  skills:
    - sweetclaude
    - sweetclaude:new-task
    - sweetclaude:hibernate
    - sweetclaude:milestones
    - hibernate-project
```

- [ ] **Step 3: Verify YAML still parses**

```bash
python3 -c "import yaml; d = yaml.safe_load(open('/Users/carsonsweet/dev/sweetclaude/config/phase-skills.yaml')); assert 'sweetclaude:milestones' in d['always_loaded']['skills']; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add config/phase-skills.yaml
git commit -m "chore(config): add sweetclaude:milestones to always_loaded"
```

---

## Task 12: Update product-user-story skill to prompt for milestone assignment

**Files:**
- Modify: `/Users/carsonsweet/dev/sweetclaude/skills/product-user-story/SKILL.md`

- [ ] **Step 1: Read current file**

```bash
cat /Users/carsonsweet/dev/sweetclaude/skills/product-user-story/SKILL.md
```

Expected full content:

```markdown
---
description: "Write user stories with acceptance criteria from features or epics. Wraps bmad:create-story with SweetClaude context."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# User Story

Write a user story for: $ARGUMENTS

## SweetClaude Context

- Stories follow As-a/I-want/So-that format with testable acceptance criteria.
- Each acceptance criterion converts to a Gherkin Given/When/Then scenario.
- Save to `stories/EPIC-XXX/` in `.sweetclaude/`.
- Update `traceability/requirements-map.md`.

## Execute

Invoke `bmad:create-story` and follow its workflow.
```

- [ ] **Step 2: Replace the final section with the post-creation milestone prompt**

Replace:

```markdown
## Execute

Invoke `bmad:create-story` and follow its workflow.
```

With:

```markdown
## Execute

1. Invoke `bmad:create-story` and follow its workflow.
2. After the story file is written, prompt for milestone assignment:

   > "Assign this story to a milestone? Current milestones:
   > - {list active + proposed milestones from `docs/milestones/`}
   > - none / later (skip for now)"

   If the user selects a milestone, invoke `sweetclaude:milestones link <US-XXX> <MS-XXX>` — do not write the `**Milestone:**` header directly; delegate to keep the bidirectional link consistent.

   If no milestones exist, skip this step and mention: "No milestones yet. Run `/sweetclaude:milestones add` to create one."
```

- [ ] **Step 3: Verify the integration text is present**

```bash
grep -c "sweetclaude:milestones link" /Users/carsonsweet/dev/sweetclaude/skills/product-user-story/SKILL.md
```

Expected: `1`

- [ ] **Step 4: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/product-user-story/SKILL.md
git commit -m "feat(user-story): prompt for milestone assignment after story creation"
```

---

## Task 13: Update product-sprint-plan to report milestone advancement

**Files:**
- Modify: `/Users/carsonsweet/dev/sweetclaude/skills/product-sprint-plan/SKILL.md`

- [ ] **Step 1: Read current file**

```bash
cat /Users/carsonsweet/dev/sweetclaude/skills/product-sprint-plan/SKILL.md
```

Expected final section:

```markdown
## Execute

Invoke `bmad:sprint-planning` and follow its workflow.
```

- [ ] **Step 2: Replace the Execute section**

Replace:

```markdown
## Execute

Invoke `bmad:sprint-planning` and follow its workflow.
```

With:

```markdown
## Execute

1. Invoke `bmad:sprint-planning` and follow its workflow.
2. After the sprint commitment is finalized, read each selected story's `**Milestone:**` header from its file.
3. Aggregate and report:

   ```
   Sprint advances:
     MS-001 Exit Stealth   2 stories
     MS-003 MVP Shipped    1 story
   Unassigned: 1 story
   ```

4. If more than 50% of sprint stories are unassigned to any milestone, flag it:

   > "{N} of {total} stories have no milestone. This sprint may be unfocused. Consider running `/sweetclaude:milestones unassigned` to triage, or confirm the sprint is intentionally tactical."

5. If no milestones exist at all, skip this step silently — no milestones is not a sprint-planning problem.
```

- [ ] **Step 3: Verify**

```bash
grep -c "Sprint advances:\|sweetclaude:milestones unassigned" /Users/carsonsweet/dev/sweetclaude/skills/product-sprint-plan/SKILL.md
```

Expected: `2`

- [ ] **Step 4: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/product-sprint-plan/SKILL.md
git commit -m "feat(sprint-plan): report milestone advancement after commitment"
```

---

## Task 14: Update status skill to show active milestones

**Files:**
- Modify: `/Users/carsonsweet/dev/sweetclaude/skills/status/SKILL.md`

- [ ] **Step 1: Read current Step 2 and Step 3 sections**

```bash
sed -n '24,60p' /Users/carsonsweet/dev/sweetclaude/skills/status/SKILL.md
```

- [ ] **Step 2: Extend "Open artifacts" in Step 2 to include milestones**

Find this block in `skills/status/SKILL.md`:

```markdown
4. **Open artifacts** — check for:
   - In-progress specs in `docs/`
   - Incomplete stories in `.sweetclaude/stories/`
   - Brainstorm outputs in `.sweetclaude/brainstorm/`
   - Strategy artifacts in `strategy/`
```

Replace with:

```markdown
4. **Open artifacts** — check for:
   - In-progress specs in `docs/`
   - Incomplete stories in `.sweetclaude/stories/`
   - Brainstorm outputs in `.sweetclaude/brainstorm/`
   - Strategy artifacts in `strategy/`
5. **Active milestones** — scan `docs/milestones/MS-*.md`. For each with `**Status:** active`, compute the `n/N criteria met` count from Measuring-success checkboxes.
```

- [ ] **Step 3: Extend the status presentation in Step 3 to include an Active milestones section**

Find this block:

```
In progress:
  - {artifact or task currently open}
  - ...

Next:
  → {the logical next step based on phase, open artifacts, and exit criteria}
```

Replace with:

```
In progress:
  - {artifact or task currently open}
  - ...

Active milestones:
  - {MS-XXX Title        n/N criteria met}
  - {MS-XXX Title        n/N criteria met — ready to complete if all met}
  (omit this section if no milestones are active)

Next:
  → {the logical next step based on phase, open artifacts, and exit criteria}
```

- [ ] **Step 4: Verify**

```bash
grep -c "Active milestones" /Users/carsonsweet/dev/sweetclaude/skills/status/SKILL.md
```

Expected: `2` (one in Step 2, one in the Step 3 template).

- [ ] **Step 5: Commit**

```bash
cd /Users/carsonsweet/dev/sweetclaude
git add skills/status/SKILL.md
git commit -m "feat(status): show active milestones in orient view"
```

---

## Task 15: Sync repo changes to installed plugin cache

**Files:**
- Create: `/Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/milestones/SKILL.md`
- Modify: `/Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/product-user-story/SKILL.md`
- Modify: `/Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/product-sprint-plan/SKILL.md`
- Modify: `/Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/status/SKILL.md`
- Modify: `/Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/config/phase-skills.yaml`

**Why this task exists:** Per the memory `feedback_sync_repo_installed.md`, the repo and the installed plugin cache must stay in sync. The repo is the source of truth; the installed cache is what Claude Code loads.

- [ ] **Step 1: Create the installed skill directory**

```bash
mkdir -p /Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0/skills/milestones
```

- [ ] **Step 2: Copy all modified/new files**

```bash
REPO=/Users/carsonsweet/dev/sweetclaude
INSTALLED=/Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0

cp "$REPO/skills/milestones/SKILL.md" "$INSTALLED/skills/milestones/SKILL.md"
cp "$REPO/skills/product-user-story/SKILL.md" "$INSTALLED/skills/product-user-story/SKILL.md"
cp "$REPO/skills/product-sprint-plan/SKILL.md" "$INSTALLED/skills/product-sprint-plan/SKILL.md"
cp "$REPO/skills/status/SKILL.md" "$INSTALLED/skills/status/SKILL.md"
cp "$REPO/config/phase-skills.yaml" "$INSTALLED/config/phase-skills.yaml"
```

- [ ] **Step 3: Verify the sync worked — diff each pair**

```bash
REPO=/Users/carsonsweet/dev/sweetclaude
INSTALLED=/Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0

diff -q "$REPO/skills/milestones/SKILL.md" "$INSTALLED/skills/milestones/SKILL.md"
diff -q "$REPO/skills/product-user-story/SKILL.md" "$INSTALLED/skills/product-user-story/SKILL.md"
diff -q "$REPO/skills/product-sprint-plan/SKILL.md" "$INSTALLED/skills/product-sprint-plan/SKILL.md"
diff -q "$REPO/skills/status/SKILL.md" "$INSTALLED/skills/status/SKILL.md"
diff -q "$REPO/config/phase-skills.yaml" "$INSTALLED/config/phase-skills.yaml"
```

Expected: no output (files identical). If any diff reports differences, re-run the cp for that file.

- [ ] **Step 4: No commit needed (installed cache is not git-tracked)**

---

## Task 16: Verification pass

**Files:** (no modifications — read-only checks)

- [ ] **Step 1: Confirm the skill is discoverable by Claude Code**

This must be done by the user in a Claude Code session. Print to the user:

> "Please start a new Claude Code session and run `/sweetclaude:help` or check the available-skills listing. Confirm that `sweetclaude:milestones` appears in the list."

Do not proceed until confirmed.

- [ ] **Step 2: Dry-run `review` on a clean project**

In a project with `.sweetclaude/state/phase.yaml` but no `docs/milestones/` directory, invoke:

```
/sweetclaude:milestones review
```

Expected output: "No milestones yet. Run `/sweetclaude:milestones add` to create one."

- [ ] **Step 3: Dry-run `add` to create MS-001**

Invoke:

```
/sweetclaude:milestones add
```

Follow the prompts to create one test milestone (e.g., "Test Milestone"). Verify:

```bash
ls docs/milestones/
# Expected: MILESTONES-INDEX.md and MS-001-test-milestone.md (or similar slug)

grep "Status: proposed" docs/milestones/MS-001-*.md
# Expected: one match
```

- [ ] **Step 4: Dry-run `review` again**

```
/sweetclaude:milestones review
```

Expected: MS-001 listed under "Later (proposed)".

- [ ] **Step 5: Cleanup test milestones** (if verifying in a real project)

Delete `docs/milestones/MS-001-test-milestone.md` and restore `MILESTONES-INDEX.md` to its pre-test state. Do not commit the test milestone.

- [ ] **Step 6: Final diff check — repo ↔ installed**

```bash
REPO=/Users/carsonsweet/dev/sweetclaude
INSTALLED=/Users/carsonsweet/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0
diff -rq "$REPO/skills/milestones" "$INSTALLED/skills/milestones"
diff -q "$REPO/config/phase-skills.yaml" "$INSTALLED/config/phase-skills.yaml"
```

Expected: no output.

---

## Post-completion

After all tasks pass:

1. Push the branch / open PR if working on a branch.
2. Update the design spec's changelog at `docs/milestones-skill-design-v1-2026-04-20.md` with a row referencing the implementation commit.
3. Surface the Open Items (canonical-artifact convention, next-bucket promotion mechanism) as backlog entries via `/sweetclaude:product/backlog`.

---

## Self-review notes

Reviewed against `docs/milestones-skill-design-v1-2026-04-20.md`:

- **Spec coverage:**
  - Skill placement (always_loaded) → Task 11 ✓
  - Storage layout (index + MS-XXX files) → Task 2 ✓
  - Milestone file schema (status, owner, depends-on, outcome, measuring-success, non-goals, contributors, notes, changelog) → Task 2 template ✓
  - Linking model (bidirectional product, one-way strategy) → Task 5 (link) ✓
  - Status taxonomy (5 states) → Task 2 ✓
  - Operations (add/review/link/status/blockers/complete/unassigned) → Tasks 3-9 ✓
  - Integrations (user-story, sprint-plan, status) → Tasks 12-14 ✓
  - No-state-file discipline → Task 10 Rules section ✓
  - Config change → Task 11 ✓
  - Open Items acknowledgment → Task 10 ✓
  - Sync rule (repo ↔ installed) → Task 15 ✓

- **Placeholder scan:** No TBD/TODO lines. All code blocks contain verbatim content. No "similar to Task N" references.

- **Type consistency:**
  - `MS-XXX` format used throughout ✓
  - `**Status:**`, `**Owner:**`, `**Depends on:**`, `**Milestone:**` header format consistent ✓
  - Operation names match between skill file, routing table, and integration-protocol section ✓
  - `achieved` vs `completed` — used `achieved` consistently ✓

- **Known-acceptable gaps (open items, not plan failures):**
  - Canonical-artifact finalization convention — documented as open item in Task 10. Implementation uses a default heuristic ("file exists and first heading is not `# DRAFT`") as a placeholder until the user picks the final convention.
  - Next-bucket promotion — documented as open item; `review` groups only Now (active) and Later (proposed) until resolved.

## Changelog

| Version | Date       | Change summary              |
|---------|------------|-----------------------------|
| 1.0     | 2026-04-20 | Initial implementation plan |
