---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Manage project issues — list, view, create, update, and close."
---

## Issue tracker selection

Read the canonical project setting before inspecting local artifacts:

```bash
ISSUE_TRACKER=$(python3 - <<'PY'
import pathlib, yaml
p = pathlib.Path('.sweetclaude/state/sweetclaude.yaml')
try:
    d = yaml.safe_load(p.read_text()) or {}
except (OSError, yaml.YAMLError):
    d = {}
print(d.get('project', {}).get('issue_tracker', 'local'))
PY
)
```

`project.issue_tracker` is `local` by default. If it is `github`, GitHub
Issues are the project system of record: do **not** read, create, migrate, or
sync `.sweetclaude/product` issue files. This includes skipping the local
migration guard below.

Only `local` and `github` are valid values. If the setting contains anything
else, report the invalid value and stop rather than guessing a tracker.

`tracker local` and `tracker github` explicitly change this per-project
setting. Treat clear natural-language requests as the same operation. For
example, “use GitHub for this project's issues”, “track issues on GitHub”, and
“stop using local issue tracking” mean `tracker github`; “use local issues
again” means `tracker local`. If the request is ambiguous about the project or
tracker, ask one clarification question rather than changing configuration.

Before changing to `github`, run the connection check below. Then update only
`project.issue_tracker` in `.sweetclaude/state/sweetclaude.yaml` with an atomic
replace; do not import, export, or delete issues as a side effect:

```python
import os, pathlib, tempfile, yaml

path = pathlib.Path('.sweetclaude/state/sweetclaude.yaml')
data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
data.setdefault('project', {})['issue_tracker'] = '<local-or-github>'
with tempfile.NamedTemporaryFile('w', dir=path.parent, suffix='.tmp',
                                 delete=False, encoding='utf-8') as tmp:
    yaml.safe_dump(data, tmp, default_flow_style=False, sort_keys=False,
                   allow_unicode=True)
    temp_path = tmp.name
os.replace(temp_path, path)
```

Confirm the selected system of record. Process this configuration operation
before routing the remaining arguments.

First verify the connection:

```bash
gh auth status 2>/dev/null && git remote get-url origin 2>/dev/null
```

If authentication or an `origin` remote is unavailable, explain which is
missing and stop. Never silently fall back to local issue files.

For `github`, route `$ARGUMENTS` directly to GitHub:

| Arguments | GitHub operation |
|---|---|
| (empty), `list`, `backlog` | `gh issue list --state open --limit 100` |
| `view <number>` | `gh issue view <number>` |
| `new` | Collect title and description one question at a time, then `gh issue create --title "..." --body "..."` |
| `update <number>` | Show `gh issue view <number>`, collect title/body/assignee/label changes, then use `gh issue edit` with only those fields |
| `close <number>` or `decline <number>` | Confirm when necessary, then `gh issue close <number>` |
| `reopen <number>` | `gh issue reopen <number>` |

Use GitHub issue numbers in this mode (for example, `#42` or `42`), not
`ISSUE-NNN`. `triage` is not a file move in GitHub mode: apply or remove the
repository's existing `triage` label with `gh issue edit`. Do not create labels
implicitly; if no suitable label exists, say so and leave the issue unchanged.
Report the GitHub URL returned by each mutation.

The local-only operations and rules below apply only when `ISSUE_TRACKER` is
`local`.

## MIGRATION GUARD

Before any other work, check for legacy migration/recovery risk:

