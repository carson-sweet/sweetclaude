---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Assess what to work on next and propose it."
---


!`bash ${CLAUDE_SKILL_DIR}/../../hooks/read-state.sh session-state`

# SweetClaude Go

Assess. Propose. Wait. Do not act until the user says proceed.

---

## Step 0: Natural-language request path

If the user passes a request after `/sweetclaude:go`, treat it as natural
language. Do not require the user to know a skill name, work-type slug, or route
command.

For `/sweetclaude:go <request>`:

1. Skip the backlog-first proposal flow below.
2. Invoke `sweetclaude:find-skill` with the user's request as context.
3. Let `find-skill` classify, confirm, write work state when appropriate, and
   invoke the matched skill.

If the request is classified as a large/high-rigor story, the matched
large-story path runs DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, and
SHIP/closeout with controller-enforced phase gates and hook-verified
enforcement. It must route through
`python3 scripts/large_story_controller.py route --route-surface /sweetclaude:go`.
Completion language is controller-owned — never claim completion the
controller has not authorized.

If the request is classified as a small/bounded story, the matched
small-story path runs DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, and
SHIP/closeout with controller-enforced phase gates and hook-verified
enforcement. It must route through
`python3 scripts/small_story_controller.py route --route-surface /sweetclaude:go`.
Completion language is controller-owned — never claim completion the
controller has not authorized.

Examples:

- `/sweetclaude:go I need to fix the auth bug`
- `/sweetclaude:go start a large story for the billing rewrite`
- `/sweetclaude:go set up corpus search for these architecture notes`
- `/sweetclaude:go review this PR for security issues`

Use the state-driven proposal flow below only when `/sweetclaude:go` is invoked
without a request.

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

