# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATOR = REPO_ROOT / "hooks" / "generate-session-state.sh"

HEADER = "# Improvement Register\n\n| # | Date | Type | Learning |\n|---|---|---|---|\n"


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    state = project / ".sweetclaude" / "state"
    state.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(project)], check=True)
    (state / "sweetclaude.yaml").write_text(yaml.safe_dump({
        "project": {"name": "fixture", "version_stage": "mvp"},
        "session": {"deference_level": "guided"},
        "work": {"active": {"id": None}},
    }))
    return project


def _state(project: Path) -> Path:
    return project / ".sweetclaude" / "state"


def _regenerate(project: Path) -> dict:
    subprocess.run(["bash", str(GENERATOR)], cwd=str(project), check=True)
    return yaml.safe_load((_state(project) / "session-state.yaml").read_text()) or {}


def _jsonl(project: Path) -> list[dict]:
    path = _state(project) / "improvement-register.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _md(project: Path) -> str:
    return (_state(project) / "improvement-register.md").read_text()


def test_empty_jsonl_with_populated_md_keeps_every_row(tmp_path):
    project = _project(tmp_path)
    (_state(project) / "improvement-register.jsonl").write_text("")
    (_state(project) / "improvement-register.md").write_text(
        HEADER
        + "| 1 | 2026-06-26 | confirmation | Keep doing X |\n"
        + "| 2 | 2026-06-26 | correction | Stop doing Y |\n"
        + "| 3 | 2026-06-27 | preference | Prefer Z |\n"
    )

    state = _regenerate(project)

    entries = {e["entry"] for e in _jsonl(project)}
    assert entries == {"Keep doing X", "Stop doing Y", "Prefer Z"}
    md = _md(project)
    for text in ("Keep doing X", "Stop doing Y", "Prefer Z"):
        assert text in md
    assert state["improvement_register_count"] == 3


def test_row_appended_to_md_survives_regeneration(tmp_path):
    project = _project(tmp_path)
    (_state(project) / "improvement-register.jsonl").write_text(json.dumps({
        "id": "lr-001", "date": "2026-11-01", "type": "correction",
        "entry": "Existing learning", "source": "manual",
        "weight": 1.0, "decay_exempt": True,
    }) + "\n")
    _regenerate(project)

    with open(_state(project) / "improvement-register.md", "a") as f:
        f.write("| 2 | 2026-11-07 | pattern | Appended learning |\n")

    state = _regenerate(project)
    state = _regenerate(project)

    entries = [e["entry"] for e in _jsonl(project)]
    assert sorted(entries) == ["Appended learning", "Existing learning"]
    assert len({e["id"] for e in _jsonl(project)}) == 2
    assert "Appended learning" in _md(project)
    assert state["improvement_register_count"] == 2


def test_count_matches_rows_kept(tmp_path):
    project = _project(tmp_path)
    (_state(project) / "improvement-register.md").write_text(
        HEADER
        + "| 1 | 2026-11-01 | correction | One |\n"
        + "| 2 | 2026-11-02 | confirmation | Two \\| with pipe |\n"
    )

    state = _regenerate(project)

    assert state["improvement_register_count"] == 2
    assert {e["entry"] for e in _jsonl(project)} == {"One", "Two | with pipe"}
    data_rows = [line for line in _md(project).splitlines()
                 if line.startswith("|") and not line.startswith("| #") and "---" not in line]
    assert len(data_rows) == 2


def test_entry_edited_in_jsonl_is_not_resurrected_from_stale_md(tmp_path):
    project = _project(tmp_path)
    (_state(project) / "improvement-register.md").write_text(
        HEADER + "| 1 | 2026-11-01 | correction | Old wording |\n"
    )
    _regenerate(project)

    entries = _jsonl(project)
    entries[0]["entry"] = "New wording"
    (_state(project) / "improvement-register.jsonl").write_text(
        "".join(json.dumps(e) + "\n" for e in entries)
    )

    state = _regenerate(project)

    assert [e["entry"] for e in _jsonl(project)] == ["New wording"]
    assert "Old wording" not in _md(project)
    assert state["improvement_register_count"] == 1


def test_retired_entry_is_not_resurrected(tmp_path):
    project = _project(tmp_path)
    (_state(project) / "improvement-register.md").write_text(
        HEADER + "| 1 | 2026-11-01 | pattern | Retire me |\n"
    )
    _regenerate(project)

    entries = _jsonl(project)
    entries[0].update({"weight": 0, "retired": True})
    (_state(project) / "improvement-register.jsonl").write_text(
        "".join(json.dumps(e) + "\n" for e in entries)
    )

    state = _regenerate(project)
    state = _regenerate(project)

    assert _jsonl(project) == []
    assert "Retire me" not in _md(project)
    assert state["improvement_register_count"] == 0


def test_rows_dropped_from_md_are_backed_up(tmp_path):
    project = _project(tmp_path)
    (_state(project) / "improvement-register.md").write_text(
        HEADER + "| 1 | 2026-11-01 | correction | Old wording |\n"
    )
    _regenerate(project)
    entries = _jsonl(project)
    entries[0]["entry"] = "New wording"
    (_state(project) / "improvement-register.jsonl").write_text(
        "".join(json.dumps(e) + "\n" for e in entries)
    )

    _regenerate(project)

    backup = _state(project) / "improvement-register.md.bak"
    assert backup.exists()
    assert "Old wording" in backup.read_text()
