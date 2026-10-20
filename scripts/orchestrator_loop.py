import glob
import os
import re
import subprocess
import sys
import yaml
from datetime import datetime, timezone

import orchestrator_actions
from success_criteria_contracts import record_workflow_closeout
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

VALID_ACTIONS = {"approve", "iterate", "retry", "skip", "abort", "reset", "accept", "acknowledge", "executed"}


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
    output_path = _output_dir_state_path(workflow_id, output_dir, project_dir)

    # State is mirrored to a canonical location and an output-dir copy. Serialize
    # once, write every temp file, then swap them all in: a write failure leaves
    # both destinations untouched rather than half-updated.
    data = yaml.safe_dump(state, default_flow_style=False, allow_unicode=True)

    targets = [canonical]
    if os.path.abspath(output_path) != os.path.abspath(canonical):
        targets.append(output_path)

    staged = []
    for dest in targets:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = dest + ".tmp"
        with open(tmp, "w") as f:
            f.write(data)
        staged.append((tmp, dest))

    for tmp, dest in staged:
        os.replace(tmp, dest)


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


def _completion_evidence_receipt(state):
    if not isinstance(state, dict):
        return None

    candidates = [
        state.get("completion_evidence_receipt"),
        state.get("evidence_receipt"),
        state.get("completion_receipt"),
    ]

    artifacts = state.get("artifacts")
    if isinstance(artifacts, dict):
        candidates.extend([
            artifacts.get("completion_evidence_receipt"),
            artifacts.get("evidence_receipt"),
            artifacts.get("completion_receipt"),
        ])

    for candidate in candidates:
        if isinstance(candidate, dict):
            candidate = candidate.get("path") or candidate.get("receipt")
        if candidate:
            return str(candidate)
    return None


def _update_item_status(project_dir, item_id, result, evidence_receipt=None):
    filepath = _find_item_file(project_dir, item_id)
    if not filepath:
        return None
    status_py = os.path.join(project_dir, "scripts", "status.py")
    if not os.path.isfile(status_py):
        print("WARNING: scripts/status.py not found, skipping status update", file=sys.stderr)
        return False
    if result == "complete":
        if not evidence_receipt:
            print(
                "WARNING: workflow completed, but SweetClaude did not mark {} done "
                "because no completion evidence receipt was recorded. Run "
                "/sweetclaude:build code-verify, then close the item with the receipt.".format(item_id),
                file=sys.stderr,
            )
            return False
        cmd = ["python3", status_py, "set-terminal",
               "--file", filepath, "--status", "done",
               "--actor", "orchestrator", "--project-dir", project_dir,
               "--evidence-receipt", evidence_receipt]
    elif result == "halted":
        cmd = ["python3", status_py, "set",
               "--file", filepath, "--status", "on-hold",
               "--actor", "orchestrator", "--project-dir", project_dir]
    else:
        return None
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        print("WARNING: status update failed for {}: {}".format(
            item_id, r.stdout.strip() or r.stderr.strip()), file=sys.stderr)
        return False
    return True


def _complete_sc(project_dir, workflow_id, result, workflow_state=None):
    from pathlib import Path as _Path
    sc = _load_sc_yaml(project_dir)
    work = sc.setdefault("work", {})
    active = work.get("active", {})
    if active and active.get("id") and active["id"] != workflow_id:
        return {"status_update": "skipped-active-mismatch"}
    item_id = active.get("id") if active else None

    # Legacy path: project-local status.py detected → use subprocess-based
    # status update with evidence receipt check (pre-ISSUE-224 orchestrator).
    status_py = os.path.join(project_dir, "scripts", "status.py")
    if item_id and os.path.isfile(status_py):
        evidence_receipt = None
        if result == "complete":
            evidence_receipt = _completion_evidence_receipt(workflow_state)
        status_updated = _update_item_status(
            project_dir, item_id, result, evidence_receipt=evidence_receipt,
        )
        if result == "complete" and status_updated is False:
            active["phase"] = "VERIFY"
            active["completion_pending_evidence"] = True
            active["workflow_completed_at"] = _now_iso()
            work["active"] = active
            _save_sc_yaml(sc, project_dir)
            return {"status_update": "evidence_required"}

    # New deterministic closeout path.
    outcome = "done" if result == "complete" else result
    record_workflow_closeout(
        _Path(project_dir), workflow_id, outcome=outcome, _legacy_result=result,
    )
    return {"status_update": "updated"}