```bash
PRODUCT_BASE=$(python3 -c "
import yaml, pathlib
p = pathlib.Path('.sweetclaude/artifact-privacy.yaml')
if p.exists():
    d = yaml.safe_load(p.read_text()) or {}
    base = d.get('categories', {}).get('product', {}).get('base_path', '')
    if base:
        print(base.rstrip('/'))
        exit()
print('.sweetclaude/product')
" 2>/dev/null || echo '.sweetclaude/product')
LEGACY_FILES=$(find "${PRODUCT_BASE}" -maxdepth 4 -type f \( -name 'BL-*.md' -o -name 'STORY-*.md' -o -name 'BUG-*.md' -o -name 'DEBT-*.md' -o -name 'CHORE-*.md' \) 2>/dev/null | wc -l | tr -d ' ')
if [ "$LEGACY_FILES" -gt 0 ]; then
  SCRIPT=${CLAUDE_PLUGIN_ROOT}/scripts/recovery/recover_project.py
  if [ ! -f "$SCRIPT" ]; then
    SCRIPT=$(find "$(dirname "${CLAUDE_PLUGIN_ROOT}")" -type f -path '*/scripts/recovery/recover_project.py' 2>/dev/null | sort -V | tail -1)
  fi
  if [ -n "$SCRIPT" ] && [ -f "$SCRIPT" ]; then
    python3 "$SCRIPT" guard --project-dir . --pretty
  else
    echo '{"status":"guard-unavailable","message":"Recovery guard unavailable. Run /sweetclaude:configure update before migration."}'
  fi
fi
```

If the guard output has `status` `run-recover`, `manual-review`,
`compatibility-mode`, `missing-product-base`, or `guard-unavailable`: print the
guard `message`, tell the user to run `/sweetclaude:configure recover` when recovery is
available, and stop. Do not recommend migration.

If the guard output has `status` `supported-migration-available`: print
"This project has a typed legacy backlog layout that can be migrated. Run
`/sweetclaude:configure migrate` to convert to the unified ISSUE-NNN taxonomy." Then stop.

If the guard output has `status` `migration-may-be-needed`: print the guard
`message`, then stop and tell the user to review `/sweetclaude:configure migrate` before
running it. Do not invoke migration from this skill.

```python
import pathlib, yaml, re, datetime, shutil

BACKLOG_BASE = pathlib.Path('.sweetclaude/product/backlog')
ROADMAP_ISSUES = pathlib.Path('.sweetclaude/product/roadmap/issues')
SKIP_FILES = {'INDEX.md', 'MIGRATION-MAP.md', 'SCHEMA.md'}

STATUSES = {'new', 'ready', 'active', 'in-review', 'blocked', 'on-hold', 'deferred', 'done', 'declined', 'abandoned', 'superseded'}
TERMINAL_STATUSES = {'done', 'declined', 'abandoned', 'superseded'}

def read_issue_file(path):
    raw = pathlib.Path(path).read_bytes().decode('utf-8').replace('\r\n', '\n')
    parts = raw.split('---', 2)
    fm = yaml.safe_load(parts[1]) or {}
    body = parts[2] if len(parts) > 2 else ''
    return fm, body

def write_issue_file(path, fm, body):
    content = f"---\n{yaml.safe_dump(fm, default_flow_style=False, sort_keys=False).rstrip()}\n---\n{body}"
    pathlib.Path(path).write_text(content, encoding='utf-8')

def find_issue_by_id(issue_id):
    for base in [BACKLOG_BASE, ROADMAP_ISSUES]:
        for p in base.rglob('*.md'):
            if p.name in SKIP_FILES:
                continue
            stem = p.stem
            if stem == issue_id or stem.startswith(issue_id + '-'):
                return p
    return None

def make_slug(title):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', title.lower())).strip('-')

def assign_new_id():
    import subprocess, json
    import os
    r = subprocess.run(['python3', os.path.expanduser('${CLAUDE_PLUGIN_ROOT}/scripts/cache.py'), '--project-dir', '.', '--query', 'next-id', '--prefix', 'ISSUE'],
        capture_output=True, text=True)
    return json.loads(r.stdout)['next_id']

def rebuild_cache():
    import subprocess, os
    subprocess.run(['python3', os.path.expanduser('${CLAUDE_PLUGIN_ROOT}/scripts/cache.py'), '--project-dir', '.', '--rebuild'], capture_output=True)

def all_issue_files():
    files = []
    for base in [BACKLOG_BASE, ROADMAP_ISSUES]:
        files.extend(p for p in base.rglob('*.md') if p.name not in SKIP_FILES)
    return files
```

# Project Issues

Manage project issues. Arguments: `$ARGUMENTS`

---

## MODE CHECK

