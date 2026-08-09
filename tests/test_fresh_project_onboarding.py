"""End-to-end verification of fresh-project onboarding (ISSUE-274).

This session opened with a user hitting an error initializing a brand new
project. ISSUE-249 diagnosed the cause and rewrote init as a dispatcher — from
reading code. Nobody ran it. There was no end-to-end onboarding test anywhere
in the suite, only migration and upgrade paths.

Skills are model-executed instructions, so a test cannot invoke one. Two things
it can do:

  * Extract and execute the Python block that init's state detection actually
    is, so an edit to the skill changes what this test runs. That is the
    routing decision itself, not a reimplementation of it.
  * Follow setup's documented write sequence against a temp project and assert
    the result is consumable by the things that read it — doctor, the session
    state hook, the drift runner.

What it cannot verify is whether the model follows the instructions. That gap
is ISSUE-275's, and it is why this file asserts state and routing rather than
behavior.
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
INIT_SKILL = REPO_ROOT / "skills" / "init" / "SKILL.md"
TEMPLATE = REPO_ROOT / "scripts" / "sweetclaude-yaml-template.py"
DOCTOR = REPO_ROOT / "scripts" / "doctor.py"
SESSION_STATE = REPO_ROOT / "hooks" / "generate-session-state.sh"
RUNNER = REPO_ROOT / "scripts" / "migrations" / "runner.py"
REGISTRY = REPO_ROOT / "config" / "migration-registry.yaml"


# --- init's real detection block ----------------------------------------

def _init_detection_source() -> str:
    """Pull the Python heredoc out of init's Step 2.

    Executing the skill's own code means a change to the skill is a change to
    what this test exercises. A copy would drift the moment someone edited
    the skill, which is the failure mode ISSUE-249 was.
    """
    text = INIT_SKILL.read_text(encoding="utf-8")
    blocks = re.findall(r"```bash\n(.*?)```", text, re.S)
    for block in blocks:
        m = re.search(r"python3 - << 'PY'\n(.*?)\nPY", block, re.S)
        if m and "STATE=" in m.group(1):
            return m.group(1)
    raise AssertionError("init's state-detection block not found — did Step 2 change?")


def _detect(project: Path) -> dict[str, str]:
    src = _init_detection_source()
    proc = subprocess.run([sys.executable, "-c", src], cwd=str(project),
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    out = {}
    for line in proc.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def test_init_detection_block_is_present_and_runnable() -> None:
    assert "STATE=" in _init_detection_source()


# --- setup's documented write sequence ----------------------------------

def _onboard(project: Path, *, name: str = "fixture", ptype: str = "new",
             stage: str = "IDEA") -> None:
    """Follow skills/setup/SKILL.md: write state, then build v4 storage."""
    state = project / ".sweetclaude" / "state"
    state.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [sys.executable, str(TEMPLATE), "--name", name, "--type", ptype,
         "--version-stage", stage, "--installed-version", "4.5.2",
         "--output", str(state / "sweetclaude.yaml")],
        capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr

    # setup marks onboarding complete once its branch finishes.
    data = yaml.safe_load((state / "sweetclaude.yaml").read_text(encoding="utf-8"))
    data.setdefault("framework", {})["setup_complete"] = True
    (state / "sweetclaude.yaml").write_text(
        yaml.safe_dump(data, default_flow_style=False, sort_keys=False), encoding="utf-8")

    for subdir in ("backlog/done", "roadmap/epics/done", "roadmap/milestones",
                   "roadmap/issues/done"):
        p = project / ".sweetclaude" / "product" / subdir
        p.mkdir(parents=True, exist_ok=True)
        (p / ".gitkeep").touch()
    trace = project / ".sweetclaude" / "traceability"
    trace.mkdir(parents=True, exist_ok=True)
    for fn in ("requirements-map.md", "ripple-map.md"):
        (trace / fn).write_text("# map\n\n| a | b |\n|---|---|\n", encoding="utf-8")

    # Steps 4 and 6 of the storage block. Both used to be missing from this
    # branch of onboarding: the plans directory was written only by Branch C,
    # and session state not at all since init stopped doing it (ISSUE-284).
    (project / ".sweetclaude" / "plans").mkdir(parents=True, exist_ok=True)
    claude = project / ".claude"
    claude.mkdir(exist_ok=True)
    for fn in ("settings.json", "settings.local.json"):
        (claude / fn).write_text(
            json.dumps({"plansDirectory": ".sweetclaude/plans"}, indent=2),
            encoding="utf-8")

    subprocess.run(["bash", str(SESSION_STATE)], cwd=str(project),
                   capture_output=True, text=True, timeout=120)


# --- the four project shapes --------------------------------------------

def _git_init(project: Path) -> Path:
    """The session-state generator resolves the root with `git rev-parse` and
    exits silently outside a repository, so a non-repo fixture would make every
    assertion about it vacuous."""
    subprocess.run(["git", "init", "-q", "-b", "main", str(project)],
                   capture_output=True, timeout=30)
    return project


@pytest.fixture
def empty_project(tmp_path: Path) -> Path:
    p = tmp_path / "empty"
    p.mkdir()
    return _git_init(p)


@pytest.fixture
def existing_codebase(tmp_path: Path) -> Path:
    p = tmp_path / "codebase"
    (p / "src").mkdir(parents=True)
    (p / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (p / "package.json").write_text('{"name": "thing"}\n', encoding="utf-8")
    return _git_init(p)


@pytest.fixture
def v3_project(tmp_path: Path) -> Path:
    p = tmp_path / "v3"
    state = p / ".sweetclaude" / "state"
    state.mkdir(parents=True)
    (state / "phase.yaml").write_text(
        yaml.safe_dump({"schema_version": 2, "version_stage": "BETA",
                        "deference_level": "collaborative"}), encoding="utf-8")
    (state / "skills.yaml").write_text(
        yaml.safe_dump({"schema_version": 2}), encoding="utf-8")
    return p


@pytest.fixture
def damaged_project(tmp_path: Path) -> Path:
    p = tmp_path / "damaged"
    state = p / ".sweetclaude" / "state"
    state.mkdir(parents=True)
    (state / "sweetclaude.yaml").write_text("{ this: is: not: valid", encoding="utf-8")
    return p


# --- shape 1 and 2: onboarding routes to setup and produces working state

@pytest.mark.parametrize("fixture_name", ["empty_project", "existing_codebase"])
def test_unconfigured_project_routes_to_setup(fixture_name, request) -> None:
    project = request.getfixturevalue(fixture_name)
    assert _detect(project)["STATE"] == "none", (
        "init must route an unconfigured project to setup")


@pytest.mark.parametrize("fixture_name", ["empty_project", "existing_codebase"])
def test_onboarding_produces_state_doctor_accepts(fixture_name, request) -> None:
    """The ISSUE-249 regression, asserted end to end: after onboarding, doctor
    must not report not-configured."""
    project = request.getfixturevalue(fixture_name)
    _onboard(project)

    r = subprocess.run([sys.executable, str(DOCTOR), "scan", "--project-dir", str(project)],
                       capture_output=True, text=True, timeout=180)
    payload = json.loads(r.stdout)
    assert payload.get("error") != "not-configured", (
        "onboarded project reports not-configured — ISSUE-249 has regressed")


@pytest.mark.parametrize("fixture_name", ["empty_project", "existing_codebase"])
def test_onboarded_project_is_configured_on_the_next_session(fixture_name, request) -> None:
    """bootstrap Step 1 keys on sweetclaude.yaml. If it is absent, the next
    session routes to migration — the exact symptom that opened this work."""
    project = request.getfixturevalue(fixture_name)
    _onboard(project)
    assert _detect(project)["STATE"] == "configured"


@pytest.mark.parametrize("fixture_name", ["empty_project", "existing_codebase"])
def test_onboarding_produces_session_state(fixture_name, request) -> None:
    """47 skills preload session state, and doctor warns when it is absent.

    init's old Step 8 generated it; rewriting init as a dispatcher dropped that,
    and setup never had it, so every freshly onboarded project carried a warning
    until its next session (ISSUE-284).

    This assertion used to be wrapped in `if ss.exists()`, which meant the file
    never being written read as a pass — and the fixtures were not git repos, so
    the generator exited early every time and the test proved nothing.
    """
    project = request.getfixturevalue(fixture_name)
    _onboard(project, name="readable", stage="GA")

    ss = project / ".sweetclaude" / "state" / "session-state.yaml"
    assert ss.exists(), "onboarding did not produce session-state.yaml"

    data = yaml.safe_load(ss.read_text(encoding="utf-8")) or {}
    assert data.get("version_stage") == "GA"
    assert data.get("project_name") == "readable"


@pytest.mark.parametrize("fixture_name", ["empty_project", "existing_codebase"])
def test_a_freshly_onboarded_project_scans_clean(fixture_name, request,
                                                 tmp_path) -> None:
    """The check that catches the next onboarding step to go missing.

    Three findings survived onboarding when this was written: session state was
    never generated, the plans directory was created only by Branch C, and
    doctor flagged a skills.yaml that v4 never writes. Each was individually
    small; together they meant nobody could tell a healthy new project from a
    broken one by running doctor (ISSUE-284).

    HOME is isolated so this asserts the same thing on every machine. Some
    doctor checks read the SweetClaude install under ~/.claude, so a developer
    with one installed and a CI checkout without one see different findings —
    which is how the first version of this test passed locally and failed in
    CI. Those findings are about the install, not the project, and are
    identified by pointing outside the project rather than by category name, so
    a new project-scoped finding cannot be excluded by accident.
    """
    project = request.getfixturevalue(fixture_name)
    _onboard(project)

    home = tmp_path / "home"
    home.mkdir()
    env = {**os.environ, "HOME": str(home)}
    r = subprocess.run([sys.executable, str(DOCTOR), "scan",
                        "--project-dir", str(project)],
                       capture_output=True, text=True, timeout=300, env=env)
    payload = json.loads(r.stdout)

    # Defaulting to [] would let an error payload — not-configured, a crash —
    # read as a clean scan, which is the same mistake this test exists to catch.
    assert "error" not in payload, payload["error"]
    assert "findings" in payload, payload

    def about_the_project(finding: dict) -> bool:
        paths = finding.get("file_paths") or []
        # A finding naming nothing is treated as the project's, so a finding
        # that stops reporting paths fails loudly instead of disappearing.
        return not paths or any(str(project) in p for p in paths)

    project_findings = [f for f in payload["findings"] if about_the_project(f)]
    assert project_findings == [], [f["id"] for f in project_findings]

    # The install findings must still be the ones an empty HOME produces. If
    # this ever empties out, the filter above has started hiding real results.
    install_findings = [f for f in payload["findings"] if not about_the_project(f)]
    assert install_findings, "expected install-scoped findings under an empty HOME"
    assert all(f["category"] == "hook_health" for f in install_findings), \
        [(f["category"], f["id"]) for f in install_findings]


@pytest.mark.parametrize("fixture_name", ["empty_project", "existing_codebase"])
def test_onboarding_builds_the_v4_storage_tree(fixture_name, request) -> None:
    project = request.getfixturevalue(fixture_name)
    _onboard(project)
    product = project / ".sweetclaude" / "product"
    for sub in ("backlog", "roadmap/epics", "roadmap/milestones", "roadmap/issues"):
        assert (product / sub).is_dir(), f"missing {sub}"
    trace = project / ".sweetclaude" / "traceability"
    assert (trace / "requirements-map.md").is_file()
    assert (trace / "ripple-map.md").is_file()


def test_onboarded_project_reports_no_migration_drift(empty_project: Path) -> None:
    """A freshly onboarded project must not look like it needs migrating."""
    _onboard(empty_project)
    r = subprocess.run(
        [sys.executable, str(RUNNER), "--project-dir", str(empty_project),
         "--registry", str(REGISTRY), "--report-drift-for-skill"],
        capture_output=True, text=True, timeout=120)
    count = next((l.split("=", 1)[1] for l in r.stdout.splitlines()
                  if l.startswith("DRIFT_COUNT=")), None)
    assert count == "0", f"fresh project reports drift: {r.stdout}"


# --- shape 3: v3 state routes to migration, not setup --------------------

def test_v3_project_routes_to_migration(v3_project: Path) -> None:
    detected = _detect(v3_project)
    assert detected["STATE"] == "legacy", (
        "a v3 project must route to migration, not be re-onboarded over")
    assert "phase.yaml" in detected.get("LEGACY_FILES", "")


def test_v3_project_state_is_left_untouched_by_detection(v3_project: Path) -> None:
    """Detection is a read. ISSUE-249's whole point is that init creates and
    changes nothing."""
    state = v3_project / ".sweetclaude" / "state"
    before = {p.name: p.read_bytes() for p in state.iterdir()}
    _detect(v3_project)
    after = {p.name: p.read_bytes() for p in state.iterdir()}
    assert after == before


# --- shape 4: damaged state routes to repair -----------------------------

def test_damaged_state_routes_to_doctor(damaged_project: Path) -> None:
    detected = _detect(damaged_project)
    assert detected["STATE"] == "damaged"
    assert detected.get("REASON")


def test_damaged_state_is_not_overwritten(damaged_project: Path) -> None:
    """Repair, not re-initialization. Overwriting an unusable state file
    destroys whatever could have been recovered from it."""
    sc = damaged_project / ".sweetclaude" / "state" / "sweetclaude.yaml"
    before = sc.read_bytes()
    _detect(damaged_project)
    assert sc.read_bytes() == before


# --- init creates nothing, in every shape --------------------------------

@pytest.mark.parametrize(
    "fixture_name",
    ["empty_project", "existing_codebase", "v3_project", "damaged_project"])
def test_init_detection_writes_nothing_at_all(fixture_name, request) -> None:
    """The ISSUE-249 contract. Asserted across every shape rather than only the
    happy path, because the v3 and damaged paths are where a stray write would
    do the most damage."""
    project = request.getfixturevalue(fixture_name)
    before = {p.relative_to(project).as_posix(): p.read_bytes()
              for p in project.rglob("*") if p.is_file()}

    _detect(project)

    after = {p.relative_to(project).as_posix(): p.read_bytes()
             for p in project.rglob("*") if p.is_file()}
    assert after == before, "init detection modified the project"


def test_partial_setup_routes_back_to_setup(tmp_path: Path) -> None:
    """An interrupted onboarding must resume, not be reported as configured."""
    project = tmp_path / "partial"
    _onboard(project)
    sc = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
    data = yaml.safe_load(sc.read_text(encoding="utf-8"))
    data["framework"]["setup_complete"] = False
    sc.write_text(yaml.safe_dump(data, default_flow_style=False, sort_keys=False),
                  encoding="utf-8")

    assert _detect(project)["STATE"] == "partial"


# --- ISSUE-280: onboarding must create current-version state --------------

def _template_output() -> dict:
    r = subprocess.run(
        [sys.executable, str(TEMPLATE), "--name", "t", "--type", "new",
         "--version-stage", "IDEA", "--installed-version", "4.5.2", "--output", "-"],
        capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return yaml.safe_load(r.stdout)


def test_onboarding_template_matches_the_registry_current_version() -> None:
    """ISSUE-280: setup wrote schema_version 1 while the registry declared 2, so
    every new project was created already needing migration — and bootstrap
    Step 5c offers only 'migrate now' or 'remove SweetClaude'."""
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    expected = registry["state_files"]["sweetclaude.yaml"]["current_version"]
    assert _template_output()["schema_version"] == expected


def test_freshly_written_state_needs_no_migration() -> None:
    """The general form, and the one that catches this recurring at v2 to v3:
    running the migration over brand-new output must be a no-op."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "sc_v1_v2", REPO_ROOT / "scripts" / "migrations" / "sweetclaude_yaml_v1_to_v2.py")
    handler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(handler)

    fresh = _template_output()
    migrated = handler.up(dict(fresh))
    assert migrated == fresh, (
        "the onboarding template produces state the migration would still "
        "change, so a new project is created out of date")
