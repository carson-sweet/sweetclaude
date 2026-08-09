---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Consolidated onboarding skill."
---



# SweetClaude Setup

Three branches. Detection is automatic.

## Step 0: Detect context

Run:
```bash
ls package.json pyproject.toml go.mod Cargo.toml Makefile 2>/dev/null | head -5
ls src/ lib/ app/ 2>/dev/null | head -5
git log --oneline -3 2>/dev/null || echo "NO_GIT_HISTORY"
find . -name "*.py" -o -name "*.ts" -o -name "*.js" -o -name "*.go" \
  2>/dev/null | grep -v node_modules | grep -v ".sweetclaude" | head -10
du -sh . 2>/dev/null | cut -f1
```

**Decision:**
- No code files, no git history → **Branch A: New Project**
- Code present, project feels organized → **Branch B: Existing Codebase**
- Code present, signs of disorganization (mixed conventions, no clear structure, many TODO/FIXME, large untracked files) → **Branch C: Messy/Inherited**

Signs of Branch C: count of TODO/FIXME/HACK/XXX comments > 20, or no consistent file naming, or zero tests.

## Branch A: New Project

> "Hi — I'm SweetClaude. I'll help you build this project with a structured workflow. Let me ask a couple of quick questions."

Ask one at a time:
1. "What's the project name?"
2. "What are you building? (one sentence)"

Then run:
```bash
mkdir -p .sweetclaude/state .sweetclaude/product/milestones \
         .sweetclaude/product/backlog .sweetclaude/product/stories \
         .sweetclaude/state/archive .sweetclaude/plans

INSTALLED=$(python3 -c "
import json
try:
    d=json.load(open('$HOME/.claude/plugins/installed_plugins.json'))
    e=[v for k,v in d.get('plugins',{}).items() if 'sweetclaude' in k.lower()]
    print(e[0][0].get('version','unknown') if e and e[0] else 'unknown')
except: print('unknown')
" 2>/dev/null)

SCRIPT=${CLAUDE_PLUGIN_ROOT}/scripts/sweetclaude-yaml-template.py
python3 "$SCRIPT" \
  --name "USER_PROVIDED_NAME" \
  --type "new" \
  --version-stage "IDEA" \
  --installed-version "$INSTALLED" \
  --output .sweetclaude/state/sweetclaude.yaml
```

Set `setup_complete: true` and the project name:
```bash
python3 - .sweetclaude/state/sweetclaude.yaml "USER_PROVIDED_NAME" << 'PY'
import sys, yaml, tempfile, os
path, name = sys.argv[1], sys.argv[2]
with open(path) as f: d = yaml.safe_load(f)
d['framework']['setup_complete'] = True
d['project']['name'] = name
with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
    yaml.dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp_name = tmp.name
os.replace(tmp_name, path)
PY
```

Configure the plan directory in project settings:

```bash
python3 - << 'PY'
import json, os, tempfile
os.makedirs('.claude', exist_ok=True)
for path in ['.claude/settings.json', '.claude/settings.local.json']:
    try:
        d = json.load(open(path))
    except:
        d = {}
    if d.get('plansDirectory') != '.sweetclaude/plans':
        d['plansDirectory'] = '.sweetclaude/plans'
        with tempfile.NamedTemporaryFile('w', dir='.claude', suffix='.tmp', delete=False) as tmp:
            json.dump(d, tmp, indent=2)
            tmp_name = tmp.name
        os.replace(tmp_name, path)
PY
```

> "All set. Here's where things stand: [project name] · IDEA stage."

Run the v4 storage setup (see **v4 Storage Setup** section below), then invoke `sweetclaude:_features`.

## Branch B: Existing Codebase

> "Hi — I'm SweetClaude. I'll help bring some structure to this project. Let me take a quick look..."

```bash
ls -la
cat README.md 2>/dev/null | head -20 || echo "No README"
git log --oneline -10 2>/dev/null || echo "No git history"
```

Ask one at a time:
1. "What's the project name?" (pre-fill from package.json/README if found)
2. "What stage is this at? (Early prototype / Active development / Approaching launch / In production)"

Map stage to version_stage:
- Early prototype → IDEA
- Active development → ALPHA
- Approaching launch → BETA
- In production → GA

Run the same directory setup and write as Branch A, with `type: existing-code` and the mapped version_stage.

> "All set. [Project name] is configured. Here's where things stand: [status summary]."

Run the v4 storage setup (see **v4 Storage Setup** section below), then invoke `sweetclaude:_features`.

## Branch C: Messy/Inherited Codebase

> "This looks like an inherited or organically grown codebase. I'll run a full assessment before setting things up — this takes a few minutes but makes everything that follows much smoother."

Run the full ASSESS → DIAGNOSE → PLAN → SCAFFOLD flow for existing codebases. Key phases:

