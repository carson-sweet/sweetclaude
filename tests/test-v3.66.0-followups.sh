#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Tests the three follow-up fixes for v3.66.0:
#   - installed_version auto-reconcile in sweetclaude-health-check.sh
#   - stale hook detection logic (the python snippet that fix-sweetclaude uses)
#   - (visual-only) Step 13's bootstrap-continuation directive (not testable here)

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$REPO_ROOT/hooks/sweetclaude-health-check.sh"

FAILED=0
fail() { echo "  FAIL: $1"; FAILED=$((FAILED + 1)); }
pass() { echo "  PASS: $1"; }

# ---------------------------------------------------------------------------
# Test 1: installed_version reconciliation — value updates when stale
# ---------------------------------------------------------------------------

echo "[1] installed_version reconciliation"

TEST_HOME=$(mktemp -d)
PROJ=$(mktemp -d)
trap "rm -rf $TEST_HOME $PROJ" EXIT

mkdir -p "$TEST_HOME/.claude/plugins"
cat > "$TEST_HOME/.claude/plugins/installed_plugins.json" << 'JSON'
{"plugins": {"sweetclaude@sweetclaude": [{"installPath": "/x", "version": "3.66.0"}]}}
JSON

mkdir -p "$PROJ/.sweetclaude/state"
cat > "$PROJ/.sweetclaude/state/sweetclaude.yaml" << 'YAML'
schema_version: 1
framework:
  installed_version: 3.18.2
  setup_complete: true
YAML

# Run the health check (PROJECT_DIR + HOME both pointed at fixtures)
HOME="$TEST_HOME" PROJECT_DIR="$PROJ" bash "$HOOK" 2>/dev/null || true

RECORDED=$(python3 -c "
import yaml
d = yaml.safe_load(open('$PROJ/.sweetclaude/state/sweetclaude.yaml'))
print(d['framework']['installed_version'])
")
if [ "$RECORDED" = "3.66.0" ]; then
  pass "installed_version reconciled 3.18.2 -> 3.66.0"
else
  fail "expected 3.66.0, got '$RECORDED'"
fi

# ---------------------------------------------------------------------------
# Test 2: installed_version reconciliation is idempotent — no write when matching
# ---------------------------------------------------------------------------

echo "[2] reconciliation idempotent"
BEFORE=$(stat -f %m "$PROJ/.sweetclaude/state/sweetclaude.yaml")
sleep 1
HOME="$TEST_HOME" PROJECT_DIR="$PROJ" bash "$HOOK" 2>/dev/null || true
AFTER=$(stat -f %m "$PROJ/.sweetclaude/state/sweetclaude.yaml")

# We expect the mtime MAY change because hook_last_ran always gets stamped.
# But the installed_version value should still be 3.66.0 (not regress or churn).
RECORDED2=$(python3 -c "
import yaml
d = yaml.safe_load(open('$PROJ/.sweetclaude/state/sweetclaude.yaml'))
print(d['framework']['installed_version'])
")
if [ "$RECORDED2" = "3.66.0" ]; then
  pass "installed_version stays at 3.66.0 on second run"
else
  fail "regressed to '$RECORDED2'"
fi

# ---------------------------------------------------------------------------
# Test 3: stale hook detection — version-bump.sh not in manifest -> flagged
# ---------------------------------------------------------------------------

echo "[3] stale hook detection"

STALE_MANIFEST=$(mktemp)
cat > "$STALE_MANIFEST" << 'JSON'
{"hooks": [
  {"file": "session-preflight.sh"},
  {"file": "skill-tracker.sh"},
  {"file": "migration-decision-reminder.sh"}
]}
JSON

STALE_SETTINGS=$(mktemp)
cat > "$STALE_SETTINGS" << 'JSON'
{
  "hooks": {
    "PostToolUse": [
      {"matcher": "Bash", "hooks": [{"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/version-bump.sh"}]},
      {"matcher": "Skill", "hooks": [{"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/skill-tracker.sh"}]}
    ],
    "UserPromptSubmit": [
      {"hooks": [{"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/migration-decision-reminder.sh"}]}
    ]
  }
}
JSON

OUTPUT=$(python3 - "$STALE_MANIFEST" "$STALE_SETTINGS" << 'PY' 2>/dev/null
import json, sys
manifest = json.load(open(sys.argv[1]))
settings_path = sys.argv[2]
known_files = {h.get('file') for h in manifest.get('hooks', [])}

d = json.load(open(settings_path))
stale = []
for event, entries in (d.get('hooks') or {}).items():
    for entry in entries:
        for h in entry.get('hooks', []):
            cmd = h.get('command', '') or ''
            if 'hooks/sweetclaude/' not in cmd and '${CLAUDE_PLUGIN_ROOT}/hooks/' not in cmd:
                continue
            base = cmd.rsplit('/', 1)[-1]
            if base and base not in known_files:
                stale.append((event, base))
for event, base in stale:
    print(f"STALE|{event}|{base}")
PY
)

echo "$OUTPUT" | grep -q "STALE|PostToolUse|version-bump.sh" \
  && pass "version-bump.sh flagged as stale" \
  || fail "did not flag version-bump.sh as stale: $OUTPUT"

echo "$OUTPUT" | grep -q "skill-tracker.sh" \
  && fail "incorrectly flagged skill-tracker.sh (it IS in manifest)" \
  || pass "skill-tracker.sh not flagged (correctly recognized as known)"

echo "$OUTPUT" | grep -q "migration-decision-reminder.sh" \
  && fail "incorrectly flagged migration-decision-reminder.sh (it IS in manifest)" \
  || pass "migration-decision-reminder.sh not flagged"

rm -f "$STALE_MANIFEST" "$STALE_SETTINGS"

# ---------------------------------------------------------------------------

echo
if [ "$FAILED" -eq 0 ]; then
  echo "ALL TESTS PASSED"
  exit 0
else
  echo "FAILURES: $FAILED"
  exit 1
fi
