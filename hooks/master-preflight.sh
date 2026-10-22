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

HOOK_IO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/hook_io.py"
INPUT=$(cat)
hook_field() { printf '%s' "$INPUT" | python3 "$HOOK_IO" field "$1"; }

TOOL=$(hook_field tool_name)
[ "$TOOL" != "Skill" ] && exit 0

SKILL_NAME=$(hook_field tool_input.skill)

# Not a sweetclaude:* skill → allow.
case "$SKILL_NAME" in
  sweetclaude:*) ;;
  *) exit 0 ;;
esac

# Lifecycle skills exempt from ALL checks.
case "$SKILL_NAME" in
  sweetclaude:bootstrap|\
  sweetclaude:configure|\
  sweetclaude:fix-sweetclaude|\
  sweetclaude:_migrate|\
  sweetclaude:purge|\
  sweetclaude:setup|\
  sweetclaude:init|\
  sweetclaude:update)
    exit 0 ;;
esac

# adopt is a lifecycle skill with no SKILL.md yet (see scripts/doctor.py); matched by bare name.
[ "${SKILL_NAME#sweetclaude:}" = "adopt" ] && exit 0

# Library-loaded lifecycle workflows are exempt the same way.
if [ "$SKILL_NAME" = "sweetclaude:library-load" ]; then
  SKILL_ARGS=$(hook_field tool_input.args)
  case "${SKILL_ARGS%% *}" in
    fix-sweetclaude|_migrate|purge|setup|init|update)
      exit 0 ;;
  esac
fi

# Resolve project root.
PROJECT_DIR=$(printf '%s' "$INPUT" | python3 "$HOOK_IO" project-dir)

# Only gate SweetClaude v2 projects.
[ ! -f "$PROJECT_DIR/.sweetclaude/state/sweetclaude.yaml" ] && exit 0
[ -f "$PROJECT_DIR/.sweetclaude-skip" ]  && exit 0
[ -f "$PROJECT_DIR/.sweetclaude/disabled" ] && exit 0

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
    python3 "$HOOK_IO" deny "BLOCKED: SweetClaude artifact drift (out-of-support-window). Run /sweetclaude:configure purge to remove, or re-onboard with /sweetclaude:configure init after archiving .sweetclaude/ manually."
  else
    python3 "$HOOK_IO" deny "BLOCKED: SweetClaude artifact drift — migration required. Invoke the sweetclaude:library-load _migrate skill to migrate, or run /sweetclaude:configure purge to remove SweetClaude."
  fi
  exit 0
fi

# Check 2: bootstrap has run this session.
FLAG_ROOT=$(python3 "$HOOK_IO" flag-root "$PROJECT_DIR")
PROJECT_HASH=$(printf '%s' "$FLAG_ROOT" | md5 2>/dev/null \
  || printf '%s' "$FLAG_ROOT" | md5sum 2>/dev/null | cut -d' ' -f1)
BOOTSTRAP_FLAG="/tmp/.sweetclaude-bootstrap-ran-${PROJECT_HASH}"
if [ ! -f "$BOOTSTRAP_FLAG" ]; then
  python3 "$HOOK_IO" deny "BLOCKED: sweetclaude:bootstrap has not run this session. Bootstrap handles drift detection and session setup. Invoke the sweetclaude:bootstrap skill first, then retry."
  exit 0
fi

# Check 3: mode gates. The single evaluator (scripts/gate_check.py) decides
# whether the requested skill or workflow may load in the project's active
# mode; it fails open when the project has no compiled gates or no active
# mode. Hard gates deny; soft gates (warn/prompt) surface as context.
GATE_CHECK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/gate_check.py"
SKILL_ARGS=$(hook_field tool_input.args)
GATE_OUTPUT=$(python3 "$GATE_CHECK" load --skill "$SKILL_NAME" --args "$SKILL_ARGS" --project-dir "$PROJECT_DIR" 2>/dev/null)
GATE_EXIT=$?
GATE_REASONS=$(python3 -c 'import json,sys
data = {}
try:
    data = json.loads(sys.stdin.read() or "{}")
except ValueError:
    pass
sys.stdout.write("\n".join(data.get("reasons") or []))' <<< "$GATE_OUTPUT" 2>/dev/null)
if [ "$GATE_EXIT" -eq 2 ]; then
  [ -n "$GATE_REASONS" ] || GATE_REASONS="BLOCKED: a mode gate denied this skill. Resolve the gate condition and retry."
  python3 "$HOOK_IO" deny "$GATE_REASONS"
  exit 0
fi
if [ "$GATE_EXIT" -eq 0 ] && [ -n "$GATE_REASONS" ]; then
  python3 "$HOOK_IO" context PreToolUse "$GATE_REASONS"
fi

exit 0