Read `mode` from pre-loaded session state.

### Shape Up (shape_up) — pitch source enforcement

If `mode` is `shape_up` AND operation is `create` (not `pitch`, `list`, or `update`):

Ask: "Is this issue derived from an approved pitch?"

- **Yes** → Ask for pitch ID (e.g., `PITCH-001`). Include `pitch_id: {PITCH-XXX}` in the frontmatter. Proceed with create.
- **No / I don't have a pitch** → Output and stop:
  > "In Shape Up mode, all issues must come from an approved pitch. The betting table has already decided what's worth building — issues outside approved pitches expand scope without an appetite trade-off.
  >
  > Write a pitch first: `/sweetclaude:build project-issues pitch`"

All other modes: proceed with standard create flow. No pitch source required.

---

## Routing

Parse the first word of `$ARGUMENTS` to determine the operation.

| First word | Operation |
|---|---|
| (empty) | → **List** all non-done issues |
| `list` | → **List** all non-done issues |
| `backlog` | → **Backlog** (issues not yet in a sprint) |
| `view <ID>` | → **View** single issue |
| `new` | → **Create** new issue interactively |
| `update <ID>` | → **Update** existing issue |
| `close <ID>` | → **Close** issue (terminal status, move to done/) |
| `decline <ID>` | → **Decline** issue (status → declined, move to archived/) |
| `triage <ID>` | → **Triage** issue (backlog → roadmap/issues, status → ready) |
| `reopen <ID>` | → **Reopen** issue (status → new, move back to origin) |

---

## List

```python
files = all_issue_files()
stories = []
for p in files:
    fm, _ = read_issue_file(p)
    if fm.get('status') not in TERMINAL_STATUSES:
        stories.append(fm)

# Sort: priority order, then by id
PRIORITY_ORDER = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3, None: 5}
stories.sort(key=lambda fm: (PRIORITY_ORDER.get(fm.get('priority'), 5), fm.get('id', '')))
```

Present as a compact table. Sort: done/abandoned last, then by priority, then by ID.

```
ID          Type    Status      Pri   Eff  Title
ISSUE-001   enhancement   new         P2    m    Add OAuth login
ISSUE-002   bug-fix       active      P0    s    Crash on empty input
...
```

After the table: `{N} issues  ({done} done, {active} active, {new} new)`

---

## Backlog

Show items with no sprint assignment and status not in done/abandoned:

```python
backlog = [fm for fm in stories if not fm.get('sprint') and fm.get('status') not in TERMINAL_STATUSES and fm.get('status') != 'deferred']
```

Present same table format as List, sorted by priority. Header: `Backlog — {N} unscheduled issues`

After table: suggest `project-sprints` to schedule issues into a sprint, or `project-backlog-triage` if more than 10 issues have no effort estimate.

---

## View


```python
path = find_issue_by_id('<ID>')
if not path:
    print(f"Issue `<ID>` not found.")
else:
    fm, body = read_issue_file(path)
```

Present as:

```
ISSUE-001 — Add OAuth login
Type:      enhancement    Status:   new
Priority:  P2             Effort:   m
Epic:      (none)         Sprint:   (none)
Origin:    manual

Description
  ...

Acceptance Criteria
  (if present)

Sprint History
  (if present)
```

If the issue has been in 2+ sprints without completing, add a warning:
`Adrift: carried over {N} sprints without completion.`

---

## Create

Ask one question at a time. Do not present a form.

1. **Title** — "What's the issue? One line."
2. **Type** — Present the workflow type categories via AskUserQuestion:
   - **New:** `net-new-feature`, `external-integration`, `onboarding-flow-design`
   - **Enhancement:** `enhancement`
   - **Fix:** `bug-fix`, `security-patch`, `hotfix`, `performance-optimization`, `rollback-revert`
   - **Chore:** `tech-debt`, `dependency-upgrade`, `infrastructure-change`, `compliance-requirement`
   - **Migration:** `technology-migration`, `data-migration`, `api-deprecation`
   - **Planning:** `release-planning`, `security-planning`, `course-correction`
   - **Research:** `spike`
   (default: `enhancement`)
