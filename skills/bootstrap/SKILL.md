---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Session startup skill — pre-flight checks, drift/update offers, and initial routing."
---

!`cat .sweetclaude/state/sweetclaude.yaml 2>/dev/null || echo "SC_YAML_NOT_FOUND"`

# SweetClaude

State pre-loaded above. One read. Make a decision. Delegate.

---

## Step 1: Handle missing or unparseable file

If the pre-loaded content is `SC_YAML_NOT_FOUND`:

```bash
ls .sweetclaude/state/phase.yaml .sweetclaude/state/skills.yaml 2>/dev/null | wc -l
```

- Count > 0 → invoke `sweetclaude:_migrate` then stop (migration tells user to re-run)
- Count = 0 → invoke `sweetclaude:setup` then stop

If the pre-loaded content exists but fails YAML parsing (malformed — check by attempting to interpret it as a YAML structure):
> "Something in my config got scrambled. Let me fix it."
Invoke `sweetclaude:fix-sweetclaude`. Stop.

## Step 2: Schema version check

Read `schema_version` from pre-loaded state.
If `schema_version` is not `1`:
- Invoke `sweetclaude:_migrate --schema-upgrade`
- Stop (migration tells user to re-run)

## Step 3: Check migration status

Read `framework.migration_status`.
- `in_progress` or `failed` → invoke `sweetclaude:_migrate` (retry). Stop.
- `complete` or `null` → continue.

## Step 4: Stale hook check

Read `framework.hook_last_ran`.
If null or more than 2 hours ago:
- Invoke `sweetclaude:_health` to run checks inline
- Re-read updated values from file before continuing

To check if stale:
```bash
python3 -c "
import yaml
from datetime import datetime, timezone, timedelta
d = yaml.safe_load(open('.sweetclaude/state/sweetclaude.yaml')) or {}
ts = d.get('framework', {}).get('hook_last_ran')
if not ts:
    print('STALE')
    exit()
try:
    t = datetime.fromisoformat(str(ts).replace('Z','+00:00'))
    stale = (datetime.now(timezone.utc) - t) > timedelta(hours=2)
    print('STALE' if stale else 'FRESH')
except:
    print('STALE')
"
```

## Step 5: Check setup complete

Read `framework.setup_complete`.
If `false`:
- Invoke `sweetclaude:setup`. Stop.

## Step 5b: Artifact-format drift check (hard demand)

Before any other offers, run the registry-driven drift scan. If artifacts are behind the framework version, the user gets a hard binary — there is no defer, no silent proceed.

```bash
# Run the scan and persist the result. The runner ships with the framework.
RUNNER=$(find ~/.claude -name "runner.py" -path "*/migrations/*" 2>/dev/null | head -1)
if [ -n "$RUNNER" ]; then
  python3 "$RUNNER" --project-dir . --scan-drift --persist >/dev/null 2>&1 || true
fi

# Read the persisted findings.
python3 -c "
import yaml
d = yaml.safe_load(open('.sweetclaude/state/sweetclaude.yaml')) or {}
drift = (d.get('framework') or {}).get('drift') or {}
count = drift.get('drift_count', 0)
print(f'DRIFT_COUNT={count}')
if count:
    for f in drift.get('findings', []):
        if f.get('needs_migration'):
            chain = 'broken' if not f.get('chain_valid') else 'ok'
            print(f\"FINDING|{f.get('file_key')}|v{f.get('on_disk_version')}->v{f.get('target_version')}|chain={chain}\")
" 2>/dev/null
```

If `DRIFT_COUNT` is 0: continue to Step 6.

If `DRIFT_COUNT > 0`: the binary prompt depends on whether any finding has `chain=broken`.

**Case A — all findings in window (chain=ok for everything):** present via **AskUserQuestion** (single-select, no "Something else"):

> "This project has artifacts behind the framework version (see findings above). SweetClaude cannot run until you decide."
>
> Options:
> - **Migrate now** — invoke `sweetclaude:_migrate` to bring artifacts up to current.
> - **Remove SweetClaude from this project (re-onboarding required to reactivate)** — invoke `sweetclaude:purge`.

