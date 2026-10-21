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
import os
import re
import sys
from datetime import date
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

SOFT_GATE_ESCAPE = "I've addressed this informally — proceed"

WORK_TYPE_SECTIONS = {
    "Net-new feature": "net-new-feature",
    "External integration": "external-integration",
    "Course correction": "course-correction",
    "Security planning": "security-planning",
    "Enhancement / iteration": "enhancement",
    "Tech debt / refactor": "tech-debt",
    "Compliance requirement": "compliance-requirement",
    "Infrastructure change": "infrastructure-change",
    "Onboarding flow design": "onboarding-flow-design",
    "Release planning": "release-planning",
    "Bug fix": "bug-fix",
    "Security patch": "security-patch",
    "Performance optimization": "performance-optimization",
    "Rollback / revert": "rollback-revert",
    "Technology migration": "technology-migration",
    "Data migration": "data-migration",
    "API deprecation": "api-deprecation",
    "Dependency upgrade": "dependency-upgrade",
    "Hotfix": "hotfix",
}

_PHASE_HEADING = re.compile(r"^\*\*([A-Z][A-Z-]+)\*\*(.*)$")
_CRITERION_BULLET = re.compile(r"^- (\S.*)$")
_PHASE_EXIT_KEY = re.compile(r"^[A-Z][A-Z-]+$")

_PHASE_GATES_CACHE: dict | None = None
_HARD_GATE_POLICY_CACHE: dict | None = None


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


def parse_phase_gates() -> dict:
    """rules/phase-gates.md -> {work_type: {PHASE: {"criteria": [str], "hard": bool}}}.

    Tolerant: only '## ' sections whose title maps to a work type are parsed,
    only top-level bullets under a '**PHASE**' heading become criteria, and a
    phase heading carrying a HARD GATE marker makes its criteria hard.
    """
    global _PHASE_GATES_CACHE
    if _PHASE_GATES_CACHE is None:
        _PHASE_GATES_CACHE = _parse_phase_gates_file(REPO_ROOT / "rules" / "phase-gates.md")
    return _PHASE_GATES_CACHE


def _parse_phase_gates_file(path: Path) -> dict:
    gates: dict = {}
    if not path.exists():
        return gates
    work_type = None
    phase = None
    hard = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            work_type = WORK_TYPE_SECTIONS.get(line[3:].strip())
            phase = None
            hard = False
            continue
        if work_type is None:
            continue
        heading = _PHASE_HEADING.match(line)
        if heading:
            phase = heading.group(1)
            hard = "HARD GATE" in heading.group(2).upper()
            continue
        if phase is None:
            continue
        bullet = _CRITERION_BULLET.match(line)
        if bullet:
            criterion = bullet.group(1).strip()
            if criterion:
                gates.setdefault(work_type, {}).setdefault(
                    phase, {"criteria": [], "hard": hard})["criteria"].append(criterion)
    return gates


def active_phase(ctx: ProjectContext) -> str:
    active = (ctx.sweetclaude.get("work") or {}).get("active") or {}
    return str(active.get("phase") or "").strip().upper()


def active_work_type(ctx: ProjectContext) -> str:
    active = (ctx.sweetclaude.get("work") or {}).get("active") or {}
    tagged = str(active.get("type") or "").strip()
    if tagged:
        return tagged
    issue = ctx.active_issue()
    return str((issue or {}).get("type") or "").strip()


def normalize_criterion(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text).casefold()).strip()


def phase_exit_records(ctx: ProjectContext) -> tuple[dict[str, list[str]], str]:
    """work.active.phase_exit -> ({PHASE: [entries]}, current phase).

    Accepts the canonical {PHASE: [criteria]} mapping plus a flat list read as
    the current phase's records.
    """
    active = (ctx.sweetclaude.get("work") or {}).get("active") or {}
    current = str(active.get("phase") or "").strip().upper()
    raw = active.get("phase_exit")
    if isinstance(raw, list):
        values = [str(v) for v in raw if str(v).strip()]
        return ({current: values} if current and values else {}), current
    if not isinstance(raw, dict):
        return {}, current
    records: dict[str, list[str]] = {}
    for key, value in raw.items():
        if not _PHASE_EXIT_KEY.match(str(key)):
            continue
        entries = value if isinstance(value, list) else ([str(value)] if value else [])
        entries = [str(v) for v in entries if str(v).strip()]
        if entries:
            records[str(key).upper()] = entries
    return records, current


