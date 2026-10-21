#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude hook I/O helper. Reads the Claude Code hook payload from stdin and
# emits the outputs documented in docs/design/hook-protocol.md.
#
# CLI (stdin carries the payload JSON for field and project-dir):
#   hook_io.py field tool_input.file_path [default]
#   hook_io.py project-dir
#   hook_io.py deny REASON
#   hook_io.py context EVENT TEXT
#   hook_io.py block REASON

from __future__ import annotations

import json
import os
import sys


def read_input(stream=None) -> dict:
    stream = stream or sys.stdin
    try:
        data = json.loads(stream.read())
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def get_field(data: dict, dotted: str, default: str = "") -> str:
    value = data
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    if value is None:
        return default
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


def project_dir(data: dict) -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR") or str(data.get("cwd") or "") or os.getcwd()


def deny_output(reason: str) -> dict:
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}


def allow_output(reason: str = "") -> dict:
    output = {"hookEventName": "PreToolUse", "permissionDecision": "allow"}
    if reason:
        output["permissionDecisionReason"] = reason
    return {"hookSpecificOutput": output}


def context_output(event: str, text: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}


def block_output(reason: str) -> dict:
    return {"decision": "block", "reason": reason}


def emit(output: dict) -> None:
    sys.stdout.write(json.dumps(output) + "\n")


def main(argv: list[str]) -> int:
    command = argv[0] if argv else ""
    if command == "field" and len(argv) >= 2:
        sys.stdout.write(get_field(read_input(), argv[1], argv[2] if len(argv) > 2 else ""))
        return 0
    if command == "project-dir":
        sys.stdout.write(project_dir(read_input()))
        return 0
    if command == "deny" and len(argv) == 2:
        emit(deny_output(argv[1]))
        return 0
    if command == "allow":
        emit(allow_output(argv[1] if len(argv) > 1 else ""))
        return 0
    if command == "context" and len(argv) == 3:
        emit(context_output(argv[1], argv[2]))
        return 0
    if command == "block" and len(argv) == 2:
        emit(block_output(argv[1]))
        return 0
    sys.stderr.write("usage: hook_io.py field|project-dir|deny|allow|context|block\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
