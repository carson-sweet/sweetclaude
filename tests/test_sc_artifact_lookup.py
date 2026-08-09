"""The storage adapter resolves the layout the project actually has (ISSUE-289).

`sc_artifact_read ISSUE-284` returned `{}` while the file sat in
`roadmap/issues/done/`. Three separate faults stacked, and each on its own was
enough to make every issue invisible:

  * the id prefix map knew `I-025` and not `ISSUE-284`, so the type never
    resolved at all
  * `issue` mapped to `product/issues`, which holds one index file; issues live
    in `roadmap/issues/`, `roadmap/issues/done/` and `backlog/`
  * the lookup globbed one directory level, so `done/` and `archived/` were
    invisible for every type

`milestone` had the second fault too — 10 files in `roadmap/milestones/`,
mapped to `milestones/`.

Empty is a legitimate answer for an id that does not exist, so 14 skills
sourcing this adapter could not tell "no such issue" from "the lookup had
nowhere to look". That is the reason it survived: it never looked broken.

These tests run against the real repository layout as well as fixtures. A
fixture built to match the current mapping would have passed throughout.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
IMPL = REPO_ROOT / "hooks" / "sc-artifact-impl.py"
ADAPTER = REPO_ROOT / "hooks" / "sc-artifact.sh"
REAL_PRODUCT = REPO_ROOT / ".sweetclaude" / "product"


def _impl():
    spec = importlib.util.spec_from_file_location("sc_artifact_impl", IMPL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


impl = _impl()

real_layout = pytest.mark.skipif(
    not (REAL_PRODUCT / "roadmap" / "issues").is_dir(),
    reason="runs against this repository's own product tree")


# --- the prefix map --------------------------------------------------------

def test_the_current_id_prefix_resolves() -> None:
    """The taxonomy moved to ISSUE-NNN and the map still only knew I-NNN, so
    the type lookup failed before any directory was consulted."""
    assert impl.PREFIX_TO_TYPE.get("ISSUE") == "issue"


def test_the_legacy_id_prefix_still_resolves() -> None:
    """37 pre-unification ids survive in backlog/archived/. Terminal, but a
    lookup by id must still find one."""
    assert impl.PREFIX_TO_TYPE.get("I") == "issue"


def test_create_assigns_the_current_prefix() -> None:
    """TYPE_TO_PREFIX used to be derived by inverting PREFIX_TO_TYPE, which
    hands `issue` whichever alias was declared last — so adding the current
    prefix could have silently made `create` emit legacy ids."""
    assert impl.TYPE_TO_PREFIX["issue"] == "ISSUE"


def test_every_type_knows_all_of_its_prefixes() -> None:
    assert set(impl.TYPE_TO_PREFIXES["issue"]) == {"ISSUE", "I"}


# --- directory resolution --------------------------------------------------

@real_layout
def test_an_issue_in_the_roadmap_tree_resolves() -> None:
    found = impl._find_file(REAL_PRODUCT, "ISSUE-001")
    assert found is not None and found.name.startswith("ISSUE-001")


@real_layout
def test_an_issue_in_a_terminal_subdirectory_resolves() -> None:
    """done/ is one level below the search root. The old lookup used iterdir,
    so everything completed was invisible."""
    done = sorted((REAL_PRODUCT / "roadmap" / "issues" / "done").glob("ISSUE-*.md"))
    assert done, "fixture assumption: this repo has completed issues"
    entity_id = done[0].name.split("-", 2)[0] + "-" + done[0].name.split("-")[1]

    assert impl._find_file(REAL_PRODUCT, entity_id) == done[0]


@real_layout
def test_an_issue_in_the_backlog_resolves() -> None:
    backlog = sorted((REAL_PRODUCT / "backlog").glob("ISSUE-*.md"))
    assert backlog, "fixture assumption: this repo has untriaged issues"
    entity_id = "-".join(backlog[0].name.split("-")[:2])

    assert impl._find_file(REAL_PRODUCT, entity_id) == backlog[0]


@real_layout
def test_a_legacy_id_in_the_archive_resolves() -> None:
    archived = sorted((REAL_PRODUCT / "backlog" / "archived").glob("I-*.md"))
    assert archived, "fixture assumption: this repo has archived legacy items"
    entity_id = "-".join(archived[0].name.split("-")[:2])

    assert impl._find_file(REAL_PRODUCT, entity_id) == archived[0]


@real_layout
def test_a_milestone_resolves() -> None:
    """The same directory fault as issues, on a second type."""
    files = sorted((REAL_PRODUCT / "roadmap" / "milestones").glob("MS-*.md"))
    assert files, "fixture assumption: this repo has milestones"
    entity_id = "-".join(files[0].name.split("-")[:2])

    assert impl._find_file(REAL_PRODUCT, entity_id) == files[0]


# --- the property that would have caught all of it -------------------------

@real_layout
@pytest.mark.parametrize("entity_type", sorted(impl.TYPE_TO_PREFIX))
def test_every_type_finds_every_file_that_exists_for_it(entity_type: str) -> None:
    """Asserted against what is on disk rather than against the mapping, so a
    mapping that points nowhere fails instead of agreeing with itself.

    Types with no artifacts in this repo pass trivially — they assert 0 == 0,
    which is honest: nothing here has verified them.
    """
    prefixes = impl.TYPE_TO_PREFIXES[entity_type]
    on_disk = {p.name for pre in prefixes
               for p in REAL_PRODUCT.rglob(f"{pre}-*.md")}
    found = {p.name for p in impl._artifact_files(
        REAL_PRODUCT, entity_type, impl.TYPE_TO_PREFIX[entity_type])}

    assert on_disk - found == set(), sorted(on_disk - found)[:10]


@real_layout
def test_the_types_this_repo_can_actually_verify() -> None:
    """Names which types the parametrised check above is real for, so a future
    reader does not mistake trivial passes for coverage."""
    verified = {t for t in impl.TYPE_TO_PREFIX
                if impl._artifact_files(REAL_PRODUCT, t, impl.TYPE_TO_PREFIX[t])}

    assert verified == {"issue", "epic", "milestone"}, verified


# --- an absent id is not the same as a broken lookup -----------------------

def _read(project: Path, entity_id: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(IMPL), "read", str(project),
         str(project / ".sweetclaude" / "product"),
         str(project / ".sweetclaude" / "state"), entity_id],
        capture_output=True, text=True, timeout=60)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / ".sweetclaude" / "product").mkdir(parents=True)
    (tmp_path / ".sweetclaude" / "state").mkdir(parents=True)
    return tmp_path


def test_a_lookup_with_nowhere_to_look_says_so(project: Path) -> None:
    """The condition that hid this for as long as it lasted."""
    r = _read(project, "ISSUE-1")

    assert r.stdout == "{}"
    assert "layout problem" in r.stderr
    assert "not a missing ISSUE-1" in r.stderr


def test_a_genuinely_absent_id_is_quiet(project: Path) -> None:
    """Otherwise every ordinary miss becomes a warning and the signal is lost."""
    (project / ".sweetclaude" / "product" / "backlog").mkdir()

    r = _read(project, "ISSUE-1")

    assert r.stdout == "{}"
    assert r.stderr.strip() == ""


def test_an_unknown_prefix_names_the_ones_that_exist(project: Path) -> None:
    r = _read(project, "WAT-1")

    assert r.stdout == "{}"
    assert "unknown id prefix" in r.stderr
    assert "ISSUE" in r.stderr


def test_stdout_stays_parseable_in_every_failure_mode(project: Path) -> None:
    """Callers parse stdout. Diagnostics belong on stderr or they break them."""
    for entity_id in ("ISSUE-1", "WAT-1"):
        assert json.loads(_read(project, entity_id).stdout) == {}


# --- through the shell adapter, as skills call it --------------------------

def _via_adapter(snippet: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-c", f'source "{ADAPTER}"\n{snippet}\n'],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120)


@real_layout
def test_skills_reading_an_issue_get_the_issue() -> None:
    """14 skills source this adapter. This is the call they make."""
    r = _via_adapter("sc_artifact_read ISSUE-001")

    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["id"] == "ISSUE-001"


@real_layout
def test_skills_listing_issues_get_more_than_nothing() -> None:
    """`sc_artifact_list issue` returned [] for the entire life of the project.
    A skill asking what work exists was told there is none."""
    r = _via_adapter("sc_artifact_list issue")

    assert len(json.loads(r.stdout)) > 100, r.stdout[:200]
