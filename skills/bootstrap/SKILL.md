---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Session startup skill — pre-flight checks, drift/update offers, and initial routing."
---


# SweetClaude

Load state, then make a decision. Delegate.

```bash
cat .sweetclaude/state/sweetclaude.yaml 2>/dev/null || echo "SC_YAML_NOT_FOUND"
```

If the output is `SC_YAML_NOT_FOUND`, the state file does not exist. Otherwise parse the output as YAML.

---

## Step 0: Pre-flight

Run the pre-flight helper to resolve runner path, plugin state, and version-dir repair.

```bash
eval "$(bash "${CLAUDE_PLUGIN_ROOT}/scripts/preflight.sh" 2>/dev/null)"
```

`RUNNER` is now set (empty if not found). `VERSION_DIR_HEALED=true` if the install directory was just repaired to a version-named path.

If `VERSION_DIR_HEALED=true`, print exactly this before continuing:

```
SweetClaude install repaired.
─────────────────────────────
Your plugin directory was misaligned with the installed version. It has been
corrected automatically. Please restart Claude Code — your full skill set will
be available in the next session.
```

Then stop. Do not continue past Step 0 in this session — the restart is required for the repair to take effect.

If `SC_PLUGIN_CHANNEL_RETIRED=true`, the installed plugin is on a retired
channel (ISSUE-241: the beta channel is retired; its branch is archived and
its marketplace no longer serves updates). Print this message with the
variables substituted, then stop before any project maintenance, migration,
doctor, setup, or recovery routing:

```
SweetClaude channel retired.
────────────────────────────
Installed plugin: {SC_PLUGIN_KEY}
Installed version: {SC_PLUGIN_VERSION}
Channel: {SC_PLUGIN_CHANNEL} (retired — no further updates)

One-time switch to the {SC_PLUGIN_RETIREMENT_TARGET_CHANNEL} channel — run
these in order so you are never double-installed (both channels' skills and
hooks load at once):

/plugin marketplace add carson-sweet/sweetclaude@main
/plugin install sweetclaude@sweetclaude-stable
/plugin marketplace remove sweetclaude-beta

(Removing the retired marketplace uninstalls its plugin, so add and install
the new channel first.) Then restart Claude Code and run /sweetclaude:configure update;
your project data migrates normally. No project files were changed.
```

Then stop. Do not invoke any project-mutating skill from this retired-channel
stop path.

If `SC_PLUGIN_STALE_BETA=true` (and the retired-channel stop above did not
fire), print this message with the variables substituted, then stop before any project
maintenance, migration, doctor, setup, or recovery routing:

```
SweetClaude beta plugin update required.
──────────────────────────────────────
Installed plugin: {SC_PLUGIN_KEY}
Installed version: {SC_PLUGIN_VERSION}
Minimum safe beta: {SC_PLUGIN_MIN_SAFE_BETA_VERSION}

Run this Claude Code command:
{SC_PLUGIN_UPDATE_COMMAND}

Then restart Claude Code and run:
/sweetclaude:configure update

Stopping here because this installed beta is old enough to have unsafe
update/recovery behavior. No project files were changed.
```

Do not invoke `/sweetclaude:configure update`, `/sweetclaude:configure doctor`,
`/sweetclaude:configure recover`, `/sweetclaude:configure migrate`, `_migrate`, setup, purge, or
any project-mutating skill from this stale-beta stop path.

---

## Step 1: Handle missing or unparseable file

If the pre-loaded content is `SC_YAML_NOT_FOUND`:

```bash
ls .sweetclaude/state/phase.yaml .sweetclaude/state/skills.yaml 2>/dev/null | wc -l
```

- Count > 0 → invoke `sweetclaude:library-load _migrate` then stop (migration tells user to re-run)
- Count = 0 → invoke `sweetclaude:library-load setup` then stop

If the pre-loaded content exists but fails YAML parsing (malformed — check by attempting to interpret it as a YAML structure):
> "Something in my config got scrambled. Let me fix it."
Invoke `sweetclaude:library-load fix-sweetclaude`. Stop.

## Step 2: Schema version check

Read `schema_version` from pre-loaded state.
If `schema_version` is not in `{1, 2}`:
- Invoke `sweetclaude:library-load _migrate --schema-upgrade`
- Stop (migration tells user to re-run)

