import os
import re
import yaml
from datetime import datetime, timezone

_WORKFLOW_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def _validate_workflow_id(workflow_id):
    if not _WORKFLOW_ID_PATTERN.match(workflow_id):
        raise ValueError(
            "Invalid workflow_id '{}' — must match [A-Za-z0-9_-]+".format(workflow_id)
        )


def _workflows_dir(project_dir):
    return os.path.join(project_dir, ".sweetclaude", "state", "workflows")


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_project_dir(project_dir):
    return os.path.abspath(project_dir)


def _check_containment(resolved_path, project_dir):
    project_root = os.path.abspath(project_dir)
    resolved = os.path.abspath(resolved_path)
    if not resolved.startswith(project_root + os.sep) and resolved != project_root:
        raise ValueError(
            "Path '{}' escapes project directory".format(resolved_path)
        )
    return resolved


def read_state(workflow_id, project_dir="."):
    _validate_workflow_id(workflow_id)
    project_dir = _resolve_project_dir(project_dir)
    path = os.path.join(_workflows_dir(project_dir), "{}.yaml".format(workflow_id))
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return None


def write_state(workflow_id, state, project_dir="."):
    _validate_workflow_id(workflow_id)
    project_dir = _resolve_project_dir(project_dir)
    wf_dir = _workflows_dir(project_dir)
    os.makedirs(wf_dir, exist_ok=True)
    state_copy = dict(state)
    state_copy["updated_at"] = _now_iso()
    target = os.path.join(wf_dir, "{}.yaml".format(workflow_id))
    tmp = target + ".tmp"
    with open(tmp, "w") as f:
        yaml.safe_dump(state_copy, f, default_flow_style=False, allow_unicode=True)
    os.replace(tmp, target)


def load_template(workflow_type, project_dir="."):
    project_dir = _resolve_project_dir(project_dir)
    path = os.path.join(project_dir, "config", "workflow-templates.yaml")
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    schema_version = data.get("schema_version", 1)
    if schema_version < 2:
        raise ValueError(
            "workflow-templates.yaml schema_version must be >= 2, got {}".format(schema_version)
        )
    if workflow_type not in data:
        raise ValueError("Workflow type '{}' not found in template".format(workflow_type))
    template_entry = data[workflow_type]
    if not isinstance(template_entry, dict) or "steps" not in template_entry:
        raise ValueError(
            "Workflow type '{}' has no 'steps' list in template".format(workflow_type)
        )
    return data[workflow_type]


def determine_next_step(state, template):
    if "current_step_id" not in state:
        raise ValueError("State is missing 'current_step_id'")
    current_step_id = state["current_step_id"]
    if current_step_id in ("COMPLETE", "HALTED"):
        return None
    steps = template["steps"]
    for step in steps:
        if step["id"] == current_step_id:
            return step
    raise ValueError(
        "current_step_id '{}' not found in template steps".format(current_step_id)
    )


def resolve_next_step_id(current_step, template, output_signal=None):
    steps = template["steps"]
    routing = current_step.get("routing")
    routed_to_continue = False

    if routing and output_signal is not None:
        if output_signal in routing:
            value = routing[output_signal]
            if value == "continue":
                routed_to_continue = True
            elif value == "hard_stop_report":
                return "HALTED"
            else:
                return value
        elif "default" in routing:
            value = routing["default"]
            if value == "continue":
                routed_to_continue = True
            elif value == "hard_stop_report":
                return "HALTED"
            else:
                return value
        else:
            raise ValueError(
                "Unrecognized output signal '{}' with no default routing key".format(output_signal)
            )

    # "continue" from routing means truly sequential — skip the next field
    if not routed_to_continue:
        next_field = current_step.get("next")
        if next_field:
            return next_field

    current_id = current_step["id"]
    for i, step in enumerate(steps):
        if step["id"] == current_id:
            if i + 1 < len(steps):
                return steps[i + 1]["id"]
            else:
                return "COMPLETE"

    raise ValueError("Step '{}' not found in template steps".format(current_id))


