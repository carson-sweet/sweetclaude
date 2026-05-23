import glob
import os
import re
import subprocess
import sys
import yaml
from datetime import datetime, timezone

import orchestrator_actions
from orchestrator import (
    assemble_context_envelope,
    record_gate_passage,
    increment_iteration,
    validate_exit_checks,
    extract_output_signal,
    _check_containment,
    _validate_workflow_id,
)

_STEP_ID_SAFE = re.compile(r"^[A-Za-z0-9_.-]+$")

VALID_ACTIONS = {"approve", "iterate", "retry", "skip", "abort", "reset", "accept", "acknowledge"}


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_defaults(project_dir):
    path = os.path.join(project_dir, "config", "orchestrator-defaults.yaml")
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def _canonical_state_path(workflow_id, project_dir):
    return os.path.join(project_dir, ".sweetclaude", "state", "workflows", "{}.yaml".format(workflow_id))


def _output_dir_state_path(workflow_id, output_dir, project_dir):
    return os.path.join(project_dir, output_dir, "{}.yaml".format(workflow_id))


def _state_file_path(workflow_id, project_dir, output_dir=None):
    if output_dir is not None:
        p = _output_dir_state_path(workflow_id, output_dir, project_dir)
        if os.path.exists(p):
            return p
    return _canonical_state_path(workflow_id, project_dir)


def _get_output_dir(project_dir):
    defaults = _load_defaults(project_dir)
    return defaults.get("paths", {}).get("output_dir", ".sweetclaude/workflows")


def _load_state(workflow_id, project_dir, output_dir=None):
    if output_dir is None:
        output_dir = _get_output_dir(project_dir)
    path = _state_file_path(workflow_id, project_dir, output_dir)
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise ValueError("Workflow state file not found for '{}'".format(workflow_id))


def _save_state(workflow_id, state, project_dir, output_dir=None):
    if output_dir is None:
        output_dir = _get_output_dir(project_dir)
    state["updated_at"] = _now_iso()

    canonical = _canonical_state_path(workflow_id, project_dir)
    os.makedirs(os.path.dirname(canonical), exist_ok=True)
    tmp = canonical + ".tmp"
    with open(tmp, "w") as f:
        yaml.safe_dump(state, f, default_flow_style=False, allow_unicode=True)
    os.replace(tmp, canonical)

    output_path = _output_dir_state_path(workflow_id, output_dir, project_dir)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    tmp2 = output_path + ".tmp"
    with open(tmp2, "w") as f:
        yaml.safe_dump(state, f, default_flow_style=False, allow_unicode=True)
    os.replace(tmp2, output_path)


def _load_sc_yaml(project_dir):
    path = os.path.join(project_dir, ".sweetclaude", "state", "sweetclaude.yaml")
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def _save_sc_yaml(data, project_dir):
    path = os.path.join(project_dir, ".sweetclaude", "state", "sweetclaude.yaml")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
    os.replace(tmp, path)


def _load_template(project_dir):
    path = os.path.join(project_dir, "config", "workflow-templates.yaml")
    with open(path) as f:
        data = yaml.safe_load(f)
    return data


def _get_steps(template_data, workflow_type):
    entry = template_data.get(workflow_type, {})
    return entry.get("steps", [])


def _validate_steps(steps, allowlist):
    for step in steps:
        sid = step.get("id", "")
        if not _STEP_ID_SAFE.match(sid):
            raise ValueError("Invalid step id '{}' — contains unsafe characters".format(sid))
        subagent_type = step.get("subagent_type")
        if subagent_type is not None:
            if subagent_type not in allowlist:
                raise ValueError("subagent_type '{}' is not in the allowlist".format(subagent_type))


def _step_index(step_id, steps):
    for i, s in enumerate(steps):
        if s["id"] == step_id:
            return i
    return -1


def _find_step(step_id, steps):
    for s in steps:
        if s["id"] == step_id:
            return s
    return None


def _find_prior_step(step_id, steps):
    idx = _step_index(step_id, steps)
    if idx <= 0:
        return None
    return steps[idx - 1]


