#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Tests Gap #1's version-aware decline decision table (bootstrap Step 6).
# Also exercises the health-check hook's hybrid version-discovery in the
# local-clone path (the only deterministic path — gh api and git ls-remote
# require network and are not covered here).

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAILED=0
fail() { echo "  FAIL: $1"; FAILED=$((FAILED + 1)); }
pass() { echo "  PASS: $1"; }

# ---------------------------------------------------------------------------
# Test 1: version-aware decline decision table
# ---------------------------------------------------------------------------

echo "[1] version-aware decline decision"

python3 - << 'PY' && pass "decision table covers all 10 cases including silent_declined" || fail "decision table"
import re, sys

def major(v):
    if not isinstance(v, str): return None
    m = re.match(r"^(\d+)\.", v.lstrip("v"))
    return int(m.group(1)) if m else None

def decide(installed, available, declined):
    if not available:
        return "silent"
    inst_maj, avail_maj = major(installed), major(available)
    if inst_maj is None or avail_maj is None:
        return "prompt"
    if avail_maj > inst_maj:
        return "prompt"
    if declined in (None, False):
        return "prompt"
    declined_maj = inst_maj if declined is True else major(str(declined))
    if declined_maj is None or avail_maj > declined_maj:
        return "prompt"
    return f"silent_declined|{inst_maj}"

cases = [
    ("3.65.0", None,     None,    "silent"),
    ("3.65.0", "3.66.0", None,    "prompt"),
    ("3.65.0", "3.66.0", False,   "prompt"),
    ("3.65.0", "3.66.0", True,    "silent_declined|3"),
    ("3.65.0", "4.0.0",  True,    "prompt"),
    ("3.65.0", "3.66.0", "3.66.0","silent_declined|3"),
    ("3.65.0", "3.67.0", "3.66.0","silent_declined|3"),
    ("3.65.0", "4.0.0",  "3.66.0","prompt"),
    ("4.0.0",  "4.5.0",  "4.0.0", "silent_declined|4"),
    ("4.0.0",  "5.0.0",  "4.0.0", "prompt"),
]
failed = 0
for inst, avail, dec, exp in cases:
    got = decide(inst, avail, dec)
    if got != exp:
        print(f"  CASE FAIL: installed={inst} available={avail} declined={dec!r} got={got} want={exp}", file=sys.stderr)
        failed += 1
sys.exit(failed)
PY

# ---------------------------------------------------------------------------
# Test 2: hook hybrid discovery — local-clone path
# ---------------------------------------------------------------------------

echo "[2] hybrid discovery — local-clone short-circuit"

# This test exercises the Python heredoc that resolves REPO_VERSION inside
# sweetclaude-health-check.sh. We extract the same logic and run it against
# a synthetic fake-HOME containing a sweetclaude-install.json + package.json.

TEST_HOME=$(mktemp -d)
trap "rm -rf $TEST_HOME" EXIT

mkdir -p "$TEST_HOME/.claude/plugins"
# Minimal installed_plugins.json so the hook reads installed version.
cat > "$TEST_HOME/.claude/plugins/installed_plugins.json" << 'JSON'
{"plugins": {"sweetclaude@sweetclaude": [{"installPath": "/nonexistent", "version": "3.65.0"}]}}
JSON

# Fake local dev clone.
mkdir -p "$TEST_HOME/dev/sweetclaude"
cat > "$TEST_HOME/dev/sweetclaude/package.json" << 'JSON'
{"name": "sweetclaude", "version": "9.9.9"}
JSON

# Point the install pointer at the fake clone.
cat > "$TEST_HOME/.claude/sweetclaude-install.json" << JSON
{"repo_path": "$TEST_HOME/dev/sweetclaude"}
JSON

RESULT=$(HOME="$TEST_HOME" python3 - "$TEST_HOME" << 'PY' 2>/dev/null
import json, os, re, subprocess, sys
HOME = sys.argv[1]

# Same logic as the hook's REPO_VERSION resolution.
install_json = os.path.join(HOME, ".claude/sweetclaude-install.json")
if os.path.exists(install_json):
    try:
        d = json.load(open(install_json))
        repo_path = d.get("repo_path", "")
        if repo_path and os.path.exists(os.path.join(repo_path, "package.json")):
            pkg = json.load(open(os.path.join(repo_path, "package.json")))
            v = pkg.get("version", "")
            if v:
                print(v); sys.exit()
    except Exception:
        pass
print("")
PY
)

