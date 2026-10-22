#!/usr/bin/env bash
# wip-limit.sh — PreToolUse hook on Bash, Write and Edit
# Denies activating an issue in Kanban mode when the WIP limit is already reached.
# Any other call is allowed, so recovery commands keep working at the limit.

set -euo pipefail

HOOK_IO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/hook_io.py"

python3 "$HOOK_IO" wip-limit
