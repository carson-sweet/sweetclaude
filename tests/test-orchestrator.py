"""
Tests for scripts/orchestrator.py — orchestrator state machine functions.

Coverage:
  - read_state (4.1)
  - write_state (4.2)
  - load_template (4.3)
  - determine_next_step (4.4)
  - resolve_next_step_id (4.5)
  - validate_exit_checks (4.6)
  - assemble_context_envelope (4.7)
  - record_gate_passage (4.8)
  - increment_iteration (4.10)
  - reset_iteration (4.11)
  - find_active_workflows (4.12)
  - extract_output_signal (4.13)
"""
import os
import sys
import yaml
import pytest

# scripts/ has no __init__.py — insert before the import so this works
# regardless of pytest conftest loading order
_SCRIPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts")
)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from orchestrator import (
    read_state,
    write_state,
    load_template,
    determine_next_step,
    resolve_next_step_id,
    validate_exit_checks,
    assemble_context_envelope,
    record_gate_passage,
    increment_iteration,
    reset_iteration,
    find_active_workflows,
    extract_output_signal,
)


# ---------------------------------------------------------------------------
# 4.1  read_state
# ---------------------------------------------------------------------------

class TestReadState:
    def test_read_state_returns_dict_for_valid_yaml(self, workflow_project_dir):
        state = read_state("STORY-025", project_dir=str(workflow_project_dir))
        assert isinstance(state, dict)
        assert state["workflow_id"] == "STORY-025"

    def test_read_state_returns_none_for_missing_file(self, tmp_path):
        result = read_state("STORY-999", project_dir=str(tmp_path))
        assert result is None

    def test_read_state_raises_on_corrupt_yaml(self, tmp_path):
        workflows_dir = tmp_path / ".sweetclaude" / "state" / "workflows"
        workflows_dir.mkdir(parents=True)
        corrupt_file = workflows_dir / "STORY-BAD.yaml"
        corrupt_file.write_text(": this: is: not: valid: yaml: {\n")
        with pytest.raises(yaml.YAMLError):
            read_state("STORY-BAD", project_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# 4.2  write_state
# ---------------------------------------------------------------------------

class TestWriteState:
    def test_write_state_creates_file(self, tmp_path, sample_state):
        write_state("STORY-025", sample_state, project_dir=str(tmp_path))
        expected = tmp_path / ".sweetclaude" / "state" / "workflows" / "STORY-025.yaml"
        assert expected.exists()

    def test_write_state_creates_workflows_directory_if_missing(self, tmp_path, sample_state):
        # No workflows/ dir exists yet
        assert not (tmp_path / ".sweetclaude" / "state" / "workflows").exists()
        write_state("STORY-025", sample_state, project_dir=str(tmp_path))
        assert (tmp_path / ".sweetclaude" / "state" / "workflows").exists()

    def test_write_state_updates_updated_at(self, tmp_path, sample_state):
        original_updated_at = sample_state["updated_at"]
        write_state("STORY-025", sample_state, project_dir=str(tmp_path))
        state_file = tmp_path / ".sweetclaude" / "state" / "workflows" / "STORY-025.yaml"
        written = yaml.safe_load(state_file.read_text())
        assert written["updated_at"] != original_updated_at

    def test_write_state_atomic_write_no_tmp_file_left_behind(self, tmp_path, sample_state):
        write_state("STORY-025", sample_state, project_dir=str(tmp_path))
        workflows_dir = tmp_path / ".sweetclaude" / "state" / "workflows"
        tmp_files = list(workflows_dir.glob("*.tmp"))
        assert tmp_files == [], f"Stale .tmp file(s) left: {tmp_files}"

    def test_write_state_content_is_readable_by_read_state(self, tmp_path, sample_state):
        write_state("STORY-025", sample_state, project_dir=str(tmp_path))
        recovered = read_state("STORY-025", project_dir=str(tmp_path))
        assert recovered["workflow_id"] == "STORY-025"
        assert recovered["workflow_type"] == sample_state["workflow_type"]


# ---------------------------------------------------------------------------
# 4.3  load_template
# ---------------------------------------------------------------------------

class TestLoadTemplate:
    def test_load_template_returns_steps_for_valid_type(self, template_project_dir):
        result = load_template("net-new-feature", project_dir=str(template_project_dir))
        assert isinstance(result, dict)
        assert "steps" in result

    def test_load_template_raises_for_missing_type(self, template_project_dir):
        with pytest.raises(ValueError):
            load_template("does-not-exist", project_dir=str(template_project_dir))

    def test_load_template_raises_for_schema_version_less_than_2(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        old_template = {
            "schema_version": 1,
            "net-new-feature": {
                "shape": "full-pipeline",
                "phases": ["DISCOVER"],
            },
        }
        (config_dir / "workflow-templates.yaml").write_text(yaml.safe_dump(old_template))
        with pytest.raises(ValueError):
            load_template("net-new-feature", project_dir=str(tmp_path))

    def test_load_template_raises_for_type_with_no_steps_list(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        no_steps_template = {
            "schema_version": 2,
            "bug-fix": {
                "shape": "diagnostic",
                "phases": ["DIAGNOSE", "IMPLEMENT"],
                # no 'steps' key
            },
        }
        (config_dir / "workflow-templates.yaml").write_text(yaml.safe_dump(no_steps_template))
        with pytest.raises(ValueError):
            load_template("bug-fix", project_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# 4.4  determine_next_step
# ---------------------------------------------------------------------------

class TestDetermineNextStep:
    def test_determine_next_step_returns_step_dict_for_valid_current_step_id(
        self, sample_state, sample_template
    ):
        sample_state["current_step_id"] = "spec"
        step = determine_next_step(sample_state, sample_template["net-new-feature"])
        assert step is not None
        assert step["id"] == "spec"

    def test_determine_next_step_returns_none_for_complete_sentinel(
        self, sample_state, sample_template
    ):
        sample_state["current_step_id"] = "COMPLETE"
        result = determine_next_step(sample_state, sample_template["net-new-feature"])
        assert result is None

    def test_determine_next_step_returns_none_for_halted_sentinel(
        self, sample_state, sample_template
    ):
        sample_state["current_step_id"] = "HALTED"
        result = determine_next_step(sample_state, sample_template["net-new-feature"])
        assert result is None

    def test_determine_next_step_raises_for_unknown_step_id(
        self, sample_state, sample_template
    ):
        sample_state["current_step_id"] = "nonexistent-step"
        with pytest.raises(ValueError):
            determine_next_step(sample_state, sample_template["net-new-feature"])


# ---------------------------------------------------------------------------
# 4.5  resolve_next_step_id
# ---------------------------------------------------------------------------

class TestResolveNextStepId:
    def test_resolve_next_step_id_sequential_advance(self, sample_template):
        """With no routing, advances to the next step in order."""
        template = sample_template["net-new-feature"]
        activate_step = template["steps"][0]  # activate -> spec
        result = resolve_next_step_id(activate_step, template, output_signal=None)
        assert result == "spec"

    def test_resolve_next_step_id_routing_table_match(self, sample_template):
        """When signal matches a routing key, jumps to the specified step."""
        template = sample_template["net-new-feature"]
        # Inject routing on 'spec' step
        template["steps"][1]["routing"] = {"gaps_found": "activate", "clean": "continue"}
        spec_step = template["steps"][1]
        result = resolve_next_step_id(spec_step, template, output_signal="gaps_found")
        assert result == "activate"

    def test_resolve_next_step_id_continue_signal_falls_through_to_sequential(
        self, sample_template
    ):
        template = sample_template["net-new-feature"]
        template["steps"][1]["routing"] = {"clean": "continue"}
        spec_step = template["steps"][1]
        result = resolve_next_step_id(spec_step, template, output_signal="clean")
        assert result == "implement"

    def test_resolve_next_step_id_hard_stop_report_returns_halted(self, sample_template):
        template = sample_template["net-new-feature"]
        template["steps"][1]["routing"] = {"critical": "hard_stop_report"}
        spec_step = template["steps"][1]
        result = resolve_next_step_id(spec_step, template, output_signal="critical")
        assert result == "HALTED"

    def test_resolve_next_step_id_default_key_used_when_signal_has_no_match(
        self, sample_template
    ):
        template = sample_template["net-new-feature"]
        template["steps"][1]["routing"] = {"clean": "continue", "default": "activate"}
        spec_step = template["steps"][1]
        result = resolve_next_step_id(spec_step, template, output_signal="unknown_signal")
        assert result == "activate"

    def test_resolve_next_step_id_raises_on_unrecognized_signal_with_no_default(
        self, sample_template
    ):
        template = sample_template["net-new-feature"]
        template["steps"][1]["routing"] = {"clean": "continue"}
        spec_step = template["steps"][1]
        with pytest.raises(ValueError):
            resolve_next_step_id(spec_step, template, output_signal="unexpected_signal")

    def test_resolve_next_step_id_next_field_used_for_loop_back_edge(self, sample_template):
        """When step has a 'next' field, it overrides sequential order."""
        template = sample_template["net-new-feature"]
        template["steps"][1]["next"] = "activate"
        spec_step = template["steps"][1]
        result = resolve_next_step_id(spec_step, template, output_signal=None)
        assert result == "activate"

    def test_resolve_next_step_id_last_step_returns_complete(self, sample_template):
        template = sample_template["net-new-feature"]
        last_step = template["steps"][-1]  # implement
        result = resolve_next_step_id(last_step, template, output_signal=None)
        assert result == "COMPLETE"


# ---------------------------------------------------------------------------
# 4.6  validate_exit_checks
# ---------------------------------------------------------------------------

class TestValidateExitChecks:
    def _make_step(self, output_artifact, exit_checks=None, input_artifacts=None):
        return {
            "id": "test-step",
            "output_artifact": output_artifact,
            "exit_checks": exit_checks,
            "input_artifacts": input_artifacts,
        }

    def test_validate_exit_checks_passes_when_file_exists_and_non_empty(
        self, tmp_path, sample_state
    ):
        output_file = tmp_path / "spec.md"
        output_file.write_text("# Spec content")
        sample_state["artifacts"]["spec_file"] = str(output_file)
        step = self._make_step("spec_file", exit_checks=["file_exists", "file_non_empty"])
        passed, failures = validate_exit_checks(step, sample_state, project_dir=str(tmp_path))
        assert passed is True
        assert failures == []

    def test_validate_exit_checks_fails_when_file_missing(self, tmp_path, sample_state):
        sample_state["artifacts"]["spec_file"] = str(tmp_path / "missing.md")
        step = self._make_step("spec_file", exit_checks=["file_exists"])
        passed, failures = validate_exit_checks(step, sample_state, project_dir=str(tmp_path))
        assert passed is False
        assert len(failures) > 0

    def test_validate_exit_checks_fails_when_file_empty(self, tmp_path, sample_state):
        output_file = tmp_path / "empty.md"
        output_file.write_text("")
        sample_state["artifacts"]["spec_file"] = str(output_file)
        step = self._make_step("spec_file", exit_checks=["file_non_empty"])
        passed, failures = validate_exit_checks(step, sample_state, project_dir=str(tmp_path))
        assert passed is False
        assert len(failures) > 0

    def test_validate_exit_checks_list_valued_artifact_all_must_exist(
        self, tmp_path, sample_state
    ):
        f1 = tmp_path / "test_a.py"
        f1.write_text("# test a")
        # f2 intentionally missing
        f2 = tmp_path / "test_b.py"
        sample_state["artifacts"]["test_files"] = [str(f1), str(f2)]
        step = self._make_step("test_files", exit_checks=["file_exists"])
        passed, failures = validate_exit_checks(step, sample_state, project_dir=str(tmp_path))
        assert passed is False
        assert len(failures) > 0

    def test_validate_exit_checks_failure_message_names_artifact(
        self, tmp_path, sample_state
    ):
        sample_state["artifacts"]["spec_file"] = str(tmp_path / "missing.md")
        step = self._make_step("spec_file", exit_checks=["file_exists"])
        passed, failures = validate_exit_checks(step, sample_state, project_dir=str(tmp_path))
        assert passed is False
        # At least one failure message should mention the artifact or path
        combined = " ".join(failures)
        assert "spec_file" in combined or "missing.md" in combined

    def test_validate_exit_checks_defaults_to_file_exists_and_non_empty_when_exit_checks_null(
        self, tmp_path, sample_state
    ):
        output_file = tmp_path / "spec.md"
        output_file.write_text("# content")
        sample_state["artifacts"]["spec_file"] = str(output_file)
        step = self._make_step("spec_file", exit_checks=None)
        passed, failures = validate_exit_checks(step, sample_state, project_dir=str(tmp_path))
        assert passed is True

    def test_validate_exit_checks_no_checks_when_both_exit_checks_and_output_artifact_null(
        self, tmp_path, sample_state
    ):
        step = self._make_step(None, exit_checks=None)
        passed, failures = validate_exit_checks(step, sample_state, project_dir=str(tmp_path))
        assert passed is True
        assert failures == []

    def test_validate_exit_checks_list_valued_artifact_all_must_be_non_empty(
        self, tmp_path, sample_state
    ):
        f1 = tmp_path / "test_a.py"
        f1.write_text("# content")
        f2 = tmp_path / "test_b.py"
        f2.write_text("")  # empty
        sample_state["artifacts"]["test_files"] = [str(f1), str(f2)]
        step = self._make_step("test_files", exit_checks=["file_non_empty"])
        passed, failures = validate_exit_checks(step, sample_state, project_dir=str(tmp_path))
        assert passed is False


# ---------------------------------------------------------------------------
# 4.7  assemble_context_envelope
# ---------------------------------------------------------------------------

class TestAssembleContextEnvelope:
    def _make_step(self, input_artifacts):
        return {
            "id": "test-step",
            "input_artifacts": input_artifacts,
            "output_artifact": None,
        }

    def test_assemble_context_envelope_resolves_artifact_keys_to_absolute_paths(
        self, tmp_path, sample_state
    ):
        spec = tmp_path / "spec.md"
        spec.write_text("# spec")
        sample_state["artifacts"]["spec_file"] = str(spec)
        step = self._make_step(["spec_file"])
        paths = assemble_context_envelope(step, sample_state, project_dir=str(tmp_path))
        assert len(paths) == 1
        assert os.path.isabs(paths[0])
        assert paths[0].endswith("spec.md")

    def test_assemble_context_envelope_flattens_list_valued_artifacts(
        self, tmp_path, sample_state
    ):
        f1 = tmp_path / "test_a.py"
        f2 = tmp_path / "test_b.py"
        f1.write_text("a")
        f2.write_text("b")
        sample_state["artifacts"]["test_files"] = [str(f1), str(f2)]
        step = self._make_step(["test_files"])
        paths = assemble_context_envelope(step, sample_state, project_dir=str(tmp_path))
        assert len(paths) == 2
        assert str(f1) in paths
        assert str(f2) in paths

    def test_assemble_context_envelope_raises_key_error_for_missing_artifact_key(
        self, tmp_path, sample_state
    ):
        step = self._make_step(["nonexistent_artifact"])
        with pytest.raises(KeyError):
            assemble_context_envelope(step, sample_state, project_dir=str(tmp_path))

    def test_assemble_context_envelope_returns_absolute_paths_for_relative_stored_paths(
        self, tmp_path, sample_state
    ):
        spec = tmp_path / "spec.md"
        spec.write_text("# spec")
        # Store a relative path
        sample_state["artifacts"]["spec_file"] = "spec.md"
        step = self._make_step(["spec_file"])
        paths = assemble_context_envelope(step, sample_state, project_dir=str(tmp_path))
        assert os.path.isabs(paths[0])


# ---------------------------------------------------------------------------
# 4.8  record_gate_passage
# ---------------------------------------------------------------------------

class TestRecordGatePassage:
    def test_record_gate_passage_appends_to_gates_passed(self, sample_state):
        updated = record_gate_passage(
            sample_state,
            gate_id="phase1-exit",
            gate_type="user_approval_hard",
            result="approved",
            decision_note=None,
        )
        assert len(updated["gates_passed"]) == 1

    def test_record_gate_passage_includes_all_required_fields(self, sample_state):
        updated = record_gate_passage(
            sample_state,
            gate_id="phase1-exit",
            gate_type="user_approval_hard",
            result="approved",
            decision_note="looks good",
        )
        gate = updated["gates_passed"][0]
        assert gate["gate_id"] == "phase1-exit"
        assert gate["gate_type"] == "user_approval_hard"
        assert gate["result"] == "approved"
        assert "decided_at" in gate
        assert gate["decision_note"] == "looks good"

    def test_record_gate_passage_does_not_write_to_disk(self, tmp_path, sample_state):
        """record_gate_passage returns updated state but does not write to disk."""
        record_gate_passage(
            sample_state,
            gate_id="phase1-exit",
            gate_type="user_approval",
            result="auto_advanced",
        )
        state_file = tmp_path / ".sweetclaude" / "state" / "workflows" / "STORY-025.yaml"
        assert not state_file.exists()


# ---------------------------------------------------------------------------
# 4.10  increment_iteration
# ---------------------------------------------------------------------------

class TestIncrementIteration:
    def test_increment_iteration_creates_counter_on_first_call(self, sample_state):
        updated, at_max = increment_iteration(sample_state, "architect-caucus", max_iterations=3)
        assert updated["iterations"]["architect-caucus"]["count"] == 1
        assert updated["iterations"]["architect-caucus"]["max"] == 3

    def test_increment_iteration_increments_on_subsequent_calls(self, sample_state):
        state, _ = increment_iteration(sample_state, "architect-caucus", max_iterations=3)
        state, _ = increment_iteration(state, "architect-caucus", max_iterations=3)
        assert state["iterations"]["architect-caucus"]["count"] == 2

    def test_increment_iteration_returns_at_max_true_when_count_reaches_max(self, sample_state):
        state, _ = increment_iteration(sample_state, "architect-caucus", max_iterations=3)
        state, _ = increment_iteration(state, "architect-caucus", max_iterations=3)
        state, at_max = increment_iteration(state, "architect-caucus", max_iterations=3)
        assert state["iterations"]["architect-caucus"]["count"] == 3
        assert at_max is True

    def test_increment_iteration_at_max_always_false_when_max_is_none(self, sample_state):
        state, at_max = increment_iteration(sample_state, "user-feedback", max_iterations=None)
        assert at_max is False
        state, at_max = increment_iteration(state, "user-feedback", max_iterations=None)
        assert at_max is False
        state, at_max = increment_iteration(state, "user-feedback", max_iterations=None)
        assert at_max is False


# ---------------------------------------------------------------------------
# 4.11  reset_iteration
# ---------------------------------------------------------------------------

class TestResetIteration:
    def test_reset_iteration_resets_count_to_zero(self, sample_state):
        sample_state["iterations"]["architect-caucus"] = {"count": 3, "max": 3}
        updated = reset_iteration(sample_state, "architect-caucus")
        assert updated["iterations"]["architect-caucus"]["count"] == 0

    def test_reset_iteration_is_no_op_for_unknown_loop_id(self, sample_state):
        updated = reset_iteration(sample_state, "nonexistent-loop")
        # Should not raise and iterations dict should not gain the key
        assert "nonexistent-loop" not in updated["iterations"]


# ---------------------------------------------------------------------------
# 4.12  find_active_workflows
# ---------------------------------------------------------------------------

class TestFindActiveWorkflows:
    def _write_workflow(self, workflows_dir, workflow_id, status, checkpoint="Test checkpoint"):
        state = {
            "workflow_id": workflow_id,
            "status": status,
            "checkpoint": checkpoint,
            "checkpoint_at": "2026-05-20T10:00:00Z",
        }
        (workflows_dir / f"{workflow_id}.yaml").write_text(yaml.safe_dump(state))

    def test_find_active_workflows_finds_active_status(self, tmp_path):
        wf_dir = tmp_path / ".sweetclaude" / "state" / "workflows"
        wf_dir.mkdir(parents=True)
        self._write_workflow(wf_dir, "STORY-001", "active")
        result = find_active_workflows(project_dir=str(tmp_path))
        ids = [w["workflow_id"] for w in result]
        assert "STORY-001" in ids

    def test_find_active_workflows_finds_waiting_for_user_status(self, tmp_path):
        wf_dir = tmp_path / ".sweetclaude" / "state" / "workflows"
        wf_dir.mkdir(parents=True)
        self._write_workflow(wf_dir, "STORY-002", "waiting_for_user")
        result = find_active_workflows(project_dir=str(tmp_path))
        ids = [w["workflow_id"] for w in result]
        assert "STORY-002" in ids

    def test_find_active_workflows_finds_error_status(self, tmp_path):
        wf_dir = tmp_path / ".sweetclaude" / "state" / "workflows"
        wf_dir.mkdir(parents=True)
        self._write_workflow(wf_dir, "STORY-003", "error")
        result = find_active_workflows(project_dir=str(tmp_path))
        ids = [w["workflow_id"] for w in result]
        assert "STORY-003" in ids

    def test_find_active_workflows_excludes_paused(self, tmp_path):
        wf_dir = tmp_path / ".sweetclaude" / "state" / "workflows"
        wf_dir.mkdir(parents=True)
        self._write_workflow(wf_dir, "STORY-004", "paused")
        result = find_active_workflows(project_dir=str(tmp_path))
        ids = [w["workflow_id"] for w in result]
        assert "STORY-004" not in ids

    def test_find_active_workflows_excludes_complete(self, tmp_path):
        wf_dir = tmp_path / ".sweetclaude" / "state" / "workflows"
        wf_dir.mkdir(parents=True)
        self._write_workflow(wf_dir, "STORY-005", "complete")
        result = find_active_workflows(project_dir=str(tmp_path))
        ids = [w["workflow_id"] for w in result]
        assert "STORY-005" not in ids

    def test_find_active_workflows_excludes_aborted(self, tmp_path):
        wf_dir = tmp_path / ".sweetclaude" / "state" / "workflows"
        wf_dir.mkdir(parents=True)
        self._write_workflow(wf_dir, "STORY-006", "aborted")
        result = find_active_workflows(project_dir=str(tmp_path))
        ids = [w["workflow_id"] for w in result]
        assert "STORY-006" not in ids

    def test_find_active_workflows_excludes_halted(self, tmp_path):
        wf_dir = tmp_path / ".sweetclaude" / "state" / "workflows"
        wf_dir.mkdir(parents=True)
        self._write_workflow(wf_dir, "STORY-007", "halted")
        result = find_active_workflows(project_dir=str(tmp_path))
        ids = [w["workflow_id"] for w in result]
        assert "STORY-007" not in ids

    def test_find_active_workflows_returns_empty_list_for_empty_directory(self, tmp_path):
        wf_dir = tmp_path / ".sweetclaude" / "state" / "workflows"
        wf_dir.mkdir(parents=True)
        result = find_active_workflows(project_dir=str(tmp_path))
        assert result == []

    def test_find_active_workflows_returns_empty_list_when_directory_missing(self, tmp_path):
        result = find_active_workflows(project_dir=str(tmp_path))
        assert result == []

    def test_find_active_workflows_result_dict_has_required_fields(self, tmp_path):
        wf_dir = tmp_path / ".sweetclaude" / "state" / "workflows"
        wf_dir.mkdir(parents=True)
        self._write_workflow(wf_dir, "STORY-010", "active", checkpoint="Step done.")
        result = find_active_workflows(project_dir=str(tmp_path))
        assert len(result) == 1
        wf = result[0]
        assert "workflow_id" in wf
        assert "status" in wf
        assert "checkpoint" in wf
        assert "checkpoint_at" in wf


# ---------------------------------------------------------------------------
# 4.13  extract_output_signal
# ---------------------------------------------------------------------------

class TestExtractOutputSignal:
    def _make_step(self, output_artifact="output"):
        return {"id": "test-step", "output_artifact": output_artifact}

    def test_extract_output_signal_reads_signal_from_yaml_frontmatter(self, tmp_path):
        output_file = tmp_path / "output.md"
        output_file.write_text("---\nsignal: clean\n---\n\nBody content here.\n")
        step = self._make_step()
        result = extract_output_signal(step, str(output_file))
        assert result == "clean"

    def test_extract_output_signal_returns_none_when_no_frontmatter(self, tmp_path):
        output_file = tmp_path / "output.md"
        output_file.write_text("# Just a heading\n\nNo frontmatter here.\n")
        step = self._make_step()
        result = extract_output_signal(step, str(output_file))
        assert result is None

    def test_extract_output_signal_returns_none_when_frontmatter_has_no_signal_field(
        self, tmp_path
    ):
        output_file = tmp_path / "output.md"
        output_file.write_text("---\nauthor: test-writer\nversion: 1\n---\n\nBody.\n")
        step = self._make_step()
        result = extract_output_signal(step, str(output_file))
        assert result is None

    def test_extract_output_signal_ignores_signal_in_body_text(self, tmp_path):
        output_file = tmp_path / "output.md"
        output_file.write_text(
            "---\nauthor: test-writer\n---\n\nsignal: critical_concerns\n\nBody text.\n"
        )
        step = self._make_step()
        result = extract_output_signal(step, str(output_file))
        assert result is None

    def test_extract_output_signal_ignores_signal_in_comment_not_frontmatter(self, tmp_path):
        output_file = tmp_path / "output.md"
        output_file.write_text("<!-- signal: critical_concerns -->\n\n# Title\n")
        step = self._make_step()
        result = extract_output_signal(step, str(output_file))
        assert result is None


# ---------------------------------------------------------------------------
# Security: path traversal prevention
# ---------------------------------------------------------------------------

class TestPathTraversalPrevention:
    def test_read_state_rejects_traversal_workflow_id(self, tmp_path):
        with pytest.raises(ValueError, match="Invalid workflow_id"):
            read_state("../../etc/passwd", project_dir=str(tmp_path))

    def test_write_state_rejects_traversal_workflow_id(self, tmp_path, sample_state):
        with pytest.raises(ValueError, match="Invalid workflow_id"):
            write_state("../../../tmp/evil", sample_state, project_dir=str(tmp_path))

    def test_read_state_rejects_slash_in_workflow_id(self, tmp_path):
        with pytest.raises(ValueError, match="Invalid workflow_id"):
            read_state("STORY/025", project_dir=str(tmp_path))

    def test_read_state_allows_valid_workflow_ids(self, tmp_path):
        result = read_state("STORY-025", project_dir=str(tmp_path))
        assert result is None

    def test_read_state_allows_underscores_in_workflow_id(self, tmp_path):
        result = read_state("STORY_025", project_dir=str(tmp_path))
        assert result is None


# ---------------------------------------------------------------------------
# Security: write_state does not mutate caller's dict
# ---------------------------------------------------------------------------

class TestWriteStateNoMutation:
    def test_write_state_does_not_mutate_callers_dict(self, tmp_path, sample_state):
        original_updated_at = sample_state["updated_at"]
        write_state("STORY-025", sample_state, project_dir=str(tmp_path))
        assert sample_state["updated_at"] == original_updated_at


# ---------------------------------------------------------------------------
# Edge case: unregistered check name
# ---------------------------------------------------------------------------

class TestUnregisteredCheckName:
    def test_validate_exit_checks_graceful_failure_on_unknown_check(self, tmp_path, sample_state):
        step = {
            "exit_checks": ["nonexistent_check"],
            "output_artifact": None,
        }
        passed, failures = validate_exit_checks(step, sample_state, project_dir=str(tmp_path))
        assert not passed
        assert any("nonexistent_check" in f for f in failures)


# ---------------------------------------------------------------------------
# Edge case: continue routing + next field
# ---------------------------------------------------------------------------

class TestContinueRoutingWithNextField:
    def test_continue_signal_skips_next_field_uses_sequential(self):
        step_with_routing_and_next = {
            "id": "review",
            "routing": {"clean": "continue", "issues": "fix"},
            "next": "earlier-step",
        }
        template = {
            "steps": [
                {"id": "review"},
                {"id": "ship"},
            ]
        }
        result = resolve_next_step_id(step_with_routing_and_next, template, output_signal="clean")
        assert result == "ship"

    def test_no_signal_with_next_field_uses_next(self):
        step_with_next = {
            "id": "review",
            "routing": {"clean": "continue", "issues": "fix"},
            "next": "earlier-step",
        }
        template = {
            "steps": [
                {"id": "review"},
                {"id": "ship"},
            ]
        }
        result = resolve_next_step_id(step_with_next, template, output_signal=None)
        assert result == "earlier-step"


# ---------------------------------------------------------------------------
# Edge case: missing state keys
# ---------------------------------------------------------------------------

class TestMissingStateKeys:
    def test_determine_next_step_raises_on_missing_current_step_id(self, sample_template):
        state = {"workflow_type": "net-new-feature"}
        template = sample_template["net-new-feature"]
        with pytest.raises(ValueError, match="current_step_id"):
            determine_next_step(state, template)

    def test_record_gate_passage_works_without_gates_passed_key(self):
        state = {}
        updated = record_gate_passage(state, "gate-1", "user_approval", "approved")
        assert len(updated["gates_passed"]) == 1


# ---------------------------------------------------------------------------
# Hotfix: artifact path containment (caucus finding C1)
# ---------------------------------------------------------------------------

class TestArtifactPathContainment:
    def test_assemble_context_envelope_rejects_traversal_path(self, tmp_path):
        step = {"input_artifacts": ["spec_file"]}
        state = {"artifacts": {"spec_file": "../../etc/passwd"}}
        with pytest.raises(ValueError, match="escapes project directory"):
            assemble_context_envelope(step, state, project_dir=str(tmp_path))

    def test_assemble_context_envelope_rejects_absolute_path_outside_project(self, tmp_path):
        step = {"input_artifacts": ["spec_file"]}
        state = {"artifacts": {"spec_file": "/etc/passwd"}}
        with pytest.raises(ValueError, match="escapes project directory"):
            assemble_context_envelope(step, state, project_dir=str(tmp_path))

    def test_assemble_context_envelope_accepts_path_within_project(self, tmp_path):
        artifact = tmp_path / "docs" / "spec.md"
        artifact.parent.mkdir(parents=True)
        artifact.write_text("spec content")
        step = {"input_artifacts": ["spec_file"]}
        state = {"artifacts": {"spec_file": "docs/spec.md"}}
        result = assemble_context_envelope(step, state, project_dir=str(tmp_path))
        assert result == [str(artifact)]

    def test_assemble_context_envelope_accepts_absolute_path_within_project(self, tmp_path):
        artifact = tmp_path / "docs" / "spec.md"
        artifact.parent.mkdir(parents=True)
        artifact.write_text("spec content")
        step = {"input_artifacts": ["spec_file"]}
        state = {"artifacts": {"spec_file": str(artifact)}}
        result = assemble_context_envelope(step, state, project_dir=str(tmp_path))
        assert result == [str(artifact)]


# ---------------------------------------------------------------------------
# Hotfix: frontmatter closing delimiter at EOF (caucus finding N4)
# ---------------------------------------------------------------------------

class TestExtractOutputSignalEOF:
    def test_signal_extracted_when_closing_delimiter_at_eof_no_trailing_newline(self, tmp_path):
        output_file = tmp_path / "output.md"
        output_file.write_text("---\nsignal: critical\n---")
        step = {"id": "review"}
        result = extract_output_signal(step, str(output_file))
        assert result == "critical"

    def test_signal_extracted_when_closing_delimiter_at_eof_with_trailing_newline(self, tmp_path):
        output_file = tmp_path / "output.md"
        output_file.write_text("---\nsignal: clean\n---\n")
        step = {"id": "review"}
        result = extract_output_signal(step, str(output_file))
        assert result == "clean"

    def test_signal_extracted_with_body_after_frontmatter(self, tmp_path):
        output_file = tmp_path / "output.md"
        output_file.write_text("---\nsignal: pass\n---\n\nBody content here.\n")
        step = {"id": "review"}
        result = extract_output_signal(step, str(output_file))
        assert result == "pass"


# ---------------------------------------------------------------------------
# Hotfix: find_active_workflows filename/id mismatch (caucus finding W8)
# ---------------------------------------------------------------------------

class TestFindActiveWorkflowsFilenameMismatch:
    def test_skips_file_where_workflow_id_does_not_match_filename(self, tmp_path):
        wf_dir = tmp_path / ".sweetclaude" / "state" / "workflows"
        wf_dir.mkdir(parents=True)
        mismatched = wf_dir / "STORY-025.yaml"
        mismatched.write_text(yaml.safe_dump({
            "workflow_id": "STORY-999",
            "status": "active",
            "checkpoint": "test",
            "checkpoint_at": "2026-05-20T10:00:00Z",
        }))
        result = find_active_workflows(project_dir=str(tmp_path))
        assert len(result) == 0

    def test_includes_file_where_workflow_id_matches_filename(self, tmp_path):
        wf_dir = tmp_path / ".sweetclaude" / "state" / "workflows"
        wf_dir.mkdir(parents=True)
        matched = wf_dir / "STORY-025.yaml"
        matched.write_text(yaml.safe_dump({
            "workflow_id": "STORY-025",
            "status": "active",
            "checkpoint": "test",
            "checkpoint_at": "2026-05-20T10:00:00Z",
        }))
        result = find_active_workflows(project_dir=str(tmp_path))
        assert len(result) == 1
        assert result[0]["workflow_id"] == "STORY-025"