if [ "$RESULT" = "9.9.9" ]; then
  pass "local clone short-circuits hybrid discovery"
else
  fail "expected 9.9.9, got '$RESULT'"
fi

# ---------------------------------------------------------------------------
# Test 3: hook syntax
# ---------------------------------------------------------------------------

echo "[3] hook script syntax"
bash -n "$REPO_ROOT/hooks/sweetclaude-health-check.sh" \
  && pass "sweetclaude-health-check.sh parses" \
  || fail "sweetclaude-health-check.sh has syntax error"

# ---------------------------------------------------------------------------
# Test 4: update skill Step 0 — clear declined (Gap #8 manual reset)
# ---------------------------------------------------------------------------

echo "[4] update Step 0 — clear declined"

RESET_TMPDIR=$(mktemp -d)
trap "rm -rf $TEST_HOME $RESET_TMPDIR" EXIT

mkdir -p "$RESET_TMPDIR/.sweetclaude/state"
cat > "$RESET_TMPDIR/.sweetclaude/state/sweetclaude.yaml" << 'YAML'
schema_version: 1
framework:
  installed_version: 3.65.0
  update:
    available: 3.66.0
    declined: 3.65.0
YAML

# Same Python snippet the update skill embeds as Step 0.
(
  cd "$RESET_TMPDIR"
  python3 - .sweetclaude/state/sweetclaude.yaml << 'PY'
import sys, yaml, tempfile, os
path = sys.argv[1]
try:
    with open(path) as f: d = yaml.safe_load(f) or {}
except Exception:
    sys.exit(0)
upd = d.setdefault('framework',{}).setdefault('update',{})
if upd.get('declined') not in (None, False):
    upd['declined'] = None
    with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
        yaml.dump(d, tmp, default_flow_style=False, allow_unicode=True, sort_keys=False)
        tmp_name = tmp.name
    os.replace(tmp_name, path)
PY
)

