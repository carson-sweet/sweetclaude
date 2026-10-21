"""R-124: Flow mode gradually accumulates thin artifacts at work-item closeout.

docs/user-guide/how-it-works.md and skills/help/modes-content.md promise that
Flow mode "quietly accumulates thin versions of key artifacts in the
background (mini brief, architecture sketch, decision log entries) — so if you
decide to switch modes later, there's something to build from". Before R-124
nothing in code wrote them; the promise was prose only.

Contract (docs basis for each name):
  - mini brief — thin version of the product brief, which plan/product-brief
    writes under the artifact-privacy product base. Per-item file:
    {product_base}/{ITEM-ID}-mini-brief.md
  - architecture sketch — thin version of the architecture doc, which
    design/design-architecture writes under the artifact-privacy technical
    base. Per-item file: {technical_base}/{ITEM-ID}-architecture-sketch.md
  - decision log entries — .sweetclaude/state/decision-log.md, in the
    design/design-manage-decisions DEC-{NNN} format.

The writes are background capture at closeout: deterministic, idempotent,
Flow-scoped, and never able to fail the closeout itself.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from status import set_terminal  # noqa: E402
from success_criteria_contracts import record_workflow_closeout  # noqa: E402
import orchestrator_loop  # noqa: E402

PRODUCT_BASE = Path(".sweetclaude") / "product"
TECHNICAL_BASE = Path(".sweetclaude") / "technical"
DECISION_LOG = Path(".sweetclaude") / "state" / "decision-log.md"


def _make_project(tmp_path: Path, *, mode: str, privacy: dict | None = None) -> Path:
    project = tmp_path / "proj"
    state = project / ".sweetclaude" / "state"
    state.mkdir(parents=True)
    (state / "sweetclaude.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 2,
                "project": {"name": "proj", "mode": mode},
                "work": {"active": None, "last_item_id": None},
                "work_history": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (state / "phase.yaml").write_text(
        yaml.safe_dump(
            {"schema_version": 2, "active_work_item": None, "last_work_item_id": None},
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    if privacy is not None:
        (project / ".sweetclaude" / "artifact-privacy.yaml").write_text(
            yaml.safe_dump(privacy), encoding="utf-8"
        )
    return project


def _make_item(
    project: Path,
    item_id: str,
    title: str,
    *,
    type_: str = "bug-fix",
    status: str = "new",
) -> Path:
    backlog = project / PRODUCT_BASE / "backlog"
    backlog.mkdir(parents=True, exist_ok=True)
    item = backlog / f"{item_id}-{title.lower().replace(' ', '-')}.md"
    fm: dict = {
        "id": item_id,
        "title": title,
        "type": type_,
        "status": status,
        "created": "2026-10-20T00:00:00+00:00",
    }
    if type_ in ("epic", "milestone"):
        fm["milestone"] = "MS-01"
    item.write_text(
        "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n\nbody\n",
        encoding="utf-8",
    )
    return item


def _artifact_paths(project: Path, item_id: str) -> tuple[Path, Path, Path]:
    return (
        project / PRODUCT_BASE / f"{item_id}-mini-brief.md",
        project / TECHNICAL_BASE / f"{item_id}-architecture-sketch.md",
        project / DECISION_LOG,
    )


def _all_thin_artifacts(project: Path) -> list[Path]:
    found = []
    for base in (PRODUCT_BASE, TECHNICAL_BASE):
        d = project / base
        if d.is_dir():
            found.extend(p for p in d.iterdir() if p.suffix == ".md")
    return found


# --- the three named artifacts, via the workflow closeout choke point ------

def test_flow_closeout_writes_the_three_named_thin_artifacts(tmp_path: Path) -> None:
    project = _make_project(tmp_path, mode="flow")
    item_id = "ISSUE-741"
    _make_item(project, item_id, "Flow radios")

    record_workflow_closeout(project, item_id)

    brief, sketch, log = _artifact_paths(project, item_id)
    assert brief.is_file(), "mini brief missing after flow closeout"
    assert sketch.is_file(), "architecture sketch missing after flow closeout"
    assert log.is_file(), "decision log missing after flow closeout"
    brief_text = brief.read_text(encoding="utf-8")
    assert item_id in brief_text
    assert "Flow radios" in brief_text
    sketch_text = sketch.read_text(encoding="utf-8")
    assert item_id in sketch_text
    assert "Flow radios" in sketch_text
    log_text = log.read_text(encoding="utf-8")
    assert item_id in log_text


# --- the same capture via the terminal-status choke point ------------------

def test_flow_set_terminal_writes_the_three_named_thin_artifacts(tmp_path: Path) -> None:
    project = _make_project(tmp_path, mode="flow")
    item_id = "ISSUE-742"
    item = _make_item(project, item_id, "Flow dials")

    set_terminal(str(item), "done", "test", project_dir=str(project))

    brief, sketch, log = _artifact_paths(project, item_id)
    assert brief.is_file()
    assert sketch.is_file()
    assert log.is_file()
    assert item_id in log.read_text(encoding="utf-8")


# --- the orchestrator path funnels through the same capture ---------------

def test_flow_orchestrator_complete_sc_writes_the_artifacts(tmp_path: Path) -> None:
    project = _make_project(tmp_path, mode="flow")
    item_id = "ISSUE-743"
    _make_item(project, item_id, "Flow knobs")

    orchestrator_loop._complete_sc(str(project), item_id, "complete")

    brief, sketch, log = _artifact_paths(project, item_id)
    assert brief.is_file()
    assert sketch.is_file()
    assert log.is_file()


# --- idempotence: a second close never duplicates --------------------------

def test_second_close_does_not_duplicate(tmp_path: Path) -> None:
    project = _make_project(tmp_path, mode="flow")
    item_id = "ISSUE-744"
    _make_item(project, item_id, "Flow stays")

    record_workflow_closeout(project, item_id)
    log_after_first = (project / DECISION_LOG).read_text(encoding="utf-8")
    brief_after_first = (project / PRODUCT_BASE / f"{item_id}-mini-brief.md").read_text(encoding="utf-8")

    record_workflow_closeout(project, item_id)

    log_text = (project / DECISION_LOG).read_text(encoding="utf-8")
    entries = re.findall(rf"^## DEC-\d+: [^\n]*{item_id}[^\n]*$", log_text, re.M)
    assert len(entries) == 1, f"decision log duplicated the entry: {entries}"
    assert log_text == log_after_first
    assert (
        (project / PRODUCT_BASE / f"{item_id}-mini-brief.md").read_text(encoding="utf-8")
        == brief_after_first
    )


def test_preexisting_brief_and_sketch_are_left_untouched(tmp_path: Path) -> None:
    project = _make_project(tmp_path, mode="flow")
    item_id = "ISSUE-745"
    _make_item(project, item_id, "Flow guards")
    brief = project / PRODUCT_BASE / f"{item_id}-mini-brief.md"
    sketch = project / TECHNICAL_BASE / f"{item_id}-architecture-sketch.md"
    brief.parent.mkdir(parents=True, exist_ok=True)
    sketch.parent.mkdir(parents=True, exist_ok=True)
    brief.write_text("PRECIOUS USER BRIEF\n", encoding="utf-8")
    sketch.write_text("PRECIOUS USER SKETCH\n", encoding="utf-8")

    record_workflow_closeout(project, item_id)

    assert brief.read_text(encoding="utf-8") == "PRECIOUS USER BRIEF\n"
    assert sketch.read_text(encoding="utf-8") == "PRECIOUS USER SKETCH\n"


def test_preexisting_decision_log_is_preserved_and_numbering_increments(
    tmp_path: Path,
) -> None:
    project = _make_project(tmp_path, mode="flow")
    item_id = "ISSUE-746"
    _make_item(project, item_id, "Flow numbers")
    log = project / DECISION_LOG
    log.write_text(
        "## DEC-003: Earlier decision\n\n"
        "**Date:** 2026-10-01\n"
        "**Status:** Accepted\n"
        "**Decision:** earlier thing\n",
        encoding="utf-8",
    )

    record_workflow_closeout(project, item_id)

    text = log.read_text(encoding="utf-8")
    assert "## DEC-003: Earlier decision" in text
    assert "## DEC-004" in text
    assert item_id in text


# --- Flow-scoped: other modes close out with no background artifacts --------

def test_kanban_closeout_writes_no_thin_artifacts(tmp_path: Path) -> None:
    project = _make_project(tmp_path, mode="kanban")
    item_id = "ISSUE-747"
    _make_item(project, item_id, "Kanban remains")

    record_workflow_closeout(project, item_id)

    brief, sketch, log = _artifact_paths(project, item_id)
    assert not brief.exists()
    assert not sketch.exists()
    assert not log.exists()


def test_non_flow_set_terminal_writes_no_thin_artifacts(tmp_path: Path) -> None:
    project = _make_project(tmp_path, mode="agile")
    item_id = "ISSUE-748"
    item = _make_item(project, item_id, "Agile remains")

    set_terminal(str(item), "done", "test", project_dir=str(project))

    assert _all_thin_artifacts(project) == []


# --- only a completed work item captures -----------------------------------

def test_abandoned_is_not_completion(tmp_path: Path) -> None:
    project = _make_project(tmp_path, mode="flow")
    item_id = "ISSUE-749"
    item = _make_item(project, item_id, "Flow abandons")

    set_terminal(str(item), "abandoned", "test", project_dir=str(project))

    assert _all_thin_artifacts(project) == []


def test_epic_done_is_not_a_work_item_close(tmp_path: Path) -> None:
    project = _make_project(tmp_path, mode="flow")
    epic_id = "EP-042"
    item = _make_item(project, epic_id, "Flow bundle", type_="epic")

    set_terminal(str(item), "done", "test", project_dir=str(project))

    brief = project / PRODUCT_BASE / f"{epic_id}-mini-brief.md"
    assert not brief.exists()
    assert not (project / DECISION_LOG).exists()


# --- artifact-privacy base paths are honored -------------------------------

def test_relocated_product_and_technical_bases_are_honored(tmp_path: Path) -> None:
    project = _make_project(
        tmp_path,
        mode="flow",
        privacy={
            "categories": {
                "product": {"base_path": "docs/product"},
                "technical": {"base_path": "docs/technical"},
            }
        },
    )
    item_id = "ISSUE-750"
    _make_item(project, item_id, "Flow relocates")

    record_workflow_closeout(project, item_id)

    assert (project / "docs" / "product" / f"{item_id}-mini-brief.md").is_file()
    assert (project / "docs" / "technical" / f"{item_id}-architecture-sketch.md").is_file()
    assert not (project / PRODUCT_BASE / f"{item_id}-mini-brief.md").exists()
    assert not (project / TECHNICAL_BASE / f"{item_id}-architecture-sketch.md").exists()
    log = project / DECISION_LOG
    assert log.is_file()
    assert item_id in log.read_text(encoding="utf-8")


# --- quiet: capture failure never blocks the closeout ----------------------

def test_capture_failure_never_blocks_the_closeout(tmp_path: Path) -> None:
    project = _make_project(
        tmp_path,
        mode="flow",
        privacy={"categories": {"product": {"base_path": "docs/product"}}},
    )
    item_id = "ISSUE-751"
    _make_item(project, item_id, "Flow survives")
    clash = project / "docs" / "product"
    clash.parent.mkdir(parents=True, exist_ok=True)
    clash.write_text("a file blocking the directory\n", encoding="utf-8")

    record_workflow_closeout(project, item_id)

    sc = yaml.safe_load(
        (project / ".sweetclaude" / "state" / "sweetclaude.yaml").read_text(encoding="utf-8")
    )
    assert any(
        isinstance(h, dict) and h.get("id") == item_id for h in sc.get("work_history", [])
    )
    item = list((project / PRODUCT_BASE).rglob(f"{item_id}-*.md"))
    assert item, "closeout must still move the item file despite capture failure"


def test_capture_failure_never_blocks_set_terminal(tmp_path: Path) -> None:
    project = _make_project(
        tmp_path,
        mode="flow",
        privacy={"categories": {"product": {"base_path": "docs/product"}}},
    )
    item_id = "ISSUE-752"
    item = _make_item(project, item_id, "Flow still closes")
    clash = project / "docs" / "product"
    clash.parent.mkdir(parents=True, exist_ok=True)
    clash.write_text("a file blocking the directory\n", encoding="utf-8")

    set_terminal(str(item), "done", "test", project_dir=str(project))

    moved = list((project / PRODUCT_BASE).rglob(f"{item_id}-*.md"))
    assert moved, "set_terminal must still complete despite capture failure"
    assert moved[0].read_text(encoding="utf-8").count("status: done") == 1


# --- the artifacts themselves: thin, honest, correctly shaped ---------------

def test_mini_brief_is_thin_and_names_the_item(tmp_path: Path) -> None:
    project = _make_project(tmp_path, mode="flow")
    item_id = "ISSUE-753"
    _make_item(project, item_id, "Flow brief")

    record_workflow_closeout(project, item_id)

    text = (project / PRODUCT_BASE / f"{item_id}-mini-brief.md").read_text(encoding="utf-8")
    assert "## Summary" in text
    body = text.split("## Summary", 1)[1]
    paragraphs = [p for p in re.split(r"\n\s*\n", body) if p.strip()]
    assert len(paragraphs) == 1, "mini brief must be a single summary paragraph"
    assert item_id in paragraphs[0]
    assert "Flow brief" in paragraphs[0]


def test_architecture_sketch_is_an_honest_skeleton(tmp_path: Path) -> None:
    project = _make_project(tmp_path, mode="flow")
    item_id = "ISSUE-754"
    _make_item(project, item_id, "Flow sketch")

    record_workflow_closeout(project, item_id)

    text = (
        project / TECHNICAL_BASE / f"{item_id}-architecture-sketch.md"
    ).read_text(encoding="utf-8")
    assert item_id in text
    assert "Flow sketch" in text
    assert f"{item_id}-flow-sketch.md" in text, "sketch must point at the item's own record"


def test_decision_entry_follows_the_dec_format(tmp_path: Path) -> None:
    project = _make_project(tmp_path, mode="flow")
    item_id = "ISSUE-755"
    _make_item(project, item_id, "Flow decides")

    record_workflow_closeout(project, item_id)

    text = (project / DECISION_LOG).read_text(encoding="utf-8")
    assert re.search(r"^## DEC-\d{3}: .+", text, re.M)
    assert "**Date:**" in text
    assert "**Status:** Accepted" in text
    assert "**Decision:**" in text
    assert re.search(r"\*\*Date:\*\* \d{4}-\d{2}-\d{2}", text)


# --- unit level ------------------------------------------------------------

def test_next_dec_number_increments_from_last_entry() -> None:
    import flow_capture

    text = "## DEC-007: one\n\nx\n\n## DEC-003: two\n\ny\n"
    assert flow_capture._next_dec_number(text) == 8


def test_next_dec_number_starts_at_one() -> None:
    import flow_capture

    assert flow_capture._next_dec_number("no decisions yet\n") == 1


def test_project_mode_reads_canonical_sweetclaude_yaml(tmp_path: Path) -> None:
    import flow_capture

    project = _make_project(tmp_path, mode="flow")
    assert flow_capture._project_mode(project) == "flow"

    sc = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
    data = yaml.safe_load(sc.read_text(encoding="utf-8"))
    del data["project"]["mode"]
    data["mode"] = "flow"
    sc.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    assert flow_capture._project_mode(project) == "flow"

    data["mode"] = "kanban"
    sc.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    assert flow_capture._project_mode(project) == "kanban"