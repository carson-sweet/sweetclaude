---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Session startup skill — pre-flight checks, drift/update offers, and initial routing."
---

!`cat .sweetclaude/state/sweetclaude.yaml 2>/dev/null || echo "SC_YAML_NOT_FOUND"`

# SweetClaude

State pre-loaded above. One read. Make a decision. Delegate.

---

## Step 0: Pre-flight

Ensure the versionless framework path is populated, then run the pre-flight helper.

```bash
if [ ! -f ~/.claude/scripts/sweetclaude/preflight.sh ]; then
  IP=$(python3 -c "
import json, os
try:
    d = json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
    entries = [e for versions in d.get('plugins', {}).values()
               for e in versions if e.get('scope') == 'user']
    entries.sort(key=lambda e: e.get('lastUpdated', ''), reverse=True)
    for e in entries:
        ip = e.get('installPath', '')
        if ip and os.path.isdir(os.path.join(ip, 'scripts')):
            print(ip)
            break
except Exception:
    pass
" 2>/dev/null)
  if [ -n "$IP" ] && [ -d "$IP/scripts" ]; then
    mkdir -p ~/.claude/scripts/sweetclaude
    rsync -a "$IP/scripts/" ~/.claude/scripts/sweetclaude/ 2>/dev/null || true
  fi
fi
eval "$(bash ~/.claude/scripts/sweetclaude/preflight.sh 2>/dev/null)"
```

`RUNNER` is now set (empty if not found). `SELF_HEAL=true` if the versionless path was just populated.

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
If `schema_version` is not in `{1, 2}`:
- Invoke `sweetclaude:_migrate --schema-upgrade`
- Stop (migration tells user to re-run)

If `schema_version` is `1`, the registry-driven runner will pick up the v1→v2 migration during the Step 5b drift scan. Bootstrap continues — it does not need to short-circuit here.

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

The drift-gate.sh SessionStart hook has already scanned for drift and written the marker if any was found. Read the marker first; if it exists, use it as the source of truth (drift-gate's scan is authoritative for the session). If the marker is absent (drift-gate didn't run, e.g. versionless path was just self-healed in Step 0), run the runner inline and parse its stdout directly — do NOT rely on the runner writing the marker (it only writes to stdout via `--report-drift-for-skill`).

```bash
DRIFT_MARKER=".sweetclaude/state/pending-drift-decision.yaml"
DRIFT_COUNT=0
CASE=A
if [ -f "$DRIFT_MARKER" ]; then
  EXISTING=$(python3 -c "
import yaml, sys
try:
    d = yaml.safe_load(open(sys.argv[1])) or {}
    print(d.get('case', 'A'))
    print(d.get('drift_count', 0))
except Exception:
    print('A')
    print(0)
" "$DRIFT_MARKER" 2>/dev/null)
  CASE=$(printf '%s\n' "$EXISTING" | sed -n '1p')
  DRIFT_COUNT=$(printf '%s\n' "$EXISTING" | sed -n '2p')
elif [ -n "$RUNNER" ] && [ -f "$RUNNER" ]; then
  DRIFT_OUTPUT=$(python3 "$RUNNER" --project-dir . --report-drift-for-skill 2>/dev/null)
  DRIFT_COUNT=$(printf '%s\n' "$DRIFT_OUTPUT" | grep '^DRIFT_COUNT=' | cut -d= -f2)
  [ -z "$DRIFT_COUNT" ] && DRIFT_COUNT=0
  if printf '%s\n' "$DRIFT_OUTPUT" | grep -q '|chain=broken'; then
    CASE=B
  fi
fi
echo "CASE=$CASE"
echo "DRIFT_COUNT=$DRIFT_COUNT"
```

If `DRIFT_COUNT` is 0: continue to Step 6.

If `DRIFT_COUNT > 0`: the binary prompt depends on `CASE`.

**Case A (CASE=A — all chains ok):** present via **AskUserQuestion** (single-select, no "Something else"):

> "{DRIFT_COUNT} SweetClaude state file(s) in this project need migration before SweetClaude can continue. Would you like to do this now?"
>
> Options:
> - **Migrate now** — invoke `sweetclaude:_migrate` to bring artifacts up to current.
> - **Remove SweetClaude from this project (re-onboarding required to reactivate)** — invoke `sweetclaude:purge`.

**Case B (CASE=B — at least one chain broken, out of 3-major support window):** present via **AskUserQuestion** (single-select):

> "This project's SweetClaude state files are too old for automatic migration (out of framework support window). How would you like to proceed?"
>
> Options:
> - **Re-onboard from scratch** — archive existing SweetClaude content and run `/sweetclaude:adopt` against a fresh state. Your old files stay as reference; adopt does not auto-import them.
> - **Remove SweetClaude from this project (re-onboarding required to reactivate)** — invoke `sweetclaude:purge`.

### Re-onboarding flow (Case B → Re-onboard from scratch)

```bash
TS=$(date -u +%Y%m%d-%H%M%S)
LEGACY=".sweetclaude.legacy/$TS"
mkdir -p ".sweetclaude.legacy"
if [ -d .sweetclaude ]; then
  mv .sweetclaude "$LEGACY"
fi
python3 ~/.claude/scripts/sweetclaude/maintenance/archive-sweetclaude-dir.py "$LEGACY"
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
# Silenced by decline. Emit the installed major so the caller can compose
# the user-facing message ("all 3.x.x updates will be skipped").
print(f"DECISION=silent_declined|{inst_maj}")
PY
```

- **DECISION=silent** → no update available; continue silently past this section.
- **DECISION=silent_declined|<major>** → user previously declined a minor in this major. Surface a brief informational message so the user is not silently kept in the dark, then continue past this section. The message MUST use the major from the decision output (parameterized — it is not always `3`):

  > "Minor updates were previously declined by the user, so all <major>.x.x updates will be skipped. Run `/sweetclaude:update` to manually update at any time."

  Show this message ONCE per session, then continue to Step 7. Do not pause for input — the user is being informed, not prompted.

- **DECISION=prompt** → present:
  > "SweetClaude [available] is out. Update now? (Yes / Not now)"
  - Yes → invoke `sweetclaude:update`. Stop.
  - Not now → write `declined: <available>` (the specific version declined), continue:

```bash
python3 ~/.claude/scripts/sweetclaude/maintenance/write-decline.py .
```

## Step 7: Route on args

If `$ARGUMENTS` is present and non-empty:
→ invoke `sweetclaude:_route` with `$ARGUMENTS`
Stop.

## Step 8: All-clear status surface

Set the bootstrap-ran session flag so the master-preflight hook knows bootstrap has completed this session:

```bash
_SC_PROJ=$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")
_SC_HASH=$(printf '%s' "$_SC_PROJ" | md5 2>/dev/null \
  || printf '%s' "$_SC_PROJ" | md5sum 2>/dev/null | cut -d' ' -f1)
touch "/tmp/.sweetclaude-bootstrap-ran-${_SC_HASH}"
```

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