DECLINED=$(python3 -c "
import yaml
d = yaml.safe_load(open('$RESET_TMPDIR/.sweetclaude/state/sweetclaude.yaml')) or {}
print(repr((d.get('framework') or {}).get('update', {}).get('declined')))
")
if [ "$DECLINED" = "None" ]; then
  pass "declined cleared to None after manual reset"
else
  fail "declined not cleared: got $DECLINED"
fi

# ---------------------------------------------------------------------------
# Test 5: runner exposes FAILURE_OUT_OF_SUPPORT_WINDOW (Gap #8)
# ---------------------------------------------------------------------------

echo "[5] runner exposes FAILURE_OUT_OF_SUPPORT_WINDOW"
python3 - "$REPO_ROOT/scripts/migrations" << 'PY' \
  && pass "FAILURE_OUT_OF_SUPPORT_WINDOW importable, equals 'out_of_support_window'" \
  || fail "FAILURE_OUT_OF_SUPPORT_WINDOW constant missing or wrong"
import sys
sys.path.insert(0, sys.argv[1])
import runner
assert hasattr(runner, "FAILURE_OUT_OF_SUPPORT_WINDOW"), "constant missing"
assert runner.FAILURE_OUT_OF_SUPPORT_WINDOW == "out_of_support_window", f"value: {runner.FAILURE_OUT_OF_SUPPORT_WINDOW!r}"
sys.exit(0)
PY

# ---------------------------------------------------------------------------
# Test 6: /sweetclaude:update Step 6b — post-sync drift detection
# ---------------------------------------------------------------------------
# After the framework sync completes, Step 6b runs the registry-driven drift
# scan against the now-installed registry and surfaces a hard demand if the
# project's state files are behind. This test simulates the exact bash from
# Step 6b against a fixture project at sweetclaude.yaml schema_version 1
# while the registry declares current_version: 2.

echo "[6] update Step 6b — post-sync drift detection"

UPD_TMPDIR=$(mktemp -d)
trap "rm -rf $UPD_TMPDIR" EXIT

mkdir -p "$UPD_TMPDIR/.sweetclaude/state"

# A project that just had framework synced to 3.67.0 but never migrated.
cat > "$UPD_TMPDIR/.sweetclaude/state/sweetclaude.yaml" << 'YAML'
schema_version: 1
project:
  name: 'test-project'
  type: existing-code
framework:
  installed_version: 3.67.0
  update:
    available: null
    declined: null
    check_error: null
YAML

# Exercise the runner's --report-drift-for-skill flag — the exact CLI the
# SKILL's Step 6b invokes. This tests both the wire-format output and that
# scan_drift+persist actually fires.
RUNNER="$REPO_ROOT/scripts/migrations/runner.py"
REGISTRY="$REPO_ROOT/config/migration-registry.yaml"
MIGRATIONS_DIR="$REPO_ROOT/scripts/migrations"

DRIFT_OUT=$(cd "$UPD_TMPDIR" && python3 "$RUNNER" --project-dir . \
  --registry "$REGISTRY" --migrations-dir "$MIGRATIONS_DIR" \
  --report-drift-for-skill 2>&1)

echo "$DRIFT_OUT" | grep -q "^DRIFT_COUNT=1$" \
  && pass "Step 6b --report-drift-for-skill reports DRIFT_COUNT=1" \
  || fail "drift count wrong: $DRIFT_OUT"

echo "$DRIFT_OUT" | grep -q "^FINDING|sweetclaude.yaml|v1->v2|chain=ok$" \
  && pass "Step 6b FINDING line is v1->v2 chain=ok" \
  || fail "finding wrong: $DRIFT_OUT"

# Also confirm --persist side effect: drift was written to sweetclaude.yaml.
PERSIST_CHECK=$(python3 -c "
import yaml
d = yaml.safe_load(open('$UPD_TMPDIR/.sweetclaude/state/sweetclaude.yaml')) or {}
print((d.get('framework') or {}).get('drift', {}).get('drift_count', 'missing'))
")
[ "$PERSIST_CHECK" = "1" ] \
  && pass "Step 6b --report-drift-for-skill also persists findings" \
  || fail "persist side-effect missing: drift_count=$PERSIST_CHECK"

# Now simulate the user picking "Migrate now" — invoke the runner the same
# way _migrate does (single-file scope).
(
  cd "$UPD_TMPDIR"
  python3 "$RUNNER" --project-dir . --registry "$REGISTRY" \
    --migrations-dir "$MIGRATIONS_DIR" --file sweetclaude.yaml >/dev/null 2>&1
)

POST=$(python3 -c "
import yaml
d = yaml.safe_load(open('$UPD_TMPDIR/.sweetclaude/state/sweetclaude.yaml')) or {}
print('schema_version=' + str(d.get('schema_version')))
")
echo "$POST" | grep -q "schema_version=2" \
  && pass "Step 6b -> Migrate now path lands at schema_version 2" \
  || fail "post-migrate schema wrong: $POST"

# Re-scan: drift should now be zero.
(
  cd "$UPD_TMPDIR"
  python3 "$RUNNER" --project-dir . --registry "$REGISTRY" \
    --migrations-dir "$MIGRATIONS_DIR" --scan-drift --persist >/dev/null 2>&1
)
POST_DRIFT=$(python3 -c "
import yaml
d = yaml.safe_load(open('$UPD_TMPDIR/.sweetclaude/state/sweetclaude.yaml')) or {}
print((d.get('framework') or {}).get('drift', {}).get('drift_count', 'missing'))
")
[ "$POST_DRIFT" = "0" ] \
  && pass "Step 6b re-scan after migration shows drift_count=0" \
  || fail "post-migrate drift not zero: $POST_DRIFT"

# ---------------------------------------------------------------------------
# Test 7: self-heal of versionless framework path
# ---------------------------------------------------------------------------
# Simulates the v3.67.0 -> v3.68.0 upgrade scenario: the v3.67.0 update
# logic rsyncs scripts/ only into {installPath}/scripts/, never creating
# ~/.claude/scripts/sweetclaude/. The new v3.68.0 skills (bootstrap and
# update) include a self-heal block that backfills the versionless path
# from the plugin cache on first run. This test verifies that block.

echo "[7] self-heal versionless framework path"

SH_TMPDIR=$(mktemp -d)
trap "rm -rf $SH_TMPDIR" EXIT

# Simulated user environment:
#  - $SH_TMPDIR/.claude/plugins/installed_plugins.json  — points to installPath
#  - $SH_TMPDIR/.claude/plugins/cache/.../1.0.0/scripts/  — has framework scripts
#  - $SH_TMPDIR/.claude/scripts/sweetclaude/             — MISSING (this is what self-heal creates)
INSTALL_PATH="$SH_TMPDIR/.claude/plugins/cache/sweetclaude/sweetclaude/1.0.0"
mkdir -p "$INSTALL_PATH/scripts/migrations"
mkdir -p "$SH_TMPDIR/.claude/plugins"
cp "$REPO_ROOT/scripts/migrations/runner.py" "$INSTALL_PATH/scripts/migrations/runner.py"
echo "print('marker-installed-from-plugin-cache')" > "$INSTALL_PATH/scripts/marker.py"
cat > "$SH_TMPDIR/.claude/plugins/installed_plugins.json" << JSON
{
  "version": 2,
  "plugins": {
    "sweetclaude@sweetclaude": [
      {
        "scope": "user",
        "installPath": "$INSTALL_PATH",
        "version": "3.68.0"
      }
    ]
  }
}
JSON

# Pre-condition: versionless path does NOT exist yet.
[ ! -d "$SH_TMPDIR/.claude/scripts/sweetclaude" ] \
  && pass "pre-condition: versionless path absent before self-heal" \
  || fail "pre-condition violated: versionless path already exists"

# Run the exact self-heal block from bootstrap/update with HOME redirected
# to the fake env so installed_plugins.json discovery hits our fixture.
HOME="$SH_TMPDIR" bash -c '
if [ ! -d ~/.claude/scripts/sweetclaude ]; then
  IP=$(python3 -c "import json, os; d = json.load(open(os.path.expanduser(\"~/.claude/plugins/installed_plugins.json\"))); print(d[\"plugins\"].get(\"sweetclaude@sweetclaude\", [{}])[0].get(\"installPath\", \"\"))" 2>/dev/null)
  if [ -n "$IP" ] && [ -d "$IP/scripts" ]; then
    mkdir -p ~/.claude/scripts/sweetclaude
    cp -R "$IP/scripts/"* ~/.claude/scripts/sweetclaude/
  fi
fi
'

# Post-condition: versionless path exists with the expected contents.
[ -f "$SH_TMPDIR/.claude/scripts/sweetclaude/migrations/runner.py" ] \
  && pass "self-heal backfilled runner.py to versionless path" \
  || fail "runner.py not backfilled"

[ -f "$SH_TMPDIR/.claude/scripts/sweetclaude/marker.py" ] \
  && pass "self-heal backfilled non-migrations scripts too" \
  || fail "marker.py not backfilled"

# Idempotency: running again should not error and should not duplicate.
MTIME1=$(stat -f %m "$SH_TMPDIR/.claude/scripts/sweetclaude/migrations/runner.py" 2>/dev/null \
  || stat -c %Y "$SH_TMPDIR/.claude/scripts/sweetclaude/migrations/runner.py")
sleep 1
HOME="$SH_TMPDIR" bash -c '
if [ ! -d ~/.claude/scripts/sweetclaude ]; then
  echo "WOULD COPY"
fi
' > "$SH_TMPDIR/idempotent.out"
MTIME2=$(stat -f %m "$SH_TMPDIR/.claude/scripts/sweetclaude/migrations/runner.py" 2>/dev/null \
  || stat -c %Y "$SH_TMPDIR/.claude/scripts/sweetclaude/migrations/runner.py")

[ "$MTIME1" = "$MTIME2" ] \
  && [ ! -s "$SH_TMPDIR/idempotent.out" ] \
  && pass "self-heal is idempotent (no copy on second run)" \
  || fail "self-heal not idempotent: mtime1=$MTIME1 mtime2=$MTIME2 out=$(cat $SH_TMPDIR/idempotent.out)"

# ---------------------------------------------------------------------------

echo
if [ "$FAILED" -eq 0 ]; then
  echo "ALL TESTS PASSED"
  exit 0
else
  echo "FAILURES: $FAILED"
  exit 1
fi