def _invoke_agent(*args, **kwargs):
    # Default (production) executor seam. A Python subprocess cannot spawn a
    # Claude Code subagent, so the real step execution is delegated to the
    # conversational model: returning this sentinel makes run_loop yield an
    # `execute_step` point. Tests inject a synchronous executor in place of this
    # function (writing the artifact / returning a signal) and so never delegate.
    return {"status": "delegate"}


def _is_delegate(value):
    return isinstance(value, dict) and value.get("status") == "delegate"


def _schema_allowed_signals(schema):
    """Return the set of valid signal values declared by a step's output_schema,
    or None when the schema does not constrain the signal.

    Supported shape:
        output_schema:
          signal:
            enum: [done, issues, blocked]
    """
    if not isinstance(schema, dict):
        return None
    sig = schema.get("signal")
    if isinstance(sig, dict) and isinstance(sig.get("enum"), list):
        return set(sig["enum"])
    return None


def _budget_limits(defaults):
    """Return (max_steps, max_tokens) from orchestrator defaults; None = unlimited."""
    b = (defaults.get("budget") or {}) if isinstance(defaults, dict) else {}
    return b.get("max_steps"), b.get("max_tokens")


def _budget_exceeded(state, defaults):
    """Return the name of the exhausted budget dimension, or None.

    `steps` is counted deterministically by the loop (one per completed step);
    `tokens` is accumulated from spend the model relays on resume("executed").
    """
    max_steps, max_tokens = _budget_limits(defaults)
    spent = state.get("budget_spent") or {}
    if max_steps is not None and spent.get("steps", 0) >= max_steps:
        return "max_steps"
    if max_tokens is not None and spent.get("tokens", 0) >= max_tokens:
        return "max_tokens"
    return None


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


def _resolve_parallel_children(workflow_id, step, output_dir, project_dir):
    """Resolve each child of a parallel step to (child, output_artifact, path)."""
    resolved = []
    for child in (step.get("parallel") or []):
        art = child.get("output_artifact")
        path = None
        if art:
            path = _make_output_path(workflow_id, step["id"], art, output_dir, project_dir)
            _check_containment(path, project_dir)
        resolved.append((child, art, path))
    return resolved


def _run_parallel_step(workflow_id, state, step, reentering, output_dir, project_dir):
    """Drive a parallel (fan-out) step.

    First visit: clean stale child outputs and yield a single `execute_step`
    whose payload lists every child for the model to spawn concurrently.
    Re-entry: validate the join policy across the children's artifacts, record
    them, and return None so the caller continues to routing/advance.
    """
    resolved = _resolve_parallel_children(workflow_id, step, output_dir, project_dir)
    join = step.get("join", "all")

    if not reentering:
        for _child, _art, path in resolved:
            if path:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError as e:
                        return {
                            "reason": "failure",
                            "step_id": step["id"],
                            "payload": {"error": str(e), "actions": ["retry", "skip", "abort"]},
                        }
                os.makedirs(os.path.dirname(path), exist_ok=True)
        state["status"] = "waiting_for_agent"
        _save_state(workflow_id, state, project_dir, output_dir)
        return {
            "reason": "execute_step",
            "step_id": step["id"],
            "payload": {
                "parallel": [
                    {
                        "agent": child.get("agent"),
                        "subagent_type": child.get("subagent_type"),
                        "model": child.get("model", "sonnet"),
                        "output_artifact": art,
                        "output_path": path,
                        "prompt": child.get("prompt", ""),
                    }
                    for (child, art, path) in resolved
                ],
                "join": join,
                "output_schema": step.get("output_schema"),
                "actions": ["executed", "abort"],
            },
        }

    # Re-entry: validate the join policy.
    present = []
    for child, art, path in resolved:
        ok = bool(path) and os.path.exists(path) and os.path.getsize(path) > 0
        if ok and art:
            state.setdefault("artifacts", {})[art] = path
        present.append((child, art, ok))

    if join == "any":
        satisfied = any(ok for _c, _a, ok in present)
    else:
        satisfied = all(ok for _c, _a, ok in present)

    if not satisfied:
        missing = [art or (child.get("agent") or "child")
                   for child, art, ok in present if not ok]
        _write_checkpoint(state, "Parallel step '{}' join '{}' unsatisfied; missing: {}".format(
            step["id"], join, ", ".join(str(m) for m in missing)))
        state["status"] = "waiting_for_user"
        _save_state(workflow_id, state, project_dir, output_dir)
        return {
            "reason": "failure",
            "step_id": step["id"],
            "payload": {
                "error": "Parallel join '{}' not satisfied; missing artifacts: {}".format(
                    join, missing),
                "actions": ["retry", "skip", "abort"],
            },
        }

    _save_state(workflow_id, state, project_dir, output_dir)
    return None


