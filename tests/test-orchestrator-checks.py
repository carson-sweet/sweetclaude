"""
Tests for scripts/orchestrator_checks.py — exit check registry and built-in checks.

Coverage:
  - CHECKS registry and @register decorator
  - file_exists check
  - file_non_empty check
  - all_artifacts_exist check
  - all_artifacts_non_empty check
"""
import os
import sys
import pytest

# scripts/ has no __init__.py — insert before the import so this works
# regardless of pytest conftest loading order
_SCRIPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts")
)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from orchestrator_checks import CHECKS, register


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_register_decorator_adds_check_to_checks_dict(self):
        # file_exists, file_non_empty, all_artifacts_exist, all_artifacts_non_empty
        # must all be registered at import time
        assert "file_exists" in CHECKS
        assert "file_non_empty" in CHECKS
        assert "all_artifacts_exist" in CHECKS
        assert "all_artifacts_non_empty" in CHECKS

    def test_register_decorator_adds_custom_check_to_checks_dict(self):
        @register("test_custom_check_xyz")
        def my_check(step, state, project_dir):
            return True, ""

        assert "test_custom_check_xyz" in CHECKS
        assert CHECKS["test_custom_check_xyz"] is my_check

    def test_registered_check_is_callable(self):
        for name, fn in CHECKS.items():
            assert callable(fn), f"CHECKS['{name}'] is not callable"

    def test_register_decorator_returns_original_function(self):
        @register("test_returns_fn_xyz")
        def my_check(step, state, project_dir):
            return True, ""

        assert callable(my_check)
        assert my_check({}, {}, ".") == (True, "")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_step(output_artifact=None, input_artifacts=None):
    return {
        "id": "test-step",
        "output_artifact": output_artifact,
        "input_artifacts": input_artifacts,
    }


def _make_state(artifacts=None):
    return {
        "workflow_id": "STORY-TEST",
        "artifacts": artifacts or {},
    }


# ---------------------------------------------------------------------------
# file_exists
# ---------------------------------------------------------------------------

class TestFileExistsCheck:
    def test_file_exists_passes_for_existing_file(self, tmp_path):
        f = tmp_path / "spec.md"
        f.write_text("# spec")
        state = _make_state({"spec_file": str(f)})
        step = _make_step(output_artifact="spec_file")
        passed, msg = CHECKS["file_exists"](step, state, str(tmp_path))
        assert passed is True

    def test_file_exists_fails_for_missing_file(self, tmp_path):
        state = _make_state({"spec_file": str(tmp_path / "missing.md")})
        step = _make_step(output_artifact="spec_file")
        passed, msg = CHECKS["file_exists"](step, state, str(tmp_path))
        assert passed is False

    def test_file_exists_list_valued_all_must_exist(self, tmp_path):
        f1 = tmp_path / "test_a.py"
        f1.write_text("content")
        f2 = tmp_path / "test_b.py"
        # f2 intentionally not created
        state = _make_state({"test_files": [str(f1), str(f2)]})
        step = _make_step(output_artifact="test_files")
        passed, msg = CHECKS["file_exists"](step, state, str(tmp_path))
        assert passed is False

    def test_file_exists_list_valued_all_exist_passes(self, tmp_path):
        f1 = tmp_path / "test_a.py"
        f1.write_text("a")
        f2 = tmp_path / "test_b.py"
        f2.write_text("b")
        state = _make_state({"test_files": [str(f1), str(f2)]})
        step = _make_step(output_artifact="test_files")
        passed, msg = CHECKS["file_exists"](step, state, str(tmp_path))
        assert passed is True

    def test_file_exists_failure_message_is_non_empty_string(self, tmp_path):
        state = _make_state({"spec_file": str(tmp_path / "missing.md")})
        step = _make_step(output_artifact="spec_file")
        passed, msg = CHECKS["file_exists"](step, state, str(tmp_path))
        assert passed is False
        assert isinstance(msg, str)
        assert len(msg) > 0

    def test_file_exists_partial_list_fails(self, tmp_path):
        f1 = tmp_path / "test_a.py"
        f1.write_text("exists")
        f2 = tmp_path / "test_b.py"
        f3 = tmp_path / "test_c.py"
        # f2 and f3 missing
        state = _make_state({"test_files": [str(f1), str(f2), str(f3)]})
        step = _make_step(output_artifact="test_files")
        passed, msg = CHECKS["file_exists"](step, state, str(tmp_path))
        assert passed is False


# ---------------------------------------------------------------------------
# file_non_empty
# ---------------------------------------------------------------------------