If `schema_version` is `1`, the registry-driven runner will pick up the v1→v2 migration during the Step 5c drift scan. Bootstrap continues — it does not need to short-circuit here.

## Step 3: Check migration status

Read `framework.migration_status`.
- `in_progress` or `failed` → invoke `sweetclaude:library-load _migrate` (retry). Stop.
- `complete` or `null` → continue.

## Step 4: Stale hook check

Read `framework.hook_last_ran`.
If null or more than 2 hours ago:
- Invoke `sweetclaude:library-load _health` to run checks inline
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
- Invoke `sweetclaude:library-load setup`. Stop.

## Step 5b: Maintenance guard — v3 artifacts and compatibility states

After confirming setup is complete, decide whether the recovery guard needs to
run, in one of two modes:

- **hard-stop** — a v4 plugin is running against a project that hasn't migrated
  yet (project `installed_version` below 4.x, or v3 `BL-*.md` files present).
  Unsafe to continue; the session stops after routing.
- **advisory** — the project is v4 but sits in a compatibility/recovery state
  (`recovery.taxonomy.status: stabilized-without-migration`), or its product
  tree still holds old-taxonomy files (`STORY-`/`BUG-`/`DEBT-`/`CHORE-`)
  despite the state claiming migration is complete. Graduation opportunities,
  blockers, and recoverable states are only visible through the guard, so it
  runs at session start, routes to an action, and the session continues.

Every status the guard can emit has a route below. There are no unrouted
statuses: bootstrap either offers the resolving action or explains honestly
why none exists.

```bash
# Resolve product_base from artifact-privacy.yaml; fall back to .sweetclaude/product
PRODUCT_BASE=$(python3 -c "
import yaml, pathlib
p = pathlib.Path('.sweetclaude/artifact-privacy.yaml')
if p.exists():
    d = yaml.safe_load(p.read_text()) or {}
    base = d.get('categories', {}).get('product', {}).get('base_path', '')
    if base:
        print(base.rstrip('/'))
        exit()
print('.sweetclaude/product')
" 2>/dev/null || echo '.sweetclaude/product')

# Detect v4 plugin: plugin version ≥ 4.x, project installed_version < 4.x
PLUGIN_V=$(python3 -c "
import json, os, re
try:
    d = json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
    entries = [e for versions in d.get('plugins', {}).values()
               for e in versions if e.get('scope') == 'user']
    for e in sorted(entries, key=lambda x: x.get('lastUpdated',''), reverse=True):
        v = e.get('version','')
        if re.match(r'^4\.', v) and 'sweetclaude' in str(e.get('installPath','')).lower():
            print(v)
            break
except Exception:
    pass
" 2>/dev/null)

PROJECT_V=$(python3 -c "
import yaml
d = yaml.safe_load(open('.sweetclaude/state/sweetclaude.yaml')) or {}
print(d.get('framework', {}).get('installed_version', ''))
" 2>/dev/null)

V3_FILES=$(find "${PRODUCT_BASE}/backlog" -maxdepth 1 -name 'BL-*.md' 2>/dev/null | wc -l | tr -d ' ')

PLUGIN_IS_V4=false
case "$PLUGIN_V" in 4.*) PLUGIN_IS_V4=true ;; esac

PROJECT_NOT_V4=false
case "$PROJECT_V" in 4.*) ;; *) PROJECT_NOT_V4=true ;; esac

COMPAT_STATE=$(python3 -c "
import yaml
d = yaml.safe_load(open('.sweetclaude/state/sweetclaude.yaml')) or {}
taxonomy = (d.get('recovery') or {}).get('taxonomy') or {}
print('yes' if taxonomy.get('status') == 'stabilized-without-migration' else 'no')
" 2>/dev/null || echo no)

LEGACY_FILES=$(find "${PRODUCT_BASE}" \( -name 'STORY-*.md' -o -name 'BUG-*.md' -o -name 'DEBT-*.md' -o -name 'CHORE-*.md' \) 2>/dev/null | wc -l | tr -d ' ')

GUARD_MODE=none
if $PLUGIN_IS_V4 && ( $PROJECT_NOT_V4 || [ "$V3_FILES" -gt 0 ] ); then
  GUARD_MODE=hard-stop
elif [ "$COMPAT_STATE" = "yes" ] || [ "$LEGACY_FILES" -gt 0 ]; then
  GUARD_MODE=advisory
fi

GUARD_STATUS=""
if [ "$GUARD_MODE" != "none" ]; then
  SCRIPT=${CLAUDE_PLUGIN_ROOT}/scripts/recovery/recover_project.py
  if [ ! -f "$SCRIPT" ]; then
    SCRIPT=$(find "$(dirname "${CLAUDE_PLUGIN_ROOT}")" -type f -path '*/scripts/recovery/recover_project.py' 2>/dev/null | sort -V | tail -1)
  fi
  if [ -n "$SCRIPT" ] && [ -f "$SCRIPT" ]; then
    GUARD_JSON=$(python3 "$SCRIPT" guard --project-dir . 2>/dev/null)
    GUARD_STATUS=$(printf '%s' "$GUARD_JSON" | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin).get('status', ''))
except Exception:
    pass
" 2>/dev/null)
  fi
  [ -z "$GUARD_STATUS" ] && GUARD_STATUS=guard-unavailable
  echo "GUARD_MODE=$GUARD_MODE"
  echo "GUARD_STATUS=$GUARD_STATUS"
  printf '%s\n' "$GUARD_JSON"
fi
```

