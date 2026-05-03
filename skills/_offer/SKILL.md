---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:_offer
user-invocable: false
description: Feature offer loop — surfaces one not_offered feature per session with human-language copy. Writes decision back to sweetclaude.yaml.
---

!`cat .sweetclaude/state/sweetclaude.yaml 2>/dev/null || echo "SC_YAML_NOT_FOUND"`

# Feature Offer

State is pre-loaded above. Read `features` map from it.

## Step 1: Find the first eligible feature

Check features in this order:
`product_milestones` → `product_backlog` → `product_personas` → `product_stories` → `document_corpus` → `usage_tracking` → `behavioral_regression`

For each feature, skip if:
- `status` is `active`, `declined`, or `offered`
- `status` is `deferred` AND `defer_until` is a future timestamp (compare to now)

The first feature where none of the skip conditions apply is the **candidate**.

If no candidate exists, return `NO_OFFER_NEEDED` to the caller — all features are handled.

## Step 2: Surface the offer

Use this copy table — exact wording, no schema field names in user output:

| Feature | Offer |
|---------|-------|
| `product_milestones` | "Want to set up some milestones? They give you a target to aim at and make it easy to see how far you've come." |
| `product_backlog` | "Want to start a backlog? It's the running list of everything you want to build — keeps ideas from falling through the cracks." |
| `product_personas` | "Want to define who your users are? Clear personas make every product decision easier — you'll refer back to them constantly." |
| `product_stories` | "Ready to write user stories? They turn your ideas into concrete, testable behavior — the input to writing code." |
| `document_corpus` | "Want to connect your docs to SweetClaude? I can search and reference them automatically so you don't have to re-explain context." |
| `usage_tracking` | "Want to turn on usage tracking? It helps surface what's working and what's slowing you down." |
| `behavioral_regression` | "Want to wire up behavioral regression testing? It checks that SweetClaude is still following the framework rules after model updates." |

Present the offer, then ask:
> "[Offer copy] (Yes / Not yet / No)"

## Step 3: Write the decision

**"Yes"** — write `status: offered`, then invoke the appropriate setup skill:
- `product_milestones`    → `sweetclaude:product-milestones`
- `product_backlog`       → `sweetclaude:project-backlog`
- `product_personas`      → `sweetclaude:product-user-personas`
- `product_stories`       → `sweetclaude:product-user-stories`
- `document_corpus`       → `sweetclaude:document-corpus`
- `usage_tracking`        → `sweetclaude:usage`
- `behavioral_regression` → `sweetclaude:behavioral-regression`

Write decision:
```bash
python3 - .sweetclaude/state/sweetclaude.yaml FEATURE_KEY offered << 'PY'
import sys, yaml
from datetime import datetime, timezone
path, feature, status = sys.argv[1], sys.argv[2], sys.argv[3]
now = datetime.now(timezone.utc).isoformat(timespec='seconds')
import tempfile, os
with open(path) as f: d = yaml.safe_load(f)
d['features'][feature].update({'status': status, 'offered_at': now, 'decided_at': now})
with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
    yaml.dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp_name = tmp.name
os.replace(tmp_name, path)
PY
```

**"Not yet"** — defer for 7 days:
```bash
python3 - .sweetclaude/state/sweetclaude.yaml FEATURE_KEY << 'PY'
import sys, yaml
from datetime import datetime, timezone, timedelta
import tempfile, os
path, feature = sys.argv[1], sys.argv[2]
now = datetime.now(timezone.utc)
defer = (now + timedelta(days=7)).isoformat(timespec='seconds')
with open(path) as f: d = yaml.safe_load(f)
d['features'][feature].update({'status': 'deferred', 'offered_at': now.isoformat(timespec='seconds'), 'defer_until': defer})
with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
    yaml.dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp_name = tmp.name
os.replace(tmp_name, path)
PY
```

**"No"** — decline permanently:
```bash
python3 - .sweetclaude/state/sweetclaude.yaml FEATURE_KEY << 'PY'
import sys, yaml
from datetime import datetime, timezone
import tempfile, os
path, feature = sys.argv[1], sys.argv[2]
now = datetime.now(timezone.utc).isoformat(timespec='seconds')
with open(path) as f: d = yaml.safe_load(f)
d['features'][feature].update({'status': 'declined', 'offered_at': now, 'decided_at': now})
with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
    yaml.dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp_name = tmp.name
os.replace(tmp_name, path)
PY
```
