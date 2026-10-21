"""R-250: releasing the test freeze for an approved test edit is logged.

Assumed interface: `python3 scripts/tdd_phase.py release --file <path> --approval <text>
--project-dir <dir>` releases the freeze and appends a `tdd_override` event carrying
`file` and `approval` to `.sweetclaude/metrics/events.log`, in the format written by
`scripts/record-event.sh`.
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
TDD_PHASE = REPO_ROOT / "scripts" / "tdd_phase.py"
GUARDIAN = REPO_ROOT / "hooks" / "test-guardian.sh"
PAYLOADS = REPO_ROOT / "tests" / "fixtures" / "hook_payloads"

TEST_FILE = "tests/test_thing.py"
APPROVAL = "user approved fixing the wrong assertion in test_thing"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    p = tmp_path / "proj"
    state = p / ".sweetclaude" / "state"
    state.mkdir(parents=True)
    metrics = p / ".sweetclaude" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "config.yaml").write_text("enabled: true\n", encoding="utf-8")
    (p / "tests").mkdir()
    (p / "src").mkdir()
    (state / "sweetclaude.yaml").write_text(yaml.safe_dump({
        "schema_version": 2,
        "framework": {"setup_complete": True},
        "work": {"active": {"id": "ISSUE-1", "phase": "IMPLEMENT"}},
    }), encoding="utf-8")
    (state / "project.yaml").write_text(yaml.safe_dump({"schema_version": 1}), encoding="utf-8")
    (p / TEST_FILE).write_text("def test_x(): assert True\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main", str(p)], capture_output=True, timeout=30)
    return p


def _tdd(project: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TDD_PHASE), *args, "--project-dir", str(project)],
        capture_output=True, text=True, timeout=60,
    )


def _freeze(project: Path) -> None:
    result = _tdd(project, "set", "--phase", "implementing")
    assert result.returncode == 0, result.stderr


def _edit_allowed(project: Path, rel: str) -> bool:
    payload = json.loads(
        (PAYLOADS / "PreToolUse-Edit.json").read_text(encoding="utf-8").replace("__CWD__", str(project))
    )
    payload["tool_input"]["file_path"] = str(project / rel)
    r = subprocess.run(
        ["bash", str(GUARDIAN)], cwd=str(project), input=json.dumps(payload),
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(project),
             "CLAUDE_PROJECT_DIR": str(project), "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
        capture_output=True, text=True, timeout=60,
    )
    if r.returncode == 2:
        return False
    assert r.returncode == 0, r.stderr
    for line in r.stdout.splitlines():
        if line.strip().startswith("{"):
            specific = json.loads(line).get("hookSpecificOutput") or {}
            if specific.get("permissionDecision") == "deny":
                return False
    return True


def _events(project: Path) -> list[dict]:
    log = project / ".sweetclaude" / "metrics" / "events.log"
    if not log.is_file():
        return []
    return [doc for doc in yaml.safe_load_all(log.read_text(encoding="utf-8")) if isinstance(doc, dict)]


def _refusal_error(result: subprocess.CompletedProcess) -> dict:
    assert result.returncode == 2, result.stderr
    assert "invalid choice" not in result.stderr, result.stderr
    payload = json.loads(result.stderr.strip().splitlines()[-1])
    assert payload["ok"] is False
    return payload


def _overrides(project: Path) -> list[dict]:
    return [event for event in _events(project) if event.get("event") == "tdd_override"]


class TestR250ReleaseWritesOverrideEvent:
    def test_release_succeeds_and_unfreezes_the_approved_test_file(self, project):
        _freeze(project)
        assert _edit_allowed(project, TEST_FILE) is False

        result = _tdd(project, "release", "--file", TEST_FILE, "--approval", APPROVAL)

        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["ok"] is True
        assert _edit_allowed(project, TEST_FILE) is True

    def test_release_writes_one_override_event_naming_file_and_approval(self, project):
        _freeze(project)

        result = _tdd(project, "release", "--file", TEST_FILE, "--approval", APPROVAL)

        assert result.returncode == 0, result.stderr
        overrides = _overrides(project)
        assert len(overrides) == 1
        event = overrides[0]
        assert str(event["file"]).endswith(TEST_FILE)
        assert event["approval"] == APPROVAL
        assert event["timestamp"]

    def test_release_without_approval_is_refused_and_leaves_the_freeze(self, project):
        _freeze(project)

        result = _tdd(project, "release", "--file", TEST_FILE)

        assert "approval" in _refusal_error(result)["error"].lower()
        assert _edit_allowed(project, TEST_FILE) is False
        assert _overrides(project) == []

    def test_release_with_blank_approval_is_refused_and_leaves_the_freeze(self, project):
        _freeze(project)

        result = _tdd(project, "release", "--file", TEST_FILE, "--approval", "  ")

        assert "approval" in _refusal_error(result)["error"].lower()
        assert _edit_allowed(project, TEST_FILE) is False
        assert _overrides(project) == []

    def test_release_without_file_is_refused(self, project):
        _freeze(project)

        result = _tdd(project, "release", "--approval", APPROVAL)

        assert "file" in _refusal_error(result)["error"].lower()
        assert _overrides(project) == []

    def test_each_release_records_its_own_event(self, project):
        _freeze(project)
        assert _tdd(project, "release", "--file", TEST_FILE, "--approval", APPROVAL).returncode == 0
        _freeze(project)
        other = "tests/test_other.py"
        (project / other).write_text("def test_y(): assert True\n", encoding="utf-8")
        assert _tdd(project, "release", "--file", other, "--approval", "second approval").returncode == 0

        overrides = _overrides(project)

        assert [str(e["file"]).endswith(name) for e, name in zip(overrides, (TEST_FILE, other))] == [True, True]
        assert [e["approval"] for e in overrides] == [APPROVAL, "second approval"]
