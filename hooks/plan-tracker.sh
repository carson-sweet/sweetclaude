#!/usr/bin/env bash
# PostToolUse/ExitPlanMode — records active plan context to .sweetclaude/state/active-plan.txt

set -euo pipefail

STATE_DIR=".sweetclaude/state"
PLANS_DIR=".sweetclaude/plans"
POINTER="$STATE_DIR/active-plan.txt"

[ -f "$STATE_DIR/sweetclaude.yaml" ] || exit 0
[ -d "$PLANS_DIR" ] || exit 0

PLAN_FILE=$(ls -t "$PLANS_DIR"/*.md 2>/dev/null | head -1 || true)
[ -z "$PLAN_FILE" ] && exit 0

SPRINT=$(python3 -c "
import glob, yaml, os
for f in sorted(glob.glob('.sweetclaude/product/sprints/*.yaml') + glob.glob('.sweetclaude/artifacts/sprints/*.yaml')):
    try:
        d = yaml.safe_load(open(f)) or {}
        if d.get('status') == 'active':
            print(d.get('name') or os.path.basename(f).replace('.yaml',''))
            break
    except: pass
" 2>/dev/null || true)

MILESTONE=$(python3 -c "
import glob, re, os, yaml
product_base = '.sweetclaude/product'
try:
    d = yaml.safe_load(open('.sweetclaude/state/session-state.yaml')) or {}
    product_base = d.get('paths', {}).get('product_base', product_base)
except: pass
for f in sorted(glob.glob(os.path.join(product_base, 'milestones', 'MS-*.md'))):
    try:
        c = open(f).read()
        m = re.search(r'\*\*Status:\*\*\s*(\w+)', c)
        if m and m.group(1).lower() not in ('achieved', 'done', 'complete'):
            h = re.search(r'^# (.+)', c, re.MULTILINE)
            stem = os.path.basename(f).replace('.md','')
            print(h.group(1).strip() if h else stem)
            break
    except: pass
" 2>/dev/null || true)

{
    echo "plan: $PLAN_FILE"
    echo "recorded_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    [ -n "$SPRINT" ]    && echo "sprint: $SPRINT"
    [ -n "$MILESTONE" ] && echo "milestone: $MILESTONE"
} > "$POINTER"
