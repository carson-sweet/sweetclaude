---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:setup
user-invocable: false
description: Consolidated setup skill — absorbs sweetclaude:on and sweetclaude:adopt. Detects project context and runs the appropriate onboarding branch. Called by /sweetclaude when setup_complete = false.
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
         .sweetclaude/state/archive

INSTALLED=$(python3 -c "
import json
try:
    d=json.load(open('$HOME/.claude/plugins/installed_plugins.json'))
    e=[v for k,v in d.get('plugins',{}).items() if 'sweetclaude' in k.lower()]
    print(e[0][0].get('version','unknown') if e and e[0] else 'unknown')
except: print('unknown')
" 2>/dev/null)

SCRIPT=$(find ~/.claude -name "sweetclaude-yaml-template.py" 2>/dev/null | head -1)
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

> "All set. Here's where things stand: [project name] · IDEA stage. What do you want to work on first?"

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

> "All set. [Project name] is configured. Here's where things stand: [status summary]. What do you want to work on first?"

## Branch C: Messy/Inherited Codebase

> "This looks like an inherited or organically grown codebase. I'll run a full assessment before setting things up — this takes a few minutes but makes everything that follows much smoother."

Run the full ASSESS → DIAGNOSE → PLAN → SCAFFOLD flow from the original `sweetclaude:adopt` skill. Key phases:

**ASSESS:** Understand what exists — architecture, dependencies, test coverage, naming conventions, tech debt surface area.
**DIAGNOSE:** Identify the highest-impact problems. Prioritize by: broken builds > no tests > no structure > style issues.
**PLAN:** Propose a scaffolding plan. Show the user what will be created/changed before touching anything.
**SCAFFOLD:** With user approval, create `.sweetclaude/` structure, generate CLAUDE.md reflecting actual codebase patterns, write `sweetclaude.yaml`.

Handoff: "SweetClaude is set up. Given what I found, here's what I'd suggest tackling first: [top recommendation from DIAGNOSE]."
