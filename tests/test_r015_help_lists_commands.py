"""R-015: help prints all nine commands, each with a one-line purpose."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
HELP_SKILL = REPO_ROOT / "skills" / "help" / "SKILL.md"
COMMANDS = ["go", "plan", "design", "build", "maintain", "configure", "utils", "status", "help"]


def _sections() -> list[str]:
    return re.split(r"(?m)^## ", HELP_SKILL.read_text(encoding="utf-8"))


def _command_lines(section: str, name: str) -> list[str]:
    pattern = re.compile(rf"(?m)^.*/sweetclaude:{name}(?![\w-]).*$")
    return [m.group(0) for m in pattern.finditer(section)]


def _has_purpose(line: str, name: str) -> bool:
    after = re.split(rf"/sweetclaude:{name}`?", line, maxsplit=1)[1]
    after = re.sub(r"^[\s`*:—–|-]+", "", after)
    return len(re.findall(r"[A-Za-z]{3,}", after)) >= 3


def _list_sections() -> list[tuple[int, str]]:
    return [
        (i, s) for i, s in enumerate(_sections())
        if all(_command_lines(s, c) for c in COMMANDS)
    ]


class TestR015HelpListsNineCommands:
    def test_one_step_lists_all_nine_commands(self) -> None:
        assert _list_sections(), "no single help step references all nine /sweetclaude:<name> commands"

    def test_each_command_has_a_one_line_purpose(self) -> None:
        holders = _list_sections()
        assert holders, "no help step lists the nine commands"
        section = holders[0][1]
        missing = [
            c for c in COMMANDS
            if not any(_has_purpose(line, c) for line in _command_lines(section, c))
        ]
        assert not missing, f"commands without a purpose on the same line: {missing}"

    def test_command_list_is_instructed_to_be_printed(self) -> None:
        holders = _list_sections()
        assert holders, "no help step lists the nine commands"
        assert re.search(r"(?i)\b(tell the user|present|print|show|display)\b", holders[0][1])

    def test_command_list_is_in_or_before_the_menu_step(self) -> None:
        holders = _list_sections()
        sections = _sections()
        menu = [i for i, s in enumerate(sections) if "main menu" in s.splitlines()[0].lower()]
        assert holders and menu, "no command list or no menu step"
        assert holders[0][0] <= menu[0]