**Case B — at least one finding has `chain=broken` (out of 3-major support window per Gap #8):** present via **AskUserQuestion** (single-select):

> "This project's artifacts are too old for automatic migration — at least one required handler is no longer shipped (3-major support window per Gap #8). SweetClaude cannot run until you decide."
>
> Options:
> - **Re-onboard from scratch** — move existing SweetClaude content to `.sweetclaude.legacy/<timestamp>/` and run `/sweetclaude:adopt` against a fresh state. Your old files stay as reference; adopt does not auto-import them.
> - **Remove SweetClaude from this project (re-onboarding required to reactivate)** — invoke `sweetclaude:purge`.

### Re-onboarding flow (Case B → Re-onboard from scratch)

Execute this block before invoking adopt:

```bash
TS=$(date -u +%Y%m%d-%H%M%S)
LEGACY=".sweetclaude.legacy/$TS"
mkdir -p ".sweetclaude.legacy"

# 1) Move .sweetclaude/ aside.
if [ -d .sweetclaude ]; then
  mv .sweetclaude "$LEGACY"
fi

# 2) Mirror artifact base_paths outside .sweetclaude/ into the legacy tree
#    so adopt can reference them without auto-migrating.
python3 - "$LEGACY" << 'PY'
import os, sys, shutil, yaml
legacy = sys.argv[1]
# Read base_paths from the legacy artifact-privacy.yaml that was just moved aside.
privacy = os.path.join(legacy, "artifact-privacy.yaml")
if not os.path.exists(privacy):
    sys.exit(0)
try:
    d = yaml.safe_load(open(privacy)) or {}
except Exception:
    sys.exit(0)
for cat, entry in (d.get("categories") or {}).items():
    if not isinstance(entry, dict): continue
    base = entry.get("base_path", "")
    if not base or base.startswith(".sweetclaude"):
        continue
    if os.path.exists(base):
        target = os.path.join(legacy, base)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.move(base, target)
PY

echo "Moved existing SweetClaude content to $LEGACY/ — adopt will use it as reference, not auto-migrate."
```

Then invoke `sweetclaude:adopt`. Adopt runs against the now-empty project. The legacy tree at `.sweetclaude.legacy/<timestamp>/` is visible to the user during onboarding so they can manually port content as needed.

There is no "Not now" option in either case. No third path. Stop after the user picks.

Locked in `scratch/v3-upgrade-assessment-2026-05-11/DECISIONS.md` Gaps #7 and #8.

## Step 6: Drift and update offers

Read `framework.consistency.status`.
If `drift_detected`:

```bash
python3 -c "
import yaml
d = yaml.safe_load(open('.sweetclaude/state/sweetclaude.yaml')) or {}
drift = d.get('framework',{}).get('consistency',{}).get('drift',[])
print(', '.join(drift) if drift else 'configuration drift detected')
"
```
> "I found some drift: [drift list]. Fix it now? (Yes / No)"
- Yes → invoke `sweetclaude:fix-sweetclaude`. Stop.
- No → continue.

Read `framework.update.available`, `framework.update.declined`, and `framework.installed_version` from pre-loaded state. Apply the version-aware decline rule (Gap #1 #8, locked in `scratch/v3-upgrade-assessment-2026-05-11/DECISIONS.md`):

- `available` is null → no offer.
- `available` is non-null:
  - Compute `is_major_bump = major(available) > major(installed_version)`.
  - If `is_major_bump` is true → **always prompt**, regardless of `declined`.
  - Else (minor/patch within installed major):
    - `declined` is null/missing/false → prompt.
    - `declined` is the boolean `true` (legacy) → treat as if user declined the installed major (silence until next major).
    - `declined` is a version string → prompt only if `major(available) > major(declined)`. Otherwise silent.

```bash
python3 - .sweetclaude/state/sweetclaude.yaml << 'PY'
import sys, yaml, re
path = sys.argv[1]
with open(path) as f: d = yaml.safe_load(f) or {}
fw = d.get("framework") or {}
installed = (fw.get("installed_version") or "").lstrip("v")
upd = fw.get("update") or {}
available = upd.get("available")
declined = upd.get("declined")

def major(v):
    if not isinstance(v, str): return None
    m = re.match(r"^(\d+)\.", v.lstrip("v"))
    return int(m.group(1)) if m else None

if not available:
    print("DECISION=silent"); sys.exit()
inst_maj, avail_maj = major(installed), major(available)
if inst_maj is None or avail_maj is None:
    print("DECISION=prompt"); sys.exit()
if avail_maj > inst_maj:
    print("DECISION=prompt"); sys.exit()
if declined in (None, False):
    print("DECISION=prompt"); sys.exit()
declined_maj = inst_maj if declined is True else major(str(declined))
if declined_maj is None or avail_maj > declined_maj:
    print("DECISION=prompt"); sys.exit()
print("DECISION=silent")
PY
```

- **DECISION=silent** → continue past this section.
- **DECISION=prompt** → present:
  > "SweetClaude [available] is out. Update now? (Yes / Not now)"
  - Yes → invoke `sweetclaude:update`. Stop.
  - Not now → write `declined: <available>` (the specific version declined), continue:

```bash
python3 - .sweetclaude/state/sweetclaude.yaml << 'PY'
import sys, yaml, tempfile, os
path = sys.argv[1]
with open(path) as f: d = yaml.safe_load(f)
available = (d.get("framework") or {}).get("update", {}).get("available")
d.setdefault('framework',{}).setdefault('update',{})['declined'] = available
with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
    yaml.dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp_name = tmp.name
os.replace(tmp_name, path)
PY
```

## Step 7: Route on args

If `$ARGUMENTS` is present and non-empty:
→ invoke `sweetclaude:_route` with `$ARGUMENTS`
Stop.

## Step 8: All-clear status surface

Read from pre-loaded state:

```bash
python3 - << 'PY'
import yaml, sys
sc_path = '.sweetclaude/state/sweetclaude.yaml'
with open(sc_path) as f:
    d = yaml.safe_load(f) or {}

p = d.get('project', {})
w = d.get('work', {})
h = d.get('work_history', [])

name   = p.get('name') or 'this project'
stage  = p.get('version_stage', '')
active = w.get('active', {}) or {}
last3  = h[:3]

print(f"**{name}** · {stage}")
if active.get('title'):
    print(f"Active: {active['title']} [{active.get('phase','')}]")
elif last3:
    print(f"Last completed: {last3[0].get('title','')} ({last3[0].get('outcome','')})")
else:
    print("No work history yet.")
PY
```

Show the output, then ask:
> "Want to work on something, or review the current plan?"
- "Work on something" → prompt for description → `sweetclaude:_route`
- "Review the plan" → "Roadmap · Backlog · Open work · Bugs — which?"