If `GUARD_MODE=none`: continue to Step 5c.

Otherwise route on `GUARD_STATUS`. In **hard-stop** mode, stop after routing
(the project must not run normal skills against unmigrated v3 artifacts). In
**advisory** mode, continue to Step 5c after the route resolves or the user
declines.

**`graduation-available`** — the project is v4-compliant and one state-only
write away from leaving compatibility mode. Present via **AskUserQuestion**:

> This project is v4-compliant and can graduate from compatibility mode now.
> Graduation is a state-only write — no work-item files change.

Options:
- **Graduate now (Recommended)** — invoke `sweetclaude:library-load doctor`; its
  maintenance route runs graduation-check and graduates with archive and
  rollback support.
- **Not now** — continue in compatibility mode.

**`graduation-blocked`** — fixable validation blockers stand between this
project and graduation. List each entry from the guard's
`graduation_blockers` array as `- {code}: {detail}`, then present via
**AskUserQuestion**:

> This project could graduate from compatibility mode, but {N} blocker(s)
> must be fixed first. Fixes run through Doctor's executor — archived and
> reversible.

Options:
- **Fix blockers and graduate (Recommended)** — invoke `sweetclaude:library-load doctor`;
  its `graduation-blocked` route resolves each blocker, re-checks, and
  graduates.
- **Not now** — continue in compatibility mode.

**`run-recover`** — a recoverable maintenance state. Present via
**AskUserQuestion**: **Run recovery now (Recommended)** (invoke
`sweetclaude:library-load recover`) or **Not now**. In hard-stop mode, stop after the
choice resolves; do not run normal skills until recovery completes.

**`migration-may-be-needed`** — flat v3 `BL-*.md` items with no recovery
state. Tell the user: "Old-format work items were found. Run
`/sweetclaude:configure migrate` to review the migration — it runs its own preflight
and safety steps." Stop (hard-stop mode only fires here).

**`supported-migration-available`** — a typed legacy backlog layout that can
now be migrated. Tell the user: "This project has a typed legacy backlog
layout. Run `/sweetclaude:configure migrate` to migrate to the unified ISSUE-NNN
taxonomy — it handles typed backlog folders (stories/, bugs/, debt/, chores/)
and creates a rollback snapshot before writing anything." Stop in hard-stop
mode; in advisory mode offer migration or continue.

**`compatibility-mode`** — legacy taxonomy layout that can be migrated.
Print one line: "This project is in compatibility mode. Run
`/sweetclaude:configure migrate` to convert to v4 layout, or `/sweetclaude:configure recover`
to check graduation eligibility." In advisory mode continue the session.

**`manual-review`** — the guard cannot classify the project safely. Print the
guard `message`, then: "Run `/sweetclaude:configure doctor` for a full diagnostic scan —
it can characterize states the guard cannot." Stop in hard-stop mode.

**`missing-product-base`** — `artifact-privacy.yaml` points at a product
directory that does not exist. Print the configured path from the guard
payload and: "Fix the `base_path` in `.sweetclaude/artifact-privacy.yaml` or
restore the directory, then restart. `/sweetclaude:configure doctor` can diagnose
this." Stop in hard-stop mode.

