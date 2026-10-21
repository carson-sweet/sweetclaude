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

import pytest
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
    "Schema mapping defined: old → new",
    "Data quality issues identified: nulls, invalid values, encoding problems",
    "Rollback plan: how to restore from backup if migration fails",
    "Downtime requirement assessed: live migration or maintenance window",
]

ENHANCEMENT_DESIGN_CRITERIA = [
    "Approach decided and documented",
    "If UX change: updated flows reviewed",
    "If API change: contracts reviewed, backward compatibility assessed",
    "Edge cases identified",
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


def decision_log(project: Path) -> str:
    path = project / ".sweetclaude" / "state" / "decision-log.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_pass_record(project: Path, gate_id: str, item_id: str = "ISSUE-001") -> None:
    log_path = project / ".sweetclaude" / "state" / "decision-log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    entry = (
        f"## {gate_id} — {item_id}\n\n"
        "**Date:** 2026-10-21\n"
        f"**Work item:** {item_id}\n"
        "**Result:** pass\n"
    )
    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write(("\n" if existing else "") + entry)


def active_state(project: Path) -> dict:
    data = yaml.safe_load(
        (project / ".sweetclaude" / "state" / "sweetclaude.yaml").read_text(encoding="utf-8"))
    return (data.get("work") or {}).get("active") or {}


SOFT_ESCAPE = "I've addressed this informally — proceed"


class TestR099SoftGateEscapeIsLogged:
    def test_soft_escape_phrase_advances_and_logs_the_override(self, tmp_path):
        project = phase_project(tmp_path, wtype="enhancement", phase="DESIGN", stage="BETA")
        result = run_gate_check("advance", "--to", "IMPLEMENT",
                                "--override-text", SOFT_ESCAPE,
                                "--project-dir", str(project))
        assert result.returncode == 0, result.stdout
        assert gate_json(result)["allow"] is True
        log = decision_log(project)
        assert "## DEC-001: Soft gate override — enhancement.DESIGN on ISSUE-001" in log
        assert "**Gate:** enhancement.DESIGN (soft)" in log
        assert "**Work item:** ISSUE-001" in log
        assert SOFT_ESCAPE in log
        assert "**Criteria waived:** " + "; ".join(ENHANCEMENT_DESIGN_CRITERIA) in log

    def test_escape_phrase_matching_is_tolerant(self, tmp_path):
        project = phase_project(tmp_path, wtype="enhancement", phase="DESIGN", stage="BETA")
        override = "I’VE ADDRESSED THIS INFORMALLY (the sketch is on the whiteboard) — PROCEED."
        result = run_gate_check("advance", "--to", "IMPLEMENT",
                                "--override-text", override,
                                "--project-dir", str(project))
        assert result.returncode == 0, result.stdout
        assert gate_json(result)["allow"] is True
        assert "Soft gate override — enhancement.DESIGN on ISSUE-001" in decision_log(project)

    def test_non_matching_override_text_still_refuses(self, tmp_path):
        project = phase_project(tmp_path, wtype="enhancement", phase="DESIGN", stage="BETA")
        result = run_gate_check("advance", "--to", "IMPLEMENT",
                                "--override-text", "just proceed please",
                                "--project-dir", str(project))
        assert result.returncode == 2, result.stdout
        assert gate_json(result)["allow"] is False
        assert decision_log(project) == ""

    def test_hard_marked_criteria_are_soft_below_ga(self, tmp_path):
        project = phase_project(tmp_path, wtype="data-migration", phase="ASSESS", stage="BETA")
        result = run_gate_check("advance", "--to", "DESIGN",
                                "--override-text", SOFT_ESCAPE,
                                "--project-dir", str(project))
        assert result.returncode == 0, result.stdout
        assert gate_json(result)["allow"] is True
        assert "Soft gate override — data-migration.ASSESS on ISSUE-001" in decision_log(project)

    def test_override_logging_is_idempotent(self, tmp_path):
        project = phase_project(tmp_path, wtype="enhancement", phase="DESIGN", stage="BETA")
        for _ in range(2):
            run_gate_check("advance", "--to", "IMPLEMENT",
                           "--override-text", SOFT_ESCAPE,
                           "--project-dir", str(project))
        assert decision_log(project).count("Soft gate override — enhancement.DESIGN on ISSUE-001") == 1

    def test_override_records_the_criteria_satisfied(self, tmp_path):
        project = phase_project(tmp_path, wtype="enhancement", phase="DESIGN", stage="BETA")
        overridden = run_gate_check("advance", "--to", "IMPLEMENT",
                                    "--override-text", SOFT_ESCAPE,
                                    "--project-dir", str(project))
        assert overridden.returncode == 0
        recorded = active_state(project).get("phase_exit", {}).get("DESIGN", [])
        assert sorted(recorded) == sorted(ENHANCEMENT_DESIGN_CRITERIA)
        retried = run_gate_check("advance", "--to", "IMPLEMENT", "--project-dir", str(project))
        assert retried.returncode == 0, retried.stdout
        assert gate_json(retried) == {"allow": True, "reasons": [], "unmet": []}


