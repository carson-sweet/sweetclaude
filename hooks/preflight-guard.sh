#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude Pre-Flight Guard
# PreToolUse — blocks ALL tool calls if the SessionStart hook flagged this
# project as needing configuration. The flag persists until the project is
# configured (.sweetclaude/state/sweetclaude.yaml or the legacy phase.yaml
# exists) or opted out (.sweetclaude-skip).

HOOK_IO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/hook_io.py"
INPUT=$(cat)
hook_field() { printf '%s' "$INPUT" | python3 "$HOOK_IO" field "$1"; }

PROJECT_DIR=$(printf '%s' "$INPUT" | python3 "$HOOK_IO" project-dir)

PROJECT_HASH=$(echo -n "$PROJECT_DIR" | md5 2>/dev/null || echo -n "$PROJECT_DIR" | md5sum 2>/dev/null | cut -d' ' -f1)
FLAG="/tmp/.sweetclaude-needs-preflight-${PROJECT_HASH}"

# No flag — allow
if [ ! -f "$FLAG" ]; then
  exit 0
fi

# Flag exists — but maybe the project was configured since it was planted
if [ -f "$PROJECT_DIR/.sweetclaude/state/sweetclaude.yaml" ] || [ -f "$PROJECT_DIR/.sweetclaude/state/phase.yaml" ] || [ -f "$PROJECT_DIR/.sweetclaude-skip" ]; then
  rm -f "$FLAG"
  exit 0
fi

# Legacy fallback
LEGACY_REPO="${PROJECT_DIR}-sweetclaude"
if [ -f "$LEGACY_REPO/state/sweetclaude.yaml" ] || [ -f "$LEGACY_REPO/state/phase.yaml" ]; then
  rm -f "$FLAG"
  exit 0
fi

# Flag exists, project still not configured — BLOCK
python3 "$HOOK_IO" deny "BLOCKED: SweetClaude is not configured for this project. Run /sweetclaude:configure init to set up, or create .sweetclaude-skip to opt out."
exit 0
