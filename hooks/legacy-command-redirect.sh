#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# SweetClaude legacy command redirect hook (UserPromptSubmit).
#
# SweetClaude 5.0 replaced one slash command per workflow with nine Tier 1
# commands. When a prompt starts with a removed /sweetclaude:<workflow>
# command, tell the user the new form and hand the request to the owning
# category. Tier 1 commands and every other prompt pass through silently.

set -u

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_INPUT=$(cat)
export HOOK_INPUT

python3 - "$HOOK_DIR/../skill-library" << 'PY' 2>/dev/null
import json
import os
import re
import sys
from pathlib import Path

TIER_ONE = {"go", "plan", "design", "build", "maintain", "configure", "utils", "status", "help"}

try:
    prompt = json.loads(os.environ.get("HOOK_INPUT", "")).get("prompt") or ""
except Exception:
    sys.exit(0)

COMMAND_PREFIX = re.escape("/sweetclaude" + ":")
match = re.match(r"\s*" + COMMAND_PREFIX + r"([A-Za-z0-9_-]+)(?:\s+(.*))?\s*$", prompt, re.S)
if not match or match.group(1) in TIER_ONE:
    sys.exit(0)

name, rest = match.group(1), (match.group(2) or "").strip()
homes = sorted(Path(sys.argv[1]).glob(f"*/{name}/SKILL.md"))

if len(homes) == 1:
    category = homes[0].parent.parent.name
    replacement = f"/sweetclaude:{category} {name}"
    args = f"{name} {rest}".strip()
    message = f"SweetClaude 5.0: /sweetclaude:{name} is now {replacement}."
    context = f"The user typed /sweetclaude:{name}, a command removed in SweetClaude 5.0. Tell the user in one sentence that it is now {replacement}, then carry out the request by invoking the Skill tool with skill sweetclaude:{category} and args {json.dumps(args)}."
else:
    message = f"SweetClaude 5.0: /sweetclaude:{name} is not a SweetClaude command. Run /sweetclaude:help to see the available commands."
    context = f"The user typed /sweetclaude:{name}, which is not a SweetClaude 5.0 command. Tell the user it does not exist and suggest /sweetclaude:help or /sweetclaude:go with a description of what they want. Do not guess at a workflow."

print(json.dumps({"systemMessage": message, "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": context}}))
PY
exit 0
