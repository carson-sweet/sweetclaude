---
spdx-license: AGPL-3.0-or-later
name: go
user-invocable: true
description: Assess what to work on next and propose it. Stops at the first obvious item found — unfinished work, hot bugs, roadmap, or debt — and waits for user approval before doing anything.
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# SweetClaude Go

Assess. Propose. Wait. Do not act until the user says proceed.

---

## Step 1: Read state directly

Session state is pre-loaded above. Use `active_work_item`, `deference`, `active_milestone`, `improvement_register_count`, `checkpoint_next`, and `paths.product_base` from there directly.

Run inline — do NOT spawn a background agent:

```bash
git log --oneline -5
git status --short
tail -25 .sweetclaude/state/checkpoint.md 2>/dev/null || echo "NO_CHECKPOINT"
ls scratch/ 2>/dev/null | grep -iE "checkpoint|continue|resume|handoff" | head -3
product_base=$(cat .sweetclaude/state/session-state.yaml 2>/dev/null | python3 -c "import yaml,sys; d=yaml.safe_load(sys.stdin); print(d.get('paths',{}).get('product_base','.sweetclaude/product'))" 2>/dev/null || echo "MANIFEST_MISSING")
if [ "$product_base" != "MANIFEST_MISSING" ]; then
  ls ${product_base}/milestones/MS-*.md 2>/dev/null | head -10
  grep -rh "\*\*Status:\*\*" ${product_base}/milestones/ 2>/dev/null | head -10
  python3 -c "
import glob, re, os
base = '${product_base}'
HORIZON_ORDER = {'next':1,'sooner':2,'soon':3,'later':4,'someday':5,'unscheduled':6}
rows = []
for f in sorted(glob.glob(os.path.join(base,'backlog','BL-*.md'))):
    c = open(f).read()
    m = re.search(r'\*\*Horizon:\*\*\s*(\S+)', c)
    h = (m.group(1).lower() if m else 'unscheduled')
    rows.append((HORIZON_ORDER.get(h, 6), os.path.basename(f)))
rows.sort()
for _, fn in rows[:60]:
    print(fn)
" 2>/dev/null
  echo "--- DONE ITEMS (exclude from proposals) ---"
  grep -irl "\*\*Status:\*\*.*done\|\*\*Status:\*\*.*deferred\|^status:.*done\|^status:.*deferred\|^completed:" ${product_base}/backlog/BL-*.md 2>/dev/null | sed 's|.*/||' | sort
  echo "--- RECENT COMMITS (cross-check item IDs) ---"
  git log --oneline -20 2>/dev/null | grep -iE "BL-[0-9]+"
else
  echo "ARTIFACT_PRIVACY_NOT_CONFIGURED — milestone and backlog paths unknown"
fi
```

Do not call `gh`. Do not read backlog file contents for routing — filenames plus the DONE ITEMS list above are enough. **Skip any file whose basename appears in the DONE ITEMS list when evaluating Priority 4.** Also skip any item whose ID appears in the RECENT COMMITS list. If state is `STATE_NOT_FOUND`, note it but continue.

## Step 2: Apply improvement register

If `improvement_register_count` in pre-loaded state is > 0, silently apply learnings from previous sessions to this session's behavior before acting. Do not announce this.

## Step 3: Find the most pressing thing

Work through the priority tiers below. Stop at the first tier that has something actionable. Note which tier triggered and why — you'll use this in the proposal.

**Priority 1 — Unfinished work in progress:**
`active_work_item.id` in pre-loaded state is set (non-null, non-`~`). Or `checkpoint_next` is set. This is the highest priority — unfinished work trumps everything.

**Priority 2 — Hot bugs / security / hotfixes:**
Any backlog filename containing `bug`, `hotfix`, `security`, `p0`, `p1`, `critical`, `urgent`.

**Priority 3 — Active roadmap:**
Milestones exist in `${product_base}/milestones/`. Any milestone has `Status: active`. Read its Contributing work items and find the first open one.

If an active milestone exists but has no open contributing work items (all done, none listed, or item files missing), record internally: MILESTONE_GAP = true, ACTIVE_MS = {the milestone filename stem}. Fall through to Priority 4.

**Priority 4 — Other backlog items:**
Non-bug backlog items. The filenames above are already sorted by horizon (next first, unscheduled last). Use the first filename in that sorted list.

If `active_milestone` is set in the pre-loaded state and MILESTONE_GAP is not already true: read the proposed item's file and check for a `**Milestone:**` header. If the header is absent or its value does not match `active_milestone`, record internally: ITEM_ORPHANED = true.

**Priority 5 — Nothing queued:**
None of the above tiers have anything actionable.

## Step 4: Produce the proposal

**Do not invoke any skill. Do not start any work. Output the proposal and stop.**

---

### If Priority 1–4 found something:

Output the bold header followed by one prose paragraph explaining the proposal. Use markdown **bold** for `PROPOSED NEXT WORK`. Do NOT include a text line of options — the menu is presented via AskUserQuestion immediately after.

```
**PROPOSED NEXT WORK**

{One clear paragraph: what you're proposing to work on, why this item ranks first, and what specifically would happen if the user says proceed. Name the work item or backlog filename. Reference the priority tier reason: "You have unfinished work in progress" / "There's an open bug" / "Your active milestone has a pending work item" / "Top of your backlog is..." Be direct, not hedging.}
```

**Drift advisories — append after the proposal paragraph when applicable (do not omit):**
- If MILESTONE_GAP is true: `⚠ Active milestone advisory: **{ACTIVE_MS}** has no open linked work items. Run \`/sweetclaude:product-milestones blockers {ACTIVE_MS}\` to check status or link new work.`
- If ITEM_ORPHANED is true: `⚠ Milestone drift: this item is not linked to your active milestone (**{active_milestone}**). Proceeding may not advance your current roadmap target.`

