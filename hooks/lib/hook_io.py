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
#   hook_io.py rel-path FILE            (project dir from stdin payload)
#   hook_io.py flag-root PROJECT_DIR
#   hook_io.py run-tests PROJECT_DIR COMMAND TIMEOUT_SECONDS

from __future__ import annotations

import json
import os
import shlex
import signal
import subprocess
import sys

OUTPUT_TAIL_BYTES = 32 * 1024


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


def relative_path(file: str, project: str) -> str:
    real_project = os.path.realpath(project)
    directory, base = os.path.split(file)
    real_file = os.path.join(os.path.realpath(directory or "."), base)
    prefix = real_project.rstrip("/") + "/"
    return real_file[len(prefix):] if real_file.startswith(prefix) else file


def flag_root(project: str) -> str:
    try:
        result = subprocess.run(["git", "-C", project, "rev-parse", "--show-toplevel"],
                                capture_output=True, text=True, timeout=30)
        top = result.stdout.strip()
        if result.returncode == 0 and top:
            return top
    except (OSError, subprocess.SubprocessError):
        pass
    return project.rstrip("/") or "/"


GIT_OPTIONS_WITH_VALUE = {"-c", "-C", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix", "--config-env"}
COMMAND_SEPARATORS = {"&&", "||", ";", "|", "&", "\n"}


def is_git_commit(command: str) -> bool:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return False
    at_start = True
    index = 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if token in COMMAND_SEPARATORS or token == "\n":
            at_start = True
            continue
        if not at_start:
            continue
        at_start = False
        if token != "git":
            continue
        while index < len(tokens) and tokens[index] not in COMMAND_SEPARATORS:
            option = tokens[index]
            if option in GIT_OPTIONS_WITH_VALUE:
                index += 2
            elif option.startswith("-"):
                index += 1
            else:
                break
        if index < len(tokens) and tokens[index] == "commit":
            return True
    return False


def run_tests(project: str, command: str, timeout_seconds: int) -> dict | None:
    proc = subprocess.Popen(["bash", "-c", command], cwd=project, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, start_new_session=True)
    try:
        out, _ = proc.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
        out, _ = proc.communicate()
        tail = out[-OUTPUT_TAIL_BYTES:].decode("utf-8", errors="replace")
        return context_output("PostToolUse",
                              f"Tests timed out after {timeout_seconds}s running: {command}\n{tail}")
    if proc.returncode == 0:
        return None
    tail = out[-OUTPUT_TAIL_BYTES:].decode("utf-8", errors="replace")
    return context_output("PostToolUse", f"Tests failed (exit {proc.returncode}) running: {command}\n{tail}")


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
    if command == "rel-path" and len(argv) == 2:
        sys.stdout.write(relative_path(argv[1], project_dir(read_input())))
        return 0
    if command == "is-git-commit":
        return 0 if is_git_commit(get_field(read_input(), "tool_input.command")) else 1
    if command == "flag-root" and len(argv) == 2:
        sys.stdout.write(flag_root(argv[1]))
        return 0
    if command == "run-tests" and len(argv) == 4:
        output = run_tests(argv[1], argv[2], int(argv[3]))
        if output:
            emit(output)
        return 0
    sys.stderr.write("usage: hook_io.py field|project-dir|deny|allow|context|block|rel-path|flag-root|run-tests\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