**ASSESS:** Understand what exists — architecture, dependencies, test coverage, naming conventions, tech debt surface area.
**DIAGNOSE:** Identify the highest-impact problems. Prioritize by: broken builds > no tests > no structure > style issues.
**PLAN:** Propose a scaffolding plan. Show the user what will be created/changed before touching anything.
**SCAFFOLD:** With user approval, create `.sweetclaude/` structure, generate CLAUDE.md reflecting actual codebase patterns, write `sweetclaude.yaml`. The plans directory and `plansDirectory` setting are created by the shared **v4 Storage Setup** block below, which every branch runs — they used to be written only here, so projects onboarded through Branch A or B never got them (ISSUE-284).

Handoff: "SweetClaude is set up. Given what I found, here's what I'd suggest tackling first: [top recommendation from DIAGNOSE]."

Run the v4 storage setup (see **v4 Storage Setup** section below), then invoke `sweetclaude:_features`.

## v4 Storage Setup

Run after `sweetclaude.yaml` is written in every branch. Creates the v4 backlog directory tree and builds the initial cache.

```python
import pathlib, yaml, datetime, tempfile, os

today = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')

# 0. Keep recovery snapshots and manifests out of source control
gitignore_path = pathlib.Path('.gitignore')
ignore_entry = '.sweetclaude/state/recovery-runs/'
ignore_comment = '# SweetClaude recovery snapshots and manifests'
existing_lines = gitignore_path.read_text().splitlines() if gitignore_path.exists() else []
if ignore_entry not in existing_lines:
    with gitignore_path.open('a', encoding='utf-8') as f:
        if existing_lines and existing_lines[-1] != '':
            f.write('\n')
        f.write(f'{ignore_comment}\n{ignore_entry}\n')

# 1. Write artifact-privacy.yaml with v4 base_path
privacy_path = pathlib.Path('.sweetclaude/state/artifact-privacy.yaml')
privacy_path.parent.mkdir(parents=True, exist_ok=True)
if privacy_path.exists():
    d = yaml.safe_load(privacy_path.read_text()) or {}
else:
    d = {}
d.setdefault('categories', {}).setdefault('product', {})['base_path'] = 'docs/product'
with tempfile.NamedTemporaryFile('w', dir=str(privacy_path.parent), suffix='.tmp', delete=False) as tmp:
    yaml.safe_dump(d, tmp, default_flow_style=False, sort_keys=False)
    tmp_name = tmp.name
os.replace(tmp_name, str(privacy_path))

# 2. Create backlog directory tree
for subdir in ['backlog/done', 'roadmap/epics/done', 'roadmap/milestones', 'roadmap/issues/done']:
    p = pathlib.Path(f'.sweetclaude/product/{subdir}')
    p.mkdir(parents=True, exist_ok=True)
    (p / '.gitkeep').touch()

# 3. Create the traceability tree that code and docs skills append to
traceability = pathlib.Path('.sweetclaude/traceability')
traceability.mkdir(parents=True, exist_ok=True)
for name, header in [
    ('requirements-map.md', '# Requirements Traceability Map\n\n| Requirement | User Story | Test | Status |\n|---|---|---|---|\n'),
    ('ripple-map.md', '# Ripple Map\n\n| Change | Affected areas | Risk level |\n|---|---|---|\n'),
]:
    p = traceability / name
    if not p.exists():
        p.write_text(header, encoding='utf-8')

# 4. Create the plans directory and point Claude Code at it
import json
plans = pathlib.Path('.sweetclaude/plans')
plans.mkdir(parents=True, exist_ok=True)
pathlib.Path('.claude').mkdir(exist_ok=True)
for path in ['.claude/settings.json', '.claude/settings.local.json']:
    try:
        d = json.loads(pathlib.Path(path).read_text())
    except Exception:
        d = {}
    if d.get('plansDirectory') != '.sweetclaude/plans':
        d['plansDirectory'] = '.sweetclaude/plans'
        with tempfile.NamedTemporaryFile('w', dir='.claude', suffix='.tmp', delete=False) as tmp:
            json.dump(d, tmp, indent=2)
            tmp_name = tmp.name
        os.replace(tmp_name, path)

# 5. Build initial cache (INDEX.md is no longer created — cache provides all views)
import subprocess, os
subprocess.run(['python3', os.path.expanduser('${CLAUDE_PLUGIN_ROOT}/scripts/cache.py'), '--project-dir', '.', '--rebuild'], capture_output=True)

# 6. Generate session state last, once everything it snapshots exists.
# session-preflight.sh regenerates this every session, so skipping it here only
# ever left one doctor warning in the window before the next session — but it
# was a regression from init's old Step 8 and nothing caught it (ISSUE-284).
subprocess.run(['bash', os.path.expanduser('${CLAUDE_PLUGIN_ROOT}/hooks/generate-session-state.sh')], capture_output=True)
```

The session-state generator resolves the project root with `git rev-parse`. In a
directory that is not a git repository it exits without writing, and the file is
created at the first session instead.

Whether these files end up tracked in the user's git tree depends on the user's `.gitignore`. In this dogfooding repo they are gitignored; the skill is verified against fixture projects for testing.