def _sequential_next(step, steps):
    idx = _step_index(step["id"], steps)
    if idx < 0:
        raise ValueError("Step '{}' not found".format(step["id"]))
    if idx + 1 < len(steps):
        return steps[idx + 1]["id"]
    return "COMPLETE"


def _resolve_next_step_id(step, steps, signal=None):
    routing = step.get("routing")
    if routing and signal is not None:
        if signal in routing:
            val = routing[signal]
            if val == "continue":
                return _sequential_next(step, steps)
            if val == "hard_stop_report":
                return "HALTED"
            return val
        elif "default" in routing:
            val = routing["default"]
            if val == "continue":
                return _sequential_next(step, steps)
            if val == "hard_stop_report":
                return "HALTED"
            return val
        else:
            raise ValueError("Unrecognized signal '{}' with no default".format(signal))
    next_field = step.get("next")
    if next_field:
        return next_field
    return _sequential_next(step, steps)


def _set_orchestrated(project_dir, workflow_id, state_file_path):
    sc = _load_sc_yaml(project_dir)
    work = sc.setdefault("work", {})
    active = work.setdefault("active", {})
    active["orchestrated"] = True
    active["workflow_state_file"] = state_file_path
    _save_sc_yaml(sc, project_dir)


def _update_sc_phase(project_dir, workflow_id, phase):
    sc = _load_sc_yaml(project_dir)
    work = sc.setdefault("work", {})
    active = work.setdefault("active", {})
    active["phase"] = phase
    _save_sc_yaml(sc, project_dir)


def _find_item_file(project_dir, item_id):
    product_dir = os.path.join(project_dir, ".sweetclaude", "product")
    for pattern in ["{}-*".format(item_id), "{}.*".format(item_id)]:
        for match in glob.glob(os.path.join(product_dir, "**", pattern), recursive=True):
            if match.endswith(".md") and "/done/" not in match and "/archived/" not in match:
                return match
    return None


def _update_item_status(project_dir, item_id, result):
    filepath = _find_item_file(project_dir, item_id)
    if not filepath:
        return
    status_py = os.path.join(project_dir, "scripts", "status.py")
    if not os.path.isfile(status_py):
        print("WARNING: scripts/status.py not found, skipping status update", file=sys.stderr)
        return
    if result == "complete":
        cmd = ["python3", status_py, "set-terminal",
               "--file", filepath, "--status", "done",
               "--actor", "orchestrator", "--project-dir", project_dir]
    elif result == "halted":
        cmd = ["python3", status_py, "set",
               "--file", filepath, "--status", "on-hold",
               "--actor", "orchestrator", "--project-dir", project_dir]
    else:
        return
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        print("WARNING: status update failed for {}: {}".format(
            item_id, r.stdout.strip() or r.stderr.strip()), file=sys.stderr)


def _complete_sc(project_dir, workflow_id, result):
    sc = _load_sc_yaml(project_dir)
    work = sc.setdefault("work", {})
    active = work.get("active", {})
    if active and active.get("id") and active["id"] != workflow_id:
        return
    item_id = active.get("id") if active else None
    if item_id:
        _update_item_status(project_dir, item_id, result)
    history = sc.setdefault("work_history", [])
    already = any(h.get("id") == workflow_id and h.get("result") == result for h in history)
    if not already:
        history.append({"id": workflow_id, "result": result, "at": _now_iso()})
    work["active"] = None
    _save_sc_yaml(sc, project_dir)


def _invoke_agent(*args, **kwargs):
    pass


def _extract_signal_from_path(output_path):
    if not output_path or not os.path.exists(output_path):
        return None
    return extract_output_signal(None, agent_output_path=output_path)


def _gate_already_passed(state, step_id, gate_type):
    """Return True only for dict entries added by record_gate_passage. Ignore string entries."""
    gates = state.get("gates_passed", [])
    key = "{}:{}".format(step_id, gate_type)
    for g in gates:
        if isinstance(g, dict):
            if g.get("gate_id") == key and g.get("gate_type") == gate_type:
                return True
    return False


def _check_orchestrated_conflict(sc, workflow_id):
    active = sc.get("work", {}).get("active", {})
    if active and active.get("orchestrated") and active.get("id") != workflow_id:
        raise ValueError(
            "Another workflow '{}' is already orchestrated".format(active.get("id"))
        )