Then immediately call AskUserQuestion with these three options:

| Option label | Description |
|---|---|
| **Proceed** | Start the proposed work now |
| **Review other items** | Show the next 2–3 candidates and pick one |
| **Something else** | I have a different direction in mind |

Use AskUserQuestion's `header` field to label the question (e.g. "Next work?"). Do not output any text alternative to the menu — the menu is the only prompt. Wait for the user's selection before doing anything.

---

### If Priority 5 — nothing queued:

Output the bold header and one prose paragraph:

```
**PROPOSED NEXT WORK**

There's nothing obviously queued. No active work item, no open bugs, no active milestone, no backlog items. I can help you plan what comes next: create milestones and epics, write user stories, or start a backlog.
```

Then call AskUserQuestion with two options:

| Option label | Description |
|---|---|
| **Start planning** | Begin a planning session — milestones, epics, stories, backlog |
| **Something else** | I have a different direction in mind |

If the user picks Start planning, invoke `sweetclaude:product-milestones`. If Something else, follow Adaptive Flow.

---

## Step 5: Handle the user's selection

**Proceed:**
Before invoking an IMPLEMENT-phase skill, check mode gates:

```bash
python3 -c "
import yaml, os, glob, sys
PROJECT_DIR = os.environ.get('PROJECT_DIR', os.getcwd())
gates_path = os.path.join(PROJECT_DIR, '.sweetclaude/state/effective-gates.yaml')
if not os.path.exists(gates_path):
    print('GATES_OK'); sys.exit()
d = yaml.safe_load(open(gates_path)) or {}
mode = d.get('mode', '')
gates = [g for g in d.get('gates', []) if g.get('phase') == 'IMPLEMENT' and g.get('action') == 'block']
for gate in gates:
    cond = gate.get('condition', '')
    req = gate.get('requires', '')
    msg = gate.get('message', 'Gate condition not met.')
    if req == 'betting_table_approved' and mode == 'shape_up':
        sc = yaml.safe_load(open(os.path.join(PROJECT_DIR, '.sweetclaude/state/sweetclaude.yaml'))) or {}
        active_id = ((sc.get('work') or {}).get('active') or {}).get('id') or ''
        issue_path = os.path.join(PROJECT_DIR, '.sweetclaude/artifacts/issues', f'{active_id}.yaml')
        approved = bool(active_id and os.path.exists(issue_path) and (yaml.safe_load(open(issue_path)) or {}).get('betting_table_approved'))
        if not approved:
            print('BLOCKED:' + msg); sys.exit()
    if cond == 'no_active_sprint' and mode == 'agile':
        sprints_dir = os.path.join(PROJECT_DIR, '.sweetclaude/artifacts/sprints')
        has_active = os.path.exists(sprints_dir) and any(
            (yaml.safe_load(open(f)) or {}).get('status') == 'active'
            for f in glob.glob(os.path.join(sprints_dir, '*.yaml'))
        )
        if not has_active:
            print('BLOCKED:' + msg); sys.exit()
print('GATES_OK')
"
```

If output starts with `BLOCKED:`, do not invoke any skill. Output the text after `BLOCKED:` and stop.

Otherwise, invoke the appropriate skill from the routing table below. One sentence explaining what you're doing.

**Review other items:**
List the next 2–3 candidates from the priority tiers, in order. For each: name it, say which tier it came from, and say which skill would handle it. Then call AskUserQuestion again with one option per candidate plus a "None of these" escape.

**Something else:**
Follow the user's direction immediately per Adaptive Flow. Track the current proposal internally so you can offer to return to it when the detour completes.

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
| any | SHIP | Security review not run and not skipped | `sweetclaude:code-review` (security mode) |
| bug-fix | DIAGNOSE | Root cause not identified | `sweetclaude:code-issue` |
| bug-fix | IMPLEMENT | Regression test not written | `sweetclaude:code-tdd` |
| security-patch | DIAGNOSE | Blast radius not assessed | `sweetclaude:code-review` |
| performance-optimization | DIAGNOSE | Baseline benchmark not established | `sweetclaude:code-issue` |
| hotfix | DIAGNOSE | Reproduction case not documented | `sweetclaude:code-issue` |
| backlog bug/hotfix | any | Open bug or hotfix in backlog | `sweetclaude:code-issue` |

### Mode-filtered routing

Read `blocked_skills` from `effective-gates.yaml` if it exists. Remove blocked skills from all suggestion lists.

Apply per mode:
- **flow:** surface project-issues, product-roadmap, product-milestones. Omit project-sprints.
- **kanban:** surface project-issues, product-roadmap, product-milestones, project-backlog. Omit project-sprints.
- **shape_up:** surface project-issues (pitch-source note), product-roadmap, product-milestones. Omit project-sprints, project-backlog.
- **agile:** surface all skills including project-sprints, project-epics.
- **unset:** apply flow filtering.

---

## Rules

- **Propose, do not act.** Never invoke a skill in Step 4. Proposals only.
- **Stop at the first thing.** Don't enumerate all issues — find the top item and propose it.
- **One paragraph, not a list.** The proposal explanation is prose, not bullet points.
- **Use AskUserQuestion, not text-imitation menus.** Never write a text line like "Proceed · Review · Something else" — that looks like a menu but isn't interactive. Always present choices via AskUserQuestion.
- **Wait after proposing.** Do not continue until the user selects an option.
- **If the user passes arguments** (e.g., `/sweetclaude:go I need to fix the auth bug`): skip Steps 1–3. Use the user's direction as the proposal, confirm it in the PROPOSED NEXT WORK format, and present the same AskUserQuestion menu before acting.