Then rebuild the cache and read backlog + roadmap state:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cache.py --project-dir . --rebuild 2>/dev/null
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cache.py --project-dir . --query backlog 2>/dev/null
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cache.py --project-dir . --query active-epic 2>/dev/null
```

If cache.py is not found or fails, scan `.sweetclaude/product/backlog/` directly for markdown files with YAML frontmatter.

Do not call `gh`. Do not read backlog file contents for routing — the cache output is enough. **Skip any item whose ID appears in recent commits when evaluating Priority 4.** If state is `STATE_NOT_FOUND`, note it but continue.

## Step 1b: Migration guard

If the backlog query returned zero items, check for unmigrated files:

```bash
product_base=$(python3 -c "
import yaml, sys
d = yaml.safe_load(open('.sweetclaude/state/session-state.yaml')) or {}
print(d.get('paths', {}).get('product_base', '.sweetclaude/product'))
" 2>/dev/null || echo ".sweetclaude/product")

find "$product_base/backlog" -maxdepth 2 -name 'BL-*.md' -o -name 'STORY-*.md' -o -name 'BUG-*.md' -o -name 'DEBT-*.md' -o -name 'CHORE-*.md' 2>/dev/null | head -5
```

If old-format files are found, output:

Run the recovery guard before recommending any migration:

```bash
SCRIPT=${CLAUDE_PLUGIN_ROOT}/scripts/recovery/recover_project.py
if [ ! -f "$SCRIPT" ]; then
  SCRIPT=$(find "$(dirname "${CLAUDE_PLUGIN_ROOT}")" -type f -path '*/scripts/recovery/recover_project.py' 2>/dev/null | sort -V | tail -1)
fi
if [ -n "$SCRIPT" ] && [ -f "$SCRIPT" ]; then
  python3 "$SCRIPT" guard --project-dir . --pretty
else
  echo '{"status":"guard-unavailable","message":"Recovery guard unavailable. Run /sweetclaude:configure update before migration."}'
fi
```

Parse the guard JSON:

- `run-recover`: output
  > Your project has old-format work items and recovery detected an unsafe migration/update state. Run `/sweetclaude:configure recover` before migration. Do not run `/sweetclaude:configure migrate` yet.
  Then stop.
- `manual-review` or `missing-product-base`: output the guard `message` and
  stop. Do not recommend migration.
- `supported-migration-available`: output
  > Your project has a typed legacy backlog layout that can now be migrated. Run `/sweetclaude:configure migrate` to convert to the unified ISSUE-NNN taxonomy — it handles typed backlog folders and creates a rollback snapshot before writing.
  Then stop.
- `compatibility-mode`: do not stop. Continue to Step 2 and use session-state
  priority logic; old work items may be invisible to cache-backed backlog views,
  but active work and checkpoint state are still usable. Do not recommend
  migration.
- `migration-may-be-needed`: output
  > Your project has backlog items in the old format (BL-NNN / STORY-NNN / BUG-NNN). This appears to be a simple migration candidate. Review `/sweetclaude:configure migrate` before executing it; if there are duplicate IDs, typed backlog folders, stale migration state, or pending doctor prompts, run `/sweetclaude:configure recover` instead.
  Then stop.
- `guard-unavailable`: output the guard `message` and stop.

If the guard did not return `compatibility-mode`, stop. Do not proceed to Step 3.

## Step 2: Apply improvement register

If `improvement_register_count` in pre-loaded state is > 0, silently apply learnings from previous sessions to this session's behavior before acting. Do not announce this.

## Step 3: Find the most pressing thing

Work through the priority tiers below. Stop at the first tier that has something actionable. Note which tier triggered and why — you'll use this in the proposal.

**Priority 1 — Unfinished work in progress:**
`active_work_item.id` in pre-loaded state is set (non-null, non-`~`). Or `checkpoint_next` is set. This is the highest priority — unfinished work trumps everything.

**Priority 2 — Hot bugs / security / hotfixes:**
Any backlog filename containing `bug`, `hotfix`, `security`, `p0`, `p1`, `critical`, `urgent`.

**Priority 3 — Active epic:**
The `active-epic` cache query returned a non-null result. Query its stories in sequence order:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cache.py --project-dir . --query epic-stories --epic {EP-NNN} 2>/dev/null
```

Propose the first open story (lowest `epic_sequence`). This is the next work item for the active capability area.

If the active epic has no open stories (all done or none linked), record internally: EPIC_GAP = true, ACTIVE_EPIC = {EP-NNN title}. Fall through to Priority 4.

**Priority 4 — Other backlog items:**
Non-bug backlog items from the cache `backlog` query, already sorted by priority (now first). Use the first item in that list. Skip any item whose ID appears in recent commits.

If an active epic exists (from Step 1's `active-epic` query) and EPIC_GAP is not already true: check the proposed item's `epic` field. If it is null or does not match the active epic ID, record internally: ITEM_ORPHANED = true.

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
- If EPIC_GAP is true: `⚠ Active epic advisory: **{ACTIVE_EPIC}** has no open linked stories. Run \`/sweetclaude:plan epics status {EP-NNN}\` to check criteria or \`/sweetclaude:plan epics link\` to assign work.`
- If ITEM_ORPHANED is true: `⚠ Epic drift: this item is not linked to the active epic (**{active epic title}**). Proceeding may not advance your current roadmap target. Run \`/sweetclaude:plan epics link {ITEM-ID} {EP-NNN}\` to assign it.`

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

There's nothing obviously queued. No active work item, no open bugs, no active epic, no backlog items. I can help you plan what comes next: create epics, write user stories, or start a backlog.
```

Then call AskUserQuestion with two options:

| Option label | Description |
|---|---|
| **Start planning** | Begin a planning session — milestones, epics, stories, backlog |
| **Something else** | I have a different direction in mind |

If the user picks Start planning, invoke `sweetclaude:library-load epics add`. If Something else, follow Adaptive Flow.

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

If the routing table resolves to a VERIFY-phase skill (`sweetclaude:library-load code-review`, `sweetclaude:library-load code-testing`, `sweetclaude:library-load documents-update-docs`): before invoking, locate the story file and check its `prs` field.

Locate the story file:
```bash
python3 - "{STORY-ID}" << 'PY'
import sys, pathlib
issue_id = sys.argv[1]
for p in pathlib.Path('.sweetclaude/product/backlog').rglob(f'{issue_id}-*.md'):
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

For SHIP phase (routing to `sweetclaude:library-load deploy-ship`): invoke `sweetclaude:library-load deploy-ship`, then after it completes and the deploy or merge is confirmed, run the **Closeout sequence** below instead of prompting next steps.

---

**Closeout sequence** (runs after SHIP confirmation — do not prompt next steps after this):

First, locate the issue file and resolve `issue_file_path`:
```bash
python3 - "{STORY-ID}" << 'PY'
import sys, pathlib
issue_id = sys.argv[1]
for p in pathlib.Path('.sweetclaude/product/backlog').rglob(f'{issue_id}-*.md'):
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

Require a fresh completion evidence receipt for `{STORY-ID}` before closing.
Use the receipt created by `/sweetclaude:build code-verify`; do not self-generate a
passing receipt from memory or old output. Validate it first:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/evidence.py validate --receipt "{receipt_path}" --subject-id "{STORY-ID}"
```

If no valid receipt exists, stop and run `/sweetclaude:build code-verify` first.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/status.py set-terminal --file "{issue_file_path}" --status done --actor go --project-dir . --evidence-receipt "{receipt_path}"
```
Report: `✓ {STORY-ID} → done/{filename}`

**Step C6 — Cache rebuilt** (handled by `set-terminal` in C5):
Report: `✓ Cache rebuilt`

**Step C7 — Clear the active work item.** Clear the canonical file first, then the
`phase.yaml` mirror if a story controller left one behind. Leaving `work.active`
set is what makes `go`, `status`, and the controllers disagree about what is in
flight.

```bash
python3 - << 'PY'
import yaml, os, tempfile

def _write(path, data):
    with tempfile.NamedTemporaryFile('w', dir='.sweetclaude/state', suffix='.tmp', delete=False) as tmp:
        yaml.dump(data, tmp, default_flow_style=False, sort_keys=False)
        tmp_name = tmp.name
    os.replace(tmp_name, path)

canonical = '.sweetclaude/state/sweetclaude.yaml'
last_id = None
if os.path.exists(canonical):
    d = yaml.safe_load(open(canonical)) or {}
    work = d.setdefault('work', {})
    last_id = (work.get('active') or {}).get('id')
    work['active'] = {'id': None, 'title': None, 'type': None, 'phase': None}
    if last_id:
        work['last_item_id'] = last_id
    _write(canonical, d)

mirror = '.sweetclaude/state/phase.yaml'
if os.path.exists(mirror):
    d = yaml.safe_load(open(mirror)) or {}
    mirror_id = (d.get('active_work_item') or {}).get('id')
    d['active_work_item'] = {'id': None, 'title': None, 'type': None, 'phase': None}
    if mirror_id or last_id:
        d['last_work_item_id'] = mirror_id or last_id
    _write(mirror, d)
PY
```

**Final output** — no menu, no "what's next?", no prompt:
```
Done. {STORY-ID} — {title} — closed.
```

**Review other items:**
List the next 2–3 candidates from the priority tiers, in order. For each: name it, say which tier it came from, and say which skill would handle it. Then call AskUserQuestion again with one option per candidate plus a "None of these" escape.

**Something else:**
Ask the user for the natural-language direction if it is not already present,
then invoke `sweetclaude:find-skill` with that request as context. Track the
current proposal internally so you can offer to return to it when the detour
completes.

---

## Routing table

| Work type | Phase | Open criterion | Skill |
|---|---|---|---|
| any | DISCOVER | No persona or scenario defined | `sweetclaude:library-load product-discovery` |
| any | DEFINE | Product brief incomplete | `sweetclaude:library-load product-brief` |
| net-new-feature | DEFINE | PRD not written | `sweetclaude:library-load product-prd` |
| any | DESIGN | Architecture not written | `sweetclaude:library-load design-architecture` |
| any | DESIGN | Tech spec not written | `sweetclaude:library-load design-tech-spec` |
| any | DESIGN | UX flows not documented | `sweetclaude:library-load design-user-flows` |
| any | DESIGN | Wireframes not generated | `sweetclaude:library-load design-wireframes` |
| any | DESIGN | UX review not run | `sweetclaude:library-load design-ux-review` |
| any | DESIGN | Solutioning gate not passed | `sweetclaude:library-load design-solutioning-gate` |
| any | DESIGN | Data model not designed | `sweetclaude:library-load design-data-model` |
| any | DESIGN | API contracts not defined | `sweetclaude:library-load design-api-design` |
| any | PLAN | User stories not written | `sweetclaude:library-load product-user-stories` |
| any | PLAN | Gherkin specs not generated | `sweetclaude:library-load code-tdd` |
| any | IMPLEMENT | Tests not written or failing | `sweetclaude:library-load code-tdd` |
| any | IMPLEMENT | Code not making tests pass | `sweetclaude:library-load code-feature` |
| tech-debt | SCOPE | Behavior not locked with tests | `sweetclaude:library-load code-tdd` |
| any | VERIFY | Code review not done | `sweetclaude:library-load code-review` |
| any | VERIFY | Tests not passing in CI | `sweetclaude:library-load code-testing` |
| any | VERIFY | Docs not updated | `sweetclaude:library-load documents-update-docs` |
| any | SHIP | Security review not run and not skipped | `sweetclaude:library-load code-review` (security mode) |
| bug-fix | DIAGNOSE | Root cause not identified | `sweetclaude:library-load code-issue` |
| bug-fix | IMPLEMENT | Regression test not written | `sweetclaude:library-load code-tdd` |
| security-patch | DIAGNOSE | Blast radius not assessed | `sweetclaude:library-load code-review` |
| performance-optimization | DIAGNOSE | Baseline benchmark not established | `sweetclaude:library-load code-issue` |
| hotfix | DIAGNOSE | Reproduction case not documented | `sweetclaude:library-load code-issue` |
| backlog bug/hotfix | any | Open bug or hotfix in backlog | `sweetclaude:library-load code-issue` |

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
- **If the user passes arguments** (e.g., `/sweetclaude:go I need to fix the auth bug`): use Step 0. Natural-language requests delegate to `sweetclaude:find-skill`; users do not need to know skill names or route commands.
