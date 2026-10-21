"""Protections that cannot run say so (ISSUE-281 follow-up).

Three protections were switched off for months with no signal: the
work-in-progress limit, the phase-dwelling guard, and test-file immutability.
Each disabled itself because the state it needed was unreadable, allowed
whatever was happening, and said nothing. Allowing looked identical to
approving, which is why nobody noticed.

The properties defended here:

  * a genuinely broken protection is reported
  * a protection correctly standing down is NOT reported — crying wolf about
    normal conditions trains people to ignore the notice, which returns us to
    silence by another route
  * the notice reaches the session-start payload, not just a log nobody reads
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
SCRIPT = REPO_ROOT / "scripts" / "protection_status.py"
PREFLIGHT = REPO_ROOT / "hooks" / "session-preflight.sh"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import protection_status as ps  # noqa: E402


def _project(tmp_path: Path, *, sc: dict | None = None, gates: dict | None = None,
             guardian: bool = False, privacy: bool = False,
             mirror: dict | None = None) -> Path:
    p = tmp_path / "proj"
    state = p / ".sweetclaude" / "state"
    state.mkdir(parents=True)
    if sc is not None:
        (state / "sweetclaude.yaml").write_text(yaml.safe_dump(sc), encoding="utf-8")
    if gates is not None:
        (state / "effective-gates.yaml").write_text(yaml.safe_dump(gates), encoding="utf-8")
    if mirror is not None:
        (state / "phase.yaml").write_text(yaml.safe_dump(mirror), encoding="utf-8")
    if guardian:
        (state / "guardian-enabled").touch()
    if privacy:
        (state / "artifact-privacy.yaml").write_text(
            yaml.safe_dump({"categories": {"product": {"base_path": "docs/product"}}}),
            encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main", str(p)],
                   capture_output=True, timeout=30)
    return p


CONFIGURED = {"schema_version": 2, "framework": {"setup_complete": True},
              "work": {"active": {"id": "ISSUE-1", "phase": "IMPLEMENT"}}}


def _status(project: Path, name: str) -> dict:
    return next(r for r in ps.check_protections(project) if r["protection"] == name)


# --- broken protections are reported -------------------------------------

def test_wip_limit_is_active_without_a_phase(tmp_path: Path) -> None:
    """Kanban chosen and limit configured: R-078 applies the limit in any phase."""
    p = _project(tmp_path, sc={"schema_version": 2, "work": {"active": {}}},
                 gates={"mode": "kanban", "wip_limit": 2}, privacy=True)
    r = _status(p, "work-in-progress limit")
    assert r["status"] == ps.ACTIVE


def test_phase_dwelling_guard_is_reported_when_state_is_unreadable(
    tmp_path: Path
) -> None:
    p = _project(tmp_path, guardian=True)
    r = _status(p, "phase-dwelling guard")
    assert r["status"] == ps.INACTIVE
    assert "doctor" in r["fix"]


def test_artifact_placement_is_reported_without_a_manifest(tmp_path: Path) -> None:
    p = _project(tmp_path, sc=CONFIGURED)
    r = _status(p, "artifact placement")
    assert r["status"] == ps.INACTIVE


def test_every_inactive_protection_says_how_to_fix_it(tmp_path: Path) -> None:
    """A notice with no remedy is noise."""
    p = _project(tmp_path, sc={"schema_version": 2, "work": {"active": {}}},
                 gates={"mode": "kanban", "wip_limit": 2}, guardian=True)
    for r in ps.inactive_only(ps.check_protections(p)):
        assert r["fix"], f"{r['protection']} reports no fix"


# --- correct stand-downs are NOT reported --------------------------------

def test_a_healthy_project_reports_nothing(tmp_path: Path) -> None:
    """The most important negative. A notice that fires on normal conditions
    gets ignored, which returns us to silence by another route."""
    p = _project(tmp_path, sc=CONFIGURED, gates={"mode": "kanban", "wip_limit": 3},
                 privacy=True)
    assert ps.inactive_only(ps.check_protections(p)) == []
    assert ps.render(ps.check_protections(p)) == ""


def test_wip_limit_outside_kanban_is_not_a_fault(tmp_path: Path) -> None:
    p = _project(tmp_path, sc=CONFIGURED, gates={"mode": "flow"}, privacy=True)
    assert _status(p, "work-in-progress limit")["status"] == ps.NOT_APPLICABLE


def test_guardian_off_is_not_a_fault(tmp_path: Path) -> None:
    p = _project(tmp_path, sc=CONFIGURED, privacy=True)
    assert _status(p, "phase-dwelling guard")["status"] == ps.NOT_APPLICABLE


def test_no_tdd_cycle_running_is_not_a_fault(tmp_path: Path) -> None:
    """Tests are only frozen while implementing. Not being frozen the rest of
    the time is the design, not a broken protection."""
    p = _project(tmp_path, sc=CONFIGURED, privacy=True)
    assert _status(p, "test-file immutability")["status"] == ps.NOT_APPLICABLE


def test_an_unconfigured_project_reports_nothing(tmp_path: Path) -> None:
    """SweetClaude not being set up is not a protection failure."""
    p = tmp_path / "bare"
    p.mkdir()
    assert ps.inactive_only(ps.check_protections(p)) == []


# --- active protections are recognised -----------------------------------

def test_test_immutability_is_reported_active_while_implementing(tmp_path: Path) -> None:
    sc = dict(CONFIGURED)
    sc["work"] = {"active": {"id": "ISSUE-1", "phase": "IMPLEMENT",
                             "tdd_phase": "implementing"}}
    p = _project(tmp_path, sc=sc, privacy=True)
    assert _status(p, "test-file immutability")["status"] == ps.ACTIVE


def test_wip_limit_is_reported_active_when_it_can_run(tmp_path: Path) -> None:
    p = _project(tmp_path, sc=CONFIGURED, gates={"mode": "kanban", "wip_limit": 4},
                 privacy=True)
    r = _status(p, "work-in-progress limit")
    assert r["status"] == ps.ACTIVE
    assert "4" in r["reason"]


def test_the_legacy_mirror_still_satisfies_the_check(tmp_path: Path) -> None:
    """A project mid-migration must not be reported as broken."""
    p = _project(tmp_path, sc={"schema_version": 2, "work": {"active": {}}},
                 gates={"mode": "kanban", "wip_limit": 2},
                 mirror={"schema_version": 2, "phase": "IMPLEMENT"}, privacy=True)
    assert _status(p, "work-in-progress limit")["status"] == ps.ACTIVE


# --- robustness ----------------------------------------------------------

def test_corrupt_state_does_not_crash_the_check(tmp_path: Path) -> None:
    p = tmp_path / "corrupt"
    state = p / ".sweetclaude" / "state"
    state.mkdir(parents=True)
    (state / "sweetclaude.yaml").write_text("{ not: valid: yaml", encoding="utf-8")
    assert isinstance(ps.check_protections(p), list)


def test_every_protection_reports_a_known_status(tmp_path: Path) -> None:
    p = _project(tmp_path, sc=CONFIGURED, privacy=True)
    for r in ps.check_protections(p):
        assert r["status"] in {ps.ACTIVE, ps.INACTIVE, ps.NOT_APPLICABLE}
        assert r["reason"]


# --- the command line ----------------------------------------------------

def _cli(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), "--project-dir", str(project),
                           *args], capture_output=True, text=True, timeout=60)


def test_cli_exits_nonzero_when_something_is_inactive(tmp_path: Path) -> None:
    p = _project(tmp_path, sc={"schema_version": 2, "work": {"active": {}}},
                 gates={"mode": "kanban", "wip_limit": 2}, privacy=True)
    assert _cli(p).returncode == 1


def test_cli_exits_zero_and_prints_nothing_when_healthy(tmp_path: Path) -> None:
    p = _project(tmp_path, sc=CONFIGURED, gates={"mode": "kanban", "wip_limit": 3},
                 privacy=True)
    r = _cli(p)
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_cli_json_is_parseable(tmp_path: Path) -> None:
    p = _project(tmp_path, sc=CONFIGURED, privacy=True)
    payload = json.loads(_cli(p, "--format", "json", "--all").stdout)
    assert payload["protections"]


# --- it has to actually reach the user -----------------------------------

def test_the_notice_reaches_the_session_start_payload(tmp_path: Path) -> None:
    """A check nobody sees is the same as no check. This asserts the notice
    lands in the payload the session actually receives."""
    p = _project(tmp_path, sc={"schema_version": 2,
                               "framework": {"setup_complete": True},
                               "work": {"active": {}}},
                 gates={"mode": "kanban", "wip_limit": 2})
    (p / ".sweetclaude" / "state" / "session-state.yaml").write_text(
        yaml.safe_dump({"schema_version": 1}), encoding="utf-8")

    r = subprocess.run(["bash", str(PREFLIGHT)], cwd=str(p),
                       env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                            "HOME": str(p), "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
                       capture_output=True, text=True, timeout=120)
    payload = json.loads(r.stdout.strip().splitlines()[-1])
    context = payload.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "Some protections cannot run" in context
    assert "work-in-progress limit" in context


def test_a_healthy_project_adds_no_notice_to_the_payload(tmp_path: Path) -> None:
    p = _project(tmp_path, sc=CONFIGURED, gates={"mode": "kanban", "wip_limit": 3},
                 privacy=True)
    (p / ".sweetclaude" / "state" / "session-state.yaml").write_text(
        yaml.safe_dump({"schema_version": 1}), encoding="utf-8")

    r = subprocess.run(["bash", str(PREFLIGHT)], cwd=str(p),
                       env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                            "HOME": str(p), "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
                       capture_output=True, text=True, timeout=120)
    payload = json.loads(r.stdout.strip().splitlines()[-1])
    context = payload.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "Some protections cannot run" not in context


def test_session_preflight_invokes_the_check() -> None:
    """Guard against the wiring being dropped while the script survives."""
    assert "protection_status.py" in PREFLIGHT.read_text(encoding="utf-8")
