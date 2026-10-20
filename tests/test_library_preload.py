from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "skill-library"
LOADER = ROOT / "skills" / "library-load" / "SKILL.md"
PRELOAD = re.compile(r"^!`(.+)`$", re.MULTILINE)
HANDLED = re.compile(r"^bash \$\{CLAUDE_SKILL_DIR\}/\.\./\.\./hooks/read-state\.sh [a-z-]+( [A-Z_]+)?$")


def test_library_preloads_use_the_form_the_loader_substitutes():
    offenders = []
    for skill in sorted(LIBRARY.glob("*/*/SKILL.md")):
        for command in PRELOAD.findall(skill.read_text(encoding="utf-8")):
            if not HANDLED.match(command):
                offenders.append(f"{skill.relative_to(ROOT)}: {command}")
    assert not offenders, "library preloads the loader cannot substitute:\n" + "\n".join(offenders)


def test_tier_one_skills_have_no_unintended_preload_commands():
    for skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
        for command in PRELOAD.findall(skill.read_text(encoding="utf-8")):
            assert HANDLED.match(command), f"{skill.relative_to(ROOT)} runs an unexpected preload: {command}"
    assert "!`bash ${CLAUDE_SKILL_DIR}/../../hooks/read-state.sh session-state`" in LOADER.read_text(encoding="utf-8")


def test_loader_states_the_preload_substitution():
    text = LOADER.read_text(encoding="utf-8")
    assert "hooks/read-state.sh <stem> [sentinel]" in text
    assert "`.sweetclaude/state/<stem>.yaml`" in text
    assert "STATE_NOT_FOUND" in text
