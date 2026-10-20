"""Local acceptance test for a freshly configured Tier 1/Tier 2 project.

This is deliberately a faux project, not a fixture copied from SweetClaude's
own state. It proves the deterministic parts of the user journey:

* a new project can select GitHub as its issue system of record;
* changing that setting does not rewrite local issue artifacts as a side effect;
* an installed plugin exposes only the nine Tier 1 commands; and
* each workflow category reaches a bounded Tier 2 library, rather than placing
  its library skills under the slash-discovery root.

It cannot prove that a language model selects the intended workflow at runtime.
That remains a live-model behavioural test.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).parents[1]
PUBLIC = {"go", "plan", "design", "build", "maintain", "configure", "utils", "status", "help"}
CATEGORIES = {"plan", "design", "build", "maintain", "configure", "utils"}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _issue_tracker_update_source() -> str:
    """Extract the exact atomic update recipe shipped to the model."""
    skill = (REPO_ROOT / "skill-library" / "build" / "project-issues" / "SKILL.md")
    text = skill.read_text(encoding="utf-8")
    section = text[text.index("Before changing to `github`"):text.index("Confirm the selected system")]
    block = re.search(r"```python\n(.*?)```", section, re.S)
    assert block, "project-issues must retain its atomic tracker-update recipe"
    return block.group(1).replace("<local-or-github>", "github")


def test_faux_project_github_tracker_and_tiered_installation(tmp_path: Path) -> None:
    project = tmp_path / "faux-catalog"
    project.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)

    state = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
    state.parent.mkdir(parents=True)
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "sweetclaude-yaml-template.py"),
            "--name", "Faux Catalog",
            "--type", "existing-code",
            "--issue-tracker", "local",
            "--output", str(state),
        ],
        check=True,
    )
    assert yaml.safe_load(state.read_text(encoding="utf-8"))["project"]["issue_tracker"] == "local"

    # A local issue is deliberately present: tracker selection must not import,
    # delete, migrate, or otherwise modify it.
    local_issue = project / ".sweetclaude" / "product" / "backlog" / "ISSUE-001-demo.md"
    local_issue.parent.mkdir(parents=True)
    local_issue.write_text("# Existing local issue\n", encoding="utf-8")
    issue_before = _digest(local_issue)

    recipe = _issue_tracker_update_source()
    subprocess.run([sys.executable, "-c", recipe], cwd=project, check=True)

    configured = yaml.safe_load(state.read_text(encoding="utf-8"))
    assert configured["project"]["issue_tracker"] == "github"
    assert _digest(local_issue) == issue_before

    issue_skill = (REPO_ROOT / "skill-library" / "build" / "project-issues" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "GitHub\nIssues are the project system of record" in issue_skill
    assert "do **not** read, create, migrate, or\nsync `.sweetclaude/product` issue files" in issue_skill
    assert "do not import, export, or delete issues as a side effect" in issue_skill

    # Model the installation boundary, which is what controls slash discovery.
    installed = tmp_path / "installed-plugin"
    shutil.copytree(REPO_ROOT / "skills", installed / "skills")
    shutil.copytree(REPO_ROOT / "skill-library", installed / "skill-library")
    discovered = {
        path.parent.name
        for path in (installed / "skills").glob("*/SKILL.md")
        if re.search(r"^user-invocable:\s*true\s*$", path.read_text(encoding="utf-8"), re.M)
    }
    assert discovered == PUBLIC
    assert not (installed / "skills" / "project-issues").exists()
    assert (installed / "skill-library" / "build" / "project-issues" / "SKILL.md").is_file()

    # Each public workflow front door names only its own loader category.
    for category in CATEGORIES:
        front_door = (installed / "skills" / category / "SKILL.md").read_text(encoding="utf-8")
        assert f"category `{category}`" in front_door
        assert "Tier 2 library loader" in front_door
        index = (installed / "skill-library" / category / "INDEX.md").read_text(encoding="utf-8")
        assert "Choose one workflow; do not load every workflow body." in index
        assert list((installed / "skill-library" / category).glob("*/SKILL.md"))

    router = (installed / "skills" / "find-skill" / "SKILL.md").read_text(encoding="utf-8")
    expected_routes = {
        "Product problem": "plan",
        "Architecture": "design",
        "Feature": "build",
        "Bug in production": "maintain",
        "SweetClaude setup": "configure",
        "Meeting preparation": "utils",
    }
    for signal, category in expected_routes.items():
        assert f"{signal}" in router
        assert f"| `{category}` |" in router
