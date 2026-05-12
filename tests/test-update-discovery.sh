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

python3 - << 'PY' && pass "decision table covers all 10 cases" || fail "decision table"
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
    return "silent"

cases = [
    ("3.65.0", None,     None,    "silent"),
    ("3.65.0", "3.66.0", None,    "prompt"),
    ("3.65.0", "3.66.0", False,   "prompt"),
    ("3.65.0", "3.66.0", True,    "silent"),
    ("3.65.0", "4.0.0",  True,    "prompt"),
    ("3.65.0", "3.66.0", "3.66.0","silent"),
    ("3.65.0", "3.67.0", "3.66.0","silent"),
    ("3.65.0", "4.0.0",  "3.66.0","prompt"),
    ("4.0.0",  "4.5.0",  "4.0.0", "silent"),
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

echo
if [ "$FAILED" -eq 0 ]; then
  echo "ALL TESTS PASSED"
  exit 0
else
  echo "FAILURES: $FAILED"
  exit 1
fi