def hard_gate_policy() -> dict:
    """Map config/workflow-templates.yaml hard_gate_policy into the check.

    Returns {"apply_at": {stages}, "tasks": {task: [prerequisites]},
    "phases": {task: [hard-gate phases]}}; unreadable config fails open to {}.
    """
    global _HARD_GATE_POLICY_CACHE
    if _HARD_GATE_POLICY_CACHE is None:
        policy: dict = {}
        try:
            data = yaml.safe_load(
                (REPO_ROOT / "config" / "workflow-templates.yaml").read_text(encoding="utf-8")
            ) or {}
            raw = data.get("hard_gate_policy") or {}
            tasks = {}
            for entry in raw.get("hard_gate_tasks") or []:
                if isinstance(entry, dict) and entry.get("task"):
                    tasks[str(entry["task"])] = [str(p) for p in entry.get("prerequisites") or []]
            phases = {}
            for wtype, entry in (data.get("work_types") or {}).items():
                if isinstance(entry, dict) and isinstance(entry.get("hard_gates"), dict):
                    phases[str(wtype)] = [str(p) for p in entry["hard_gates"].keys()]
            policy = {
                "apply_at": {str(s).upper() for s in raw.get("hard_gates_apply_at") or []},
                "tasks": tasks,
                "phases": phases,
            }
        except (OSError, yaml.YAMLError, AttributeError):
            pass
        _HARD_GATE_POLICY_CACHE = policy
    return _HARD_GATE_POLICY_CACHE


def project_version_stage(ctx: ProjectContext) -> str:
    project = ctx.sweetclaude.get("project") or {}
    return str(project.get("version_stage") or "").strip().upper() if isinstance(project, dict) else ""


def soft_escape_matches(text: str) -> bool:
    """Config soft_gate_escape phrase: case-insensitive, prefix
    "I've addressed this informally", suffix "— proceed", optional note
    between, curly and straight apostrophes equal."""
    normalized = str(text or "").replace("\u2019", "'").strip().casefold()
    return bool(re.match(r"^i've addressed this informally\b.*\u2014 proceed\.?$",
                        normalized, re.DOTALL))


def hard_override_matches(text: str, gate_id: str) -> bool:
    normalized = str(text or "").replace("\u2019", "'").casefold()
    return f"i accept the risk of {str(gate_id).casefold()}" in normalized


def _next_dec_number(text: str) -> int:
    numbers = [int(m) for m in re.findall(r"^## DEC-(\d+):", text, re.M)]
    return max(numbers) + 1 if numbers else 1


def append_gate_override_entry(ctx: ProjectContext, kind: str, gate_id: str,
                               phase: str, target: str, waived: list[str]) -> None:
    """Append the override entry to decision-log.md in the DEC-NNN format.

    Idempotent: an existing entry with the same kind, gate and work item is
    left alone. The entry carries the Gate and Work item fields the
    design-manage-decisions format uses, plus the waived criteria.
    """
    log_path = Path(ctx.project_dir) / ".sweetclaude" / "state" / "decision-log.md"
    try:
        existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    except OSError:
        return
    title = f"{'Soft' if kind == 'soft' else 'Hard'} gate override — {gate_id} on {ctx.active_work_id}"
    if re.search(r"^## DEC-\d+: " + re.escape(title) + r"$", existing, re.M):
        return
    today = date.today().isoformat()
    if kind == "soft":
        decision = f'Soft-gate escape accepted: "{SOFT_GATE_ESCAPE}".'
        rationale = (
            "Soft gates are advisory; the escape phrase is the approved bypass "
            "(config/workflow-templates.yaml hard_gate_policy.soft_gate_escape)."
        )
        consequences = (
            f"The unmet {phase} exit criteria are recorded as satisfied by override; "
            "the advance proceeds."
        )
    else:
        decision = f'Explicit risk acceptance recorded: "I accept the risk of {gate_id}".'
        rationale = (
            "Hard gates cannot be soft-bypassed; only explicit risk acceptance passes them "
            "(config/workflow-templates.yaml hard_gate_policy.hard_gate_override)."
        )
        consequences = (
            f"The user accepted the risk of proceeding without {gate_id}; "
            "the override is recorded here."
        )
    fields = [
        f"**Date:** {today}",
        "**Status:** Accepted",
        f"**Context:** Phase advance from {phase} to {str(target).upper()} requested with an "
        f"unmet {'soft' if kind == 'soft' else 'hard'} gate.",
        f"**Gate:** {gate_id} ({kind})",
        f"**Work item:** {ctx.active_work_id}",
    ]
    if waived:
        fields.append(f"**Criteria waived:** {'; '.join(waived)}")
    fields.extend([
        f"**Decision:** {decision}",
        f"**Rationale:** {rationale}",
        f"**Consequences:** {consequences}",
    ])
    entry = f"## DEC-{_next_dec_number(existing):03d}: {title}\n\n" + "\n".join(fields) + "\n"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    body = existing.rstrip("\n")
    with open(log_path, "a", encoding="utf-8") as handle:
        if body:
            handle.write("\n\n" + entry.lstrip())
        else:
            handle.write(entry)