def _make_output_path(workflow_id, step_id, output_artifact, output_dir, project_dir):
    if not output_artifact:
        return None
    return os.path.join(project_dir, output_dir, workflow_id, "{}.md".format(output_artifact))


def _write_checkpoint(state, message):
    state["checkpoint"] = message
    state["checkpoint_at"] = _now_iso()


def _add_session(state):
    sessions = state.setdefault("sessions", [])
    sessions.append({
        "started_at": _now_iso(),
        "ended_at": None,
        "steps_completed": [],
    })


def run_loop(workflow_id, project_dir=".", deference_level="collaborative"):
    _validate_workflow_id(workflow_id)
    project_dir = os.path.abspath(project_dir)
    defaults = _load_defaults(project_dir)
    output_dir = defaults.get("paths", {}).get("output_dir", ".sweetclaude/workflows")
    _check_containment(os.path.join(project_dir, output_dir), project_dir)
    default_max = defaults.get("iteration_limits", {}).get("default_max", 3)
    subagent_allowlist = set(defaults.get("subagent_types", {}).get("allowlist", ["code", "research", "housekeeping"]))

    sc = _load_sc_yaml(project_dir)
    _check_orchestrated_conflict(sc, workflow_id)

    template_data = _load_template(project_dir)
    state = _load_state(workflow_id, project_dir, output_dir)
    workflow_type = state.get("workflow_type", "net-new-feature")
    steps = _get_steps(template_data, workflow_type)

    _validate_steps(steps, subagent_allowlist)

    state_file_path = _state_file_path(workflow_id, project_dir, output_dir)
    _set_orchestrated(project_dir, workflow_id, state_file_path)

    while True:
        state = _load_state(workflow_id, project_dir, output_dir)
        current_step_id = state.get("current_step_id")

        if current_step_id == "COMPLETE":
            _complete_sc(project_dir, workflow_id, "complete")
            return {"reason": "complete", "step_id": "COMPLETE", "payload": {}}

        if current_step_id == "HALTED":
            _complete_sc(project_dir, workflow_id, "halted")
            return {"reason": "halted", "step_id": "HALTED", "payload": {}}

        step = _find_step(current_step_id, steps)
        if step is None:
            raise ValueError("Step '{}' not found in template".format(current_step_id))

        gate = step.get("gate")
        if gate:
            already_passed = _gate_already_passed(state, step["id"], gate)
            if not already_passed:
                is_hard = gate == "user_approval_hard"
                if is_hard or deference_level == "collaborative":
                    state["status"] = "waiting_for_user"
                    _save_state(workflow_id, state, project_dir, output_dir)
                    return {
                        "reason": "gate",
                        "step_id": step["id"],
                        "payload": {
                            "gate_type": gate,
                            "options": ["approve", "iterate"],
                            "actions": ["approve", "iterate"],
                        }
                    }

        output_artifact = step.get("output_artifact")
        output_path = None
        if output_artifact:
            output_path = _make_output_path(workflow_id, step["id"], output_artifact, output_dir, project_dir)
            _check_containment(output_path, project_dir)

            existing_artifact_path = state.get("artifacts", {}).get(output_artifact)
            if existing_artifact_path:
                _check_containment(existing_artifact_path, project_dir)
                existing_abs = os.path.abspath(existing_artifact_path)
                output_abs = os.path.abspath(output_path)
                if existing_abs != output_abs and os.path.exists(existing_artifact_path):
                    try:
                        os.remove(existing_artifact_path)
                    except OSError as e:
                        return {
                            "reason": "failure",
                            "step_id": step["id"],
                            "payload": {"error": str(e), "actions": ["retry", "skip", "abort"]}
                        }

            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError as e:
                    return {
                        "reason": "failure",
                        "step_id": step["id"],
                        "payload": {"error": str(e), "actions": ["retry", "skip", "abort"]}
                    }
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

        agent = step.get("agent")
        agent_return_value = None
        if agent is not None:
            try:
                envelope = assemble_context_envelope(step, state, project_dir)
                input_paths = envelope
            except KeyError:
                input_paths = []

            prompt_parts = []
            if input_paths:
                prompt_parts.append("Input files: " + " ".join(str(p) for p in input_paths))
            if output_path:
                prompt_parts.append("Write output to: {}".format(output_path))
                prompt_parts.append("Output dir: {}".format(
                    os.path.join(project_dir, output_dir)))
            prompt = "\n".join(prompt_parts) if prompt_parts else ""

            model = step.get("model", "sonnet")

            agent_return_value = _invoke_agent(
                step=step,
                state=state,
                state_param=state,
                project_dir_str=project_dir,
                prompt=prompt,
                output_path=output_path,
                input_paths=input_paths,
                model=model,
            )
        else:
            agent_return_value = _invoke_agent(
                step=step,
                state=state,
                state_param=state,
                project_dir_str=project_dir,
                prompt="",
                output_path=output_path,
                input_paths=[],
                model=step.get("model"),
            )
            action_name = step.get("action")
            if action_name is not None:
                try:
                    action_result = orchestrator_actions.dispatch(step, state, project_dir)
                except Exception as e:
                    return {
                        "reason": "failure",
                        "step_id": step["id"],
                        "payload": {"error": str(e), "actions": ["retry", "skip", "abort"]}
                    }
                if isinstance(action_result, dict) and action_result.get("status") == "failure":
                    return {
                        "reason": "failure",
                        "step_id": step["id"],
                        "payload": {
                            "error": action_result.get("message", "Action returned failure"),
                            "actions": ["retry", "skip", "abort"],
                        }
                    }

        state = _load_state(workflow_id, project_dir, output_dir)

        if output_path and output_artifact:
            state.setdefault("artifacts", {})[output_artifact] = output_path
            _save_state(workflow_id, state, project_dir, output_dir)

        signal = None
        if output_path:
            signal = _extract_signal_from_path(output_path)
        elif isinstance(agent_return_value, dict):
            signal = agent_return_value.get("signal", None)

        escalation = step.get("escalation")
        if escalation and signal == escalation.get("signal"):
            state["status"] = "waiting_for_user"
            _save_state(workflow_id, state, project_dir, output_dir)
            return {
                "reason": "escalation",
                "step_id": step["id"],
                "payload": {
                    "signal": signal,
                    "escalation": escalation,
                    "actions": ["acknowledge", "abort"],
                }
            }

        routing = step.get("routing")
        if routing:
            if signal is None:
                _write_checkpoint(state, "Step '{}' failed: no signal on routed step".format(step["id"]))
                state["status"] = "waiting_for_user"
                _save_state(workflow_id, state, project_dir, output_dir)
                return {
                    "reason": "failure",
                    "step_id": step["id"],
                    "payload": {
                        "error": "No signal produced by routed step",
                        "actions": ["retry", "skip", "abort"],
                    }
                }
            if signal not in routing and "default" not in routing:
                _write_checkpoint(state, "Step '{}' failed: unrecognized signal '{}'".format(step["id"], signal))
                state["status"] = "waiting_for_user"
                _save_state(workflow_id, state, project_dir, output_dir)
                return {
                    "reason": "failure",
                    "step_id": step["id"],
                    "payload": {
                        "error": "Unrecognized signal '{}'".format(signal),
                        "actions": ["retry", "skip", "abort"],
                    }
                }

        exit_checks_list = step.get("exit_checks")
        if exit_checks_list or output_artifact:
            passed, failures = validate_exit_checks(step, state, project_dir)
            if not passed:
                _write_checkpoint(state, "Step '{}' exit checks failed: {}".format(
                    step["id"], "; ".join(failures)))
                state["status"] = "waiting_for_user"
                _save_state(workflow_id, state, project_dir, output_dir)
                return {
                    "reason": "failure",
                    "step_id": step["id"],
                    "payload": {
                        "error": "Exit check failures: {}".format(failures),
                        "missing_artifact": output_artifact,
                        "actions": ["retry", "skip", "abort"],
                    }
                }

        try:
            next_step_id = _resolve_next_step_id(step, steps, signal)
        except ValueError as e:
            _write_checkpoint(state, "Routing error: {}".format(e))
            state["status"] = "waiting_for_user"
            _save_state(workflow_id, state, project_dir, output_dir)
            return {
                "reason": "failure",
                "step_id": step["id"],
                "payload": {"error": str(e), "actions": ["retry", "skip", "abort"]}
            }

        current_idx = _step_index(current_step_id, steps)
        next_idx = _step_index(next_step_id, steps) if next_step_id not in ("COMPLETE", "HALTED") else len(steps)

        is_backward = next_step_id not in ("COMPLETE", "HALTED") and next_idx < current_idx

        if is_backward:
            max_iters = step.get("max_iterations") or default_max
            loop_id = "{}-loop".format(step["id"])
            counter_key = "{}->{}" .format(next_step_id, current_step_id)

            iteration_counters = state.setdefault("iteration_counters", {})
            current_count = iteration_counters.get(counter_key, 0)
            at_counter_max = current_count >= max_iters

            iteration_counters[counter_key] = current_count + 1

            state, at_max_iter = increment_iteration(state, loop_id, max_iters)
            at_max = at_max_iter or at_counter_max

            if at_max:
                _write_checkpoint(state, "Max iterations reached for step '{}'".format(step["id"]))
                state["status"] = "waiting_for_user"
                _save_state(workflow_id, state, project_dir, output_dir)
                return {
                    "reason": "max_iterations",
                    "step_id": step["id"],
                    "payload": {
                        "loop_id": loop_id,
                        "counter_key": counter_key,
                        "options": ["reset", "skip", "abort"],
                        "actions": ["reset", "skip", "abort"],
                    }
                }

            for intermediate_idx in range(next_idx, current_idx + 1):
                intermediate_step = steps[intermediate_idx] if intermediate_idx < len(steps) else None
                if intermediate_step:
                    ig = intermediate_step.get("gate")
                    if ig:
                        gate_key_full = "{}:{}".format(intermediate_step["id"], ig)
                        gates = state.get("gates_passed", [])
                        state["gates_passed"] = [g for g in gates if (
                            g.get("gate_id") != gate_key_full if isinstance(g, dict) else g != gate_key_full
                        )]

        completed = state.setdefault("completed_steps", [])
        if current_step_id not in completed:
            completed.append(current_step_id)

        _write_checkpoint(state, "Completed step '{}'".format(current_step_id))
        state["current_step_id"] = next_step_id
        state["status"] = "active"

        if next_step_id not in ("COMPLETE", "HALTED"):
            next_step_obj = _find_step(next_step_id, steps)
            if next_step_obj:
                _update_sc_phase(project_dir, workflow_id, next_step_obj.get("phase", ""))

        _save_state(workflow_id, state, project_dir, output_dir)