class TestR100HardGateRiskAcceptanceIsLogged:
    def test_soft_phrase_alone_does_not_pass_a_hard_gate(self, tmp_path):
        project = phase_project(tmp_path, wtype="data-migration", phase="ASSESS", stage="GA")
        result = run_gate_check("advance", "--to", "DESIGN",
                                 "--override-text", SOFT_ESCAPE,
                                 "--project-dir", str(project))
        assert result.returncode == 2, result.stdout
        payload = gate_json(result)
        assert payload["allow"] is False
        assert any('Override requires explicit risk acceptance: "I accept the risk of data-migration.ASSESS".'
                   in reason for reason in payload["reasons"])

    def test_risk_acceptance_phrase_passes_and_logs(self, tmp_path):
        project = phase_project(tmp_path, wtype="data-migration", phase="ASSESS", stage="GA")
        write_pass_record(project, "solutioning-gate")
        write_pass_record(project, "change-impact-analysis")
        result = run_gate_check("advance", "--to", "DESIGN",
                                 "--override-text", "I accept the risk of data-migration.ASSESS",
                                 "--project-dir", str(project))
        assert result.returncode == 0, result.stdout
        assert gate_json(result)["allow"] is True
        log = decision_log(project)
        assert "Hard gate override — data-migration.ASSESS on ISSUE-001" in log
        assert "**Gate:** data-migration.ASSESS (hard)" in log
        assert "**Work item:** ISSUE-001" in log
        assert 'Explicit risk acceptance recorded: "I accept the risk of data-migration.ASSESS".' in log

    def test_risk_acceptance_for_a_different_gate_is_refused(self, tmp_path):
        project = phase_project(tmp_path, wtype="data-migration", phase="ASSESS", stage="GA")
        write_pass_record(project, "solutioning-gate")
        write_pass_record(project, "change-impact-analysis")
        result = run_gate_check("advance", "--to", "DESIGN",
                                 "--override-text", "I accept the risk of data-migration.VERIFY",
                                 "--project-dir", str(project))
        assert result.returncode == 2, result.stdout
        assert gate_json(result)["allow"] is False


HARD_GATE_MATRIX = [
    ("data-migration", "ASSESS", "DESIGN"),
    ("data-migration", "VERIFY", "SHIP"),
    ("infrastructure-change", "DESIGN", "IMPLEMENT"),
    ("technology-migration", "DESIGN", "PLAN"),
    ("technology-migration", "CUTOVER", "CLEANUP"),
    ("security-patch", "VERIFY", "SHIP"),
]

HARD_GATE_PREREQUISITES = {
    "data-migration": ["solutioning-gate", "change-impact-analysis"],
    "infrastructure-change": ["solutioning-gate", "change-impact-analysis", "rollback-plan"],
    "technology-migration": ["solutioning-gate", "change-impact-analysis", "parallel-run-plan"],
    "security-patch": ["security-review-post-fix"],
}


def all_criteria_satisfied(wtype: str, phase: str) -> list[str]:
    return list(gate_check.parse_phase_gates()[wtype][phase]["criteria"])


