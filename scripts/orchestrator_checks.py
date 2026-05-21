import os

CHECKS = {}


def register(name):
    def decorator(fn):
        CHECKS[name] = fn
        return fn
    return decorator


def _resolve_artifact_paths(artifact_key, state, project_dir):
    artifacts = state.get("artifacts", {})
    if artifact_key not in artifacts:
        return None, "Artifact key '{}' not found in state".format(artifact_key)
    value = artifacts[artifact_key]
    if isinstance(value, list):
        return value, ""
    return [value], ""


def _check_containment(resolved_path, project_dir):
    project_root = os.path.abspath(project_dir)
    resolved = os.path.abspath(resolved_path)
    if not resolved.startswith(project_root + os.sep) and resolved != project_root:
        raise ValueError(
            "Path '{}' escapes project directory".format(resolved_path)
        )
    return resolved


def _make_absolute(path, project_dir):
    if os.path.isabs(path):
        resolved = path
    else:
        resolved = os.path.join(project_dir, path)
    _check_containment(resolved, project_dir)
    return resolved


@register("file_exists")
def check_file_exists(step, state, project_dir):
    artifact_key = step.get("output_artifact")
    if not artifact_key:
        return True, ""
    paths, err = _resolve_artifact_paths(artifact_key, state, project_dir)
    if paths is None:
        return False, err
    missing = []
    for p in paths:
        abs_p = _make_absolute(p, project_dir)
        if not os.path.exists(abs_p):
            missing.append(abs_p)
    if missing:
        return False, "Missing files for {}: {}".format(artifact_key, ", ".join(missing))
    return True, ""


@register("file_non_empty")
def check_file_non_empty(step, state, project_dir):
    artifact_key = step.get("output_artifact")
    if not artifact_key:
        return True, ""
    paths, err = _resolve_artifact_paths(artifact_key, state, project_dir)
    if paths is None:
        return False, err
    empty = []
    for p in paths:
        abs_p = _make_absolute(p, project_dir)
        if not os.path.exists(abs_p) or os.path.getsize(abs_p) == 0:
            empty.append(abs_p)
    if empty:
        return False, "Empty files for {}: {}".format(artifact_key, ", ".join(empty))
    return True, ""


@register("all_artifacts_exist")
def check_all_artifacts_exist(step, state, project_dir):
    input_artifacts = step.get("input_artifacts") or []
    missing = []
    for key in input_artifacts:
        paths, err = _resolve_artifact_paths(key, state, project_dir)
        if paths is None:
            missing.append(err)
            continue
        for p in paths:
            abs_p = _make_absolute(p, project_dir)
            if not os.path.exists(abs_p):
                missing.append("{}: {}".format(key, abs_p))
    if missing:
        return False, "Missing input artifacts: {}".format(", ".join(missing))
    return True, ""


@register("all_artifacts_non_empty")
def check_all_artifacts_non_empty(step, state, project_dir):
    input_artifacts = step.get("input_artifacts") or []
    empty = []
    for key in input_artifacts:
        paths, err = _resolve_artifact_paths(key, state, project_dir)
        if paths is None:
            empty.append(err)
            continue
        for p in paths:
            abs_p = _make_absolute(p, project_dir)
            if not os.path.exists(abs_p) or os.path.getsize(abs_p) == 0:
                empty.append("{}: {}".format(key, abs_p))
    if empty:
        return False, "Empty input artifacts: {}".format(", ".join(empty))
    return True, ""
