---
name: sweetclaude:go
description: Figure out what to do next and do it. Reads project state, assesses progress against phase gate exit criteria, and routes to the right skill without asking for a menu selection.
---

# SweetClaude Go

Read state. Make a call. Act.

---

## Step 1: Read project state

```bash
cat .sweetclaude/state/phase.yaml
git log --oneline -7
git status --short
```

Also scan for open artifacts:
- Uncommitted files in `.sweetclaude/`
- Files in `docs/` modified recently
- Files in `.sweetclaude/stories/` or `.sweetclaude/brainstorm/`

---

## Step 2: Determine situation

### Situation A — No active work item

`active_work_item.type`, `.phase`, or `.workflow` is `~` or null.

Before asking the user, scan for pending work and apply this priority stack:

```bash
# 1. Open bugs — GitHub issues labeled bug or hotfix
gh issue list --label bug,hotfix --state open --limit 5 2>/dev/null

# 2. Backlog items — scan for type indicators in filenames and content
ls .sweetclaude/backlog/*.md 2>/dev/null
for f in .sweetclaude/backlog/*.md; do head -3 "$f" 2>/dev/null; done

# 3. Roadmap / epic plan documents
find docs/ -maxdepth 2 \( -name "*roadmap*" -o -name "*epic*" -o -name "*sprint*" \) 2>/dev/null | head -5

# 4. Stories not yet started
find .sweetclaude/stories/ -name "*.md" 2>/dev/null | head -10
```

**Apply this priority order — stop at the first tier that has items:**

**Tier 1 — Active bugs**
If open GitHub issues labeled bug/hotfix exist, OR if any backlog item is type bug/hotfix/security:
> "Open bug: {title}. Starting bug-fix workflow."
Invoke `sweetclaude:find-skill` with that bug as input. Stop.

**Tier 2 — Active roadmap**
If a roadmap/epic plan exists and has unshipped items:
Read the plan. Find the next unshipped epic or tier.

Before asking the user anything, assess what already exists for this item:
```bash
# Search for stories, specs, designs, code related to this epic
find .sweetclaude/stories/ -name "*.md" 2>/dev/null | xargs grep -l "{epic_id}\|{epic_title}" 2>/dev/null
find . -name "*.feature" 2>/dev/null | head -5
find docs/ -type f -name "*.md" 2>/dev/null | xargs grep -l "{epic_id}\|{epic_title}" 2>/dev/null | head -5
```

From what exists, determine the phase:
- No artifacts → DISCOVER
- Discovery/brief/PRD exists but no design → DESIGN
- Architecture or tech spec exists but no stories → PLAN
- User stories or Gherkin specs exist but no passing tests → IMPLEMENT
- Tests exist and passing → VERIFY

Then present:
> "Roadmap in progress. Next: {epic title}.
>
> Assessment: {what was found — e.g. '4 user stories with Gherkin specs already written'}. Placing at {phase}.
>
> Continue from {phase}?"

If confirmed, use the routing table to invoke the right skill for the assessed `{work type}` × `{phase}`. Do NOT route through `sweetclaude:find-skill` — go directly to the appropriate skill. Stop.

**Tier 3 — Tech debt and chores**
If backlog items are typed as debt/chore/cleanup/refactor, or if no roadmap exists:

Before asking, scan for any existing scope documents or tests related to this item in `.sweetclaude/` and `docs/`.

> "No bugs or active roadmap. Top debt/chore item: {title}. {Brief assessment of what exists}. Start that?"
If confirmed, use the routing table to invoke the right skill directly. Stop.

**Tier 4 — General backlog**
If any other backlog items exist:
> "Nothing urgent. Backlog has {N} items — top: {title}. Start that, or tell me what you want to work on."
If confirmed, assess artifacts as in Tier 2, then invoke the right skill directly.

**If nothing is queued anywhere:**
> "No active work item, no backlog, no roadmap. What do you want to work on?"
Invoke `sweetclaude:find-skill` with their response. Stop.

---

### Situation B — Active work item exists

Read the exit criteria for `{active_work_item.type}` × `{active_work_item.phase}` from `~/.claude/rules/sweetclaude/phase-gates.md`.

Assess each criterion against the observable evidence (git log, artifacts, file presence). Mark each: **met** / **open** / **unknown**.

**If all criteria are met:**
> "[{id}] {title} — {phase} is complete.
>
> Exit criteria: all met.
> Next phase: {next phase in workflow}.
>
> Advance?"

If yes, run the phase transition sequence from the master skill. Stop.

**If criteria are open:**

Identify the single highest-priority open criterion. Map it to the skill that addresses it using the routing table below. Then act:

> "[{id}] {title} — {phase}.
>
> Next: {what needs to happen, one sentence}.
>
> Running that now."

Invoke the skill. Stop.

**If state is ambiguous** (cannot determine met vs open from evidence alone):

Ask exactly one question to resolve it:
> "[{id}] {title} — {phase}. I can't tell from git history whether {criterion} is done.
>
> {one yes/no question}"

After the answer, re-assess and act. If still unclear after one answer, say so and stop — do not loop.

---

## Routing table

Map the first open criterion to the right skill. For work types and phases not listed, read the exit criteria and use judgment.

| Work type | Phase | Open criterion | Skill |
|---|---|---|---|
| any | DISCOVER | No persona or scenario defined | `sweetclaude:product-discovery` |
| any | DEFINE | Product brief incomplete or missing | `sweetclaude:product-brief` |
| net-new-feature | DEFINE | PRD not written | `sweetclaude:product-prd` |
| any | DESIGN | Architecture not written | `sweetclaude:design-architecture` |
| any | DESIGN | Tech spec not written | `sweetclaude:design-tech-spec` |
| any | DESIGN | UX flows not documented | `sweetclaude:design-ux` |
| any | DESIGN | Solutioning gate not passed | `sweetclaude:design-solutioning-gate` |
| any | DESIGN | Data model not designed | `sweetclaude:design-data-model` |
| any | DESIGN | API contracts not defined | `sweetclaude:design-api-design` |
| any | PLAN | User stories not written | `sweetclaude:product-user-stories` |
| any | PLAN | Gherkin specs not generated | `sweetclaude:code-tdd` |
| any | IMPLEMENT | Tests not written or failing | `sweetclaude:code-tdd` |
| any | IMPLEMENT | Code not making tests pass | `sweetclaude:code-feature` |
| tech-debt | SCOPE | Behavior not locked with tests | `sweetclaude:code-tdd` |
| any | VERIFY | Code review not done | `sweetclaude:code-review` |
| any | VERIFY | Tests not passing in CI | `sweetclaude:code-testing` |
| any | VERIFY | Docs not updated | `sweetclaude:documents-update-docs` |
| bug-fix | DIAGNOSE | Root cause not identified | `sweetclaude:code-issue` |
| bug-fix | IMPLEMENT | Regression test not written | `sweetclaude:code-tdd` |
| security-patch | DIAGNOSE | Blast radius not assessed | `sweetclaude:code-review` |
| performance-optimization | DIAGNOSE | Baseline benchmark not established | `sweetclaude:code-issue` |
| hotfix | DIAGNOSE | Reproduction case not documented | `sweetclaude:code-issue` |

---

## Rules

- **Never present a menu.** Pick the next action and invoke it.
- **Never ask "what do you want to do?"** when state is readable. Read it and act.
- **Do not skip phases.** If DESIGN exit criteria are open, do not route to PLAN.
- **One ambiguity question maximum.** If still unclear after the answer, surface the situation and stop — do not loop.
- **When invoking a skill**, briefly tell the user what you are doing and why before invoking it. One sentence.
