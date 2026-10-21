#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""SweetClaude mode-gate evaluator.

Evaluates the compiled mode gates in .sweetclaude/state/effective-gates.yaml
(produced by scripts/generate-effective-gates.sh from config/mode-gates.yaml)
against a requested skill load or phase advance.

Subcommands:
    load    --skill S [--args A] --project-dir D
    advance --to PHASE [--override-text T] --project-dir D

Prints {"allow": bool, "reasons": [...], "unmet": [...]} on stdout and exits 0
when allowed, 2 when denied, 1 on evaluation failure (treated as allow by
fail-open callers). Artifacts are resolved through the canonical store adapter
in hooks/sc-artifact-impl.py; legacy artifact-privacy overrides are honoured by
its resolve_product_base.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import yaml

EXIT_ALLOW = 0
EXIT_DENY = 2
EXIT_ERROR = 1

REPO_ROOT = Path(__file__).resolve().parent.parent

CATEGORY_SKILLS = ("build", "maintain")
LIBRARY_CATEGORIES = ("plan", "design", "build", "maintain", "configure", "utils")

IMPLEMENT_WORKFLOWS = frozenset({
    "code-feature", "code-issue", "code-tdd", "code-debt", "hotfix",
    "security-patch", "small-story", "large-story", "john-wick",
    "orchestrator", "rollback-revert",
})
SHIP_WORKFLOWS = frozenset({"deploy-ship"})
NON_ENTRY_WORKFLOWS = frozenset({
    "code-review", "code-testing", "code-verify", "john-wick-checkin",
    "product-sprint-plan", "product-user-tdd-tests", "project-backlog",
    "project-backlog-triage", "project-epics", "project-gh-import-issues",
    "project-gh-sync-issues", "project-issues", "project-sprints",
    "project-themes", "testing-accessibility", "testing-compliance",
    "testing-performance", "testing-plan", "testing-security",
    "testing-session", "postmortem", "something-broke",
})

HARD_GATE_SUFFIX = " Hard gate: SweetClaude will not proceed until the condition is met."
DEFAULT_SOFT_ESCAPE = "acknowledge it explicitly to proceed anyway"

CRITERIA = {
    "no_active_sprint": "an active sprint in the sprint store",
    "betting_table_approved": "betting table approval on the active issue",
    "wip_limit_reached": "the WIP limit not already reached",
    "issue_not_in_sprint": "the active issue assigned to the active sprint",
    "sprint_complete": "the active sprint closed once its issues are done",
    "ship_no_ship_decision": "a recorded ship/no-ship decision",
    "issues_from_backlog": "issues derived from an approved pitch",
}


def _load_module(name: str, relative: str):
    path = REPO_ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_effective_gates(project_dir: str) -> dict | None:
    path = Path(project_dir) / ".sweetclaude" / "state" / "effective-gates.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def load_sweetclaude_state(project_dir: str) -> dict:
    path = Path(project_dir) / ".sweetclaude" / "state" / "sweetclaude.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


class ProjectContext:
    def __init__(self, project_dir: str, effective: dict) -> None:
        self.project_dir = project_dir
        self.effective = effective
        self.artifact_impl = _load_module("gate_check_sc_artifact_impl", "hooks/sc-artifact-impl.py")
        self.hook_io = _load_module("gate_check_hook_io", "hooks/lib/hook_io.py")
        self.sweetclaude = load_sweetclaude_state(project_dir)
        self.product_base = self.artifact_impl.resolve_product_base(Path(project_dir))
        self.active_work_id = str(((self.sweetclaude.get("work") or {}).get("active") or {}).get("id") or "")
        self._active_sprints = None
        self._issue_rows = None

    def active_sprints(self) -> list[dict]:
        if self._active_sprints is None:
            rows = []
            for path in self.artifact_impl._artifact_files(self.product_base, "sprint", "SP"):
                try:
                    row = self.artifact_impl._parse_metadata(path.read_text(encoding="utf-8"))
                except OSError:
                    continue
                if str((row or {}).get("status") or "").lower() == "active" and row.get("id"):
                    rows.append(row)
            self._active_sprints = rows
        return self._active_sprints

    def active_sprint_ids(self) -> set[str]:
        return {str(row.get("id")).upper() for row in self.active_sprints()}

    def issue_rows(self) -> list[dict]:
        if self._issue_rows is None:
            rows = []
            for path in self.artifact_impl._artifact_files(self.product_base, "issue", "ISSUE"):
                try:
                    content = path.read_text(encoding="utf-8")
                except OSError:
                    continue
                row = self.artifact_impl._parse_metadata(content)
                if row:
                    row["_status"] = self.hook_io.issue_status(content)
                    rows.append(row)
            self._issue_rows = rows
        return self._issue_rows

    def active_issue_count(self) -> int:
        return sum(1 for row in self.issue_rows() if row["_status"] in self.hook_io.ACTIVE_STATUSES)

    def active_issue(self) -> dict | None:
        if not self.active_work_id:
            return None
        path = self.artifact_impl._find_file(self.product_base, self.active_work_id)
        if path is None:
            return None
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            return None
        return self.artifact_impl._parse_metadata(content)

    def wip_limit(self) -> int:
        try:
            return int(self.effective.get("wip_limit", 3))
        except (TypeError, ValueError):
            return 3

    def truthy(self, value) -> bool:
        return value is True or str(value).strip().lower() in {"true", "yes", "1"}


