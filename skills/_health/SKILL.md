---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Consistency scan and version check."
---

# Health Check

Run the health check script inline. Called when `hook_last_ran` is stale — covers the case where the skill is invoked outside a normal session start.

## Step 1: Run the check

```bash
PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo ".")
SCRIPT=$(find ~/.claude -name "sweetclaude-health-check.sh" 2>/dev/null | head -1)
if [ -z "$SCRIPT" ]; then
  echo "HEALTH_CHECK_SCRIPT_MISSING"
else
  PROJECT_DIR="$PROJECT_DIR" bash "$SCRIPT" 2>/dev/null \
    && echo "HEALTH_CHECK_COMPLETE" \
    || echo "HEALTH_CHECK_FAILED"
fi
```

If `HEALTH_CHECK_SCRIPT_MISSING`:
> "Health check script missing. Run `/sweetclaude:update` to reinstall."
Stop.

## Step 2: Report result to caller

After the script runs, read `.sweetclaude/state/sweetclaude.yaml` and return the updated values to the orchestrator:
- `framework.consistency.status`
- `framework.update.available`

The orchestrator will act on these values in Steps 6 and 7 of its decision tree.

## Step 3: v4 storage lint rules

Run these checks any time health is invoked. Each check is gated as noted. Output findings inline — the caller decides whether to surface them.

```python
import pathlib, yaml, re

BACKLOG_BASE = pathlib.Path('docs/product/backlog')
ROADMAP_BASE = pathlib.Path('docs/product/roadmap')
SC_YAML = pathlib.Path('.sweetclaude/state/sweetclaude.yaml')

lint_findings = []

def read_fm(path):
    try:
        raw = pathlib.Path(path).read_bytes().decode('utf-8').replace('\r\n', '\n')
        parts = raw.split('---', 2)
        return yaml.safe_load(parts[1]) or {}
    except Exception:
        return {}

if BACKLOG_BASE.exists():
    TYPE_DIRS = {'story': 'stories', 'bug': 'bugs', 'debt': 'debt', 'chore': 'chores'}
    TYPE_PREFIX = {'story': 'STORY', 'bug': 'BUG', 'debt': 'DEBT', 'chore': 'CHORE'}

    # Rule 1: No story ID in both backlog and roadmap (gate: skip if roadmap absent)
    if ROADMAP_BASE.exists():
        backlog_ids = set()
        for p in BACKLOG_BASE.rglob('*.md'):
            if p.name in ('INDEX.md', 'MIGRATION-MAP.md'):
                continue
            fm = read_fm(p)
            id_ = fm.get('id')
            if id_:
                backlog_ids.add(id_)
        roadmap_ids = set()
        for p in ROADMAP_BASE.rglob('*.md'):
            fm = read_fm(p)
            id_ = fm.get('id')
            if id_:
                roadmap_ids.add(id_)
        cross = backlog_ids & roadmap_ids
        for id_ in sorted(cross):
            lint_findings.append(f"cross-location-duplicate-id:{id_}")

    # Rule 2: All roadmap stories live in epic dirs (gate: skip if roadmap absent)
    # Phase 2 — defer until EP-009

    # Rule 3: Counter state matches file count
    if (BACKLOG_BASE / 'INDEX.md').exists():
        index_raw = (BACKLOG_BASE / 'INDEX.md').read_text(encoding='utf-8')
        index_parts = index_raw.split('---', 2)
        index_fm = yaml.safe_load(index_parts[1]) or {}
        counters = index_fm.get('counters', {})
        for typ, dir_name in TYPE_DIRS.items():
            prefix = TYPE_PREFIX[typ]
            # Find highest NNN in active + done files
            max_seen = 0
            for p in (BACKLOG_BASE / dir_name).rglob('*.md'):
                m = re.match(rf'^{prefix}-(\d+)-', p.name)
                if m:
                    max_seen = max(max_seen, int(m.group(1)))
            stored = counters.get(typ, 0)
            if max_seen > stored:
                lint_findings.append(f"counter-drift:{typ} (stored={stored}, max_id_seen={max_seen})")

    # Rule 4: No v3 BL-NNN files present
    sc_version = ''
    if SC_YAML.exists():
        try:
            sc_d = yaml.safe_load(SC_YAML.read_text()) or {}
            sc_version = sc_d.get('framework', {}).get('installed_version', '')
        except Exception:
            pass
    v3_files = list(pathlib.Path('.sweetclaude/product/backlog').glob('BL-*.md')) if pathlib.Path('.sweetclaude/product/backlog').exists() else []
    if v3_files and sc_version.startswith('4.'):
        lint_findings.append(f"v3-files-present:{len(v3_files)} BL-NNN files remain under .sweetclaude/product/backlog/. Run /sweetclaude:migrate.")

    # Rule 5: done/ ↔ status invariant
    for typ, dir_name in TYPE_DIRS.items():
        type_dir = BACKLOG_BASE / dir_name
        done_dir = type_dir / 'done'
        # Files in done/ must have status done or abandoned
        if done_dir.exists():
            for p in done_dir.glob('*.md'):
                fm = read_fm(p)
                if fm.get('status') not in ('done', 'abandoned'):
                    lint_findings.append(f"done-status-mismatch:{p.name} is in done/ but has status={fm.get('status')}")
        # Files with done/abandoned status must be in done/
        if type_dir.exists():
            for p in type_dir.glob('*.md'):  # only immediate children, not done/
                fm = read_fm(p)
                if fm.get('status') in ('done', 'abandoned'):
                    lint_findings.append(f"done-status-mismatch:{p.name} has status={fm.get('status')} but is not in done/")

if lint_findings:
    print("## v4 Lint Findings")
    for f in lint_findings:
        print(f"- {f}")
else:
    print("## v4 Lint: OK")
```

Surface any findings to the caller. If invoked from `big-picture` or `project-backlog-triage`, print findings before the skill's normal output.
