from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
SETUP_SKILL = REPO_ROOT / "skill-library" / "configure" / "setup" / "SKILL.md"
MASTER_SKILL = REPO_ROOT / "skills" / "master" / "SKILL.md"


def branch_section(letter: str) -> str:
    text = SETUP_SKILL.read_text()
    match = re.search(
        rf"^## Branch {letter}:.*?(?=^## |\Z)", text, re.MULTILINE | re.DOTALL
    )
    assert match, f"setup SKILL.md has no '## Branch {letter}:' section"
    return match.group(0)
