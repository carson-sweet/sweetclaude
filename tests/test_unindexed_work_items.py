"""A work item the cache refuses is reported, not dropped (ISSUE-290).

`_rebuild_cache` validates each file's frontmatter and appends failures to a
`skipped` list. The list was returned and every caller discarded it, so an item
that failed validation kept existing as a file and stopped existing everywhere
else — no list, no query, no backlog view.

Nine items in this repository were invisible that way. One was titled "Cache
taxonomy rebuild indexes zero items in full pytest suite".

The reasons were mundane: `type: bug` where the vocabulary says `bug-fix`, and
provenance prose in `source`, which is an enum of auto|manual. Mundane is the
point — nothing about the failure was loud enough to notice, which is what let
it last.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
CACHE = REPO_ROOT / "scripts" / "cache.py"
DOCTOR = REPO_ROOT / "scripts" / "doctor.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import doctor as doc  # noqa: E402
from cache import _rebuild_cache  # noqa: E402


def _item(**overrides) -> str:
    fm = {"id": "ISSUE-001", "type": "bug-fix", "title": "t", "status": "new",
          "created": "2026-01-01T00:00:00+00:00", "source": "manual"}
    fm.update(overrides)
    return f"---\n{yaml.safe_dump(fm, default_flow_style=False, sort_keys=False)}---\n\nbody\n"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    p = tmp_path / "proj"
    (p / ".sweetclaude" / "state").mkdir(parents=True)
    (p / ".sweetclaude" / "state" / "sweetclaude.yaml").write_text(
        yaml.safe_dump({"schema_version": 2,
                        "framework": {"setup_complete": True}}), encoding="utf-8")
    (p / ".sweetclaude" / "artifact-privacy.yaml").write_text(
        yaml.safe_dump({"categories": {"product": {"base_path": ".sweetclaude/product"}}}),
        encoding="utf-8")
    (p / ".sweetclaude" / "product" / "backlog").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(p)],
                   capture_output=True, timeout=30)
    return p


def _write(project: Path, name: str, **overrides) -> Path:
    path = project / ".sweetclaude" / "product" / "backlog" / name
    path.write_text(_item(**overrides), encoding="utf-8")
    return path


# --- the rebuild says what it dropped ------------------------------------

def test_the_rebuild_records_what_it_skipped(project: Path) -> None:
    _write(project, "ISSUE-001-ok.md")
    _write(project, "ISSUE-002-bad.md", id="ISSUE-002", type="bug")

    result = _rebuild_cache(str(project))

    assert result["ingested"] == 1
    assert len(result["skipped"]) == 1
    assert "invalid type" in result["skipped"][0]["reasons"][0]


def _rebuild_cli(project: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CACHE), "--project-dir",
                           str(project), "--rebuild"],
                          capture_output=True, text=True, timeout=120)


def test_the_command_line_warns_on_stderr(project: Path) -> None:
    """The JSON always carried this. Callers capture stdout and throw it away,
    so the record existed and nobody ever saw it."""
    _write(project, "ISSUE-002-bad.md", id="ISSUE-002", type="bug")

    result = _rebuild_cli(project)

    assert "not indexed" in result.stderr
    assert "ISSUE-002-bad.md" in result.stderr
    assert "invalid type" in result.stderr


def test_the_warning_names_the_consequence_not_just_the_fault(
    project: Path
) -> None:
    """"invalid type" alone reads as a lint nit. The item vanishing from every
    query is the part that matters."""
    _write(project, "ISSUE-002-bad.md", id="ISSUE-002", type="bug")

    assert "invisible to every query" in _rebuild_cli(project).stderr


def test_a_clean_rebuild_says_nothing(project: Path) -> None:
    """A warning that fires on healthy projects gets ignored, which returns us
    to silence by another route."""
    _write(project, "ISSUE-001-ok.md")

    result = _rebuild_cli(project)

    assert result.stderr.strip() == ""


def test_stdout_stays_parseable_when_something_is_skipped(project: Path) -> None:
    """Callers parse stdout. Diagnostics belong on stderr or they break them."""
    _write(project, "ISSUE-002-bad.md", id="ISSUE-002", type="bug")

    assert json.loads(_rebuild_cli(project).stdout)["ingested"] == 0


# --- doctor reports it durably -------------------------------------------

def _findings(project: Path) -> list[doc.Finding]:
    return doc.check_unindexed_work_items(doc.build_project_state(project))


def test_doctor_reports_an_item_that_never_reached_the_index(
    project: Path
) -> None:
    _write(project, "ISSUE-002-bad.md", id="ISSUE-002", type="bug")

    findings = _findings(project)

    assert len(findings) == 1
    assert findings[0].id == "storage-lint:unindexed:work-items"
    assert findings[0].severity == "warning"


def test_the_finding_names_the_file_and_the_reason(project: Path) -> None:
    """Without both, nobody can act on it."""
    _write(project, "ISSUE-002-bad.md", id="ISSUE-002", type="bug")

    finding = _findings(project)[0]

    assert "ISSUE-002-bad.md" in finding.detail
    assert "invalid type" in finding.detail


def test_a_healthy_project_produces_no_finding(project: Path) -> None:
    _write(project, "ISSUE-001-ok.md")

    assert _findings(project) == []


def test_the_finding_reaches_a_full_scan(project: Path) -> None:
    """A check absent from the registry is a check nobody runs."""
    _write(project, "ISSUE-002-bad.md", id="ISSUE-002", type="bug")
    home = project.parent / "home"
    home.mkdir(exist_ok=True)

    result = subprocess.run([sys.executable, str(DOCTOR), "scan",
                             "--project-dir", str(project)],
                            capture_output=True, text=True, timeout=300,
                            env={**os.environ, "HOME": str(home)})
    payload = json.loads(result.stdout)

    assert "error" not in payload, payload.get("error")
    assert "storage-lint:unindexed:work-items" in [f["id"] for f in payload["findings"]]


# --- the two shapes that actually occurred --------------------------------

def test_a_legacy_type_alias_is_caught(project: Path) -> None:
    """Five of the nine. `bug` and `chore` predate the unified vocabulary."""
    _write(project, "ISSUE-002-bad.md", id="ISSUE-002", type="chore")

    assert _rebuild_cache(str(project))["skipped"]


def test_provenance_prose_in_the_source_enum_is_caught(project: Path) -> None:
    """The other four. `source` is auto|manual; these carried a sentence."""
    _write(project, "ISSUE-002-bad.md", id="ISSUE-002",
           source="MS-007 IMP-004 validation")

    skipped = _rebuild_cache(str(project))["skipped"]

    assert skipped and "source" in skipped[0]["reasons"][0]


@pytest.mark.skipif(
    not (REPO_ROOT / ".sweetclaude" / "product").is_dir(),
    reason="this repo's product tree is gitignored, so CI has none to check")
def test_this_repository_indexes_everything_it_has() -> None:
    """The regression guard for the nine that were corrected.

    Local only: `.sweetclaude/` is gitignored, so a CI checkout has no product
    tree and this would assert nothing while appearing to pass. Skipped there
    rather than left to look like coverage it is not.
    """
    result = _rebuild_cache(str(REPO_ROOT))

    assert result["skipped"] == [], [
        (Path(e["path"]).name, e["reasons"]) for e in result["skipped"]]