_AFFIRM_VERDICTS = {"confirmed", "real", "pass", "true", "yes", "valid"}


def _verify_slots(workflow_id, step, output_dir, project_dir):
    """Resolve a verify step into (config, count, [(artifact, path), ...])."""
    cfg = step.get("verify") or {}
    try:
        count = int(cfg.get("count", 3) or 3)
    except (TypeError, ValueError):
        count = 3
    count = max(1, count)
    base = cfg.get("output_artifact", "verdict")
    slots = []
    for i in range(1, count + 1):
        art = "{}-{}".format(base, i)
        path = _make_output_path(workflow_id, step["id"], art, output_dir, project_dir)
        _check_containment(path, project_dir)
        slots.append((art, path))
    return cfg, count, slots


def _verdict_passes(threshold, confirmed, total):
    """Apply a verify threshold to an affirm-vote tally."""
    if isinstance(threshold, bool):
        threshold = "majority"
    if isinstance(threshold, int):
        return confirmed >= threshold
    t = str(threshold or "majority").lower()
    if t == "all":
        return total > 0 and confirmed == total
    if t == "any":
        return confirmed >= 1
    return confirmed > (total / 2.0)


def _run_verify_step(workflow_id, state, step, reentering, output_dir, project_dir):
    """Drive an adversarial-verify (fan-out + vote) step.

    First visit: clean stale verdict slots and yield one `execute_step` asking
    the model to spawn N independent verifiers, each returning a 'confirmed' or
    'refuted' verdict. Re-entry: tally the affirm votes (relayed verdicts
    preferred, else read each verdict artifact), apply the threshold, and set
    the step signal to 'confirmed' or 'refuted' for routing.
    """
    cfg, count, slots = _verify_slots(workflow_id, step, output_dir, project_dir)
    threshold = cfg.get("threshold", "majority")

    if not reentering:
        for _art, path in slots:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError as e:
                    return {
                        "reason": "failure",
                        "step_id": step["id"],
                        "payload": {"error": str(e), "actions": ["retry", "skip", "abort"]},
                    }
            os.makedirs(os.path.dirname(path), exist_ok=True)
        state["status"] = "waiting_for_agent"
        _save_state(workflow_id, state, project_dir, output_dir)
        return {
            "reason": "execute_step",
            "step_id": step["id"],
            "payload": {
                "verify": {
                    "agent": cfg.get("agent"),
                    "subagent_type": cfg.get("subagent_type"),
                    "model": cfg.get("model", "sonnet"),
                    "count": count,
                    "threshold": threshold,
                    "instruction": cfg.get(
                        "instruction",
                        "Independently attempt to REFUTE the claim. Default to "
                        "'refuted' when uncertain; return 'confirmed' only if it holds."),
                    "slots": [{"output_artifact": art, "output_path": path} for art, path in slots],
                },
                "actions": ["executed", "abort"],
            },
        }

    # Re-entry: gather verdicts (relayed preferred, else read each artifact).
    relayed = (state.get("pending_verdicts") or {}).get(step["id"])
    verdicts = []
    missing = []
    if isinstance(relayed, list) and relayed:
        verdicts = [str(v).lower() for v in relayed]
    else:
        for art, path in slots:
            sig = _extract_signal_from_path(path) if path else None
            if sig is None:
                missing.append(art)
            else:
                verdicts.append(str(sig).lower())
                state.setdefault("artifacts", {})[art] = path

    if missing:
        _write_checkpoint(state, "Verify step '{}' missing verdicts: {}".format(
            step["id"], ", ".join(missing)))
        state["status"] = "waiting_for_user"
        _save_state(workflow_id, state, project_dir, output_dir)
        return {
            "reason": "failure",
            "step_id": step["id"],
            "payload": {
                "error": "Missing verdicts: {}".format(missing),
                "actions": ["retry", "skip", "abort"],
            },
        }

    confirmed = sum(1 for v in verdicts if v in _AFFIRM_VERDICTS)
    total = len(verdicts)
    aggregate = "confirmed" if _verdict_passes(threshold, confirmed, total) else "refuted"
    state.setdefault("step_signals", {})[step["id"]] = aggregate
    state.setdefault("verify_results", {})[step["id"]] = {
        "confirmed": confirmed,
        "total": total,
        "threshold": threshold,
        "signal": aggregate,
    }
    if isinstance(state.get("pending_verdicts"), dict):
        state["pending_verdicts"].pop(step["id"], None)
    _save_state(workflow_id, state, project_dir, output_dir)
    return None


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
            payload = _complete_sc(project_dir, workflow_id, "complete", workflow_state=state)
            return {"reason": "complete", "step_id": "COMPLETE", "payload": payload or {}}

        if current_step_id == "HALTED":
            payload = _complete_sc(project_dir, workflow_id, "halted", workflow_state=state)
            return {"reason": "halted", "step_id": "HALTED", "payload": payload or {}}

        budget_hit = _budget_exceeded(state, defaults)
        if budget_hit:
            _write_checkpoint(state, "Budget exhausted ({})".format(budget_hit))
            state["status"] = "waiting_for_user"
            _save_state(workflow_id, state, project_dir, output_dir)
            return {
                "reason": "budget_exhausted",
                "step_id": current_step_id,
                "payload": {
                    "limit": budget_hit,
                    "spent": state.get("budget_spent", {}),
                    "options": ["reset", "abort"],
                    "actions": ["reset", "abort"],
                },
            }

        step = _find_step(current_step_id, steps)
        if step is None:
            raise ValueError("Step '{}' not found in template".format(current_step_id))

        # Re-entry after the model executed this step out of band (resume action
        # "executed"). The artifact is already on disk; skip invocation and stale
        # output cleanup so we don't discard the model's work.
        reentering = state.get("step_executed") == current_step_id

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

        # Parallel (fan-out) step: the model spawns all children concurrently,
        # then the join policy is validated on re-entry. Routing/advance below is
        # shared with single steps.
        parallel_children = step.get("parallel")
        if parallel_children:
            parallel_result = _run_parallel_step(
                workflow_id, state, step, reentering, output_dir, project_dir)
            if parallel_result is not None:
                return parallel_result

        # Adversarial-verify step: fan out N verifiers and route on the vote.
        verify_spec = step.get("verify")
        if verify_spec:
            verify_result = _run_verify_step(
                workflow_id, state, step, reentering, output_dir, project_dir)
            if verify_result is not None:
                return verify_result

        output_artifact = step.get("output_artifact")
        output_path = None
        if output_artifact:
            output_path = _make_output_path(workflow_id, step["id"], output_artifact, output_dir, project_dir)
            _check_containment(output_path, project_dir)

            existing_artifact_path = state.get("artifacts", {}).get(output_artifact)
            if existing_artifact_path and not reentering:
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

            if os.path.exists(output_path) and not reentering:
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
        if parallel_children or verify_spec:
            # Execution was handled by _run_parallel_step / _run_verify_step;
            # artifacts and any aggregate signal are already recorded. Fall
            # through to routing/advance.
            pass
        elif agent is not None:
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

            if reentering:
                # Model already executed this step out of band; its output is on
                # disk. Skip invocation and fall through to post-processing.
                agent_return_value = None
            else:
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
                if _is_delegate(agent_return_value):
                    state["status"] = "waiting_for_agent"
                    _save_state(workflow_id, state, project_dir, output_dir)
                    return {
                        "reason": "execute_step",
                        "step_id": step["id"],
                        "payload": {
                            "agent": agent,
                            "subagent_type": step.get("subagent_type"),
                            "model": model,
                            "input_paths": [str(p) for p in input_paths],
                            "output_path": output_path,
                            "prompt": prompt,
                            "output_schema": step.get("output_schema"),
                            "actions": ["executed", "abort"],
                        },
                    }
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
        provided_signal = (state.get("step_signals") or {}).get(current_step_id)
        if provided_signal is not None:
            # Structured signal relayed by the model from the subagent's
            # schema-validated output; preferred over scraping the artifact.
            signal = provided_signal
        elif output_path:
            signal = _extract_signal_from_path(output_path)
        elif isinstance(agent_return_value, dict):
            signal = agent_return_value.get("signal", None)

        schema = step.get("output_schema")
        if schema is not None and signal is not None:
            allowed = _schema_allowed_signals(schema)
            if allowed is not None and signal not in allowed:
                _write_checkpoint(state, "Step '{}' signal '{}' violates output_schema".format(
                    step["id"], signal))
                state["status"] = "waiting_for_user"
                _save_state(workflow_id, state, project_dir, output_dir)
                return {
                    "reason": "failure",
                    "step_id": step["id"],
                    "payload": {
                        "error": "Signal '{}' is not permitted by output_schema (allowed: {})".format(
                            signal, sorted(allowed)),
                        "actions": ["retry", "skip", "abort"],
                    },
                }

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
                # Don't leave state pointing at an artifact that was never
                # produced. (file_exists reads state["artifacts"], so the pointer
                # must be set *before* validation; drop it only when the file is
                # genuinely missing. It is re-recorded if the step is retried.)
                if output_artifact and output_path and not os.path.exists(output_path):
                    state.get("artifacts", {}).pop(output_artifact, None)
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
        if isinstance(state.get("step_signals"), dict):
            state["step_signals"].pop(current_step_id, None)
        budget_spent = state.setdefault("budget_spent", {"steps": 0, "tokens": 0})
        budget_spent["steps"] = budget_spent.get("steps", 0) + 1
        state["current_step_id"] = next_step_id
        state["step_executed"] = None
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

    if action == "executed":
        # The model finished executing the step that yielded `execute_step` and
        # wrote its artifact. Mark it executed and re-enter the loop, which skips
        # invocation and runs post-processing (signal, routing, exit checks).
        # The model may relay a structured signal from the subagent's
        # schema-validated output; it takes precedence over scraping the artifact.
        provided_signal = decision.get("signal")
        if provided_signal is None and isinstance(decision.get("result"), dict):
            provided_signal = decision["result"].get("signal")
        state["step_executed"] = current_step_id
        if provided_signal is not None:
            state.setdefault("step_signals", {})[current_step_id] = provided_signal
        verdicts = decision.get("verdicts")
        if isinstance(verdicts, list) and verdicts:
            state.setdefault("pending_verdicts", {})[current_step_id] = verdicts
        cost = decision.get("tokens")
        if cost is None:
            cost = decision.get("cost")
        if isinstance(cost, (int, float)) and not isinstance(cost, bool) and cost > 0:
            bs = state.setdefault("budget_spent", {"steps": 0, "tokens": 0})
            bs["tokens"] = bs.get("tokens", 0) + cost
        state["status"] = "active"
        _save_state(workflow_id, state, project_dir, output_dir)
        return run_loop(workflow_id, project_dir=project_dir, deference_level=deference_level)

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
            state["step_executed"] = None
            if isinstance(state.get("step_signals"), dict):
                state["step_signals"].pop(prior["id"], None)
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
        state["step_executed"] = None
        if isinstance(state.get("step_signals"), dict):
            state["step_signals"].pop(current_step_id, None)
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
        if isinstance(state.get("budget_spent"), dict):
            state["budget_spent"] = {"steps": 0, "tokens": 0}
        state["status"] = "active"
        _write_checkpoint(state, "Iteration counters and budget reset")
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
