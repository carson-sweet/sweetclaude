"""The product base setting is written where readers resolve it (ISSUE-286).

`setup` wrote `.sweetclaude/state/artifact-privacy.yaml`. All 37 readers — skills,
hooks, doctor, the migration guard — resolve `.sweetclaude/artifact-privacy.yaml`.
Nothing read what onboarding wrote, so `base_path: docs/product` never took
effect, and the fallback every reader uses happened to match where the tree was
actually built. Nothing visibly broke, which is why it survived.

This repository has the file at the right path because it predates the defect,
so self-hosting could never have surfaced it. Found by onboarding a project that
is not SweetClaude.

The default changes with the path. Making the writer correct without changing the
default would have activated `docs/product` for the first time and started
creating directories inside users' documentation trees — the thing ISSUE-285 says
must be asked rather than assumed.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
SETUP_SKILL = REPO_ROOT / "skills" / "setup" / "SKILL.md"
DOCTOR = REPO_ROOT / "scripts" / "doctor.py"
SESSION_STATE = REPO_ROOT / "hooks" / "generate-session-state.sh"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import doctor as doc  # noqa: E402

CANONICAL = ".sweetclaude/artifact-privacy.yaml"
STRAY = ".sweetclaude/state/artifact-privacy.yaml"


def _storage_block() -> str:
    """The v4 Storage Setup block setup actually runs.

    Reading the skill rather than restating it means an edit to the skill is an
    edit to what these tests check.
    """
    text = SETUP_SKILL.read_text(encoding="utf-8")
    start = text.index("## v4 Storage Setup")
    block = re.search(r"```python\n(.*?)```", text[start:], re.S)
    assert block, "setup's v4 Storage Setup python block not found"
    return block.group(1)


# --- the writer and the readers agree ------------------------------------

def test_setup_writes_where_readers_resolve() -> None:
    """The whole defect in one assertion."""
    block = _storage_block()

    assert f"pathlib.Path('{CANONICAL}')" in block, (
        f"setup must write {CANONICAL}; readers do not resolve anything else")
    assert f"'{STRAY}'" not in block, (
        f"{STRAY} is read by nothing")


def test_the_default_base_is_where_the_tree_is_built() -> None:
    """A default that points somewhere the tree is not is the same class of
    lie, just louder once the path is fixed."""
    block = _storage_block()

    assert "'.sweetclaude/product'" in block
    assert "'docs/product'" not in block, (
        "docs/product as a default would create directories in the user's "
        "documentation tree without asking — ISSUE-285")


def test_setup_does_not_clobber_a_relocated_base() -> None:
    """setup used to assign base_path unconditionally, so re-running it would
    have discarded a user's relocation. setdefault leaves an existing choice
    alone."""
    block = _storage_block()

    assert "setdefault(\n    'base_path'" in block or "setdefault('base_path'" in block, block


def test_doctors_fallback_matches_setups_default() -> None:
    """If these two ever disagree, a project with no config file and a project
    with a default one resolve to different trees."""
    resolved = doc._resolve_product_base(Path("/proj"), None)

    assert resolved == Path("/proj/.sweetclaude/product")
    assert "'.sweetclaude/product'" in _storage_block()


def test_the_reader_idiom_is_the_canonical_path_everywhere() -> None:
    """Guards the drift this issue is about: one writer moving back, or a new
    reader inventing its own path."""
    offenders = []
    for root in ("skills", "hooks", "scripts"):
        for path in (REPO_ROOT / root).rglob("*"):
            if not path.is_file() or path.suffix not in {".md", ".sh", ".py"}:
                continue
            body = path.read_text(encoding="utf-8", errors="ignore")
            if "state/artifact-privacy" in body or "state', 'artifact-privacy" in body:
                offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == [], (
        f"these resolve artifact-privacy.yaml under state/, which nothing "
        f"reads: {offenders}")


# --- doctor reports the unread file --------------------------------------

@pytest.fixture
def project(tmp_path: Path) -> Path:
    p = tmp_path / "proj"
    (p / ".sweetclaude" / "state").mkdir(parents=True)
    (p / ".sweetclaude" / "state" / "sweetclaude.yaml").write_text(
        yaml.safe_dump({"schema_version": 2, "framework": {"setup_complete": True}}),
        encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main", str(p)],
                   capture_output=True, timeout=30)
    return p


def _privacy(base: str) -> str:
    return yaml.safe_dump({"categories": {"product": {"base_path": base}}})


def _findings(project: Path) -> list[doc.Finding]:
    return doc.check_artifact_privacy_location(doc.build_project_state(project))


def test_an_unread_settings_file_is_reported(project: Path) -> None:
    (project / STRAY).write_text(_privacy("docs/product"), encoding="utf-8")

    findings = _findings(project)

    assert len(findings) == 1
    assert findings[0].id == "config-compat:unread-location:artifact-privacy.yaml"
    assert findings[0].severity == "warning"


def test_the_report_names_what_is_declared_and_what_is_in_effect(
    project: Path
) -> None:
    """Without both, the user cannot tell whether removing it costs them
    anything."""
    (project / STRAY).write_text(_privacy("docs/product"), encoding="utf-8")

    detail = _findings(project)[0].detail

    assert "docs/product" in detail
    assert str(project / ".sweetclaude" / "product") in detail


def test_the_fix_removes_the_file_that_is_not_read(project: Path) -> None:
    (project / STRAY).write_text(_privacy("docs/product"), encoding="utf-8")

    f = _findings(project)[0]

    assert f.fix_type == "auto"
    assert f.fix_recipe["action"] == "delete_file"
    assert f.fix_recipe["file"] == str(project / STRAY)


def test_removing_it_cannot_change_where_artifacts_resolve(project: Path) -> None:
    """The property that makes an automatic fix safe: the file is not read, so
    deleting it is a no-op for every consumer."""
    (project / STRAY).write_text(_privacy("docs/product"), encoding="utf-8")
    before = doc.build_project_state(project).product_base

    (project / STRAY).unlink()
    after = doc.build_project_state(project).product_base

    assert before == after == project / ".sweetclaude" / "product"


def test_a_project_with_the_setting_in_the_right_place_is_not_reported(
    project: Path
) -> None:
    (project / CANONICAL).write_text(_privacy("docs/product"), encoding="utf-8")

    assert _findings(project) == []


def test_a_project_with_no_settings_file_is_not_reported(project: Path) -> None:
    assert _findings(project) == []


def test_a_relocated_base_in_the_right_place_takes_effect(project: Path) -> None:
    """The setting is meant to work. Proving the canonical path is live is what
    makes the stray path a defect rather than a preference."""
    (project / CANONICAL).write_text(_privacy("docs/product"), encoding="utf-8")

    assert doc.build_project_state(project).product_base == project / "docs" / "product"


def test_an_unparseable_stray_file_is_still_reported(project: Path) -> None:
    """A corrupt file in an unread location must not crash the scan or slip
    past as absent."""
    (project / STRAY).write_text("{ not: valid: yaml", encoding="utf-8")

    findings = _findings(project)

    assert len(findings) == 1
    assert "(none)" in findings[0].detail


# --- end to end ----------------------------------------------------------

def test_the_finding_reaches_a_full_scan(project: Path) -> None:
    """A check absent from the registry is a check nobody runs."""
    (project / STRAY).write_text(_privacy("docs/product"), encoding="utf-8")
    home = project.parent / "home"
    home.mkdir(exist_ok=True)

    r = subprocess.run([sys.executable, str(DOCTOR), "scan",
                        "--project-dir", str(project)],
                       capture_output=True, text=True, timeout=300,
                       env={**os.environ, "HOME": str(home)})
    payload = json.loads(r.stdout)

    assert "error" not in payload, payload.get("error")
    ids = [f["id"] for f in payload["findings"]]
    assert "config-compat:unread-location:artifact-privacy.yaml" in ids, ids
