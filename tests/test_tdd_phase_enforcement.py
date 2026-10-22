"""Test-file freezing is actually enforced (ISSUE-282).

`rules/tdd-levels.md` promised "test files are immutable during
implementation". The guardian hook checked for `tdd_phase: implementing` and
nothing in the repo ever wrote that value, so the block never fired. The rule
had never once been enforced.

The existing hook tests passed throughout, because they wrote `tdd_phase`
into their own fixtures — correct logic, verified against input the system
never produced. That is the specific failure this file is written to avoid,
so **no test here hand-writes the marker.** Every one drives
`scripts/tdd_phase.py`, which is what `skill-library/build/code-tdd/SKILL.md` invokes.

The honest limit: a test cannot make the model follow a skill. What is proven
here is that the mechanism the skill calls produces the enforcement it claims.
Whether the model calls it is a behavioural question, and belongs to the
external-judge harness.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
TDD_PHASE = REPO_ROOT / "scripts" / "tdd_phase.py"
GUARDIAN = REPO_ROOT / "hooks" / "test-guardian.sh"
SKILL = REPO_ROOT / "skill-library" / "build" / "code-tdd" / "SKILL.md"
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))

import tdd_phase as tp  # noqa: E402
from hook_stdin import deny_reason, payload, run_hook, verdict  # noqa: E402


@pytest.fixture
def project(tmp_path: Path) -> Path:
    p = tmp_path / "proj"
    state = p / ".sweetclaude" / "state"
    state.mkdir(parents=True)
    (p / "tests").mkdir()
    (p / "src").mkdir()
    (state / "sweetclaude.yaml").write_text(yaml.safe_dump({
        "schema_version": 2,
        "framework": {"setup_complete": True},
        "work": {"active": {"id": "ISSUE-1", "phase": "IMPLEMENT"}},
    }), encoding="utf-8")
    (state / "project.yaml").write_text(yaml.safe_dump({"schema_version": 1}),
                                        encoding="utf-8")
    (p / "tests" / "test_thing.py").write_text("def test_x(): assert True\n",
                                               encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main", str(p)],
                   capture_output=True, timeout=30)
    return p


def set_phase(project: Path, phase: str) -> dict:
    """Drive the same entry point the skill calls. Never write the marker directly."""
    r = subprocess.run([sys.executable, str(TDD_PHASE), "set", "--phase", phase,
                        "--project-dir", str(project)],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def clear_phase(project: Path) -> None:
    subprocess.run([sys.executable, str(TDD_PHASE), "clear",
                    "--project-dir", str(project)],
                   capture_output=True, text=True, timeout=60, check=True)


def guardian_run(project: Path, rel: str) -> subprocess.CompletedProcess:
    stdin = payload("PreToolUse-Edit", project, file_path=str(project / rel))
    return run_hook("test-guardian.sh", project, stdin)


def edit(project: Path, rel: str) -> bool:
    """Run the guardian for an edit. True = allowed, False = denied."""
    r = guardian_run(project, rel)
    outcome = verdict(r)
    if outcome == "deny":
        return False
    if outcome == "allow":
        return True
    raise AssertionError(f"guardian gave no valid decision: exit={r.returncode} {r.stdout!r} {r.stderr!r}")


# --- the whole point -----------------------------------------------------

def test_tests_are_frozen_once_implementation_starts(project: Path) -> None:
    """The promise in rules/tdd-levels.md, asserted end to end for the first
    time. The marker is set through the same script the skill calls."""
    assert edit(project, "tests/test_thing.py") is True, "frozen before RED"

    set_phase(project, "writing_tests")
    assert edit(project, "tests/test_thing.py") is True, "frozen while writing tests"

    set_phase(project, "implementing")
    assert edit(project, "tests/test_thing.py") is False, (
        "test file was editable during implementation — the rule is not enforced")


def test_source_stays_writable_while_tests_are_frozen(project: Path) -> None:
    """Freezing tests must not freeze the code you are meant to be fixing."""
    set_phase(project, "implementing")
    assert edit(project, "src/thing.py") is True


def test_the_freeze_releases_when_the_cycle_returns_to_writing_tests(
    project: Path
) -> None:
    set_phase(project, "implementing")
    assert edit(project, "tests/test_thing.py") is False

    set_phase(project, "writing_tests")
    assert edit(project, "tests/test_thing.py") is True


def test_clearing_the_marker_releases_the_freeze(project: Path) -> None:
    set_phase(project, "implementing")
    assert edit(project, "tests/test_thing.py") is False

    clear_phase(project)
    assert edit(project, "tests/test_thing.py") is True


def test_refactoring_does_not_freeze_tests(project: Path) -> None:
    set_phase(project, "refactoring")
    assert edit(project, "tests/test_thing.py") is True


def test_the_block_says_what_to_do_instead(project: Path) -> None:
    set_phase(project, "implementing")
    r = guardian_run(project, "tests/test_thing.py")
    assert "Fix your code, not the tests" in deny_reason(r)


# --- where the marker lives ----------------------------------------------

def test_the_marker_is_written_to_the_canonical_state_file(project: Path) -> None:
    set_phase(project, "implementing")
    sc = yaml.safe_load(
        (project / ".sweetclaude" / "state" / "sweetclaude.yaml").read_text())
    assert sc["work"]["active"]["tdd_phase"] == "implementing"


def test_setting_the_marker_does_not_create_the_legacy_mirror(project: Path) -> None:
    """Creating phase.yaml would resurrect the file every v4 consumer stopped
    reading (ISSUE-251)."""
    set_phase(project, "implementing")
    assert not (project / ".sweetclaude" / "state" / "phase.yaml").exists()


def test_an_existing_mirror_is_kept_in_step(project: Path) -> None:
    """The story controllers maintain phase.yaml while a workflow runs. If it
    is there, it must not go stale."""
    mirror = project / ".sweetclaude" / "state" / "phase.yaml"
    mirror.write_text(yaml.safe_dump({"schema_version": 2, "phase": "IMPLEMENT"}),
                      encoding="utf-8")

    result = set_phase(project, "implementing")

    assert result["mirrored_to_phase_yaml"] is True
    assert yaml.safe_load(mirror.read_text())["tdd_phase"] == "implementing"


def test_the_marker_survives_alongside_other_active_work_state(project: Path) -> None:
    """Writing the marker must not clobber the work item it belongs to."""
    set_phase(project, "implementing")
    active = yaml.safe_load(
        (project / ".sweetclaude" / "state" / "sweetclaude.yaml").read_text()
    )["work"]["active"]
    assert active["id"] == "ISSUE-1"
    assert active["phase"] == "IMPLEMENT"


# --- the writer's own contract -------------------------------------------

def test_reading_back_what_was_written(project: Path) -> None:
    set_phase(project, "implementing")
    assert tp.get_phase(project) == "implementing"


def test_an_unset_marker_reads_as_none(project: Path) -> None:
    assert tp.get_phase(project) is None


@pytest.mark.parametrize("phase", ["writing_tests", "implementing", "refactoring"])
def test_every_valid_phase_is_accepted(project: Path, phase: str) -> None:
    assert set_phase(project, phase)["tdd_phase"] == phase


def test_an_invalid_phase_is_refused(project: Path) -> None:
    r = subprocess.run([sys.executable, str(TDD_PHASE), "set", "--phase", "nonsense",
                        "--project-dir", str(project)],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode != 0


def test_an_unconfigured_project_is_refused_not_silently_created(tmp_path: Path) -> None:
    """Writing state into a project that has none would fabricate a
    half-configured project."""
    r = subprocess.run([sys.executable, str(TDD_PHASE), "set", "--phase", "implementing",
                        "--project-dir", str(tmp_path)],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 2
    assert not (tmp_path / ".sweetclaude").exists()


def test_only_implementing_reports_tests_as_frozen(project: Path) -> None:
    assert set_phase(project, "implementing")["tests_frozen"] is True
    assert set_phase(project, "writing_tests")["tests_frozen"] is False
    assert set_phase(project, "refactoring")["tests_frozen"] is False


# --- the skill has to actually call it -----------------------------------

def test_the_skill_records_the_freeze_at_its_transition_points() -> None:
    """The mechanism is worthless if the process never invokes it. This is the
    exact gap that left the rule unenforced."""
    text = SKILL.read_text(encoding="utf-8")
    assert "tdd_phase.py set --phase implementing" in text, (
        "code-tdd never records that implementation has started")
    assert "tdd_phase.py set --phase writing_tests" in text or \
           "tdd_phase.py clear" in text, (
        "code-tdd never releases the freeze, so tests stay locked afterwards")


def test_the_documented_rule_no_longer_overclaims() -> None:
    """The rule text used to state the hook enforced this, full stop. It only
    does so once the marker is recorded, and saying otherwise is how this went
    unnoticed."""
    text = SKILL.read_text(encoding="utf-8")
    section = text.split("### Tests Are Immutable During Implementation", 1)[1]
    section = section.split("###", 1)[0]
    assert "tdd_phase" in section, "the rule does not say what enforcement depends on"


def test_nothing_in_this_file_hand_writes_the_marker() -> None:
    """Guard against this suite drifting into the failure it exists to catch:
    a green test that supplies the state the system is supposed to produce."""
    source = Path(__file__).read_text(encoding="utf-8")
    body = source.split('"""', 2)[2]
    offenders = [
        line.strip() for line in body.splitlines()
        if re.search(r"tdd_phase\s*[\"']?\s*[:=]", line)
        and "safe_dump" in line or re.search(r'["\']tdd_phase["\']\s*:', line)
    ]
    assert not offenders, (
        "a test writes tdd_phase directly instead of driving tdd_phase.py: "
        f"{offenders}")


