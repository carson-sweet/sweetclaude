---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Assess what to work on next and propose it."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:go" 2>/dev/null || true`

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
```

Then read the v4 backlog from `docs/product/backlog/INDEX.md` (v4 storage) if it exists, otherwise fall back to legacy:

```python
import pathlib, yaml, re, os

BACKLOG_INDEX = pathlib.Path('docs/product/backlog/INDEX.md')

if BACKLOG_INDEX.exists():
    # v4 storage: read active story files sorted by priority
    BACKLOG_BASE = pathlib.Path('docs/product/backlog')
    PRIORITY_ORDER = {'now': 1, 'soon': 2, 'later': 3, 'someday': 4, None: 5}
    active_items = []
    done_ids = set()
    for p in BACKLOG_BASE.rglob('*.md'):
        if p.name in ('INDEX.md', 'MIGRATION-MAP.md'):
            continue
        try:
            raw = p.read_bytes().decode('utf-8').replace('\r\n', '\n')
            parts = raw.split('---', 2)
            fm = yaml.safe_load(parts[1]) or {}
        except Exception:
            continue
        status = fm.get('status', 'new')
        if status in ('done', 'abandoned'):
            done_ids.add(fm.get('id', ''))
        elif status != 'deferred' and '/done/' not in str(p):
            active_items.append(fm)
    active_items.sort(key=lambda fm: (PRIORITY_ORDER.get(fm.get('priority'), 5), fm.get('id', '')))
    print("--- V4 BACKLOG (priority order) ---")
    for fm in active_items[:60]:
        print(f"{fm.get('id', '?')}  {fm.get('type', 'story')}  {fm.get('priority', '—')}  {fm.get('title', '')[:60]}")
    print("--- DONE ITEMS ---")
    for id_ in sorted(done_ids):
        print(id_)
    print("--- RECENT COMMITS (cross-check item IDs) ---")
    import subprocess
    result = subprocess.run(['git', 'log', '--oneline', '-20'], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if re.search(r'(STORY|BUG|DEBT|CHORE)-\d+', line):
            print(line)
else:
    # Legacy fallback — should not occur on v4 installs
    print("BACKLOG_INDEX_NOT_FOUND — run /sweetclaude:migrate to upgrade to v4 storage")
```

Do not call `gh`. Do not read backlog file contents for routing — the ID+priority+title list above is enough. **Skip any item whose ID appears in the DONE ITEMS list when evaluating Priority 4.** Also skip any item whose ID appears in the RECENT COMMITS list. If state is `STATE_NOT_FOUND`, note it but continue.

Roadmap routing (milestones, MS-*.md) remains untouched — Phase 2 work.

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
Before checking mode gates, check for a stale plan pointer:

```bash
python3 - << 'PY'
import os
pointer = '.sweetclaude/state/active-plan.txt'
if not os.path.exists(pointer):
    print('NO_PLAN')
    exit()
lines = dict(
    line.split(': ', 1) for line in open(pointer).read().strip().splitlines()
    if ': ' in line
)
plan = lines.get('plan', '').strip()
if plan and os.path.exists(plan):
    print(f'STALE_PLAN:{plan}')
else:
    print('NO_PLAN')
PY
```

If output starts with `STALE_PLAN:`, surface the plan and offer to archive it before starting new work. Use AskUserQuestion:

| Option | Description |
|---|---|
| **Archive it** | Move the plan to `.sweetclaude/plans/archive/` before starting new work |
| **Keep it** | Leave the plan file as-is and start new work |

If "Archive it": run the archive logic from `deploy-ship` Step 7 (read pointer, slug H1, move to milestone/sprint folder, clear pointer). Then continue.

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

**Pre-routing: PR recording at VERIFY phase entry**

If the routing table resolves to a VERIFY-phase skill (`sweetclaude:code-review`, `sweetclaude:code-testing`, `sweetclaude:documents-update-docs`): before invoking, locate the story file and check its `prs` field.