def validate_exit_checks(step, state, project_dir="."):
    import orchestrator_checks as _checks_module

    project_dir = _resolve_project_dir(project_dir)
    exit_checks = step.get("exit_checks")
    output_artifact = step.get("output_artifact")

    if exit_checks is None:
        if output_artifact is None:
            return True, []
        exit_checks = ["file_exists", "file_non_empty"]

    failures = []
    for check_name in exit_checks:
        check_fn = _checks_module.CHECKS.get(check_name)
        if check_fn is None:
            failures.append("Unknown exit check: '{}'".format(check_name))
            continue
        passed, msg = check_fn(step, state, project_dir)
        if not passed:
            failures.append(msg)

    return (len(failures) == 0), failures


def _resolve_artifact_path(raw_path, project_dir):
    if os.path.isabs(raw_path):
        return raw_path
    return os.path.join(project_dir, raw_path)


def assemble_context_envelope(step, state, project_dir="."):
    project_dir = _resolve_project_dir(project_dir)
    artifacts = state.get("artifacts", {})
    input_artifacts = step.get("input_artifacts") or []
    result = []
    for key in input_artifacts:
        if key not in artifacts:
            raise KeyError(key)
        value = artifacts[key]
        if isinstance(value, list):
            for p in value:
                result.append(_resolve_artifact_path(p, project_dir))
        else:
            result.append(_resolve_artifact_path(value, project_dir))
    return result


def record_gate_passage(state, gate_id, gate_type, result, decision_note=None):
    gate_record = {
        "gate_id": gate_id,
        "gate_type": gate_type,
        "result": result,
        "decided_at": _now_iso(),
        "decision_note": decision_note,
    }
    state.setdefault("gates_passed", []).append(gate_record)
    return state


def increment_iteration(state, loop_id, max_iterations):
    iterations = state.setdefault("iterations", {})
    if loop_id not in iterations:
        iterations[loop_id] = {"count": 1, "max": max_iterations}
    else:
        iterations[loop_id]["count"] += 1
        iterations[loop_id]["max"] = max_iterations

    count = iterations[loop_id]["count"]
    max_val = iterations[loop_id]["max"]

    at_max = False
    if max_val is not None and count >= max_val:
        at_max = True

    return state, at_max


def reset_iteration(state, loop_id):
    iterations = state.get("iterations", {})
    if loop_id in iterations:
        iterations[loop_id]["count"] = 0
    return state


def find_active_workflows(project_dir="."):
    project_dir = _resolve_project_dir(project_dir)
    wf_dir = _workflows_dir(project_dir)
    if not os.path.exists(wf_dir):
        return []

    active_statuses = {"active", "waiting_for_user", "error"}
    result = []
    for fname in os.listdir(wf_dir):
        if not fname.endswith(".yaml"):
            continue
        path = os.path.join(wf_dir, fname)
        try:
            with open(path, "r") as f:
                state = yaml.safe_load(f)
        except Exception:
            continue
        if not isinstance(state, dict):
            continue
        if state.get("status") in active_statuses:
            result.append({
                "workflow_id": state.get("workflow_id"),
                "status": state.get("status"),
                "checkpoint": state.get("checkpoint"),
                "checkpoint_at": state.get("checkpoint_at"),
            })
    return result


def extract_output_signal(step, agent_output_path):
    try:
        with open(agent_output_path, "r") as f:
            content = f.read()
    except (OSError, IOError):
        return None

    if not content.startswith("---\n") and not content.startswith("---\r\n"):
        return None

    end = content.find("\n---\n", 3)
    if end == -1:
        end = content.find("\n---\r\n", 3)
    if end == -1:
        return None

    frontmatter_text = content[content.index("\n") + 1:end].strip()
    try:
        fm = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError:
        return None

    if not isinstance(fm, dict):
        return None

    return fm.get("signal", None)
