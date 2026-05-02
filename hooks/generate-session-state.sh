#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude Session State Generator
# Builds .sweetclaude/state/session-state.yaml from constituent state files.
# Called by: session-preflight.sh (sync at startup), state-regenerator.sh (background after writes)

PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -z "$PROJECT_DIR" ]; then exit 0; fi

PHASE_YAML="$PROJECT_DIR/.sweetclaude/state/phase.yaml"
if [ ! -f "$PHASE_YAML" ]; then exit 0; fi

OUTPUT="$PROJECT_DIR/.sweetclaude/state/session-state.yaml"

export PROJECT_DIR

python3 - > "$OUTPUT" 2>/dev/null <<'PYEOF'
import yaml, os
from datetime import datetime, timezone

project_dir = os.environ['PROJECT_DIR']
state_dir = os.path.join(project_dir, '.sweetclaude', 'state')

with open(os.path.join(state_dir, 'phase.yaml')) as f:
    phase = yaml.safe_load(f) or {}

# Count improvement register table rows (skip header and separator lines)
reg_count = 0
reg_path = os.path.join(state_dir, 'improvement-register.md')
if os.path.exists(reg_path):
    with open(reg_path) as f:
        lines = f.readlines()
    reg_count = sum(1 for l in lines
                    if l.strip().startswith('|')
                    and not l.strip().startswith('| #')
                    and '---' not in l)

# Last Next: line from checkpoint
checkpoint_next = None
cp_path = os.path.join(state_dir, 'checkpoint.md')
if os.path.exists(cp_path):
    with open(cp_path) as f:
        next_lines = [l for l in f.readlines() if l.strip().startswith('Next:')]
    if next_lines:
        checkpoint_next = next_lines[-1].replace('Next:', '').strip()

# Resolved artifact paths
product_base = '.sweetclaude/product'
strategy_base = '.sweetclaude/strategy'
privacy_path = os.path.join(project_dir, '.sweetclaude', 'artifact-privacy.yaml')
if os.path.exists(privacy_path):
    with open(privacy_path) as f:
        privacy = yaml.safe_load(f) or {}
    cats = privacy.get('categories', {})
    product_base = cats.get('product', {}).get('base_path', product_base)
    strategy_base = cats.get('strategy', {}).get('base_path', strategy_base)

# First active milestone
active_milestone = None
milestones_dir = os.path.join(project_dir, product_base, 'milestones')
if os.path.exists(milestones_dir):
    for fn in sorted(os.listdir(milestones_dir)):
        if fn.startswith('MS-') and fn.endswith('.md'):
            with open(os.path.join(milestones_dir, fn)) as f:
                if '**Status:** active' in f.read():
                    active_milestone = fn[:-3]
                    break

awi = phase.get('active_work_item') or {}

result = {
    'schema_version': 1,
    'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    'project_name': phase.get('project_name', ''),
    'version_stage': phase.get('version_stage', ''),
    'deference': phase.get('deference_level', ''),
    'active_work_item': {
        'id': awi.get('id'),
        'title': awi.get('title'),
        'type': awi.get('type'),
        'phase': awi.get('phase'),
    },
    'active_milestone': active_milestone,
    'improvement_register_count': reg_count,
    'checkpoint_next': checkpoint_next,
    'paths': {
        'product_base': product_base,
        'strategy_base': strategy_base,
    },
}

print(yaml.dump(result, default_flow_style=False, sort_keys=False), end='')
PYEOF