class TestFileNonEmptyCheck:
    def test_file_non_empty_passes_for_non_empty_file(self, tmp_path):
        f = tmp_path / "spec.md"
        f.write_text("# some content")
        state = _make_state({"spec_file": str(f)})
        step = _make_step(output_artifact="spec_file")
        passed, msg = CHECKS["file_non_empty"](step, state, str(tmp_path))
        assert passed is True

    def test_file_non_empty_fails_for_empty_file(self, tmp_path):
        f = tmp_path / "empty.md"
        f.write_text("")
        state = _make_state({"spec_file": str(f)})
        step = _make_step(output_artifact="spec_file")
        passed, msg = CHECKS["file_non_empty"](step, state, str(tmp_path))
        assert passed is False

    def test_file_non_empty_list_valued_all_must_be_non_empty(self, tmp_path):
        f1 = tmp_path / "test_a.py"
        f1.write_text("content")
        f2 = tmp_path / "test_b.py"
        f2.write_text("")  # empty
        state = _make_state({"test_files": [str(f1), str(f2)]})
        step = _make_step(output_artifact="test_files")
        passed, msg = CHECKS["file_non_empty"](step, state, str(tmp_path))
        assert passed is False

    def test_file_non_empty_list_valued_all_non_empty_passes(self, tmp_path):
        f1 = tmp_path / "test_a.py"
        f1.write_text("content a")
        f2 = tmp_path / "test_b.py"
        f2.write_text("content b")
        state = _make_state({"test_files": [str(f1), str(f2)]})
        step = _make_step(output_artifact="test_files")
        passed, msg = CHECKS["file_non_empty"](step, state, str(tmp_path))
        assert passed is True

    def test_file_non_empty_failure_message_is_non_empty_string(self, tmp_path):
        f = tmp_path / "empty.md"
        f.write_text("")
        state = _make_state({"spec_file": str(f)})
        step = _make_step(output_artifact="spec_file")
        passed, msg = CHECKS["file_non_empty"](step, state, str(tmp_path))
        assert passed is False
        assert isinstance(msg, str)
        assert len(msg) > 0


# ---------------------------------------------------------------------------
# all_artifacts_exist
# ---------------------------------------------------------------------------

class TestAllArtifactsExistCheck:
    def test_all_artifacts_exist_passes_when_all_input_artifacts_exist(self, tmp_path):
        f1 = tmp_path / "story.md"
        f1.write_text("story")
        f2 = tmp_path / "spec.md"
        f2.write_text("spec")
        state = _make_state({"story_file": str(f1), "spec_file": str(f2)})
        step = _make_step(input_artifacts=["story_file", "spec_file"])
        passed, msg = CHECKS["all_artifacts_exist"](step, state, str(tmp_path))
        assert passed is True

    def test_all_artifacts_exist_fails_when_any_input_artifact_missing(self, tmp_path):
        f1 = tmp_path / "story.md"
        f1.write_text("story")
        state = _make_state({
            "story_file": str(f1),
            "spec_file": str(tmp_path / "missing.md"),
        })
        step = _make_step(input_artifacts=["story_file", "spec_file"])
        passed, msg = CHECKS["all_artifacts_exist"](step, state, str(tmp_path))
        assert passed is False

    def test_all_artifacts_exist_list_valued_all_paths_must_exist(self, tmp_path):
        f1 = tmp_path / "test_a.py"
        f1.write_text("a")
        f2 = tmp_path / "test_b.py"
        # f2 missing
        state = _make_state({"test_files": [str(f1), str(f2)]})
        step = _make_step(input_artifacts=["test_files"])
        passed, msg = CHECKS["all_artifacts_exist"](step, state, str(tmp_path))
        assert passed is False

    def test_all_artifacts_exist_failure_message_is_non_empty_string(self, tmp_path):
        state = _make_state({"story_file": str(tmp_path / "missing.md")})
        step = _make_step(input_artifacts=["story_file"])
        passed, msg = CHECKS["all_artifacts_exist"](step, state, str(tmp_path))
        assert passed is False
        assert isinstance(msg, str)
        assert len(msg) > 0


# ---------------------------------------------------------------------------
# all_artifacts_non_empty
# ---------------------------------------------------------------------------

class TestAllArtifactsNonEmptyCheck:
    def test_all_artifacts_non_empty_passes_when_all_input_artifacts_non_empty(self, tmp_path):
        f1 = tmp_path / "story.md"
        f1.write_text("story content")
        f2 = tmp_path / "spec.md"
        f2.write_text("spec content")
        state = _make_state({"story_file": str(f1), "spec_file": str(f2)})
        step = _make_step(input_artifacts=["story_file", "spec_file"])
        passed, msg = CHECKS["all_artifacts_non_empty"](step, state, str(tmp_path))
        assert passed is True

    def test_all_artifacts_non_empty_fails_when_any_input_artifact_empty(self, tmp_path):
        f1 = tmp_path / "story.md"
        f1.write_text("story content")
        f2 = tmp_path / "spec.md"
        f2.write_text("")  # empty
        state = _make_state({"story_file": str(f1), "spec_file": str(f2)})
        step = _make_step(input_artifacts=["story_file", "spec_file"])
        passed, msg = CHECKS["all_artifacts_non_empty"](step, state, str(tmp_path))
        assert passed is False

    def test_all_artifacts_non_empty_list_valued_all_paths_must_be_non_empty(self, tmp_path):
        f1 = tmp_path / "test_a.py"
        f1.write_text("content")
        f2 = tmp_path / "test_b.py"
        f2.write_text("")  # empty
        state = _make_state({"test_files": [str(f1), str(f2)]})
        step = _make_step(input_artifacts=["test_files"])
        passed, msg = CHECKS["all_artifacts_non_empty"](step, state, str(tmp_path))
        assert passed is False

    def test_all_artifacts_non_empty_failure_message_is_non_empty_string(self, tmp_path):
        f1 = tmp_path / "empty.md"
        f1.write_text("")
        state = _make_state({"story_file": str(f1)})
        step = _make_step(input_artifacts=["story_file"])
        passed, msg = CHECKS["all_artifacts_non_empty"](step, state, str(tmp_path))
        assert passed is False
        assert isinstance(msg, str)
        assert len(msg) > 0