def record_phase_exit(ctx: ProjectContext, phase: str, satisfied: list[str]) -> None:
    """Record satisfied criteria under work.active.phase_exit atomically.

    Follows the _save_sc_yaml conventions in scripts/orchestrator_loop.py:
    round-trip the state file, write to a temp file, os.replace into place.
    """
    state_path = Path(ctx.project_dir) / ".sweetclaude" / "state" / "sweetclaude.yaml"
    try:
        data = yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return
    if not isinstance(data, dict):
        return
    work = data.get("work")
    if not isinstance(work, dict):
        return
    active = work.get("active")
    if not isinstance(active, dict) or not active.get("id"):
        return
    raw = active.get("phase_exit")
    records: dict[str, list[str]] = {}
    if isinstance(raw, list):
        records[phase] = [str(v) for v in raw if str(v).strip()]
    elif isinstance(raw, dict):
        for key, value in raw.items():
            if not _PHASE_EXIT_KEY.match(str(key)):
                continue
            entries = value if isinstance(value, list) else ([str(value)] if value else [])
            entries = [str(v) for v in entries if str(v).strip()]
            if entries:
                records[str(key).upper()] = entries
    merged = list(records.get(phase, []))
    known = {normalize_criterion(v) for v in merged}
    for entry in satisfied:
        if normalize_criterion(entry) not in known:
            merged.append(str(entry))
            known.add(normalize_criterion(entry))
    records[phase] = merged
    active["phase_exit"] = records
    work["active"] = active
    tmp = state_path.with_name(state_path.name + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            yaml.safe_dump(data, handle, default_flow_style=False, allow_unicode=True)
        os.replace(tmp, state_path)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass


def gate_pass_record(ctx: ProjectContext, gate_id: str, item_id: str) -> bool:
    """True when decision-log.md has an entry headed `gate_id` with
    "Result: pass" and the work item id — the solutioning-gate pass-record
    convention, generalized to every hard-gate prerequisite."""
    log_path = Path(ctx.project_dir) / ".sweetclaude" / "state" / "decision-log.md"
    try:
        text = log_path.read_text(encoding="utf-8")
    except OSError:
        return False
    wanted = str(gate_id).casefold()
    for chunk in re.split(r"^## ", text, flags=re.M)[1:]:
        heading = chunk.splitlines()[0].casefold().strip()
        if heading != wanted and not re.match(re.escape(wanted) + r"[\s:—-]", heading):
            continue
        body = re.sub(r"[*_]", "", chunk).casefold()
        if "result: pass" in body and item_id.casefold() in body:
            return True
    return False


def phase_exit_criteria(phase: str, ctx: ProjectContext, override_text: str = "") -> list[dict]:
    """The exit criteria for the work item's current phase, parsed from
    rules/phase-gates.md minus the ones recorded as satisfied under
    work.active.phase_exit, as a list of gate entries. The current phase is
    read from work.active.phase and the work type from work.active.type
    (falling back to the active item's frontmatter type); unknown types and
    missing phases fail open. Criteria under a phase heading marked HARD GATE
    are hard at the stages in hard_gate_policy.hard_gates_apply_at and soft
    below them, per the policy in config/workflow-templates.yaml. A soft gate
    is passed by the soft_gate_escape phrase, a hard gate only by the per-gate
    risk-acceptance phrase; both override paths are returned for the caller
    to log and record.
    """
    current = active_phase(ctx)
    item_id = ctx.active_work_id
    if not item_id or not current or current == str(phase).strip().upper():
        return []
    wtype = active_work_type(ctx)
    if not wtype:
        return []
    section = parse_phase_gates().get(wtype, {}).get(current)
    if not section:
        return []
    records, _ = phase_exit_records(ctx)
    satisfied = {normalize_criterion(c) for c in records.get(current, [])}
    satisfied_gates = {str(g).casefold() for entries in records.values() for g in entries}
    unmet = [c for c in section["criteria"] if normalize_criterion(c) not in satisfied]
    entries: list[dict] = []
    gate_id = f"{wtype}.{current}"
    hard = bool(section["hard"]) and project_version_stage(ctx) in (hard_gate_policy().get("apply_at") or set())
    if unmet:
        listing = "; ".join(unmet)
        if hard and hard_override_matches(override_text, gate_id):
            entries.append({"id": gate_id, "met": True, "action": "block",
                            "override": ("hard", gate_id, current, unmet)})
        elif not hard and soft_escape_matches(override_text):
            entries.append({"id": gate_id, "met": True, "action": "block",
                            "override": ("soft", gate_id, current, unmet)})
        else:
            if hard:
                reason = (
                    f"Gate {gate_id} unmet: exit criteria for {current} not recorded as satisfied. "
                    f"Unmet: {listing}.{HARD_GATE_SUFFIX} "
                    f'Override requires explicit risk acceptance: "I accept the risk of {gate_id}".'
                )
            else:
                reason = (
                    f"Gate {gate_id} unmet: exit criteria for {current} not recorded as satisfied. "
                    f"Unmet: {listing}. Soft gate: bypass with \"{SOFT_GATE_ESCAPE}\" "
                    "(the override is logged to the decision log)."
                )
            entries.append({"id": gate_id, "met": False, "action": "block", "reason": reason})

    if project_version_stage(ctx) not in (hard_gate_policy().get("apply_at") or set()):
        return entries

    policy = hard_gate_policy()
    tasks = policy.get("tasks") or {}
    solutioning_met = ("solutioning-gate".casefold() in satisfied_gates
                       or gate_pass_record(ctx, "solutioning-gate", item_id))
    if current in (policy.get("phases") or {}).get(wtype, []):
        for prerequisite in tasks.get(wtype, []):
            if (prerequisite.casefold() in satisfied_gates
                    or gate_pass_record(ctx, prerequisite, item_id)):
                continue
            if hard_override_matches(override_text, prerequisite):
                entries.append({"id": prerequisite, "met": True, "action": "block",
                                "override": ("hard", prerequisite, current, [prerequisite])})
                continue
            entries.append({
                "id": prerequisite, "met": False, "action": "block",
                "reason": (
                    f"Gate {prerequisite} unmet: required by the hard gate policy before "
                    f"{wtype} advances past {current} (config/workflow-templates.yaml "
                    f"hard_gate_tasks).{HARD_GATE_SUFFIX} "
                    f'Override requires explicit risk acceptance: "I accept the risk of {prerequisite}".'
                ),
            })
    emitted = {str(entry.get("id")) for entry in entries}
    if (current == "DESIGN" and wtype in tasks and not solutioning_met
            and "solutioning-gate" not in emitted):
        if hard_override_matches(override_text, "solutioning-gate"):
            entries.append({"id": "solutioning-gate", "met": True, "action": "block",
                            "override": ("hard", "solutioning-gate", current, ["solutioning-gate"])})
        else:
            entries.append({
                "id": "solutioning-gate", "met": False, "action": "block",
                "reason": (
                    f"Gate solutioning-gate unmet: required before DESIGN exits for hard-gate "
                    f"work type {wtype} (config/workflow-templates.yaml hard_gate_tasks). Run "
                    f"/sweetclaude:design design-solutioning-gate for {item_id} and record the "
                    "pass in .sweetclaude/state/decision-log.md (a 'solutioning-gate' entry with "
                    f"'Result: pass').{HARD_GATE_SUFFIX} "
                    'Override requires explicit risk acceptance: "I accept the risk of solutioning-gate".'
                ),
            })
    target = str(phase).strip().upper()
    if (target == "DESIGN" and current != "DESIGN" and wtype in tasks
            and not solutioning_met and "solutioning-gate" not in emitted):
        entries.append({
            "id": "solutioning-gate", "met": False, "action": "prompt",
            "reason": (
                "Solutioning gate required before DESIGN exits: run /sweetclaude:design "
                f"design-solutioning-gate for {item_id} and record the pass in "
                ".sweetclaude/state/decision-log.md (a 'solutioning-gate' entry with 'Result: pass')."
            ),
        })
    return entries


def evaluate_advance(phase: str, override_text: str, ctx: ProjectContext) -> dict:
    result = evaluate_gates_for_phase(phase, ctx, override_text)
    overrides = []
    for entry in phase_exit_criteria(phase, ctx, override_text):
        override = entry.get("override")
        if override:
            overrides.append(override)
            continue
        if entry.get("met") is False:
            result["unmet"].append(str(entry.get("id") or ""))
            result["reasons"].append(str(entry.get("reason") or ""))
            if entry.get("action") in HARD_ACTIONS:
                result["allow"] = False
    if result["allow"] and overrides and ctx.active_work_id:
        for kind, gate_id, phase_key, waived in overrides:
            append_gate_override_entry(ctx, kind, gate_id, phase_key, phase, waived)
            record_phase_exit(ctx, phase_key, waived)
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