def no_active_sprint(ctx: ProjectContext) -> bool:
    return not ctx.active_sprints()


def issue_not_in_sprint(ctx: ProjectContext) -> bool:
    if not ctx.active_sprints():
        return False
    issue = ctx.active_issue()
    if issue is None:
        return False
    assigned = str(issue.get("sprint") or issue.get("sprint_id") or "")
    return not assigned or assigned.upper() not in ctx.active_sprint_ids()


def sprint_complete(ctx: ProjectContext) -> bool:
    sprints = ctx.active_sprints()
    if not sprints:
        return False
    sprint_id = str(sprints[0].get("id")).upper()
    issues = [row for row in ctx.issue_rows()
              if str(row.get("sprint") or row.get("sprint_id") or "").upper() == sprint_id]
    if not issues:
        return False
    return all(row["_status"] == "done" for row in issues)


def wip_limit_reached(ctx: ProjectContext) -> bool:
    return ctx.active_issue_count() >= ctx.wip_limit()


def betting_table_approved_met(ctx: ProjectContext) -> bool:
    if not ctx.active_work_id:
        return False
    issue = ctx.active_issue()
    if issue is not None and ctx.truthy(issue.get("betting_table_approved")):
        return True
    legacy = (Path(ctx.project_dir) / ".sweetclaude" / "artifacts" / "issues"
              / f"{ctx.active_work_id}.yaml")
    try:
        data = yaml.safe_load(legacy.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return False
    return ctx.truthy((data or {}).get("betting_table_approved"))


CONDITION_HOLDERS = {
    "no_active_sprint": no_active_sprint,
    "issue_not_in_sprint": issue_not_in_sprint,
    "sprint_complete": sprint_complete,
    "wip_limit_reached": wip_limit_reached,
}

REQUIREMENT_MET = {
    "betting_table_approved": betting_table_approved_met,
}

HARD_ACTIONS = frozenset({"block", "required"})
SOFT_ACTIONS = frozenset({"warn", "prompt"})


def format_message(gate: dict, ctx: ProjectContext) -> str:
    message = str(gate.get("message") or "Gate condition not met.")
    try:
        return message.format(current=ctx.active_issue_count(), limit=ctx.wip_limit())
    except (KeyError, IndexError, ValueError):
        return message


def gate_reason(gate: dict, ctx: ProjectContext, override_text: str) -> str:
    gate_id = str(gate.get("condition") or gate.get("requires") or "")
    criterion = CRITERIA.get(gate_id, gate_id)
    base = f"Gate {gate_id} unmet: {format_message(gate, ctx)}. Unmet: {criterion}."
    if gate.get("action") in HARD_ACTIONS:
        return base + HARD_GATE_SUFFIX
    escape = override_text or DEFAULT_SOFT_ESCAPE
    return base + f" Soft gate: {escape}."


def evaluate_gate(gate: dict, ctx: ProjectContext) -> bool | None:
    condition = gate.get("condition")
    requires = gate.get("requires")
    if condition:
        check = CONDITION_HOLDERS.get(str(condition))
        return check(ctx) if check is not None else None
    if requires:
        check = REQUIREMENT_MET.get(str(requires))
        return not check(ctx) if check is not None else None
    return None


def evaluate_gates_for_phase(phase: str, ctx: ProjectContext, override_text: str) -> dict:
    reasons: list[str] = []
    unmet: list[str] = []
    allowed = True
    for gate in ctx.effective.get("gates") or []:
        if not isinstance(gate, dict) or str(gate.get("phase") or "") != phase:
            continue
        action = str(gate.get("action") or "")
        try:
            unmet_gate = evaluate_gate(gate, ctx)
        except Exception:
            unmet_gate = None
        if unmet_gate is not True:
            continue
        gate_id = str(gate.get("condition") or gate.get("requires") or "")
        unmet.append(gate_id)
        reasons.append(gate_reason(gate, ctx, override_text))
        if action in HARD_ACTIONS:
            allowed = False
    return {"allow": allowed, "reasons": reasons, "unmet": unmet}


def phase_exit_criteria(phase: str, ctx: ProjectContext) -> list[dict]:
    return []


def evaluate_advance(phase: str, override_text: str, ctx: ProjectContext) -> dict:
    result = evaluate_gates_for_phase(phase, ctx, override_text)
    for criterion in phase_exit_criteria(phase, ctx):
        if criterion.get("met") is False:
            result["unmet"].append(str(criterion.get("id") or ""))
            result["reasons"].append(str(criterion.get("reason") or ""))
            if criterion.get("action") in HARD_ACTIONS:
                result["allow"] = False
    return result


def bare_skill_name(skill: str) -> str:
    name = str(skill or "")
    return name.removeprefix("sweetclaude:")


def load_target_phases(skill: str, args: str) -> list[str]:
    bare = bare_skill_name(skill)
    tokens = str(args or "").split()
    workflow = ""
    for token in tokens[:2]:
        if token in IMPLEMENT_WORKFLOWS or token in SHIP_WORKFLOWS or token in NON_ENTRY_WORKFLOWS:
            workflow = token
            break
    if bare in IMPLEMENT_WORKFLOWS:
        return ["IMPLEMENT"]
    if bare in SHIP_WORKFLOWS:
        return ["SHIP"]
    if bare in NON_ENTRY_WORKFLOWS:
        return []
    if bare == "library-load":
        if workflow:
            return ["IMPLEMENT"] if workflow in IMPLEMENT_WORKFLOWS else (
                ["SHIP"] if workflow in SHIP_WORKFLOWS else [])
        first = tokens[0] if tokens else ""
        return ["IMPLEMENT"] if first in CATEGORY_SKILLS else []
    if bare in CATEGORY_SKILLS:
        return [] if workflow else ["IMPLEMENT"]
    return []


def evaluate_load(skill: str, args: str, override_text: str, ctx: ProjectContext) -> dict:
    reasons: list[str] = []
    unmet: list[str] = []
    allowed = True
    for phase in load_target_phases(skill, args):
        result = evaluate_gates_for_phase(phase, ctx, override_text)
        allowed = allowed and result["allow"]
        reasons.extend(result["reasons"])
        unmet.extend(result["unmet"])
    return {"allow": allowed, "reasons": reasons, "unmet": unmet}


def allow_result() -> dict:
    return {"allow": True, "reasons": [], "unmet": []}


def emit(result: dict) -> int:
    sys.stdout.write(json.dumps(result) + "\n")
    return EXIT_DENY if result["allow"] is False else EXIT_ALLOW


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="gate_check.py", description="SweetClaude mode-gate evaluator")
    commands = parser.add_subparsers(dest="command", required=True)

    load_cmd = commands.add_parser("load", help="evaluate gates before a skill or workflow loads")
    load_cmd.add_argument("--skill", required=True)
    load_cmd.add_argument("--args", default="")
    load_cmd.add_argument("--override-text", default="")
    load_cmd.add_argument("--project-dir", default=".")

    advance_cmd = commands.add_parser("advance", help="evaluate gates for a phase advance")
    advance_cmd.add_argument("--to", required=True, dest="phase")
    advance_cmd.add_argument("--override-text", default="")
    advance_cmd.add_argument("--project-dir", default=".")

    parsed = parser.parse_args(argv)

    effective = load_effective_gates(parsed.project_dir)
    if effective is None:
        return emit(allow_result())
    gates = effective.get("gates")
    effective["gates"] = [g for g in gates if isinstance(g, dict)] if isinstance(gates, list) else []
    ctx = ProjectContext(parsed.project_dir, effective)
    if parsed.command == "load":
        return emit(evaluate_load(parsed.skill, parsed.args, parsed.override_text, ctx))
    return emit(evaluate_advance(parsed.phase, parsed.override_text, ctx))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))