3. **Description** — For net-new-feature: "As a [who], they want [what] so that [why]?" For bug-fix/hotfix: "Steps to reproduce?" For tech-debt: "What's the structural problem?" For other types: "What needs to be done?"
4. **Acceptance criteria** (net-new-feature/bug-fix/enhancement only) — "What conditions make this done? List them one per line, or say none."
5. **Priority** — "P0 / P1 / P2 / P3?" (default: P2)
6. **Effort** — "s / m / l / xl?" (default: m)
7. **Epic** — "Does this belong to an epic?" List available epics first, or say none.

Once all answers collected:

```python
today = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
typ = '<type>'  # workflow type key from config/workflow-templates.yaml
new_id = assign_new_id()
slug = make_slug('<title>')
fm = {
    'id': new_id,
    'type': typ,
    'title': '<title>',
    'status': 'new',
    'priority': '<priority>',
    'effort': '<effort>',
    'epic': '<epic_id or null>',
    'milestone': None,
    'sprint': None,
    'tags': [],
    'origin': 'manual',
    'created': today,
    'updated': today,
    'closed_date': None,
}
dest = BACKLOG_BASE / f"{new_id}-{slug}.md"
body = f"\n## Description\n\n<description>\n\n## Acceptance Criteria\n\n<ac>\n"
write_issue_file(dest, fm, body)
```

Confirm: `Created {new_id} — {title}`

---

## Update

```python
path = find_issue_by_id('<ID>')
fm, body = read_issue_file(path)
```

Show the current values. Ask: "What would you like to change?" Accept natural language or field=value pairs.

Map the user's intent to fields:
- "move to sprint SP-003" → `sprint: SP-003`, `status: active`
- "set priority to P1" → `priority: P1`
- "assign to epic EP-001" → `epic: EP-001`
- "remove from sprint" → `sprint: null`
- "mark blocked" → `status: blocked`
- "put on hold" → `status: on-hold`
- "defer" → `status: deferred`, ask for optional `deferred_reason`
- "start review" → `status: in-review`
- "add acceptance criteria" → append to body Acceptance Criteria section

**Status validation:** Transition rules and audit logging are handled by `scripts/status.py`. Setting `superseded` requires `superseded_by` to be set first. Setting `deferred` accepts optional `deferred_reason`.

Then:

```python
if '<superseded>' and not fm.get('superseded_by'):
    fm['superseded_by'] = '<replacement_id>'
if '<deferred>' and '<reason_provided>':
    fm['deferred_reason'] = '<reason>'
write_issue_file(path, fm, body)
```

If status is changing, update via the status CLI (do NOT set `fm['status']` directly):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/status.py set --file {path} --status {new_status} --actor project-issues --project-dir .
```

Confirm: `Updated {ID} — {list of changed fields}`

---

## Close

Set a terminal status and move to `roadmap/issues/done/`. Only applies to triaged issues (in `roadmap/issues/`). Default status is `done`; also accepts `abandoned` or `superseded`.

If the issue is in `backlog/`, reject: "This issue hasn't been triaged. Use `decline` to reject it, or `triage` it first."

If `superseded`, ask: "What issue replaces this one?" Set `superseded_by: ISSUE-NNN` in frontmatter.

If `terminal_status` is `done` and current status is not `in-review` or `active`, warn: "This issue hasn't reached review. Close anyway?" Proceed only on confirmation.


If `terminal_status` is `done`, require a valid completion evidence receipt.
Use the receipt created by `sweetclaude:library-load code-verify`; do not self-generate a
passing receipt from memory or a stale prior run. Validate it before closing:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/evidence.py validate --receipt {receipt_path} --subject-id <ID>
```

If no valid receipt exists, stop and run `/sweetclaude:build code-verify` first.

```python
path = find_issue_by_id('<ID>')
if not (ROADMAP_ISSUES in path.parents or path.parent == ROADMAP_ISSUES):
    print("This issue hasn't been triaged. Use `decline` to reject it, or `triage` it first.")
    return
terminal_status = '<status>'  # done, abandoned, or superseded
if terminal_status == 'superseded':
    fm, body = read_issue_file(path)
    fm['superseded_by'] = '<replacement_id>'
    write_issue_file(path, fm, body)
```

