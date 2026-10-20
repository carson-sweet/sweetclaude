"""Output-contract coverage for the three _migrate helpers (ISSUE-253).

skill-library/configure/_migrate/SKILL.md shells out to these at lines 45, 54, and 145 and
parses one line of stdout. The contract is the prefix before the pipe. If a
helper crashes or changes its prefix, the skill misreads the result and can
proceed as though a snapshot exists when it does not.

Invoked as subprocesses on purpose — that is how the skill calls them, and it
is the only way to cover the argv handling and the import-failure branch.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
MIGRATIONS = REPO_ROOT / "scripts" / "migrations"
RUNNER = MIGRATIONS / "runner.py"

SNAPSHOT = MIGRATIONS / "run_snapshot.py"
MIGRATE = MIGRATIONS / "run_migrate.py"
ROLLBACK = MIGRATIONS / "run_rollback.py"


def _run(script: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True, text=True, timeout=120,
        cwd=str(cwd) if cwd else None,
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A minimal project with v1 state on disk."""
    state = tmp_path / ".sweetclaude" / "state"
    state.mkdir(parents=True)
    (state / "sweetclaude.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "project": {"name": "fixture"}}),
        encoding="utf-8",
    )
    return tmp_path


# --- argv contracts ------------------------------------------------------

def test_snapshot_without_args_reports_usage_and_fails() -> None:
    r = _run(SNAPSHOT)
    assert r.returncode == 1
    assert r.stdout.startswith("SNAPSHOT_FAILED|usage:")


def test_migrate_without_args_reports_usage_as_json_error() -> None:
    r = _run(MIGRATE)
    assert r.returncode == 1
    assert "usage" in json.loads(r.stdout)["error"]


def test_rollback_without_args_reports_usage_and_fails() -> None:
    r = _run(ROLLBACK)
    assert r.returncode == 1
    assert r.stdout.startswith("ROLLBACK_FAIL|usage:")


def test_rollback_with_only_runner_arg_still_reports_usage() -> None:
    """Rollback needs runner AND snapshot json; one arg must not slip through."""
    r = _run(ROLLBACK, str(RUNNER))
    assert r.returncode == 1
    assert r.stdout.startswith("ROLLBACK_FAIL|usage:")


# --- runner resolution (ISSUE-267) --------------------------------------
#
# These helpers used to accept a runner_path and then ignore it: Python puts a
# script's own directory on sys.path[0], so `from runner import ...` resolved
# to the sibling before the inserted path was ever consulted. They now load
# runner_path by explicit file location when it exists and fall back to the
# sibling when it does not. The fallback is what kept migrations working while
# the argument was ignored, so dropping it would turn a stale $RUNNER into a
# hard failure.

@pytest.mark.parametrize("script", [SNAPSHOT, MIGRATE, ROLLBACK], ids=lambda p: p.stem)
def test_missing_runner_path_falls_back_to_the_sibling(
    script: Path, tmp_path: Path, project: Path
) -> None:
    """A stale or empty $RUNNER must not break an otherwise working install."""
    args = [str(tmp_path / "nowhere" / "runner.py")]
    if script is ROLLBACK:
        args.append("{}")
    args.append(str(project))
    r = _run(script, *args)
    assert "cannot import runner" not in r.stdout, r.stdout
    assert "Traceback" not in r.stderr


def test_explicit_runner_path_is_actually_used(tmp_path: Path) -> None:
    """Proof the argument is honoured rather than quietly ignored: point it at
    a copy of the runner carrying a marker, and observe the marker."""
    alt_dir = tmp_path / "other-install"
    alt_dir.mkdir()
    alt_runner = alt_dir / "runner.py"
    marker = "MARKER_FROM_THE_EXPLICIT_RUNNER"
    alt_runner.write_text(
        (MIGRATIONS / "runner.py").read_text(encoding="utf-8")
        + f'\n\nEXPLICIT_RUNNER_MARKER = "{marker}"\n',
        encoding="utf-8",
    )

    probe = tmp_path / "probe_explicit.py"
    probe.write_text(
        "import importlib.util\n"
        f"spec = importlib.util.spec_from_file_location('h', r'{SNAPSHOT}')\n"
        "mod = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(mod)\n"
        f"runner_mod = mod._import_runner(r'{alt_runner}')\n"
        "print(getattr(runner_mod, 'EXPLICIT_RUNNER_MARKER', 'NOT_THE_EXPLICIT_RUNNER'))\n",
        encoding="utf-8",
    )
    r = subprocess.run([sys.executable, str(probe)], capture_output=True,
                       text=True, timeout=120)
    assert marker in r.stdout, r.stdout + r.stderr


