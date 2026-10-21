#!/usr/bin/env bash
# wip-limit.sh — PreToolUse hook on Bash
# Blocks IMPLEMENT entry in Kanban mode when WIP limit is reached.
# Allows silently or denies through PreToolUse permissionDecision.

set -euo pipefail

HOOK_IO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/hook_io.py"
PROJECT_DIR=$(python3 "$HOOK_IO" project-dir)
EFFECTIVE_GATES="$PROJECT_DIR/.sweetclaude/state/effective-gates.yaml"
PHASE_YAML="$PROJECT_DIR/.sweetclaude/state/phase.yaml"
SC_YAML="$PROJECT_DIR/.sweetclaude/state/sweetclaude.yaml"

allow()  { exit 0; }
block() { python3 "$HOOK_IO" deny "$1"; exit 0; }

[ -f "$EFFECTIVE_GATES" ] || allow

mode=$(python3 -c "
import yaml
with open('$EFFECTIVE_GATES') as f: d=yaml.safe_load(f)
print(d.get('mode','flow'))
" 2>/dev/null) || allow

[ "$mode" = "kanban" ] || allow

# Phase lives at work.active.phase in sweetclaude.yaml. phase.yaml is a mirror
# the story controllers write lazily and onboarding never creates, so gating on
# it disabled this hook entirely on v4 projects (ISSUE-281).
phase=$(SC_YAML="$SC_YAML" PHASE_YAML="$PHASE_YAML" python3 - <<'PYEOF' 2>/dev/null || echo ""
import os, yaml

def load(path):
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

sc = load(os.environ.get("SC_YAML", ""))
phase = ((sc.get("work") or {}).get("active") or {}).get("phase")
if not phase:
    phase = load(os.environ.get("PHASE_YAML", "")).get("phase")
print(phase or "")
PYEOF
)

[ "$phase" = "IMPLEMENT" ] || allow

wip_limit=$(python3 -c "
import yaml
with open('$EFFECTIVE_GATES') as f: d=yaml.safe_load(f)
print(d.get('wip_limit', 3))
" 2>/dev/null) || allow

in_progress=$(python3 -c "
import yaml, os, glob
d = '$PROJECT_DIR/.sweetclaude/artifacts/issues'
if not os.path.exists(d):
    print(0); exit()
count = sum(
    1 for f in glob.glob(os.path.join(d,'*.yaml'))
    if (yaml.safe_load(open(f)) or {}).get('status') == 'in_progress'
)
print(count)
" 2>/dev/null) || allow

if [ "$in_progress" -ge "$wip_limit" ]; then
    block "WIP limit reached ($in_progress/$wip_limit items in_progress). Complete or move an item before starting new work."
else
    allow
fi
