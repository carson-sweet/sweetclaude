---
name: sweetclaude:go
description: Figure out what to do next and do it. Reads project state, assesses progress against phase gate exit criteria, and routes to the right skill without asking for a menu selection.
---

# SweetClaude Go

Read state. Make a call. Act.

---

## Step 1: Gather project state (background)

Spawn a background agent using the Agent tool with **no subagent_type** (fork — tool calls are invisible to the main conversation). Pass this exact prompt:

---
Read the following files and run the following commands from the current working directory. Return ONLY structured data — no prose, no explanations.

**Reads:**
1. `.sweetclaude/state/phase.yaml` — full contents
2. Find first roadmap/epic plan file: `find docs/ -maxdepth 2 \( -name "*roadmap*" -o -name "*epic*" -o -name "*sprint*" \) 2>/dev/null | head -1` — if found, read it fully; if not, return "none"
3. Backlog files: `ls .sweetclaude/backlog/*.md 2>/dev/null` — for each, read first 5 lines

**Commands:**
4. `git log --oneline -7`
5. `git status --short`
6. `gh issue list --label bug,hotfix --state open --limit 5 2>/dev/null` — return "none" if no issues or gh not available

**Phase gates (conditional):**
7. If phase.yaml has `active_work_item` with type and phase both non-null/non-~: read `~/.claude/rules/sweetclaude/phase-gates.md` and extract only the section for that work type and phase. Return "not_applicable" if no active work item.

**Return this exact structure:**
```
PHASE_YAML:
  {full yaml contents}
ACTIVE_TYPE: {active_work_item.type or "none"}
ACTIVE_PHASE: {active_work_item.phase or "none"}
ACTIVE_WORKFLOW: {active_work_item.workflow as comma-separated list or "none"}
ACTIVE_ID: {active_work_item.id or "none"}
ACTIVE_TITLE: {active_work_item.title or "none"}
GIT_LOG:
  {output of command 4, one line per commit}
GIT_DIRTY: {yes if command 5 has output, no if empty}
OPEN_BUGS:
  {output of command 6 or "none"}
ROADMAP_PATH: {path found or "none"}
ROADMAP_CONTENT:
  {full content of roadmap file or "none"}
BACKLOG_FILES:
  {filename}: {first 5 lines}
  ...
PHASE_GATES_SECTION:
  {extracted section for active type × phase, or "not_applicable"}
```
---

Wait for the background agent to complete. Use its returned data block for Step 2.

---

## Step 2: Determine situation

### Situation A — No active work item

`ACTIVE_TYPE`, `ACTIVE_PHASE`, or `ACTIVE_WORKFLOW` is "none" or null.

Before asking the user, assess available work using this priority stack:

**Tier 1 — Active bugs**
If `OPEN_BUGS` has entries, OR if any `BACKLOG_FILES` entry has type bug/hotfix/security in its first 5 lines:
> "Open bug: {title}. Starting bug-fix workflow."
Invoke `sweetclaude:find-skill` with that bug as input. Stop.

**Tier 2 — Active roadmap**
If `ROADMAP_PATH` is not "none" and `ROADMAP_CONTENT` contains unshipped items:

Parse the roadmap content. Find the next epic/item where `Status:` is not `shipped` or `complete`.

Read the `Status:` field directly from the roadmap content:
- `not_started` → start from first phase in the workflow
- `in_progress` + a `Phase:` annotation → use that phase
- `in_progress` without annotation → ask: "Where are you in {epic title}? (e.g. designing / writing code / ready for review)"
- `blocked` → skip this epic, check the next one

Then present:
> "Roadmap in progress. Next: {epic title}.
>
> Status: {status}. Starting at {phase}.
>
> Continue?"

If confirmed, use the routing table to invoke the right skill for `{work type}` × `{phase}`. Do NOT route through `sweetclaude:find-skill` — go directly to the appropriate skill. Stop.

**Tier 3 — Tech debt and chores**
If `BACKLOG_FILES` has items typed as debt/chore/cleanup/refactor, or if no roadmap exists:

> "No bugs or active roadmap. Top debt/chore item: {title}. Start that?"
If confirmed, use the routing table to invoke the right skill directly. Stop.

**Tier 4 — General backlog**
If any other backlog items exist:
> "Nothing urgent. Backlog has {N} items — top: {title}. Start that, or tell me what you want to work on."
If confirmed, invoke the right skill directly.

**If nothing is queued anywhere:**
> "No active work item, no backlog, no roadmap. What do you want to work on?"
Invoke `sweetclaude:find-skill` with their response. Stop.

---

### Situation B — Active work item exists

Use `PHASE_GATES_SECTION` from the background fork data. Assess each criterion against the observable evidence from `GIT_LOG`, `GIT_DIRTY`, and artifact presence. Mark each criterion: **met** / **open** / **unknown**.

**If all criteria are met:**
> "[{ACTIVE_ID}] {ACTIVE_TITLE} — {ACTIVE_PHASE} is complete.
>
> Exit criteria: all met.
> Next phase: {next phase in ACTIVE_WORKFLOW}.
>
> Advance?"

If yes, run the phase transition sequence from the master skill. Stop.

**If criteria are open:**

Identify the single highest-priority open criterion. Map it to the skill that addresses it using the routing table below. Then act:

> "[{ACTIVE_ID}] {ACTIVE_TITLE} — {ACTIVE_PHASE}.
>
> Next: {what needs to happen, one sentence}.
>
> Running that now."

Invoke the skill. Stop.

**If state is ambiguous** (cannot determine met vs open from evidence alone):

Ask exactly one question to resolve it:
> "[{ACTIVE_ID}] {ACTIVE_TITLE} — {ACTIVE_PHASE}. I can't tell from git history whether {criterion} is done.
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
- **Never scan code directories or git history to infer phase.** Use structured state: phase.yaml → roadmap Status: field → backlog front matter. If none, ask the user.