def test_runner_resolution_raises_when_neither_path_exists(tmp_path: Path) -> None:
    """Both candidates missing is a broken install, not a fallback case."""
    isolated = tmp_path / "install"
    isolated.mkdir()
    copy = isolated / SNAPSHOT.name
    copy.write_text(SNAPSHOT.read_text(encoding="utf-8"), encoding="utf-8")

    probe = tmp_path / "probe_absent.py"
    probe.write_text(
        "import importlib.util\n"
        f"spec = importlib.util.spec_from_file_location('h', r'{copy}')\n"
        "mod = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(mod)\n"
        "try:\n"
        f"    mod._import_runner(r'{isolated / 'nope.py'}')\n"
        "    print('NO_ERROR')\n"
        "except ImportError:\n"
        "    print('IMPORT_ERROR')\n",
        encoding="utf-8",
    )
    r = subprocess.run([sys.executable, str(probe)], capture_output=True,
                       text=True, timeout=120)
    assert "IMPORT_ERROR" in r.stdout, r.stdout + r.stderr


@pytest.mark.parametrize(
    "script,prefix",
    [(SNAPSHOT, "SNAPSHOT_FAILED|cannot import runner"),
     (ROLLBACK, "ROLLBACK_FAIL|cannot import runner")],
)
def test_helper_reports_absent_runner_rather_than_traceback(
    script: Path, prefix: str, tmp_path: Path, project: Path
) -> None:
    """Broken install: the helper is present but runner.py beside it is not."""
    isolated = tmp_path / "install" / "migrations"
    isolated.mkdir(parents=True)
    copy = isolated / script.name
    copy.write_text(script.read_text(encoding="utf-8"), encoding="utf-8")

    args = [str(isolated / "runner.py")]
    if script is ROLLBACK:
        args.append("{}")
    args.append(str(project))

    r = _run(copy, *args)
    assert r.returncode == 1
    assert r.stdout.startswith(prefix), r.stdout
    assert "Traceback" not in r.stderr


def test_migrate_reports_absent_runner_as_json_error(tmp_path: Path, project: Path) -> None:
    isolated = tmp_path / "install" / "migrations"
    isolated.mkdir(parents=True)
    copy = isolated / MIGRATE.name
    copy.write_text(MIGRATE.read_text(encoding="utf-8"), encoding="utf-8")

    r = _run(copy, str(isolated / "runner.py"), str(project))
    assert r.returncode == 1
    assert "cannot import runner" in json.loads(r.stdout)["error"]


# --- rollback input validation ------------------------------------------

@pytest.mark.parametrize("junk", ["not json", "[]", "{}", '{"unexpected_key": 1}'])
def test_rollback_rejects_unusable_snapshot_json(junk: str, project: Path) -> None:
    """A malformed snapshot must fail closed. Rollback is the last line of
    defence; it must never silently no-op and report success."""
    r = _run(ROLLBACK, str(RUNNER), junk, str(project))
    assert r.returncode == 1
    assert r.stdout.startswith("ROLLBACK_FAIL|"), r.stdout
    assert not r.stdout.startswith("ROLLBACK_OK")


def test_rollback_fails_when_snapshot_tarball_is_missing(project: Path) -> None:
    """Snapshot JSON that parses but points at a tarball that no longer
    exists — the state after someone cleans out backups/."""
    snap = json.dumps({
        "tarball_path": str(project / ".sweetclaude" / "state" / "backups" / "gone.tar.gz"),
        "git_tag": "",
        "git_tag_created": False,
        "git_stash_ref": None,
        "created_at": "2026-08-08T00:00:00Z",
        "source_paths": [".sweetclaude"],
    })
    r = _run(ROLLBACK, str(RUNNER), snap, str(project))
    assert r.returncode == 1
    assert r.stdout.startswith("ROLLBACK_FAIL|"), r.stdout


# --- snapshot marker handling -------------------------------------------

def test_snapshot_ignores_unparseable_marker_and_does_not_reuse_it(project: Path) -> None:
    """A corrupt pending-migration-snapshot.json must not be trusted as a
    valid prior snapshot — that would skip taking a real one."""
    marker = project / ".sweetclaude" / "state" / "pending-migration-snapshot.json"
    marker.write_text("{ this is not json", encoding="utf-8")

    r = _run(SNAPSHOT, str(RUNNER), str(project))
    # Either it takes a fresh snapshot or it fails; it must not report OK with
    # the corrupt marker's contents.
    assert "this is not json" not in r.stdout
    if r.stdout.startswith("SNAPSHOT_OK|"):
        payload = json.loads(r.stdout.split("|", 1)[1])
        assert Path(payload["tarball_path"]).exists()