def resume_loop(workflow_id, decision, project_dir=".", deference_level="collaborative"):
    _validate_workflow_id(workflow_id)
    project_dir = os.path.abspath(project_dir)
    defaults = _load_defaults(project_dir)
    output_dir = defaults.get("paths", {}).get("output_dir", ".sweetclaude/workflows")
    _check_containment(os.path.join(project_dir, output_dir), project_dir)

    sc = _load_sc_yaml(project_dir)
    _check_orchestrated_conflict(sc, workflow_id)

    state = _load_state(workflow_id, project_dir, output_dir)

    current_step_id = state.get("current_step_id")
    if current_step_id in ("HALTED",) or state.get("status") == "HALTED":
        raise ValueError("Workflow '{}' is halted and cannot be resumed".format(workflow_id))
    if current_step_id == "COMPLETE":
        raise ValueError("Workflow '{}' is already complete".format(workflow_id))

    if state.get("status") == "active":
        raise ValueError("Workflow '{}' is still active (not yielded)".format(workflow_id))

    action = decision.get("action")
    if action not in VALID_ACTIONS:
        raise ValueError("Invalid action '{}'. Valid: {}".format(action, VALID_ACTIONS))

    if action == "abort":
        _write_checkpoint(state, "Workflow aborted by user")
        state["status"] = "HALTED"
        state["current_step_id"] = "HALTED"
        _save_state(workflow_id, state, project_dir, output_dir)
        _complete_sc(project_dir, workflow_id, "halted")
        return {"reason": "halted", "step_id": "HALTED", "payload": {}}

    template_data = _load_template(project_dir)
    workflow_type = state.get("workflow_type", "net-new-feature")
    steps = _get_steps(template_data, workflow_type)

    _add_session(state)
    _save_state(workflow_id, state, project_dir, output_dir)

    if action == "approve":
        step = _find_step(current_step_id, steps)
        if step:
            gate = step.get("gate")
            if gate:
                record_gate_passage(state, "{}:{}".format(step["id"], gate), gate, "approved")
                _save_state(workflow_id, state, project_dir, output_dir)
        return run_loop(workflow_id, project_dir=project_dir, deference_level=deference_level)

    if action == "iterate":
        prior = _find_prior_step(current_step_id, steps)
        if prior:
            state["current_step_id"] = prior["id"]
            state["status"] = "active"
            _save_state(workflow_id, state, project_dir, output_dir)
        return {"reason": "iterated", "step_id": state.get("current_step_id"), "payload": {}}

    if action == "retry":
        step = _find_step(current_step_id, steps)
        if step:
            output_artifact = step.get("output_artifact")
            if output_artifact:
                artifact_path = state.get("artifacts", {}).get(output_artifact)
                if artifact_path and os.path.exists(artifact_path):
                    os.remove(artifact_path)
                else:
                    output_path = _make_output_path(workflow_id, step["id"], output_artifact, output_dir, project_dir)
                    if os.path.exists(output_path):
                        os.remove(output_path)
        state["status"] = "active"
        _save_state(workflow_id, state, project_dir, output_dir)
        return run_loop(workflow_id, project_dir=project_dir, deference_level=deference_level)

    if action == "skip":
        step = _find_step(current_step_id, steps)
        reason = decision.get("reason", "skipped by user")
        skips = state.setdefault("skipped_steps", [])
        skips.append({"step_id": current_step_id, "reason": reason, "at": _now_iso()})
        completed = state.setdefault("completed_steps", [])
        if current_step_id not in completed:
            completed.append(current_step_id)
        next_step_id = _sequential_next(step, steps) if step else "COMPLETE"
        state["current_step_id"] = next_step_id
        state["status"] = "active"
        _write_checkpoint(state, "Skipped step '{}'".format(current_step_id))
        _save_state(workflow_id, state, project_dir, output_dir)
        return {"reason": "skipped", "step_id": next_step_id, "payload": {}}

    if action == "reset":
        state_counters = state.get("iteration_counters", {})
        for key in list(state_counters.keys()):
            state_counters[key] = 0
        state["iteration_counters"] = state_counters
        iterations = state.get("iterations", {})
        for key in list(iterations.keys()):
            iterations[key]["count"] = 0
        state["iterations"] = iterations
        state["status"] = "active"
        _write_checkpoint(state, "Iteration counters reset")
        _save_state(workflow_id, state, project_dir, output_dir)
        return {"reason": "reset", "step_id": current_step_id, "payload": {}}

    if action in ("accept", "acknowledge"):
        state["status"] = "active"
        step = _find_step(current_step_id, steps)
        next_step_id = _sequential_next(step, steps) if step else "COMPLETE"
        state["current_step_id"] = next_step_id
        _save_state(workflow_id, state, project_dir, output_dir)
        return run_loop(workflow_id, project_dir=project_dir, deference_level=deference_level)

    state["status"] = "active"
    _save_state(workflow_id, state, project_dir, output_dir)
    return run_loop(workflow_id, project_dir=project_dir, deference_level=deference_level)


if __name__ == "__main__":
    import json
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["run", "resume"])
    parser.add_argument("--workflow-id", required=True)
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--deference-level", default="collaborative")
    parser.add_argument("--decision-json", default=None)
    args = parser.parse_args()

    if args.command == "run":
        result = run_loop(args.workflow_id, project_dir=args.project_dir,
                          deference_level=args.deference_level)
    elif args.command == "resume":
        decision = json.loads(args.decision_json) if args.decision_json else {}
        result = resume_loop(args.workflow_id, decision, project_dir=args.project_dir,
                             deference_level=args.deference_level)

    if result is not None:
        print(json.dumps(result))
