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

SCRIPT=~/.claude/scripts/sweetclaude/sweetclaude-yaml-template.py
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
**SCAFFOLD:** With user approval, create `.sweetclaude/` structure (including `.sweetclaude/plans/`), generate CLAUDE.md reflecting actual codebase patterns, write `sweetclaude.yaml`. Also configure `plansDirectory`:

```bash
mkdir -p .sweetclaude/plans
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

Handoff: "SweetClaude is set up. Given what I found, here's what I'd suggest tackling first: [top recommendation from DIAGNOSE]."

Run the v4 storage setup (see **v4 Storage Setup** section below), then invoke `sweetclaude:_features`.

## v4 Storage Setup

Run after `sweetclaude.yaml` is written in every branch. Creates the v4 backlog directory tree and writes the initial INDEX.md.

```python
import pathlib, yaml, datetime, tempfile, os

today = datetime.date.today().isoformat()

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
for subdir in ['stories/done', 'bugs/done', 'debt/done', 'chores/done']:
    p = pathlib.Path(f'docs/product/backlog/{subdir}')
    p.mkdir(parents=True, exist_ok=True)
    (p / '.gitkeep').touch()

# 3. Write INDEX.md (skip if already exists to avoid overwriting live data)
index_path = pathlib.Path('docs/product/backlog/INDEX.md')
if not index_path.exists():
    index_content = f"""---
counters:
  story: 0
  bug: 0
  debt: 0
  chore: 0
updated: {today}
---

# Backlog INDEX

This file is the source of truth for backlog counter state and the visible table of unscheduled work.

## Stories
| ID | Title | Status | Priority | Effort | Tags |
|---|---|---|---|---|---|

## Bugs
| ID | Title | Status | Priority | Effort | Tags |
|---|---|---|---|---|---|

## Debt
| ID | Title | Status | Priority | Effort | Tags |
|---|---|---|---|---|---|

## Chores
| ID | Title | Status | Priority | Effort | Tags |
|---|---|---|---|---|---|
"""
    index_path.write_text(index_content, encoding='utf-8')
```

Whether these files end up tracked in the user's git tree depends on the user's `.gitignore`. In this dogfooding repo they are gitignored; the skill is verified against fixture projects for testing.
