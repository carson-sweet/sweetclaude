#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude Master Pre-Flight (PreToolUse hook)
#
# Intercepts Skill invocations of sweetclaude:* and enforces two invariants:
#
#   1. No pending artifact-drift decision (pending-drift-decision.yaml absent).
#      Writes pending-drift-decision.yaml on drift are done by the drift-gate.sh
#      SessionStart hook. Resolution paths (_migrate, purge) are exempt.
#
#   2. Bootstrap has run this session (flag set by sweetclaude:bootstrap).
#      Blocks if bootstrap has not run, directing the user to do so.
#
# Lifecycle skills exempt from ALL checks (they either ARE the resolution path
# or must run before bootstrap):
#   bootstrap, fix-sweetclaude, _migrate, purge, setup, init, adopt, update
#
# Bootstrap sets the session flag by running:
#   touch "/tmp/.sweetclaude-bootstrap-ran-$(project_hash)"
# where project_hash = md5 of the absolute project root path.
#
# Registered as a global PreToolUse hook (matcher: Skill) via T6 / install.sh.
# Not wired until T4 (bootstrap) sets the flag on completion.

TOOL="${CLAUDE_TOOL_NAME:-}"
[ "$TOOL" != "Skill" ] && { echo '{"ok": true}'; exit 0; }

# Read skill name from stdin JSON.
INPUT=$(cat)
SKILL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_input.skill // empty' 2>/dev/null || true)
if [ -z "$SKILL_NAME" ]; then
  SKILL_NAME=$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('skill', ''))
except Exception:
    print('')
" 2>/dev/null || true)
fi

# Not a sweetclaude:* skill → allow.
case "$SKILL_NAME" in
  sweetclaude:*) ;;
  *) echo '{"ok": true}'; exit 0 ;;
esac

# Lifecycle skills exempt from ALL checks.
case "$SKILL_NAME" in
  sweetclaude:bootstrap|\
  sweetclaude:fix-sweetclaude|\
  sweetclaude:_migrate|\
  sweetclaude:purge|\
  sweetclaude:setup|\
  sweetclaude:init|\
  sweetclaude:adopt|\
  sweetclaude:update)
    echo '{"ok": true}'; exit 0 ;;
esac

# Resolve project root.
PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$PROJECT_DIR" ]; then
  echo '{"ok": true}'; exit 0
fi

# Only gate SweetClaude v2 projects.
[ ! -f "$PROJECT_DIR/.sweetclaude/state/sweetclaude.yaml" ] && { echo '{"ok": true}'; exit 0; }
[ -f "$PROJECT_DIR/.sweetclaude-skip" ]  && { echo '{"ok": true}'; exit 0; }
[ -f "$PROJECT_DIR/.sweetclaude/disabled" ] && { echo '{"ok": true}'; exit 0; }

# Check 1: pending drift decision — blocks until resolved via exempt skills.
DRIFT_MARKER="$PROJECT_DIR/.sweetclaude/state/pending-drift-decision.yaml"
if [ -f "$DRIFT_MARKER" ]; then
  CASE=$(python3 -c "
import sys, yaml
try:
    d = yaml.safe_load(open(sys.argv[1])) or {}
    print(d.get('case', 'A'))
except Exception:
    print('A')
" "$DRIFT_MARKER" 2>/dev/null)
  if [ "$CASE" = "B" ]; then
    echo '{"ok": false, "reason": "BLOCKED: SweetClaude artifact drift (out-of-support-window). Run /sweetclaude:purge to remove, or re-onboard with /sweetclaude:adopt after archiving .sweetclaude/ manually."}'
  else
    echo '{"ok": false, "reason": "BLOCKED: SweetClaude artifact drift — migration required. Run /sweetclaude:_migrate to migrate, or /sweetclaude:purge to remove SweetClaude."}'
  fi
  exit 0
fi

# Check 2: bootstrap has run this session.
PROJECT_HASH=$(printf '%s' "$PROJECT_DIR" | md5 2>/dev/null \
  || printf '%s' "$PROJECT_DIR" | md5sum 2>/dev/null | cut -d' ' -f1)
BOOTSTRAP_FLAG="/tmp/.sweetclaude-bootstrap-ran-${PROJECT_HASH}"
if [ ! -f "$BOOTSTRAP_FLAG" ]; then
  echo '{"ok": false, "reason": "BLOCKED: sweetclaude:bootstrap has not run this session. Bootstrap handles drift detection and session setup. Run /sweetclaude:bootstrap first, then retry."}'
  exit 0
fi

echo '{"ok": true}'
exit 0
