---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Feature configuration — shows all optional SweetClaude features with descriptions and current status, lets the user enable or disable them."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:_features" 2>/dev/null || true`

# Feature Configuration

## Step 1: Read current state

```bash
python3 - << 'PY'
import yaml, os

sc_path = '.sweetclaude/state/sweetclaude.yaml'
try:
    with open(sc_path) as f:
        d = yaml.safe_load(f) or {}
except:
    d = {}

features = d.get('features', {})

def get_status(key):
    v = features.get(key)
    if isinstance(v, dict):
        return v.get('status', 'not_configured')
    return 'not_configured'

statuses = {k: get_status(k) for k in [
    'product_milestones', 'product_backlog', 'product_personas',
    'product_stories', 'document_corpus', 'usage_tracking', 'behavioral_regression',
]}

# usage_tracking: ground truth is the metrics config file, not just the yaml status
try:
    mc = yaml.safe_load(open('.sweetclaude/metrics/config.yaml'))
    if mc.get('enabled', False):
        statuses['usage_tracking'] = 'active'
except:
    pass

enabled = sum(1 for s in statuses.values() if s == 'active')
total = len(statuses)
all_unconfigured = all(s not in ('active', 'declined') for s in statuses.values())

print(f"ENABLED:{enabled}")
print(f"TOTAL:{total}")
print(f"FIRST_TIME:{str(all_unconfigured).upper()}")
for k, s in statuses.items():
    print(f"{k}:{s}")
PY
```

## Step 2: Present features and collect choices

Use this table for all feature labels and descriptions:

| Key | Label | Description |
|---|---|---|
| `product_milestones` | Product milestones | Milestone tracking — set concrete targets and see progress toward them |
| `product_backlog` | Product backlog | Running list of everything to build — keeps ideas from falling through the cracks |
| `product_personas` | User personas | Define your target users — clearer personas make every product decision easier |
| `product_stories` | User stories | Turn ideas into testable acceptance criteria — the direct input to TDD and code |
| `document_corpus` | Document corpus | Connect your docs for automatic reference — SweetClaude searches them so you don't re-explain context |
| `usage_tracking` | Usage tracking | Local metrics: skill usage, phase gate outcomes, TDD enforcement — stored in `.sweetclaude/metrics/`, committed with the project, no external services |
| `behavioral_regression` | Behavioral regression | Verify SweetClaude follows framework rules after model updates — catches regressions in Claude's behavior |

If `FIRST_TIME` is `TRUE`:
> "SweetClaude has optional features — here's what's available. Select the ones you want enabled:"

Otherwise:
> "This project has {ENABLED} of {TOTAL} features enabled. Select all the features you want on — including any already enabled:"

Use **AskUserQuestion** (multiSelect: true) with all 7 features as options:
- **label**: the feature label — append " ✓" if the feature's current status is `active`
- **description**: the feature description from the table above

## Step 3: Write decisions

Compute the final state from the user's selections:
- Selected → `active`
- Not selected → `declined`

Track which features are **newly enabled** (selected AND were not previously `active`) — those need onboarding in Step 4.

Write all decisions in one atomic update:

```bash
python3 - .sweetclaude/state/sweetclaude.yaml KEY STATUS [KEY STATUS ...] << 'PY'
import sys, yaml, tempfile, os
from datetime import datetime, timezone

path = sys.argv[1]
pairs = sys.argv[2:]
now = datetime.now(timezone.utc).isoformat(timespec='seconds')

with open(path) as f:
    d = yaml.safe_load(f) or {}

features = d.setdefault('features', {})
it = iter(pairs)
for key, status in zip(it, it):
    if not isinstance(features.get(key), dict):
        features[key] = {}
    features[key].update({'status': status, 'decided_at': now})

with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
    yaml.dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp_name = tmp.name
os.replace(tmp_name, path)
print('OK')
PY
```

## Step 4: Onboard newly-enabled features

For each feature that is newly enabled (was not previously `active`), invoke its onboarding action. Complete each before starting the next.

| Feature key | Action |
|---|---|
| `product_milestones` | invoke `sweetclaude:product-milestones` with argument `onboard` |
| `product_backlog` | invoke `sweetclaude:project-backlog` with argument `onboard` |
| `product_personas` | invoke `sweetclaude:user-personas` with argument `onboard` |
| `product_stories` | invoke `sweetclaude:product-user-stories` with argument `onboard` |
| `document_corpus` | invoke `sweetclaude:document-corpus` with argument `onboard` |
| `usage_tracking` | invoke `sweetclaude:usage on` |
| `behavioral_regression` | invoke `sweetclaude:behavioral-regression` |

If no features are newly enabled, say: "Feature configuration saved." and stop.
