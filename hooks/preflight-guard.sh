#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude Pre-Flight Guard
# PreToolUse — blocks ALL tool calls if the SessionStart hook flagged this
# project as needing configuration. The flag persists until the project is
# configured (.sweetclaude/state/phase.yaml exists) or opted out (.sweetclaude-skip).

PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")

# No git repo — allow
if [ -z "$PROJECT_DIR" ]; then
  echo '{"ok": true}'
  exit 0
fi

PROJECT_HASH=$(echo -n "$PROJECT_DIR" | md5 2>/dev/null || echo -n "$PROJECT_DIR" | md5sum 2>/dev/null | cut -d' ' -f1)
FLAG="/tmp/.sweetclaude-needs-preflight-${PROJECT_HASH}"

# No flag — allow
if [ ! -f "$FLAG" ]; then
  echo '{"ok": true}'
  exit 0
fi

# Flag exists — but maybe the project was configured since it was planted
if [ -f "$PROJECT_DIR/.sweetclaude/state/phase.yaml" ] || [ -f "$PROJECT_DIR/.sweetclaude-skip" ]; then
  rm -f "$FLAG"
  echo '{"ok": true}'
  exit 0
fi

# Legacy fallback
LEGACY_REPO="${PROJECT_DIR}-sweetclaude"
if [ -f "$LEGACY_REPO/state/phase.yaml" ]; then
  rm -f "$FLAG"
  echo '{"ok": true}'
  exit 0
fi

# Flag exists, project still not configured — BLOCK
echo '{"ok": false, "reason": "BLOCKED: SweetClaude is not configured for this project. Run /sweetclaude:init to set up, or create .sweetclaude-skip to opt out."}'
exit 0
