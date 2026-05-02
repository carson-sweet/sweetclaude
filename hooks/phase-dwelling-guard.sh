#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude Phase Dwelling Guard
# Stop hook — scans Claude's last response for advancement-pushing language.
# Blocks the response and asks Claude to revise if phrases like "ready to move on?"
# are detected. Only active when Protocol Guardian is enabled.

PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")

# No git repo — allow
if [ -z "$PROJECT_DIR" ]; then
  exit 0
fi

# SweetClaude not active for this project — allow
if [ ! -f "$PROJECT_DIR/.sweetclaude/state/phase.yaml" ]; then
  exit 0
fi

# Guardian not enabled — allow (this hook is a guardian-only enforcement)
if [ ! -f "$PROJECT_DIR/.sweetclaude/state/guardian-enabled" ]; then
  exit 0
fi

# Extract Claude's last response text from the session transcript.
# Claude Code sets CLAUDE_TRANSCRIPT_PATH when a transcript is available.
RESPONSE_TEXT=""

if [ -n "$CLAUDE_TRANSCRIPT_PATH" ] && [ -f "$CLAUDE_TRANSCRIPT_PATH" ]; then
  RESPONSE_TEXT=$(python3 - "$CLAUDE_TRANSCRIPT_PATH" 2>/dev/null << 'PYEOF'
import sys, json

path = sys.argv[1]
try:
    with open(path) as f:
        lines = f.readlines()
except Exception:
    sys.exit(0)

for line in reversed(lines):
    line = line.strip()
    if not line:
        continue
    try:
        obj = json.loads(line)
        if obj.get("type") == "assistant":
            content = obj.get("message", {}).get("content", [])
            texts = [
                b["text"] for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            if texts:
                print("\n".join(texts))
                break
    except Exception:
        continue
PYEOF
)
fi

# No response text available — allow
if [ -z "$RESPONSE_TEXT" ]; then
  exit 0
fi

# Patterns that indicate Claude is pushing for phase advancement.
# Keep to clear, unambiguous phrases. False positives degrade UX more than
# false negatives.
FOUND=$(echo "$RESPONSE_TEXT" | grep -oi \
  "ready to move on\|shall we proceed\|want to move forward\|ready to advance\|proceed to the next\|move on to the next\|should we move on\|time to move on\|let's move on\|ready to continue to the next\|shall we move on" \
  | head -1)

if [ -n "$FOUND" ]; then
  cat << EOF
PHASE DWELLING GUARD: Response contains advancement-pushing language ("$FOUND").

SweetClaude must not prompt the user to advance phases. The user decides when a phase is done — not the framework.

Please revise your response: present the work, offer to continue iterating or answer questions, and remove any language that invites or suggests moving to the next step. The user will signal advancement when they are ready.
EOF
  exit 2
fi

exit 0
