#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# tdd-commit-gate.sh — PreToolUse hook on Bash
# Denies a git commit that adds implementation source files on a TDD story
# branch with no earlier "test: RED" commit. Any other call is allowed.

set -euo pipefail

HOOK_IO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/hook_io.py"

python3 "$HOOK_IO" tdd-commit-gate