# --- test-file detection is about the project, not the disk ---------------

def test_a_source_file_is_not_a_test_because_of_where_the_project_lives(
    tmp_path: Path
) -> None:
    """Found while writing this suite: the guardian matched its test-file
    patterns against the absolute path, so a project checked out beneath a
    directory named e.g. `test_harness_run` had every source file refused
    during implementation. Whether a file is a test is a property of its path
    within the project.
    """
    parent = tmp_path / "test_harness_run"
    project = parent / "myapp"
    state = project / ".sweetclaude" / "state"
    state.mkdir(parents=True)
    (project / "src").mkdir()
    (state / "sweetclaude.yaml").write_text(yaml.safe_dump({
        "schema_version": 2, "framework": {"setup_complete": True},
        "work": {"active": {"phase": "IMPLEMENT"}}}), encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main", str(project)],
                   capture_output=True, timeout=30)
    set_phase(project, "implementing")

    assert edit(project, "src/thing.py") is True, (
        "a source file was refused because a directory above the project "
        "contained 'test_'")


def test_real_test_files_are_still_detected_in_such_a_project(tmp_path: Path) -> None:
    """The fix must not stop the guardian recognising genuine test files."""
    project = tmp_path / "tests_dir_parent" / "myapp"
    state = project / ".sweetclaude" / "state"
    state.mkdir(parents=True)
    (project / "tests").mkdir()
    (state / "sweetclaude.yaml").write_text(yaml.safe_dump({
        "schema_version": 2, "framework": {"setup_complete": True},
        "work": {"active": {"phase": "IMPLEMENT"}}}), encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main", str(project)],
                   capture_output=True, timeout=30)
    set_phase(project, "implementing")

    assert edit(project, "tests/test_thing.py") is False


def test_gherkin_specs_are_frozen_too(project: Path) -> None:
    set_phase(project, "implementing")
    assert edit(project, "src/login.feature") is False