Locate the story file:
```bash
python3 - "{STORY-ID}" << 'PY'
import sys, pathlib
story_id = sys.argv[1]
for p in pathlib.Path('docs/product/backlog').rglob(f'{story_id}-*.md'):
    if 'INDEX' not in p.name.upper() and '/done/' not in str(p):
        print(p); exit()
print('NOT_FOUND')
PY
```

If `NOT_FOUND`: skip PR recording and continue to routing.

Otherwise read the story's `prs` field (`yaml.safe_load` the frontmatter). If `prs` is empty, ask via AskUserQuestion:

| Option | Description |
|---|---|
| **Enter PR number** | I'll record it against this story |
| **Skip — no PR** | Continue to VERIFY without tracking a PR |

If a number is entered:
1. `git rev-parse --abbrev-ref HEAD` — get current branch
2. Append `{number: N, branch: {current-branch}, opened_at: {today}}` to `prs`
3. Write back atomically (tmp file + `os.replace`), preserving all other frontmatter

If skipped: continue. Note: "No PR tracked — closeout will skip PR closure."

**Routing: invoke the appropriate skill**

For all phases other than SHIP: invoke the appropriate skill from the routing table below. One sentence explaining what you're doing.

For SHIP phase (routing to `sweetclaude:deploy-ship`): invoke `sweetclaude:deploy-ship`, then after it completes and the deploy or merge is confirmed, run the **Closeout sequence** below instead of prompting next steps.

---

**Closeout sequence** (runs after SHIP confirmation — do not prompt next steps after this):

First, locate the story file and resolve `story_file_path`:
```bash
python3 - "{STORY-ID}" << 'PY'
import sys, pathlib
story_id = sys.argv[1]
for p in pathlib.Path('docs/product/backlog').rglob(f'{story_id}-*.md'):
    if 'INDEX' not in p.name.upper() and '/done/' not in str(p):
        print(p); exit()
print('NOT_FOUND')
PY
```
If `NOT_FOUND`: report "⚠ Story file not found — closeout aborted." Stop.

Output: "Running closeout for {STORY-ID}…"

Run each step in order. If any step fails, report the failure inline and **continue** to the next step — never abort mid-sequence.

**Step C1 — Sub-PR scan** (superseded open PRs not already in `prs`):

First fetch to ensure remote refs are current:
```bash
git fetch --prune 2>/dev/null
```

Then scan:
```bash
python3 - << 'PY'
import subprocess, json
r = subprocess.run(['gh', 'pr', 'list', '--state', 'open', '--json', 'number,headRefName'],
    capture_output=True, text=True)
if r.returncode != 0:
    print('GH_UNAVAILABLE'); exit()
for pr in json.loads(r.stdout or '[]'):
    branch = pr['headRefName']
    r2 = subprocess.run(['git', 'merge-base', '--is-ancestor', f'origin/{branch}', 'HEAD'],
        capture_output=True)
    if r2.returncode == 0:
        print(f"SUPERSEDED:{pr['number']}:{branch}")
PY
```
If `GH_UNAVAILABLE`: note "gh unavailable — PR closure skipped", skip C1 and C2, continue from C3.
For each `SUPERSEDED:N:branch` not already in `prs`: `gh pr close N --comment "Superseded by closeout of {STORY-ID}."` Report: `✓ PR #N [branch] — closed (superseded)`

**Step C2 — Close tracked PRs**: for each entry in `prs`:
```bash
gh pr view {number} --json state -q '.state' 2>/dev/null || echo "UNKNOWN"
```
- `OPEN` → `gh pr close {number} --comment "Closed as part of {STORY-ID} closeout."` → `✓ PR #{number} closed`
- `MERGED` → `✓ PR #{number} already merged — skipped`
- `CLOSED` → `✓ PR #{number} already closed — skipped`
- `UNKNOWN` or gh error → warn and continue

