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

Before asking the user, scan for pending work:

```bash
# Backlog items
ls .sweetclaude/backlog/*.md 2>/dev/null

# Roadmap or epic plan documents
find docs/ -name "*roadmap*" -o -name "*epic*" -o -name "*plan*" 2>/dev/null | head -5

# Unstarted stories
find .sweetclaude/stories/ -name "*.md" 2>/dev/null | head -10
```

**If backlog items or roadmap exists:**

Read them. Identify the highest-priority next item — top of the backlog, or the next unshipped tier in the roadmap. Present it:

> "No active work item. Here's what's queued:
>
> **Backlog:** {N} items — top item: {title} ({filename})
> **Roadmap:** {next unshipped epic or milestone}
>
> Start with {recommended item}?"

If the user confirms, invoke `sweetclaude:find-skill` with that item as input. If they redirect, invoke `sweetclaude:find-skill` with their choice instead.

**If nothing is queued:**

> "No active work item and nothing in the backlog. What do you want to work on?"

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