For `done`:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/status.py set-terminal --file {path} --status done --actor project-issues --project-dir . --evidence-receipt {receipt_path}
```

For `abandoned` or `superseded`:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/status.py set-terminal --file {path} --status {terminal_status} --actor project-issues --project-dir .
```

`set-terminal` handles: status change, `closed_date`, file move to `done/`, audit log, cache rebuild.

Confirm: `Closed {ID} — {title} [{terminal_status}]`

If the issue was the last open issue in an epic, surface:
`All issues in {EP-NNN} are now done. Run project-epics to close the epic.`

---

## Decline

Evaluate and reject an issue. Only applies to issues in `backlog/` — triaged issues should be closed with `abandoned` or `superseded` instead.

```python
path = find_issue_by_id('<ID>')
if ROADMAP_ISSUES in path.parents or path.parent == ROADMAP_ISSUES:
    print("This issue has been triaged. Use `close` with status abandoned or superseded instead.")
    return
```

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/status.py set-terminal --file {path} --status declined --actor project-issues --project-dir .
```

`set-terminal` handles: status change, `closed_date`, file move to `archived/`, audit log, cache rebuild.

Confirm: `Declined {ID} — {title}`

---

## Triage

Move an issue from backlog to roadmap/issues, marking it ready for development.

```python
path = find_issue_by_id('<ID>')
if ROADMAP_ISSUES in path.parents or path.parent == ROADMAP_ISSUES:
    print("Already triaged.")
    return
if 'archived' in str(path):
    print("This issue was declined. Reopen it first.")
    return

ROADMAP_ISSUES.mkdir(parents=True, exist_ok=True)
new_path = ROADMAP_ISSUES / path.name
shutil.move(str(path), str(new_path))
```

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/status.py set --file {new_path} --status ready --actor project-issues --project-dir .
```

Confirm: `Triaged {ID} — {title} → roadmap/issues/`

---

## Reopen

Reopen a closed issue. Returns it to the directory it came from: `roadmap/issues/done/` → `roadmap/issues/`, `backlog/archived/` → `backlog/`.

```python
path = find_issue_by_id('<ID>')
fm, body = read_issue_file(path)

# Determine destination
if str(ROADMAP_ISSUES / 'done') in str(path.parent):
    new_path = ROADMAP_ISSUES / path.name
elif '/archived/' in str(path):
    new_path = BACKLOG_BASE / path.name
else:
    new_path = None

# Move file out of done/archived first
if new_path and new_path != path:
    shutil.move(str(path), str(new_path))
    path = new_path

# Clear closure fields
fm['sprint'] = None
fm['closed_date'] = None
fm['superseded_by'] = None
fm['deferred_reason'] = None
write_issue_file(path, fm, body)
```

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/status.py set --file {path} --status new --actor project-issues --project-dir . --reopen
```

Confirm: `Reopened {ID} — returned to {destination}`

---

## Rules

- Never delete an issue. Use `close` (terminal status), `decline` (rejected at triage), or set status=abandoned.
- Issues live in two trees: `backlog/` (untriaged) and `roadmap/issues/` (committed). `triage` moves between them.
- Three lifecycle moves per spec: triage (backlog → roadmap/issues), complete (roadmap/issues → roadmap/issues/done), discard (backlog → backlog/archived).
- `close` only works on triaged issues (in roadmap/issues). Use `decline` for backlog issues.
- 11 valid statuses: new, ready, active, in-review, blocked, on-hold, deferred, done, declined, abandoned, superseded.
- Terminal statuses (done, declined, abandoned, superseded) require `reopen` to reverse.
- Sprint assignment always goes through `update`, not direct write, so sprint history in the body is maintained.
- If `$ARGUMENTS` contains an ID that doesn't look like an issue ID (`ISSUE-NNN`), say: "That doesn't look like an issue ID. IDs take the form ISSUE-NNN."