class TestR101HardGateMatrix:
    def test_hard_gate_policy_maps_the_config(self):
        policy = gate_check.hard_gate_policy()
        assert policy["apply_at"] == {"GA", "SCALED", "MAINTAINED"}
        assert sorted(policy["tasks"]["data-migration"]) == sorted(
            HARD_GATE_PREREQUISITES["data-migration"])
        assert sorted(policy["tasks"]["security-patch"]) == ["security-review-post-fix"]
        assert sorted(policy["phases"]["data-migration"]) == ["ASSESS", "VERIFY"]
        assert policy["phases"]["infrastructure-change"] == ["DESIGN"]
        assert sorted(policy["phases"]["technology-migration"]) == ["CUTOVER", "DESIGN"]
        assert policy["phases"]["security-patch"] == ["VERIFY"]

    @pytest.mark.parametrize("wtype,phase,target", HARD_GATE_MATRIX)
    def test_ga_advance_past_hard_gate_phase_denied_without_prerequisites(self, tmp_path, wtype, phase, target):
        project = phase_project(tmp_path, wtype=wtype, phase=phase, stage="GA",
                                satisfied=all_criteria_satisfied(wtype, phase))
        result = run_gate_check("advance", "--to", target, "--project-dir", str(project))
        assert result.returncode == 2, result.stdout
        payload = gate_json(result)
        assert payload["allow"] is False
        assert set(HARD_GATE_PREREQUISITES[wtype]) <= set(payload["unmet"])
        for prerequisite in HARD_GATE_PREREQUISITES[wtype]:
            assert any(f"Gate {prerequisite} unmet" in reason
                       and "hard_gate_tasks" in reason
                       for reason in payload["reasons"])

    @pytest.mark.parametrize("wtype,phase,target", HARD_GATE_MATRIX)
    def test_ga_advance_allowed_with_prerequisite_pass_records(self, tmp_path, wtype, phase, target):
        project = phase_project(tmp_path, wtype=wtype, phase=phase, stage="GA",
                                satisfied=all_criteria_satisfied(wtype, phase))
        for prerequisite in HARD_GATE_PREREQUISITES[wtype]:
            write_pass_record(project, prerequisite)
        result = run_gate_check("advance", "--to", target, "--project-dir", str(project))
        assert result.returncode == 0, result.stdout
        assert gate_json(result)["allow"] is True

    @pytest.mark.parametrize("wtype,phase,target", HARD_GATE_MATRIX)
    def test_below_ga_the_matrix_does_not_apply(self, tmp_path, wtype, phase, target):
        project = phase_project(tmp_path, wtype=wtype, phase=phase, stage="BETA",
                                satisfied=all_criteria_satisfied(wtype, phase))
        result = run_gate_check("advance", "--to", target, "--project-dir", str(project))
        assert result.returncode == 0, result.stdout
        assert gate_json(result)["allow"] is True


class TestR101WorkTypeTagging:
    @staticmethod
    def write_item(project: Path, item_type: str | None) -> None:
        folder = project / ".sweetclaude" / "product" / "backlog"
        folder.mkdir(parents=True, exist_ok=True)
        frontmatter = {"id": "ISSUE-001", "title": "Migration work", "type": item_type,
                       "status": "active", "created": "2026-10-21"}
        if item_type is None:
            frontmatter.pop("type")
        (folder / "ISSUE-001-migration-work.md").write_text(
            "---\n" + yaml.safe_dump(frontmatter, sort_keys=False) + "---\n\n"
            "# ISSUE-001: Migration work\n",
            encoding="utf-8",
        )

    def sync(self, project: Path):
        import small_story_controller
        small_story_controller._sync_sweetclaude_yaml_active(project, "ISSUE-001", "DEFINE")

    def test_controller_tags_hard_gate_types(self, tmp_path):
        project = tmp_path / "project"
        project.mkdir()
        self.write_item(project, "data-migration")
        self.sync(project)
        assert active_state(project).get("type") == "data-migration"

    def test_controller_does_not_tag_other_known_types(self, tmp_path):
        project = tmp_path / "project"
        project.mkdir()
        self.write_item(project, "bug-fix")
        self.sync(project)
        assert not active_state(project).get("type")

    def test_controller_leaves_type_untouched_when_not_knowable(self, tmp_path):
        project = tmp_path / "project"
        project.mkdir()
        (project / ".sweetclaude" / "state").mkdir(parents=True)
        (project / ".sweetclaude" / "state" / "sweetclaude.yaml").write_text(
            yaml.safe_dump({"work": {"active": {"id": "ISSUE-001", "type": "security-patch"}}}),
            encoding="utf-8")
        self.sync(project)
        assert active_state(project).get("type") == "security-patch"