**Step C3 — Switch off story branch, then delete**: if the current branch matches any branch in `prs`, switch to main first:
```bash
git checkout main 2>/dev/null
```
Then for each `branch` in `prs`:
```bash
python3 - "{branch}" << 'PY'
import sys, subprocess
branch = sys.argv[1]
if subprocess.run(['git','rev-parse','--verify', branch], capture_output=True).returncode != 0:
    print('NOT_FOUND'); exit()
r = subprocess.run(['git','branch','-d', branch], capture_output=True, text=True)
if r.returncode == 0:
    print('DELETED')
elif 'not fully merged' in r.stderr:
    print('UNMERGED')
else:
    print(f'ERROR:{r.stderr.strip()}')
PY
```
- `DELETED` → `✓ branch {branch} deleted`
- `UNMERGED` → `⚠ branch {branch} has unmerged commits — skipped`
- `NOT_FOUND` → `✓ branch {branch} already gone`
- `ERROR:...` → `⚠ branch {branch}: {error}`

**Step C4 — Delete remote branch**: for each `branch` in `prs`:
```bash
git ls-remote --heads origin {branch} | grep -q . \
  && git push origin --delete {branch} 2>/dev/null \
  && echo "DELETED" || echo "NOT_FOUND"
```
Report: `✓ origin/{branch} deleted` or `✓ origin/{branch} not present — skipped`

**Step C5 — Move story to `done/` and update frontmatter**:
```bash
python3 - "{story_file_path}" "{today}" << 'PY'
import sys, yaml, os, shutil, tempfile
path, today = sys.argv[1], sys.argv[2]
raw = open(path).read()
parts = raw.split('---', 2)
fm = yaml.safe_load(parts[1]) or {}
fm['status'] = 'done'
fm['closed_date'] = today
updated = '---\n' + yaml.dump(fm, default_flow_style=False, allow_unicode=True) + '---' + parts[2]
with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
    tmp.write(updated); tmp_name = tmp.name
os.rename(tmp_name, path)
dest_dir = os.path.join(os.path.dirname(path), 'done')
os.makedirs(dest_dir, exist_ok=True)
dest = os.path.join(dest_dir, os.path.basename(path))
shutil.move(path, dest)
print(f'MOVED:{dest}')
PY
```
Report: `✓ {STORY-ID} → done/{filename}`

**Step C6 — Update INDEX.md** (remove story row, atomic write):
```bash
python3 - "{STORY-ID}" << 'PY'
import sys, os, tempfile
story_id = sys.argv[1]
path = 'docs/product/backlog/INDEX.md'
if not os.path.exists(path): print('NOT_FOUND'); exit()
lines = open(path).readlines()
filtered = [l for l in lines if story_id not in l]
if len(filtered) == len(lines): print('ROW_NOT_FOUND'); exit()
with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
    tmp.writelines(filtered); tmp_name = tmp.name
os.replace(tmp_name, path)
print('UPDATED')
PY
```
Report: `✓ INDEX.md updated` or `⚠ INDEX.md row not found — skipped`

**Step C7 — Clear active_work_item** (if `phase.yaml` exists):
```bash
python3 - << 'PY'
import yaml, os, tempfile
path = '.sweetclaude/state/phase.yaml'
if not os.path.exists(path): exit()
d = yaml.safe_load(open(path)) or {}
last_id = (d.get('active_work_item') or {}).get('id')
d['active_work_item'] = {'id': None, 'title': None, 'type': None, 'phase': None}
if last_id:
    d['last_work_item_id'] = last_id
with tempfile.NamedTemporaryFile('w', dir='.sweetclaude/state', suffix='.tmp', delete=False) as tmp:
    yaml.dump(d, tmp, default_flow_style=False); tmp_name = tmp.name
os.replace(tmp_name, path)
PY
```

**Final output** — no menu, no "what's next?", no prompt:
```
Done. {STORY-ID} — {title} — closed.
```

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
