"""The regenerator watches every file the generator reads (ISSUE-281).

`state-regenerator.sh` fires `generate-session-state.sh` when a constituent
state file changes. Its watch list named `phase.yaml` and not
`sweetclaude.yaml`.

phase.yaml is a mirror the story controllers write lazily; onboarding never
creates it, so most v4 projects do not have one. Every real state change went to
sweetclaude.yaml, matched nothing in the list, and regenerated nothing.
session-state.yaml — which 47 skills preload — went stale with no signal. The
hook exited 0 every time, which is what silence looks like when a watcher is
watching the wrong file.

The durable property is not "sweetclaude.yaml is in the list". It is that the
list covers what the generator reads, so an input added to the generator later
cannot be forgotten here.
"""

from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[1]
HOOKS = REPO_ROOT / "hooks"
REGENERATOR = HOOKS / "state-regenerator.sh"
GENERATOR = HOOKS / "generate-session-state.sh"


def watch_list() -> set[str]:
    """Basenames the regenerator dispatches on."""
    body = REGENERATOR.read_text(encoding="utf-8")
    case = re.search(r"case \"\$FILE\" in(.*?)esac", body, re.S).group(1)
    return {Path(p).name for p in re.findall(r"\*/[^|)\s\\]+", case)}


def generator_inputs() -> set[str]:
    """Files generate-session-state.sh opens for reading."""
    body = GENERATOR.read_text(encoding="utf-8")
    names = set()
    for var, parts in re.findall(r"(\w+)\s*=\s*os\.path\.join\(([^)]*)\)", body):
        literals = re.findall(r"'([^']+)'", parts)
        if literals and literals[-1].endswith((".yaml", ".md", ".jsonl")):
            names.add(literals[-1])
    read_vars = set(re.findall(r"with open\((\w+)\)", body))
    paths = dict(re.findall(r"(\w+)\s*=\s*os\.path\.join\(([^)]*)\)", body))
    read_names = set()
    for var in read_vars:
        literals = re.findall(r"'([^']+)'", paths.get(var, ""))
        if literals:
            read_names.add(literals[-1])
    return read_names or names


# --- the property ---------------------------------------------------------

def test_the_watch_list_covers_every_file_the_generator_reads() -> None:
    missing = generator_inputs() - watch_list()

    assert not missing, (
        f"generate-session-state.sh reads {sorted(missing)} but "
        f"state-regenerator.sh does not watch them, so a change to one "
        f"regenerates nothing and session-state.yaml goes stale")


def test_the_canonical_state_file_is_watched() -> None:
    """The specific instance. phase.yaml is a mirror most v4 projects never
    have; sweetclaude.yaml is where state actually changes."""
    assert "sweetclaude.yaml" in watch_list()


def test_the_legacy_mirror_is_still_watched() -> None:
    """A project mid-migration writes phase.yaml. Swapping one for the other
    would move the bug rather than fix it."""
    assert "phase.yaml" in watch_list()


def test_the_extraction_finds_a_real_list() -> None:
    """If either parser silently returned nothing, the property test above
    would pass by comparing two empty sets."""
    assert len(watch_list()) >= 6
    assert len(generator_inputs()) >= 3


# --- behaviour ------------------------------------------------------------

def _project(tmp_path: Path) -> Path:
    p = tmp_path / "proj"
    state = p / ".sweetclaude" / "state"
    state.mkdir(parents=True)
    (state / "sweetclaude.yaml").write_text(yaml.safe_dump({
        "schema_version": 2,
        "project": {"name": "t", "version_stage": "GA"},
        "framework": {"setup_complete": True},
        "work": {"active": {"id": "ISSUE-1", "phase": "IMPLEMENT"}},
    }), encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main", str(p)],
                   capture_output=True, timeout=30)
    return p


def _regenerated(project: Path, file_path: Path, *, tool: str = "Write",
                 timeout: float = 20.0) -> bool:
    """The hook backgrounds the generator, so the effect is polled for."""
    out = project / ".sweetclaude" / "state" / "session-state.yaml"
    if out.exists():
        out.unlink()
    subprocess.run(["bash", str(REGENERATOR)], cwd=str(project),
                   env={"PATH": "/usr/bin:/bin:/usr/local/bin",
                        "HOME": str(project),
                        "CLAUDE_TOOL_NAME": tool,
                        "CLAUDE_FILE_PATH": str(file_path)},
                   capture_output=True, timeout=60)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if out.exists():
            return True
        time.sleep(0.1)
    return False


def test_writing_canonical_state_regenerates(tmp_path: Path) -> None:
    """Was xfail(strict) against ISSUE-281; now a live assertion."""
    project = _project(tmp_path)

    assert _regenerated(
        project, project / ".sweetclaude" / "state" / "sweetclaude.yaml")


def test_writing_the_mirror_still_regenerates(tmp_path: Path) -> None:
    project = _project(tmp_path)
    mirror = project / ".sweetclaude" / "state" / "phase.yaml"
    mirror.write_text(yaml.safe_dump({"schema_version": 2, "phase": "IMPLEMENT"}),
                      encoding="utf-8")

    assert _regenerated(project, mirror)


def test_an_unwatched_file_does_not_regenerate(tmp_path: Path) -> None:
    """Firing on every write would run the generator constantly."""
    project = _project(tmp_path)

    assert not _regenerated(project, project / "src" / "main.py", timeout=2.0)


def test_a_read_does_not_regenerate(tmp_path: Path) -> None:
    project = _project(tmp_path)

    assert not _regenerated(
        project, project / ".sweetclaude" / "state" / "sweetclaude.yaml",
        tool="Read", timeout=2.0)