**`guard-unavailable`** — the guard script is missing from the install. Print:
"Recovery guard unavailable — the install is incomplete. Run
`/sweetclaude:configure update` to repair it, then restart." Stop in hard-stop mode.

**`ok`** — nothing to do; continue to Step 5c.

Recommend `/sweetclaude:configure migrate` for statuses `migration-may-be-needed`,
`supported-migration-available`, and `compatibility-mode`.

## Step 5c: Artifact-format drift check (hard demand)

Runs whenever Step 5b did not stop the session (guard mode `none`, or an advisory route that resolved or was declined). Catches steady-state schema drift on projects that are already at v4 but have schema versions behind the registry's current.

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
> - **Migrate now** — invoke `sweetclaude:library-load _migrate` to bring artifacts up to current.
> - **Remove SweetClaude from this project (re-onboarding required to reactivate)** — invoke `sweetclaude:library-load purge`.

**Case B (CASE=B — at least one chain broken, out of 3-major support window):** present via **AskUserQuestion** (single-select):

> "This project's SweetClaude state files are too old for automatic migration (out of framework support window). How would you like to proceed?"
>
> Options:
> - **Re-onboard from scratch** — archive existing SweetClaude content and run `/sweetclaude:configure init` against a fresh state. Your old files stay as reference; init does not auto-import them.
> - **Remove SweetClaude from this project (re-onboarding required to reactivate)** — invoke `sweetclaude:library-load purge`.

### Re-onboarding flow (Case B → Re-onboard from scratch)

Archive `.sweetclaude/` aside through the re-adopt script (reversible, no inline
`mv`), then mirror any relocated artifact bases into the same legacy tree:

```bash
RA=$(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/recovery/re_adopt.py execute --project-dir .)
LEGACY=$(python3 -c "import json,sys;print(json.loads(sys.stdin.read())['legacy_path'])" <<<"$RA")
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/maintenance/archive-sweetclaude-dir.py "$LEGACY"
echo "Archived existing SweetClaude content to $LEGACY/ — init will use it as reference, not auto-migrate."
```

`re_adopt.py execute` moves `.sweetclaude/` into `.sweetclaude.legacy/<timestamp>/`
and reports `legacy_path`; the archive helper then relocates the artifact bases
(e.g. `docs/product`) under that same path.

Then invoke `sweetclaude:library-load init`. Init runs against the now-empty project and
re-onboards the existing source. The legacy tree at
`.sweetclaude.legacy/<timestamp>/` is visible to the user during onboarding so
they can manually port content as needed; init does not auto-import it.

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
- Yes → invoke `sweetclaude:library-load fix-sweetclaude`. Stop.
- No → continue.

