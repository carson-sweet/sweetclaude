"""Shared helpers for driving hooks the way Claude Code 2.1.305 does.

A hook receives one JSON object on stdin, built here from the captured payloads
in tests/fixtures/hook_payloads/. The environment never carries
CLAUDE_TOOL_NAME, CLAUDE_FILE_PATH or CLAUDE_TRANSCRIPT_PATH. Output is judged
against docs/design/hook-protocol.md: a PreToolUse block is a
permissionDecision deny or exit 2 with stderr, feedback is additionalContext or
a decision block, and an {"ok": ...} object is ignored by Claude Code so it is
never a valid answer.

Shell tests call this file as a CLI:

    hook_stdin.py payload KIND CWD [key=value ...] [--tool NAME]
    hook_stdin.py verdict EXIT_CODE [STDERR_FILE] < hook-stdout
    hook_stdin.py feedback < hook-stdout
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
HOOKS = REPO_ROOT / "hooks"
PAYLOADS = REPO_ROOT / "tests" / "fixtures" / "hook_payloads"
UNSET_IN_CLAUDE_CODE = ("CLAUDE_TOOL_NAME", "CLAUDE_FILE_PATH", "CLAUDE_TRANSCRIPT_PATH", "PROJECT_DIR")


def payload(kind: str, cwd: Path | str, *, tool: str | None = None, **tool_input) -> str:
    raw = (PAYLOADS / f"{kind}.json").read_text(encoding="utf-8").replace("__CWD__", str(cwd))
    data = json.loads(raw)
    if tool:
        data["tool_name"] = tool
    if tool_input:
        data["tool_input"] = {**data.get("tool_input", {}), **tool_input}
    return json.dumps(data)


def stop_payload(cwd: Path | str, text: str, *, active: bool = False, transcript: Path | str | None = None) -> str:
    data = json.loads(payload("Stop-none", cwd))
    data["stop_hook_active"] = active
    data["last_assistant_message"] = text
    if transcript is not None:
        data["transcript_path"] = str(transcript)
    return json.dumps(data)


def prompt_payload(cwd: Path | str, prompt: str = "continue") -> str:
    data = json.loads(payload("UserPromptSubmit-none", cwd))
    data["prompt"] = prompt
    return json.dumps(data)


def hook_env(project: Path, extra: dict | None = None) -> dict:
    env = os.environ.copy()
    for var in UNSET_IN_CLAUDE_CODE:
        env.pop(var, None)
    env.update({
        "HOME": str(project),
        "CLAUDE_PROJECT_DIR": str(project),
        "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT),
        "CLAUDE_PLUGIN_DATA": str(project / ".plugin-data"),
    })
    env.update(extra or {})
    return env


def run_hook(name: str, project: Path, stdin: str, *, env: dict | None = None) -> subprocess.CompletedProcess:
    runner = ["python3"] if name.endswith(".py") else ["bash"]
    return subprocess.run([*runner, str(HOOKS / name)], cwd=str(project), env=hook_env(project, env),
                          input=stdin, capture_output=True, text=True, timeout=60)


def parse_json(text: str):
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


def stdout_json(result: subprocess.CompletedProcess):
    return parse_json(result.stdout)


def feedback_text(result: subprocess.CompletedProcess) -> str:
    data = stdout_json(result)
    if not isinstance(data, dict):
        return ""
    specific = data.get("hookSpecificOutput") or {}
    parts = [specific.get("additionalContext") or ""]
    if data.get("decision") == "block":
        parts.append(data.get("reason") or "")
    return "\n".join(part for part in parts if part)


def deny_reason(result: subprocess.CompletedProcess) -> str:
    if result.returncode == 2:
        return result.stderr
    data = stdout_json(result)
    if not isinstance(data, dict):
        return ""
    specific = data.get("hookSpecificOutput") or {}
    return str(specific.get("permissionDecisionReason") or data.get("reason") or "")


def verdict_of(returncode: int, stdout: str, stderr: str = "") -> str:
    if returncode == 2:
        return "deny" if stderr.strip() else "invalid"
    if returncode != 0:
        return "invalid"
    data = parse_json(stdout)
    if isinstance(data, dict):
        if "ok" in data:
            return "invalid"
        specific = data.get("hookSpecificOutput") or {}
        if specific.get("permissionDecision") == "deny":
            return "deny" if str(specific.get("permissionDecisionReason") or "").strip() else "invalid"
        if data.get("decision") == "block":
            return "block" if str(data.get("reason") or "").strip() else "invalid"
    if '"ok"' in stdout.replace("'", '"'):
        return "invalid"
    return "allow"


def verdict(result: subprocess.CompletedProcess) -> str:
    return verdict_of(result.returncode, result.stdout, result.stderr)


def is_denied(result: subprocess.CompletedProcess) -> bool:
    return verdict(result) == "deny"


def is_allowed(result: subprocess.CompletedProcess) -> bool:
    return verdict(result) == "allow"


def assert_denied(result: subprocess.CompletedProcess) -> None:
    assert verdict(result) == "deny", (
        f"expected a deny (permissionDecision deny, or exit 2 with stderr); "
        f"exit={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}")


def assert_allowed(result: subprocess.CompletedProcess) -> None:
    assert verdict(result) == "allow", (
        f"expected allow (exit 0, no deny, no block, no ok key); "
        f"exit={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}")


def assert_blocked(result: subprocess.CompletedProcess) -> None:
    assert verdict(result) == "block", (
        f'expected {{"decision": "block", "reason": ...}}; '
        f"exit={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}")


def _cli(argv: list[str]) -> int:
    command = argv[0]
    if command == "payload":
        kind, cwd, rest = argv[1], argv[2], argv[3:]
        tool = None
        fields = {}
        index = 0
        while index < len(rest):
            if rest[index] == "--tool":
                tool = rest[index + 1]
                index += 2
                continue
            key, _, value = rest[index].partition("=")
            fields[key] = value
            index += 1
        sys.stdout.write(payload(kind, cwd, tool=tool, **fields))
        return 0
    if command == "verdict":
        stderr = Path(argv[2]).read_text(encoding="utf-8") if len(argv) > 2 else ""
        print(verdict_of(int(argv[1]), sys.stdin.read(), stderr))
        return 0
    if command == "feedback":
        data = parse_json(sys.stdin.read())
        if isinstance(data, dict):
            specific = data.get("hookSpecificOutput") or {}
            print(specific.get("additionalContext") or "")
            if data.get("decision") == "block":
                print(data.get("reason") or "")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
