"""Tier 1 discovery and Tier 2 library boundaries."""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).parents[1]
CORE = REPO_ROOT / "skills"
LIBRARY = REPO_ROOT / "skill-library"

PUBLIC = {"go", "plan", "design", "build", "maintain", "configure", "utils", "status", "help"}
CATEGORIES = {"plan", "design", "build", "maintain", "configure", "utils"}


def _invocable(skill: Path) -> bool:
    text = skill.read_text(encoding="utf-8")
    return bool(re.search(r"^user-invocable:\s*true\s*$", text, re.M))


def test_only_tier_one_commands_are_publicly_discoverable() -> None:
    discovered = {p.parent.name for p in CORE.glob("*/SKILL.md") if _invocable(p)}
    assert discovered == PUBLIC


def test_every_library_category_has_an_index_and_a_workflow() -> None:
    assert {p.name for p in LIBRARY.iterdir() if p.is_dir()} == CATEGORIES
    for category in CATEGORIES:
        root = LIBRARY / category
        assert (root / "INDEX.md").is_file()
        assert list(root.glob("*/SKILL.md")), category


def test_library_is_installed_but_not_a_discovered_skill_root() -> None:
    sync = (REPO_ROOT / "scripts" / "sync-to-installed.sh").read_text(encoding="utf-8")
    assert '"$REPO_ROOT/skill-library/" "$INSTALL_PATH/skill-library/"' in sync
    assert (CORE / "library-load" / "SKILL.md").is_file()
