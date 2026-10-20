"""Preflight guards must key on the v4 state file (ISSUE-250).

v4 moved configuration detection to .sweetclaude/state/sweetclaude.yaml.
Nothing in the onboarding path (skill-library/configure/setup, skill-library/configure/_features) creates
phase.yaml — small_story_controller writes it lazily on the first story
workflow. A guard that gates solely on phase.yaml therefore refuses to run
on a correctly configured, freshly onboarded project.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
SKILL_LIBRARY_DIR = REPO_ROOT / "skill-library"
PREFLIGHT_HOOK = REPO_ROOT / "hooks" / "preflight-guard.sh"

GUARD_BLOCK = re.compile(r"<preflight-guard>(.*?)</preflight-guard>", re.DOTALL)


def _guarded_skills() -> list[tuple[str, str]]:
    found = []
    for skill_md in sorted([*SKILLS_DIR.glob("*/SKILL.md"), *SKILL_LIBRARY_DIR.glob("*/*/SKILL.md")]):
        match = GUARD_BLOCK.search(skill_md.read_text(encoding="utf-8"))
        if match:
            found.append((skill_md.relative_to(REPO_ROOT).as_posix(), match.group(1)))
    return found


def test_corpus_has_guarded_skills() -> None:
    """Guard the guard — if the block markers change, this suite goes silent."""
    assert len(_guarded_skills()) >= 40


@pytest.mark.parametrize("rel_path,guard", _guarded_skills(), ids=lambda v: v if isinstance(v, str) and v.endswith("SKILL.md") else "")
def test_guard_accepts_v4_state_file(rel_path: str, guard: str) -> None:
    if "phase.yaml" not in guard:
        return
    assert "sweetclaude.yaml" in guard, (
        f"{rel_path} preflight guard gates on phase.yaml without accepting "
        "sweetclaude.yaml. A v4 project onboarded through setup has no "
        "phase.yaml, so this skill refuses to run on a configured project."
    )


@pytest.mark.parametrize("rel_path,guard", _guarded_skills(), ids=lambda v: v if isinstance(v, str) and v.endswith("SKILL.md") else "")
def test_guard_never_routes_to_non_invocable_setup(rel_path: str, guard: str) -> None:
    assert "/sweetclaude:setup" not in guard, (
        f"{rel_path} preflight guard tells the user to run /sweetclaude:setup, "
        "but skill-library/configure/setup/SKILL.md is user-invocable: false. Route to "
        "/sweetclaude:init instead."
    )


def test_preflight_hook_accepts_v4_state_file() -> None:
    text = PREFLIGHT_HOOK.read_text(encoding="utf-8")
    configured_checks = [
        line for line in text.splitlines()
        if "state/phase.yaml" in line and line.strip().startswith("if ")
    ]
    assert configured_checks, "expected preflight-guard.sh to check for project state"
    for line in configured_checks:
        assert "state/sweetclaude.yaml" in line, (
            "hooks/preflight-guard.sh treats a project as unconfigured unless "
            f"phase.yaml exists: {line.strip()}"
        )
