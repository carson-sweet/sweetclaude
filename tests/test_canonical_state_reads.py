"""Skills must read canonical state from sweetclaude.yaml (ISSUE-251).

sweetclaude.yaml is the canonical v4 state file. phase.yaml is a mirror
that small_story_controller and success_criteria_contracts write lazily —
onboarding never creates it. A skill that opens phase.yaml without an
existence guard crashes on any project that has not yet run a story
workflow; a skill that treats it as the source of truth diverges from what
go, status, and the controllers read.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
LIBRARY_DIR = REPO_ROOT / "skill-library"
TEMPLATE = REPO_ROOT / "scripts" / "sweetclaude-yaml-template.py"

# behavioral-regression builds a phase.yaml fixture under /tmp on purpose.
FIXTURE_AUTHORS = {"behavioral-regression"}

UNGUARDED_OPEN = re.compile(
    r"(?:yaml\.safe_load\(open\(|open\()\s*['\"][^'\"]*state/phase\.yaml"
)


def _skill_docs() -> list[Path]:
    return sorted(
        [
            *(p for p in SKILLS_DIR.glob("*/*.md") if p.name != "README.md"),
            *(p for p in LIBRARY_DIR.glob("*/*/*.md") if p.name != "README.md"),
        ]
    )


def _relevant_docs() -> list[tuple[str, str]]:
    out = []
    for doc in _skill_docs():
        if doc.parent.name in FIXTURE_AUTHORS:
            continue
        text = doc.read_text(encoding="utf-8")
        if "phase.yaml" in text:
            out.append((doc.relative_to(REPO_ROOT).as_posix(), text))
    return out


@pytest.mark.parametrize("rel_path,text", _relevant_docs(), ids=lambda v: v if isinstance(v, str) and v.endswith(".md") else "")
def test_no_unguarded_phase_yaml_open(rel_path: str, text: str) -> None:
    hits = UNGUARDED_OPEN.findall(text)
    assert not hits, (
        f"{rel_path} opens phase.yaml directly. A v4 project onboarded through "
        "setup has no phase.yaml until the first story workflow runs, so this "
        "raises FileNotFoundError. Read sweetclaude.yaml, or guard the open."
    )


@pytest.mark.parametrize("rel_path,text", _relevant_docs(), ids=lambda v: v if isinstance(v, str) and v.endswith(".md") else "")
def test_phase_yaml_is_never_the_only_state_source(rel_path: str, text: str) -> None:
    assert "sweetclaude.yaml" in text, (
        f"{rel_path} references phase.yaml but never sweetclaude.yaml. "
        "phase.yaml is a controller-maintained mirror, not the source of truth."
    )


def test_template_defines_project_mode() -> None:
    """project-mode needs a canonical home for `mode`."""
    text = TEMPLATE.read_text(encoding="utf-8")
    assert re.search(r"^\s*'mode':", text, re.MULTILINE), (
        "scripts/sweetclaude-yaml-template.py must define project.mode so "
        "project-mode has a canonical home for the project mode."
    )


def test_template_project_block_shape() -> None:
    """Guard the guard — mode must land inside the project block."""
    import subprocess
    import sys

    out = subprocess.run(
        [sys.executable, str(TEMPLATE), "--name", "t", "--output", "-"],
        capture_output=True, text=True, timeout=30, check=True,
    ).stdout
    data = yaml.safe_load(out)
    assert "mode" in data["project"], "project.mode missing from generated state"


def test_template_defines_issue_tracker_with_a_local_default() -> None:
    """Issue management needs a per-project system-of-record choice."""
    import subprocess
    import sys

    def render(*args: str) -> dict:
        return yaml.safe_load(subprocess.run(
            [sys.executable, str(TEMPLATE), "--name", "t", *args, "--output", "-"],
            capture_output=True, text=True, timeout=30, check=True,
        ).stdout)

    assert render()["project"]["issue_tracker"] == "local"
    assert render("--issue-tracker", "github")["project"]["issue_tracker"] == "github"


def test_project_issues_recognizes_natural_language_tracker_changes() -> None:
    """The option must be usable without knowing the tracker subcommand."""
    skill = (LIBRARY_DIR / "build" / "project-issues" / "SKILL.md").read_text(encoding="utf-8")
    assert "use GitHub for this project's issues" in skill
    assert "stop using local issue tracking" in skill
    assert "do not import, export, or delete issues as a side effect" in skill
