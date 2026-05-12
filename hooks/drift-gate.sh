#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude Drift Gate (SessionStart hook)
#
# Detects artifact-format drift at session start. On drift: writes
# .sweetclaude/state/pending-drift-decision.yaml and emits additionalContext
# instructing Claude to present AskUserQuestion before any other work.
#
# Registered as a global SessionStart hook. Silent when not in a SweetClaude
# project or when no drift is found.
#
# Pending-marker re-use: if the marker already exists from a prior session,
# the hook re-surfaces the decision without re-running the drift scan.

PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null)
[ -z "$PROJECT_DIR" ] && exit 0

# Only run for SweetClaude v2 projects
[ ! -f "$PROJECT_DIR/.sweetclaude/state/sweetclaude.yaml" ] && exit 0

# Opt-out
[ -f "$PROJECT_DIR/.sweetclaude-skip" ] && exit 0
[ -f "$PROJECT_DIR/.sweetclaude/disabled" ] && exit 0

MARKER="$PROJECT_DIR/.sweetclaude/state/pending-drift-decision.yaml"

_esc() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/\\r}"
  s="${s//$'\t'/\\t}"
  s="${s//$'\033'/\\u001b}"
  printf '%s' "$s"
}

_IDE_NOTE="Note: systemMessage may not be visible in IDE environments (VS Code extension). If the user has not acknowledged the above message, surface it as your first response before taking any other action."

# Emit the AskUserQuestion instruction for the given case.
_emit_drift_ctx() {
  local case="$1"
  local drift_count="$2"
  local _RED=$'\033[0;31m'
  local _RST=$'\033[0m'

  if [ "$case" = "B" ]; then
    SYS_MSG="${_RED}SweetClaude: artifact drift detected (out-of-support-window) - migration required before proceeding.${_RST}"
    CTX="STOP - CRITICAL: SweetClaude artifact drift detected (Case B - chain broken, out of 3-major support window). DO NOT invoke sweetclaude:bootstrap or any SweetClaude skill automatically. FIRST use AskUserQuestion with: question='SweetClaude artifacts are too old for automatic migration (out of support window). SweetClaude cannot run until you decide.', options=['Re-onboard from scratch (move existing content to .sweetclaude.legacy/ and run /sweetclaude:adopt)', 'Remove SweetClaude from this project (re-onboarding required to reactivate)']. Block all other work until resolved. Marker: .sweetclaude/state/pending-drift-decision.yaml. ${_IDE_NOTE}"
  else
    SYS_MSG="${_RED}SweetClaude: artifact drift detected (${drift_count} file(s) behind framework) - migration required before proceeding.${_RST}"
    CTX="STOP - CRITICAL: SweetClaude artifact drift detected (Case A - ${drift_count} file(s) behind framework version). DO NOT invoke sweetclaude:bootstrap or any SweetClaude skill automatically. FIRST use AskUserQuestion with: question='SweetClaude has ${drift_count} artifact(s) behind the framework version. SweetClaude cannot run until you decide.', options=['Migrate now (run sweetclaude:_migrate)', 'Remove SweetClaude from this project (run sweetclaude:purge)']. Block all other work until resolved. Marker: .sweetclaude/state/pending-drift-decision.yaml. ${_IDE_NOTE}"
  fi

  printf '{"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' \
    "$(_esc "$SYS_MSG")" "$(_esc "$CTX")"
}

# If marker already exists from a prior session, re-surface without re-scanning.
if [ -f "$MARKER" ]; then
  EXISTING_CASE=$(python3 -c "
import sys, yaml
try:
    d = yaml.safe_load(open(sys.argv[1])) or {}
    print(d.get('case', 'A'))
    print(d.get('drift_count', 1))
except Exception:
    print('A')
    print(1)
" "$MARKER" 2>/dev/null)
  EX_CASE=$(printf '%s\n' "$EXISTING_CASE" | sed -n '1p')
  EX_COUNT=$(printf '%s\n' "$EXISTING_CASE" | sed -n '2p')
  _emit_drift_ctx "${EX_CASE:-A}" "${EX_COUNT:-1}"
  exit 0
fi

# Find runner — versionless path first, then installPath fallback.
RUNNER="$HOME/.claude/scripts/sweetclaude/migrations/runner.py"
if [ ! -f "$RUNNER" ]; then
  RUNNER=$(python3 -c "
import json, os
try:
    d = json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))
    entries = [e for versions in d.get('plugins', {}).values()
               for e in versions if e.get('scope') == 'user']
    entries.sort(key=lambda e: e.get('lastUpdated', ''), reverse=True)
    for e in entries:
        ip = e.get('installPath', '')
        r = os.path.join(ip, 'scripts', 'migrations', 'runner.py')
        if os.path.exists(r):
            print(r)
            break
except Exception:
    pass
" 2>/dev/null)
fi
[ -z "$RUNNER" ] || [ ! -f "$RUNNER" ] && exit 0

# Run drift scan.
DRIFT_OUTPUT=$(python3 "$RUNNER" --project-dir "$PROJECT_DIR" --report-drift-for-skill 2>/dev/null)
DRIFT_COUNT=$(printf '%s\n' "$DRIFT_OUTPUT" | grep '^DRIFT_COUNT=' | cut -d= -f2)
[ -z "$DRIFT_COUNT" ] || [ "$DRIFT_COUNT" = "0" ] && exit 0

# Classify: Case A (all chains ok) or Case B (at least one broken).
if printf '%s\n' "$DRIFT_OUTPUT" | grep -q '|chain=broken'; then
  CASE="B"
else
  CASE="A"
fi

# Write marker.
FINDINGS_JSON=$(printf '%s\n' "$DRIFT_OUTPUT" | grep '^FINDING|' | python3 -c "
import sys, json
findings = []
for line in sys.stdin:
    parts = line.strip().split('|')
    if len(parts) >= 4:
        findings.append({
            'file_key': parts[1],
            'migration': parts[2],
            'chain': parts[3].replace('chain=', '')
        })
print(json.dumps(findings))
" 2>/dev/null)

python3 - "$MARKER" "$CASE" "$DRIFT_COUNT" "$FINDINGS_JSON" << 'PY' 2>/dev/null
import sys, yaml, json, os, tempfile
from datetime import datetime, timezone
marker, case, drift_count, findings_json = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
try:
    findings = json.loads(findings_json) if findings_json else []
except Exception:
    findings = []
d = {
    'case': case,
    'drift_count': int(drift_count),
    'findings': findings,
    'created_at': datetime.now(timezone.utc).isoformat()
}
os.makedirs(os.path.dirname(marker), exist_ok=True)
with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(marker), suffix='.tmp', delete=False) as tmp:
    yaml.safe_dump(d, tmp, default_flow_style=False, sort_keys=False)
    tmp_name = tmp.name
os.replace(tmp_name, marker)
PY

_emit_drift_ctx "$CASE" "$DRIFT_COUNT"
