#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Flow-mode background capture of thin artifacts at work-item closeout.

Implements the promise from docs/user-guide/how-it-works.md and
skills/help/modes-content.md: Flow mode quietly accumulates thin versions of
key artifacts in the background (mini brief, architecture sketch, decision log
entries) so switching to a heavier mode later leaves something to build from.

Base paths honor .sweetclaude/artifact-privacy.yaml — the source of truth per
hooks/generate-session-state.sh:
  - mini brief -> categories.product.base_path (default .sweetclaude/product,
    where plan/product-brief writes full briefs)
  - architecture sketch -> categories.technical.base_path (default
    .sweetclaude/technical, where design/design-architecture writes full docs)
  - decision entry -> .sweetclaude/state/decision-log.md in the
    design/design-manage-decisions DEC-{NNN} format

Background means: written by code at closeout without interrupting the user,
idempotent (existing artifacts are left alone, one decision entry per item),
Flow-scoped (other modes capture nothing), and capture failures log a warning
but never raise — they must not be able to fail a closeout.
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

import yaml

CONTAINER_TYPES = ("epic", "milestone", "sprint")
DEFAULT_PRODUCT_BASE = ".sweetclaude/product"
DEFAULT_TECHNICAL_BASE = ".sweetclaude/technical"
DECISION_LOG = Path(".sweetclaude") / "state" / "decision-log.md"

_DEC_ENTRY = re.compile(r"^## DEC-(\d+):", re.M)


def project_mode(project: Path) -> str:
    """Project mode from the canonical state file, mirroring
    hooks/generate-session-state.sh: sweetclaude.yaml project.mode, then a
    top-level mode key."""
    sc_path = Path(project) / ".sweetclaude" / "state" / "sweetclaude.yaml"
    if not sc_path.exists():
        return ""
    try:
        data = yaml.safe_load(sc_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return ""
    if not isinstance(data, dict):
        return ""
    project_section = data.get("project") or {}
    mode = ""
    if isinstance(project_section, dict):
        mode = project_section.get("mode") or ""
    if not mode:
        mode = data.get("mode") or ""
    return str(mode)


def artifact_base(project: Path, category: str, default: str) -> Path:
    """Resolve a category base path from .sweetclaude/artifact-privacy.yaml."""
    base = default
    privacy_path = Path(project) / ".sweetclaude" / "artifact-privacy.yaml"
    if privacy_path.exists():
        try:
            data = yaml.safe_load(privacy_path.read_text(encoding="utf-8")) or {}
            configured = ((data.get("categories") or {}).get(category) or {}).get("base_path", "")
            if isinstance(configured, str) and configured.strip():
                base = configured.strip().rstrip("/")
        except Exception:
            pass
    return Path(project) / base


def next_dec_number(text: str) -> int:
    numbers = [int(m) for m in _DEC_ENTRY.findall(text)]
    return max(numbers) + 1 if numbers else 1


def capture_flow_closeout(
    project: Path,
    item_id: str,
    *,
    title: str | None = None,
    outcome: str = "done",
) -> None:
    """Write the thin artifacts for a completed work item in Flow mode.

    Never raises: background capture logs failures to stderr and returns so a
    closeout cannot be blocked by capture problems.
    """
    try:
        if outcome != "done" or not item_id:
            return
        project = Path(project)
        if project_mode(project) != "flow":
            return
        resolved_title = (title or "").strip() or item_id
        today = date.today().isoformat()
        _write_mini_brief(project, item_id, resolved_title, today)
        _write_architecture_sketch(project, item_id, resolved_title, today)
        _append_decision_entry(project, item_id, resolved_title, today)
    except Exception as exc:
        print(
            f"WARNING: flow thin-artifact capture failed for {item_id}: {exc}",
            file=sys.stderr,
        )


def _write_mini_brief(project: Path, item_id: str, title: str, today: str) -> None:
    path = artifact_base(project, "product", DEFAULT_PRODUCT_BASE) / f"{item_id}-mini-brief.md"
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        f"id: {item_id}\n"
        f"title: {title}\n"
        f"completed: {today}\n"
        "capture: flow-mode-closeout\n"
        "---\n\n"
        f"# Mini Brief — {item_id}: {title}\n\n"
        "## Summary\n\n"
        f"{item_id} ({title}) was completed on {today}. This one-paragraph mini brief is "
        "background capture from Flow mode: it records the work item's completion so a "
        "later, heavier mode has something to build from. The work item's own record is "
        "the source; expand this into a full product brief after switching modes.\n",
        encoding="utf-8",
    )


def _write_architecture_sketch(project: Path, item_id: str, title: str, today: str) -> None:
    path = (
        artifact_base(project, "technical", DEFAULT_TECHNICAL_BASE)
        / f"{item_id}-architecture-sketch.md"
    )
    if path.exists():
        return
    record = _item_record_pointer(project, item_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Architecture Sketch — {item_id}: {title}",
        "",
        f"- Work item: {item_id} — {title} (done, closed {today})",
    ]
    if record:
        lines.append(f"- Record: {record}")
    lines.extend(
        [
            "- Key files/areas: not recorded by the closeout path — this sketch is an "
            "honest skeleton, not a fabricated map. Fill it in when the item's shape matters.",
            "",
            "Background capture at closeout in Flow mode.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _append_decision_entry(project: Path, item_id: str, title: str, today: str) -> None:
    path = Path(project) / DECISION_LOG
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    marker = f"**Item:** {item_id}"
    if marker in existing:
        return
    number = next_dec_number(existing)
    entry = (
        f"## DEC-{number:03d}: Completed {item_id} — {title}\n\n"
        f"**Date:** {today}\n"
        "**Status:** Accepted\n"
        "**Context:** Flow-mode background capture at work-item closeout.\n"
        f"{marker}\n\n"
        f"**Decision:** {item_id} ({title}) is complete.\n"
        "**Rationale:** The completion itself is the decision; the closeout path records "
        "no alternatives, so none are fabricated here.\n"
        f"**Consequences:** {item_id}'s completion is part of the decision record.\n"
    )
    body = existing.rstrip("\n")
    with open(path, "a", encoding="utf-8") as handle:
        if body:
            handle.write("\n\n" + entry.lstrip())
        else:
            handle.write(entry)


def _item_record_pointer(project: Path, item_id: str) -> str:
    try:
        from success_criteria_contracts import find_backlog_file

        found = find_backlog_file(Path(project), item_id)
        if found and found.exists():
            return found.relative_to(Path(project)).as_posix()
    except Exception:
        pass
    return ""