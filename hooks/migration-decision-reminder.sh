#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# SweetClaude migration-decision reminder hook (UserPromptSubmit).
#
# Implements the Defer-decision flow from Gap #6 (BL-068).
#
# After a successful migration, the _migrate skill offers three end-of-session
# options: Accept, Initiate rollback, Defer decision. If the user picks Defer,
# _migrate writes .sweetclaude/state/pending-migration-decision.yaml with the
# snapshot info and turn_count: 0.
#
# This hook fires on every UserPromptSubmit:
#   - No marker file → exit silently.
#   - Marker present, turn_count < 10 → inject a reminder via additionalContext.
#   - Marker present, turn_count >= 10 → hard-block via continue: false.
#
# The marker is cleared by _migrate when the user picks Accept or completes
# rollback.

set -u

PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$PROJECT_DIR" ]; then
  echo '{"ok": true}'
  exit 0
fi

MARKER="$PROJECT_DIR/.sweetclaude/state/pending-migration-decision.yaml"

if [ ! -f "$MARKER" ]; then
  # No pending decision — silent.
  echo '{"ok": true}'
  exit 0
fi

# Read + increment turn_count atomically, return the new value.
NEW_COUNT=$(python3 - "$MARKER" << 'PY' 2>/dev/null
import sys, yaml, tempfile, os
path = sys.argv[1]
try:
    with open(path) as f:
        d = yaml.safe_load(f) or {}
except Exception:
    print(-1)
    sys.exit(0)
turn = int(d.get('turn_count', 0)) + 1
d['turn_count'] = turn
try:
    with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(path), suffix='.tmp', delete=False) as tmp:
        yaml.safe_dump(d, tmp, default_flow_style=False, sort_keys=False)
        tmp_name = tmp.name
    os.replace(tmp_name, path)
except Exception:
    print(-1)
    sys.exit(0)
print(turn)
PY
)

if [ -z "$NEW_COUNT" ] || [ "$NEW_COUNT" = "-1" ]; then
  # Marker unreadable — fail open.
  echo '{"ok": true}'
  exit 0
fi

# Read snapshot info for the message.
SNAP_INFO=$(python3 - "$MARKER" << 'PY' 2>/dev/null
import sys, yaml
with open(sys.argv[1]) as f:
    d = yaml.safe_load(f) or {}
snap = d.get('snapshot') or {}
print(f"tar:{snap.get('tarball_path','?')} git:{snap.get('git_tag','?')}")
PY
)

_esc() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  printf '%s' "$s"
}

if [ "$NEW_COUNT" -ge 10 ]; then
  # Hard-block.
  MSG="⛔ Pending migration decision (turn $NEW_COUNT/10 — limit reached). You MUST pick Accept or Initiate rollback before continuing. Snapshot: $SNAP_INFO. Resolve via /sweetclaude:_migrate or a manual rollback."
  CTX="A migration completed but has not been accepted. The Defer decision window has expired. STOP all other work. Surface this message to the user and ask: Accept the migration (clears the marker) or Initiate rollback (typed confirmation required). Do not proceed with any other task until the marker file at .sweetclaude/state/pending-migration-decision.yaml is cleared."
  printf '{"continue":false,"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"%s"}}\n' \
    "$(_esc "$MSG")" "$(_esc "$CTX")"
  exit 0
fi

# Reminder.
MSG="⚠ Pending migration decision (turn $NEW_COUNT/10). Accept or Initiate rollback when ready. Snapshot: $SNAP_INFO."
CTX="A migration completed but has not been accepted. Surface a short reminder to the user that they have a pending Accept/Rollback decision. Do not block; allow the user to continue with other work. Decision is forced at turn 10."
printf '{"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"%s"}}\n' \
  "$(_esc "$MSG")" "$(_esc "$CTX")"
exit 0