def test_snapshot_does_not_reuse_marker_whose_tarball_vanished(project: Path) -> None:
    marker = project / ".sweetclaude" / "state" / "pending-migration-snapshot.json"
    marker.write_text(json.dumps({
        "tarball_path": str(project / "backups" / "vanished.tar.gz"),
        "git_tag": "",
    }), encoding="utf-8")

    r = _run(SNAPSHOT, str(RUNNER), str(project))
    assert "vanished.tar.gz" not in r.stdout


# --- migrate on a project with nothing to do ----------------------------

def _git_project(tmp_path: Path) -> Path:
    """Committed git project with v1 state, .sweetclaude/ gitignored."""
    proj = tmp_path / "gitproj"
    (proj / ".sweetclaude" / "state").mkdir(parents=True)
    (proj / ".gitignore").write_text(".sweetclaude/\n", encoding="utf-8")
    (proj / ".sweetclaude" / "state" / "phase.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "phase": "IMPLEMENT",
                        "work_type": "refactor"}), encoding="utf-8")
    (proj / "README.md").write_text("tracked\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main", str(proj)],
                   capture_output=True, text=True, timeout=30)
    for args in (["config", "user.email", "t@t.invalid"], ["config", "user.name", "T"],
                 ["add", "-A"], ["commit", "-q", "-m", "init"]):
        subprocess.run(["git", "-C", str(proj), *args], capture_output=True, timeout=30)
    return proj


def test_snapshot_success_path_writes_marker_and_reports_ok(tmp_path: Path) -> None:
    proj = _git_project(tmp_path)
    r = _run(SNAPSHOT, str(RUNNER), str(proj))

    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.startswith("SNAPSHOT_OK|")
    payload = json.loads(r.stdout.split("|", 1)[1])
    assert Path(payload["tarball_path"]).exists()

    marker = proj / ".sweetclaude" / "state" / "pending-migration-snapshot.json"
    assert marker.exists(), "helper must persist the snapshot marker for rollback"
    assert json.loads(marker.read_text())["tarball_path"] == payload["tarball_path"]


def test_snapshot_is_idempotent_and_reuses_a_valid_marker(tmp_path: Path) -> None:
    """Step 1 can re-run after an interrupted migration. It must reuse the
    existing snapshot rather than stacking duplicates."""
    proj = _git_project(tmp_path)
    first = json.loads(_run(SNAPSHOT, str(RUNNER), str(proj)).stdout.split("|", 1)[1])
    second = json.loads(_run(SNAPSHOT, str(RUNNER), str(proj)).stdout.split("|", 1)[1])

    assert first["tarball_path"] == second["tarball_path"]
    assert first["git_tag"] == second["git_tag"]


def test_rollback_success_path_restores_and_clears_the_marker(tmp_path: Path) -> None:
    """The full skill sequence: snapshot at line 45, migrate at 54, roll back
    at 145 — all three through the subprocess interface the skill uses."""
    proj = _git_project(tmp_path)
    phase = proj / ".sweetclaude" / "state" / "phase.yaml"
    marker = proj / ".sweetclaude" / "state" / "pending-migration-snapshot.json"

    before = phase.read_bytes()
    snap_out = _run(SNAPSHOT, str(RUNNER), str(proj))
    snapshot_json = snap_out.stdout.split("|", 1)[1].strip()

    assert _run(MIGRATE, str(RUNNER), str(proj)).returncode == 0
    assert phase.read_bytes() != before, "migration did not change state"

    r = _run(ROLLBACK, str(RUNNER), snapshot_json, str(proj))
    assert r.returncode == 0, r.stdout
    assert r.stdout.startswith("ROLLBACK_OK|")
    assert phase.read_bytes() == before, "rollback did not restore state"
    assert not marker.exists(), "successful rollback must clear the pending marker"


def test_migrate_emits_json_array_and_exits_zero(project: Path) -> None:
    """run_migrate always prints a JSON array of per-file results. The skill
    parses this; a bare string or a traceback would break Step 2."""
    r = _run(MIGRATE, str(RUNNER), str(project))
    assert r.returncode == 0, r.stderr
    results = json.loads(r.stdout)
    assert isinstance(results, list)
    for entry in results:
        assert {"file_key", "success", "target_version"} <= set(entry)
