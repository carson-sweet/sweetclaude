"""Contract tests for the phase-gate remediation rows (R-098, R-099, R-100, R-101, R-103).

scripts/gate_check.py evaluates the compiled mode gates and, for phase-advance
requests, the exit criteria parsed from rules/phase-gates.md plus the hard
gate policy in config/workflow-templates.yaml. Per the approved ledger
decisions, the advance check reads the work item's current phase and type from
work.active in .sweetclaude/state/sweetclaude.yaml and the satisfied criteria
recorded under work.active.phase_exit, so these tests drive `advance` directly
against fixture projects.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE_CHECK = REPO_ROOT / "scripts" / "gate_check.py"
SCRIPTS_DIR = REPO_ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import gate_check  # noqa: E402

DESIGN_CRITERIA = [
    "Architecture document written and reviewed",
    "Tech spec written and reviewed",
    "Data model designed",
    "API contracts defined (if applicable)",
    "UX flows documented",
    "Solutioning gate passed",
    "Key design decisions recorded",
]

DATA_MIGRATION_ASSESS_CRITERIA = [
    "Data to migrate identified: tables, collections, files, volume",
    "Schema mapping defined: old to new",
    "Data quality issues identified: nulls, invalid values, encoding problems",
    "Rollback plan: how to restore from backup if migration fails",
    "Downtime requirement assessed: live migration or maintenance window",
]


def run_gate_check(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(GATE_CHECK), *args],
                          capture_output=True, text=True, timeout=30)


def gate_json(result: subprocess.CompletedProcess) -> dict:
    return json.loads(result.stdout)


def write_state(project: Path, active: dict, *, stage: str = "GA", mode: str = "flow") -> None:
    state = project / ".sweetclaude" / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "sweetclaude.yaml").write_text(yaml.safe_dump({
        "schema_version": 2,
        "project": {"name": "t", "mode": mode, "version_stage": stage},
        "framework": {"setup_complete": True},
        "work": {"active": active},
    }, sort_keys=False), encoding="utf-8")


def write_gates(project: Path) -> None:
    state = project / ".sweetclaude" / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "effective-gates.yaml").write_text(yaml.safe_dump({
        "schema_version": 1, "mode": "flow", "default_tdd_level": 1,
        "blocked_skills": [], "gates": [],
    }), encoding="utf-8")


def phase_project(root: Path, *, wtype: str, phase: str, stage: str = "GA",
                  satisfied: list[str] | None = None,
                  active: dict | None = None) -> Path:
    project = root / "project"
    project.mkdir(parents=True)
    write_gates(project)
    item = active if active is not None else {"id": "ISSUE-001", "phase": phase, "type": wtype}
    if satisfied is not None:
        item["phase_exit"] = {phase: satisfied}
    write_state(project, item, stage=stage)
    return project


class TestR098AdvanceRefusesUnmetExitCriteria:
    def test_advance_past_design_with_unmet_criteria_is_refused(self, tmp_path):
        project = phase_project(tmp_path, wtype="net-new-feature", phase="DESIGN")
        result = run_gate_check("advance", "--to", "PLAN", "--project-dir", str(project))
        assert result.returncode == 2, result.stdout
        payload = gate_json(result)
        assert payload["allow"] is False
        assert "net-new-feature.DESIGN" in payload["unmet"]
        assert any("Unmet: " + "; ".join(DESIGN_CRITERIA) + "." in reason
                   for reason in payload["reasons"]), payload["reasons"]

    def test_each_unmet_criterion_is_named_verbatim(self, tmp_path):
        project = phase_project(tmp_path, wtype="net-new-feature", phase="DESIGN")
        payload = gate_json(run_gate_check("advance", "--to", "PLAN", "--project-dir", str(project)))
        listing = next(r for r in payload["reasons"] if "Unmet:" in r)
        for criterion in DESIGN_CRITERIA:
            assert criterion in listing

    def test_recorded_satisfied_criteria_allow_the_advance(self, tmp_path):
        project = phase_project(tmp_path, wtype="net-new-feature", phase="DESIGN",
                                satisfied=list(DESIGN_CRITERIA))
        result = run_gate_check("advance", "--to", "PLAN", "--project-dir", str(project))
        assert result.returncode == 0, result.stdout
        assert gate_json(result) == {"allow": True, "reasons": [], "unmet": []}

    def test_partial_records_name_only_the_unmet_criteria(self, tmp_path):
        project = phase_project(tmp_path, wtype="net-new-feature", phase="DESIGN",
                                satisfied=DESIGN_CRITERIA[:2])
        payload = gate_json(run_gate_check("advance", "--to", "PLAN", "--project-dir", str(project)))
        assert payload["allow"] is False
        listing = next(r for r in payload["reasons"] if "Unmet:" in r)
        assert "; ".join(DESIGN_CRITERIA[2:]) + "." in listing
        for criterion in DESIGN_CRITERIA[:2]:
            assert criterion not in listing

    def test_unknown_work_type_fails_open(self, tmp_path):
        project = phase_project(tmp_path, wtype="story", phase="DESIGN")
        result = run_gate_check("advance", "--to", "PLAN", "--project-dir", str(project))
        assert result.returncode == 0, result.stdout
        assert gate_json(result) == {"allow": True, "reasons": [], "unmet": []}

    def test_missing_current_phase_fails_open(self, tmp_path):
        project = phase_project(tmp_path, wtype="net-new-feature", phase="",
                                active={"id": "ISSUE-001", "type": "net-new-feature"})
        result = run_gate_check("advance", "--to", "PLAN", "--project-dir", str(project))
        assert result.returncode == 0, result.stdout
        assert gate_json(result) == {"allow": True, "reasons": [], "unmet": []}

    def test_advance_to_the_current_phase_checks_nothing(self, tmp_path):
        project = phase_project(tmp_path, wtype="net-new-feature", phase="DESIGN")
        result = run_gate_check("advance", "--to", "DESIGN", "--project-dir", str(project))
        assert result.returncode == 0, result.stdout
        assert gate_json(result) == {"allow": True, "reasons": [], "unmet": []}


class TestR098PhaseGatesParser:
    def test_all_nineteen_work_type_sections_parse(self):
        gates = gate_check.parse_phase_gates()
        assert sorted(gates) == sorted([
            "net-new-feature", "external-integration", "course-correction",
            "security-planning", "enhancement", "tech-debt",
            "compliance-requirement", "infrastructure-change",
            "onboarding-flow-design", "release-planning", "bug-fix",
            "security-patch", "performance-optimization", "rollback-revert",
            "technology-migration", "data-migration", "api-deprecation",
            "dependency-upgrade", "hotfix",
        ])

    def test_criteria_are_kept_as_bullet_text(self):
        gates = gate_check.parse_phase_gates()
        assert gates["data-migration"]["ASSESS"]["criteria"] == DATA_MIGRATION_ASSESS_CRITERIA

    def test_hard_gate_phase_headings_mark_their_criteria_hard(self):
        gates = gate_check.parse_phase_gates()
        assert gates["data-migration"]["VERIFY"]["hard"] is True
        assert gates["technology-migration"]["CUTOVER"]["hard"] is True
        assert gates["infrastructure-change"]["DESIGN"]["hard"] is True
        assert gates["security-patch"]["VERIFY"]["hard"] is True
        assert gates["net-new-feature"]["DESIGN"]["hard"] is False

    def test_non_work_type_sections_are_not_parsed_as_criteria(self):
        gates = gate_check.parse_phase_gates()
        assert "Phase Definitions" not in gates
        assert "Skill entry gates" not in gates
        assert not any(
            "understand the problem space before committing" in criterion
            for phases in gates.values()
            for phase in phases.values()
            for criterion in phase["criteria"]
        )

    def test_indented_sub_bullets_stay_out_of_the_criteria(self):
        gates = gate_check.parse_phase_gates()
        criteria = gates["security-planning"]["DEFINE"]["criteria"]
        assert "Applicable standards mapped with rationale and business trigger:" in criteria
        assert not any(criterion.startswith("GDPR") for criterion in criteria)