Read `framework.update.available`, `framework.update.declined`, and `framework.installed_version` from pre-loaded state. Apply the version-aware decline rule (Gap #1 #8, locked in `scratch/v3-upgrade-assessment-2026-05-11/DECISIONS.md`):

- `available` is null → no offer.
- `available` is a prerelease (`-beta`/`-rc`/`-alpha`) while the installed version is not → no offer, ever (ISSUE-248: stable installs are never prompted with prerelease versions, regardless of what an older hook wrote to state).
- `available` is non-null (minor, patch, or major bump):
  - `declined` is null/missing/false → prompt.
  - `declined` is the boolean `true` (legacy) → treat as if user declined the installed major (silence until next major).
  - `declined` is a version string → prompt only if `major(available) > major(declined)`. Otherwise silent. A decline silences every later release in its own major: installed 4.5.3 with `declined: 5.0.0` stays silent for 5.0.0 and 5.1.0, and prompts again for 6.0.0. An undeclined major bump always prompts.

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

def is_prerelease(v):
    return bool(re.search(r"-(?:beta|rc|alpha)", str(v or ""), re.IGNORECASE))

if not available:
    print("DECISION=silent"); sys.exit()
# ISSUE-248: never prompt a stable install with a prerelease version, no
# matter what an older health-check hook left in framework.update.available.
if is_prerelease(available) and not is_prerelease(installed):
    print("DECISION=silent"); sys.exit()
inst_maj, avail_maj = major(installed), major(available)
if inst_maj is None or avail_maj is None:
    print("DECISION=prompt"); sys.exit()
if declined in (None, False):
    print("DECISION=prompt"); sys.exit()
declined_maj = inst_maj if declined is True else major(str(declined))
if declined_maj is None or avail_maj > declined_maj:
    print("DECISION=prompt"); sys.exit()
# Silenced by decline. Emit the silenced major so the caller can compose
# the user-facing message ("all 3.x.x updates will be skipped").
print(f"DECISION=silent_declined|{max(inst_maj, avail_maj)}")
PY
```

- **DECISION=silent** → no update available; continue silently past this section.
- **DECISION=silent_declined|<major>** → user previously declined an update in this major. Surface a brief informational message so the user is not silently kept in the dark, then continue past this section. The message MUST use the major from the decision output (parameterized — it is not always `3`):

  > "Updates were previously declined by the user, so all <major>.x.x updates will be skipped. Run `/sweetclaude:configure update` to manually update at any time."

  Show this message ONCE per session, then continue to Step 7. Do not pause for input — the user is being informed, not prompted.

- **DECISION=prompt** → present:
  > "SweetClaude [available] is out. Update now? (Yes / Not now)"
  - Yes → invoke `sweetclaude:library-load update`. Stop.
  - Not now → write `declined: <available>` (the specific version declined), continue:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/maintenance/write-decline.py .
```

## Step 6b: Doctor checkup prompt

Check if a doctor checkup prompt is pending:

```bash
DOCTOR_MARKER=".sweetclaude/state/doctor-prompt-pending.json"
if [ -f "$DOCTOR_MARKER" ]; then
  python3 -c "
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print('TRIGGER=' + d.get('trigger', 'unknown'))
except Exception:
    print('TRIGGER=unknown')
" "$DOCTOR_MARKER" 2>/dev/null
fi
```

If the marker exists, present a prompt based on the trigger type via AskUserQuestion:

- **Time trigger** (`TRIGGER=time`): "It's been a while since your last checkup. Want me to run one?"
- **Update trigger** (`TRIGGER=update`): "You just updated SweetClaude — want to run a quick checkup?"
- **Migration trigger** (`TRIGGER=migration`): "Migration just completed — want to run a quick checkup?"
- **Unknown/other** (`TRIGGER=unknown` or any other value): "Want to run a quick checkup?"

Options:
- **Yes** — invoke `sweetclaude:library-load doctor`, then remove the marker file
- **Not now** — remove the marker file (session-scoped suppression; the health-check hook rewrites it next session if the condition still holds)

Remove the marker regardless of choice:

```bash
rm -f "$DOCTOR_MARKER" 2>/dev/null || true
```

If the marker does not exist, continue silently.

---

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

Record a `session_start` event if metrics are enabled:

```bash
_SC_METRICS_CONFIG=".sweetclaude/metrics/config.yaml"
_SC_EVENTS_LOG=".sweetclaude/metrics/events.log"
if [ -f "$_SC_METRICS_CONFIG" ] && grep -q "enabled: true" "$_SC_METRICS_CONFIG" 2>/dev/null; then
  _SC_PHASE=$(python3 -c "
import yaml
d = yaml.safe_load(open('.sweetclaude/state/sweetclaude.yaml')) or {}
print(d.get('work', {}).get('active', {}).get('phase') or 'none')
" 2>/dev/null || echo "none")
  _SC_DEFERENCE=$(python3 -c "
import yaml
d = yaml.safe_load(open('.sweetclaude/state/sweetclaude.yaml')) or {}
print(d.get('session', {}).get('deference_level') or 'unknown')
" 2>/dev/null || echo "unknown")
  _SC_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  printf -- '---\ntimestamp: %s\nevent: session_start\nphase: %s\ndeference: %s\n' \
    "$_SC_TS" "$_SC_PHASE" "$_SC_DEFERENCE" >> "$_SC_EVENTS_LOG"
fi
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

name    = p.get('name') or 'this project'
stage   = p.get('version_stage', '')
sc_ver  = d.get('framework', {}).get('installed_version', '')
active  = w.get('active', {}) or {}
last3   = h[:3]

ver_str = f"SweetClaude {sc_ver} · " if sc_ver else ""
print(f"{ver_str}**{name}** · {stage}")
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
