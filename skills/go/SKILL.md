---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:go
description: Figure out what to do next and do it. Reads project state, assesses progress against phase gate exit criteria, and routes to the right skill without asking for a menu selection.
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# SweetClaude Go

Read state. Make a call. Act. No background agent — reads files directly.

---

## Step 1: Read state directly

Session state is pre-loaded above. Use `active_work_item`, `deference`, `active_milestone`, `improvement_register_count`, `checkpoint_next`, and `paths.product_base` from there directly.

Run inline — do NOT spawn a background agent:

```bash
git log --oneline -5
git status --short
tail -25 .sweetclaude/state/checkpoint.md 2>/dev/null || echo "NO_CHECKPOINT"
ls scratch/ 2>/dev/null | grep -iE "checkpoint|continue|resume|handoff" | head -3
ls .sweetclaude/backlog/*.md 2>/dev/null | head -10
product_base=$(cat .sweetclaude/state/session-state.yaml 2>/dev/null | python3 -c "import yaml,sys; d=yaml.safe_load(sys.stdin); print(d.get('paths',{}).get('product_base','.sweetclaude/product'))" 2>/dev/null || echo "MANIFEST_MISSING")
if [ "$product_base" != "MANIFEST_MISSING" ]; then
  ls ${product_base}/milestones/MS-*.md 2>/dev/null | head -10
  grep -rh "\*\*Status:\*\*" ${product_base}/milestones/ 2>/dev/null | head -10
  ls ${product_base}/backlog/*.md 2>/dev/null | head -10
else
  echo "ARTIFACT_PRIVACY_NOT_CONFIGURED — milestone and backlog paths unknown"
fi
```

Do not call `gh`. Do not read backlog file contents — filenames are enough for routing. If state is `STATE_NOT_FOUND`, note `ARTIFACT_PRIVACY_NOT_CONFIGURED` in status but do not block operation — `go` can still run for non-planning work.

## Step 2: Apply improvement register

If `improvement_register_count` in pre-loaded state is > 0, silently apply learnings from previous sessions to this session's behavior before acting. Do not announce this unless the entries are directly relevant to the decision you are about to make.

## Step 3: Determine situation

### Situation A — No active work item

`active_work_item.id` in pre-loaded state is null or `~`.

Check the checkpoint first:
- If `checkpoint_next` in pre-loaded state is set (or checkpoint.md has a `Next:` line from a recent entry), surface it:
  > "Last checkpoint says: {Next: line}. Continue from there?"
  If yes, route directly to the appropriate skill per the routing table. Stop.

If no useful checkpoint, check the roadmap and backlog from the `ls` and `grep` output:

**Tier 1 — Bugs/hotfixes:** Any backlog filename containing `bug`, `hotfix`, `security`:
> "Open item: {filename slug}. Starting that now."
Route to `sweetclaude:code-issue`. Stop.

**Tier 2 — Roadmap (milestones):** Milestones exist in `${product_base}/milestones/`. Check the Status grep output:
- If any milestone has `Status: active`: read its Contributing work items and find the first open one. Route to the appropriate skill for that work item. Say which milestone and item you're working from.
- If milestones exist but none are `active` (all `proposed`, `achieved`, `dropped`, `superseded`):
  > "Roadmap has no active milestone — nothing currently queued. Check backlog?"
  If yes, fall through to Tier 3.
- If no `MS-*.md` files exist:
  Fall through to Tier 3 without comment.

**Tier 3 — Backlog items exist (non-bug):**
> "No active work item. Top backlog item: {first filename slug}. Start that?"
If yes, route directly to the right skill per the routing table. Stop.

**Tier 4 — Nothing queued:**
> "No active work item and no backlog. What do you want to work on?"
Invoke `sweetclaude:find-skill` with their response. Stop.

---

### Situation B — Active work item exists

Read `~/.claude/rules/sweetclaude/phase-gates.md`. Extract only the section for `active_work_item.type` × `active_work_item.phase`. Assess each exit criterion against git log, git dirty state, and checkpoint content. Mark each: **met** / **open** / **unknown**.

**If all criteria are met:**
> "[{id}] {title} — {phase} is complete. All exit criteria met.
> Next phase: {next phase in workflow}. Advance?"

If yes, run the phase transition sequence from the master skill. Stop.

**If criteria are open:**

Identify the single highest-priority open criterion. Map it to a skill via the routing table. Then:

> "[{id}] {title} — {phase}.
> Next: {what needs to happen, one sentence}.
> Running that now."

Invoke the skill. Stop.

**If state is ambiguous:**

Ask exactly one question to resolve it. After the answer, re-assess and act. If still unclear after one answer, surface the situation and stop — do not loop.

---

## Routing table

| Work type | Phase | Open criterion | Skill |
|---|---|---|---|
| any | DISCOVER | No persona or scenario defined | `sweetclaude:product-discovery` |
| any | DEFINE | Product brief incomplete | `sweetclaude:product-brief` |
| net-new-feature | DEFINE | PRD not written | `sweetclaude:product-prd` |
| any | DESIGN | Architecture not written | `sweetclaude:design-architecture` |
| any | DESIGN | Tech spec not written | `sweetclaude:design-tech-spec` |
| any | DESIGN | UX flows not documented | `sweetclaude:design-user-flows` |
| any | DESIGN | Wireframes not generated | `sweetclaude:design-wireframes` |
| any | DESIGN | UX review not run | `sweetclaude:design-ux-review` |
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
- **Never ask "what do you want to do?"** when state is readable.
- **Do not skip phases.** If DESIGN exit criteria are open, do not route to PLAN.
- **One ambiguity question maximum.** If still unclear after the answer, surface the situation and stop.
- **When invoking a skill**, one sentence explaining why before invoking.
- **Never scan code directories or git history to infer phase.** Use pre-loaded session state → checkpoint → backlog filenames. If none, ask.
