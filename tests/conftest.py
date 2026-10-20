"""
Shared fixtures for orchestrator tests.
"""
import os
import sys
import yaml
import pytest

# Make scripts/ importable — scripts/ has no __init__.py
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPTS_DIR))


@pytest.fixture
def sample_state():
    """Minimal valid workflow state dict."""
    return {
        "schema_version": 1,
        "workflow_id": "ISSUE-025",
        "workflow_type": "net-new-feature",
        "workflow_shape": "full-pipeline",
        "template_version": "1",
        "status": "active",
        "started_at": "2026-05-20T10:00:00Z",
        "updated_at": "2026-05-20T10:00:00Z",
        "current_step_id": "activate",
        "completed_steps": [],
        "artifacts": {},
        "gates_passed": [],
        "iterations": {},
        "checkpoint": "Workflow started.",
        "checkpoint_at": "2026-05-20T10:00:00Z",
        "error": None,
        "sessions": [
            {
                "started_at": "2026-05-20T10:00:00Z",
                "ended_at": None,
                "steps_completed": [],
            }
        ],
    }


@pytest.fixture
def sample_template():
    """Minimal valid workflow template dict with schema_version >= 2."""
    return {
        "schema_version": 2,
        "net-new-feature": {
            "shape": "full-pipeline",
            "phases": ["DISCOVER", "DEFINE", "IMPLEMENT"],
            "steps": [
                {
                    "id": "activate",
                    "phase": "ACTIVATION",
                    "agent": "housekeeping",
                    "model": "sonnet",
                    "subagent_type": "code",
                    "input_artifacts": None,
                    "output_artifact": None,
                    "gate": None,
                    "routing": None,
                    "max_iterations": None,
                    "next": None,
                    "exit_checks": None,
                    "escalation": None,
                    "action": None,
                },
                {
                    "id": "spec",
                    "phase": "DEFINE",
                    "agent": "spec-writer",
                    "model": "opus",
                    "subagent_type": "research",
                    "input_artifacts": ["story_file"],
                    "output_artifact": "spec_file",
                    "gate": "user_approval",
                    "routing": None,
                    "max_iterations": None,
                    "next": None,
                    "exit_checks": ["file_exists", "file_non_empty"],
                    "escalation": None,
                    "action": None,
                },
                {
                    "id": "implement",
                    "phase": "IMPLEMENT",
                    "agent": "implementer",
                    "model": "sonnet",
                    "subagent_type": "code",
                    "input_artifacts": ["spec_file"],
                    "output_artifact": "source_files",
                    "gate": None,
                    "routing": None,
                    "max_iterations": None,
                    "next": None,
                    "exit_checks": ["file_exists", "file_non_empty"],
                    "escalation": None,
                    "action": None,
                },
            ],
        },
    }


@pytest.fixture
def workflow_project_dir(tmp_path, sample_state):
    """
    Project directory with a real workflows/ state directory and
    a pre-written ISSUE-025.yaml state file.
    """
    workflows_dir = tmp_path / ".sweetclaude" / "state" / "workflows"
    workflows_dir.mkdir(parents=True)
    state_file = workflows_dir / "ISSUE-025.yaml"
    state_file.write_text(yaml.safe_dump(sample_state))
    return tmp_path


@pytest.fixture
def template_project_dir(tmp_path, sample_template):
    """Project directory with a valid config/workflow-templates.yaml."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    template_file = config_dir / "workflow-templates.yaml"
    template_file.write_text(yaml.safe_dump(sample_template))
    return tmp_path
