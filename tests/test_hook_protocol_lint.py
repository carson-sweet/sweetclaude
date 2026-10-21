"""Static lint of hooks/ against the verified Claude Code hook protocol (phase 2).

docs/design/hook-protocol.md: CLAUDE_TOOL_NAME, CLAUDE_FILE_PATH and
CLAUDE_TRANSCRIPT_PATH are never set, {"ok": ...} output is ignored, and a
PreToolUse hook blocks only through permissionDecision deny or exit 2. Every
violation is reported as file:line. Comment-only lines are not code and are
skipped. sc-artifact.sh and sc-artifact-impl.py are CLIs, not hooks, so their
{"ok": ...} results are for human callers and are exempt from the ok rule.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
HOOKS = REPO_ROOT / "hooks"
UNSET_ENV = re.compile(r"CLAUDE_(?:TOOL_NAME|FILE_PATH|TRANSCRIPT_PATH)")
OK_KEY = re.compile(r"""\\?["']ok\\?["']\s*:""")
BLOCK_WORDS = re.compile(r"block|deny|denied|refus", re.IGNORECASE)
EMITTERS = re.compile(r"\b(echo|printf|cat|print)\b")
CLI_NOT_HOOKS = {"sc-artifact.sh", "sc-artifact-impl.py"}


def hook_files() -> list[Path]:
    return sorted([*HOOKS.glob("*.sh"), *HOOKS.glob("*.py")])


def code_lines(path: Path):
    comment = "//" if path.suffix == ".js" else "#"
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip().startswith(comment):
            continue
        yield number, line


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def pre_tool_use_scripts() -> list[Path]:
    config = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))
    scripts = []
    for group in config["hooks"].get("PreToolUse", []):
        for hook in group["hooks"]:
            name = hook["command"].rsplit("/", 1)[-1]
            scripts.append(HOOKS / name)
    return sorted(set(scripts))


def test_no_hook_reads_unset_claude_env_vars():
    offenders = [
        f"{relative(path)}:{number}: {line.strip()}"
        for path in hook_files()
        for number, line in code_lines(path)
        if UNSET_ENV.search(line)
    ]
    assert not offenders, "hooks read env vars Claude Code does not set (use stdin JSON):\n" + "\n".join(offenders)


def test_no_hook_emits_ok_json():
    offenders = [
        f"{relative(path)}:{number}: {line.strip()}"
        for path in hook_files()
        if path.name not in CLI_NOT_HOOKS
        for number, line in code_lines(path)
        if OK_KEY.search(line)
    ]
    assert not offenders, '{"ok": ...} is ignored by Claude Code and must not be printed:\n' + "\n".join(offenders)


def test_pre_tool_use_hooks_never_block_with_exit_zero_and_no_permission_decision():
    offenders = []
    for path in pre_tool_use_scripts():
        text = path.read_text(encoding="utf-8")
        if "permissionDecision" in text or re.search(r"\bexit 2\b", text):
            continue
        lines = list(code_lines(path))
        for index, (number, line) in enumerate(lines):
            if not re.search(r"\bexit 0\b", line):
                continue
            window = " ".join(candidate for _, candidate in lines[max(0, index - 3):index + 1])
            if EMITTERS.search(window) and BLOCK_WORDS.search(window):
                offenders.append(f"{relative(path)}:{number}: blocks with exit 0 and no permissionDecision or exit 2")
    assert not offenders, "\n".join(offenders)

