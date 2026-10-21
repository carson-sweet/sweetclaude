#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# SweetClaude hook I/O helper. Reads the Claude Code hook payload from stdin and
# emits the outputs documented in docs/design/hook-protocol.md.
#
# CLI (stdin carries the payload JSON for field and project-dir):
#   hook_io.py field tool_input.file_path [default]
#   hook_io.py project-dir
#   hook_io.py deny REASON
#   hook_io.py context EVENT TEXT
#   hook_io.py block REASON
#   hook_io.py rel-path FILE            (project dir from stdin payload)
#   hook_io.py flag-root PROJECT_DIR
#   hook_io.py run-tests PROJECT_DIR COMMAND TIMEOUT_SECONDS
#   hook_io.py wip-limit                (PreToolUse payload on stdin; denies a fourth activation)
#   hook_io.py test-targets             (PreToolUse payload on stdin; prints test files being written)
#   hook_io.py tdd-state SC_YAML PHASE_YAML   (prints phase, tdd_phase, released files; exit 3 without PyYAML)
#   hook_io.py detect-test-command PROJECT_DIR

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import re
import shlex
import signal
import subprocess
import sys

OUTPUT_TAIL_BYTES = 32 * 1024


def read_input(stream=None) -> dict:
    stream = stream or sys.stdin
    try:
        data = json.loads(stream.read())
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def get_field(data: dict, dotted: str, default: str = "") -> str:
    value = data
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            return default
        value = value[part]
    if value is None:
        return default
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


def project_dir(data: dict) -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR") or str(data.get("cwd") or "") or os.getcwd()


def relative_path(file: str, project: str) -> str:
    real_project = os.path.realpath(project)
    directory, base = os.path.split(file)
    real_file = os.path.join(os.path.realpath(directory or "."), base)
    prefix = real_project.rstrip("/") + "/"
    return real_file[len(prefix):] if real_file.startswith(prefix) else file


def flag_root(project: str) -> str:
    try:
        result = subprocess.run(["git", "-C", project, "rev-parse", "--show-toplevel"],
                                capture_output=True, text=True, timeout=30)
        top = result.stdout.strip()
        if result.returncode == 0 and top:
            return top
    except (OSError, subprocess.SubprocessError):
        pass
    return project.rstrip("/") or "/"


GIT_OPTIONS_WITH_VALUE = {"-c", "-C", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix", "--config-env"}
COMMAND_SEPARATORS = {"&&", "||", ";", "|", "&", "\n"}


def is_git_commit(command: str) -> bool:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return False
    at_start = True
    index = 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if token in COMMAND_SEPARATORS or token == "\n":
            at_start = True
            continue
        if not at_start:
            continue
        at_start = False
        if token != "git":
            continue
        while index < len(tokens) and tokens[index] not in COMMAND_SEPARATORS:
            option = tokens[index]
            if option in GIT_OPTIONS_WITH_VALUE:
                index += 2
            elif option.startswith("-"):
                index += 1
            else:
                break
        if index < len(tokens) and tokens[index] == "commit":
            return True
    return False


def run_tests(project: str, command: str, timeout_seconds: int) -> dict | None:
    proc = subprocess.Popen(["bash", "-c", command], cwd=project, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, start_new_session=True)
    try:
        out, _ = proc.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
        out, _ = proc.communicate()
        tail = out[-OUTPUT_TAIL_BYTES:].decode("utf-8", errors="replace")
        return context_output("PostToolUse",
                              f"Tests timed out after {timeout_seconds}s running: {command}\n{tail}")
    if proc.returncode == 0:
        return None
    tail = out[-OUTPUT_TAIL_BYTES:].decode("utf-8", errors="replace")
    return context_output("PostToolUse", f"Tests failed (exit {proc.returncode}) running: {command}\n{tail}")


HEREDOC_OPERATOR = re.compile(r"(?<!<)<<(?!<)-?\s*(?:'([^']*)'|\"([^\"]*)\"|\\?([A-Za-z0-9_]+))")


def strip_heredoc_bodies(command: str) -> str:
    kept = []
    pending: list[str] = []
    for line in command.split("\n"):
        if pending:
            if line.strip() == pending[0]:
                pending.pop(0)
            continue
        kept.append(line)
        for match in HEREDOC_OPERATOR.finditer(line):
            pending.append(match.group(1) or match.group(2) or match.group(3))
    return " ; ".join(kept)


def tokenize_shell(command: str) -> list[str]:
    lexer = shlex.shlex(strip_heredoc_bodies(command), posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return [token.strip("'\"") for token in re.findall(r"""&>>|&>|>>|>\||>|[;&|()]+|[^\s;&|()<>]+""", command)]


TEST_PATH_PATTERNS = ("test/", "tests/", "__tests__/", "spec/", "specs/", ".test.", ".spec.", "_test.", "_spec.", "test_")


def is_test_path(relative: str) -> bool:
    return relative.endswith(".feature") or any(pattern in relative for pattern in TEST_PATH_PATTERNS)


REDIRECT_OPERATORS = {">", ">>", "&>", "&>>", ">|"}
SEGMENT_SEPARATORS = {"&&", "||", ";", "|", "&", "(", ")", "|&", ";;"}
SHELL_INTERPRETERS = {"bash", "sh", "zsh", "dash"}
MAX_SHELL_NESTING = 2


def command_segments(tokens: list[str]) -> list[list[str]]:
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token in SEGMENT_SEPARATORS:
            segments.append([])
        else:
            segments[-1].append(token)
    return [segment for segment in segments if segment]


def redirect_targets(segment: list[str]) -> tuple[list[str], list[str]]:
    words: list[str] = []
    targets: list[str] = []
    skip_next = False
    for index, token in enumerate(segment):
        if skip_next:
            skip_next = False
            continue
        if token in REDIRECT_OPERATORS:
            if index + 1 < len(segment):
                targets.append(segment[index + 1])
            skip_next = True
        elif token in {"<", "<<", "<<<", ">&", "<&"}:
            skip_next = True
        else:
            words.append(token)
    return words, targets


def sed_in_place_targets(args: list[str]) -> list[str]:
    in_place = False
    has_script_option = False
    positional: list[str] = []
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        if arg.startswith("--"):
            if arg.startswith("--in-place"):
                in_place = True
            elif arg in {"--expression", "--file"}:
                has_script_option = True
                index += 1
            elif arg.startswith(("--expression=", "--file=")):
                has_script_option = True
        elif arg in {"-e", "-f"}:
            has_script_option = True
            index += 1
        elif arg.startswith("-") and len(arg) > 1:
            in_place = in_place or "i" in arg[1:]
        elif arg:
            positional.append(arg)
    if not in_place:
        return []
    return positional if has_script_option else positional[1:]


def copy_destinations(args: list[str], base: str) -> list[str]:
    operands: list[str] = []
    target_directory = ""
    index = 0
    while index < len(args):
        arg = args[index]
        index += 1
        if arg in {"-t", "--target-directory"} and index < len(args):
            target_directory = args[index]
            index += 1
        elif arg.startswith("--target-directory="):
            target_directory = arg.split("=", 1)[1]
        elif arg.startswith("-") and len(arg) > 1:
            continue
        else:
            operands.append(arg)
    if target_directory:
        return [os.path.join(target_directory, os.path.basename(source)) for source in operands]
    if len(operands) < 2:
        return []
    destination = operands[-1]
    absolute = destination if os.path.isabs(destination) else os.path.join(base, destination)
    if destination.endswith("/") or os.path.isdir(absolute):
        return [os.path.join(destination, os.path.basename(source)) for source in operands[:-1]]
    return [destination]


def written_paths(command: str, base: str, nesting: int = 0) -> list[str]:
    paths: list[str] = []
    for segment in command_segments(tokenize_shell(command)):
        words, targets = redirect_targets(segment)
        paths.extend(targets)
        while words and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]):
            words = words[1:]
        if not words:
            continue
        name = os.path.basename(words[0])
        args = words[1:]
        if name == "tee":
            paths.extend(arg for arg in args if not arg.startswith("-"))
        elif name == "sed":
            paths.extend(sed_in_place_targets(args))
        elif name in {"cp", "mv", "install"}:
            paths.extend(copy_destinations(args, base))
        elif name in SHELL_INTERPRETERS and nesting < MAX_SHELL_NESTING and "-c" in args:
            position = args.index("-c")
            if position + 1 < len(args):
                paths.extend(written_paths(args[position + 1], base, nesting + 1))
    return [path for path in paths if path and path != "/dev/null" and not path.startswith("&")]


def test_targets(data: dict) -> list[str]:
    project = project_dir(data)
    tool = str(data.get("tool_name") or "")
    tool_input = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    if tool in {"Write", "Edit", "NotebookEdit"}:
        target = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
        if not target:
            return []
        relative = relative_path(target, project)
        return [relative] if is_test_path(relative) else []
    if tool != "Bash":
        return []
    base = str(data.get("cwd") or project)
    found: list[str] = []
    for path in written_paths(str(tool_input.get("command") or ""), base):
        if "$" in path or path.startswith("~"):
            relative = path
        else:
            absolute = path if os.path.isabs(path) else os.path.join(base, path)
            relative = relative_path(os.path.normpath(absolute), project)
            if os.path.isabs(relative):
                continue
        if is_test_path(relative) and relative not in found:
            found.append(relative)
    return found


def tdd_state(sc_yaml: str, phase_yaml: str) -> tuple[str, str, list[str]]:
    import yaml

    def load(path: str) -> dict:
        try:
            with open(path, encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            return data if isinstance(data, dict) else {}
        except (OSError, yaml.YAMLError):
            return {}

    canonical = load(sc_yaml) if sc_yaml else {}
    mirror = load(phase_yaml) if phase_yaml else {}
    active = (canonical.get("work") or {}).get("active") or {}
    phase = active.get("phase") or mirror.get("phase") or ""
    tdd = active.get("tdd_phase") or mirror.get("tdd_phase") or ""
    released = [str(item) for item in (active.get("tdd_released_files") or [])]
    return str(phase), str(tdd), released


def detect_test_command(project: str) -> str:
    def read(name: str) -> str:
        try:
            with open(os.path.join(project, name), encoding="utf-8", errors="replace") as handle:
                return handle.read()
        except OSError:
            return ""

    pytest_markers = (("pytest.ini", ""), ("pyproject.toml", "pytest"), ("setup.cfg", "pytest"),
                      ("tox.ini", "pytest"), ("conftest.py", ""))
    for name, marker in pytest_markers:
        if os.path.isfile(os.path.join(project, name)) and marker in read(name):
            return "python3 -m pytest -q"
    try:
        scripts = (json.loads(read("package.json")) or {}).get("scripts") or {}
    except ValueError:
        scripts = {}
    script = scripts.get("test") if isinstance(scripts, dict) else None
    if isinstance(script, str) and script.strip() and "no test specified" not in script:
        return "npm test --silent"
    return ""


ISSUE_FILE = re.compile(r"^(ISSUE-\d+)-.*\.md$", re.IGNORECASE)
FRONTMATTER_STATUS = re.compile(r"^status:\s*[\"']?([\w-]+)", re.MULTILINE | re.IGNORECASE)
BOLD_STATUS = re.compile(r"^\*\*Status:\*\*\s*([\w-]+)", re.MULTILINE | re.IGNORECASE)


def issue_status(content: str) -> str:
    frontmatter = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    match = FRONTMATTER_STATUS.search(frontmatter.group(1)) if frontmatter else BOLD_STATUS.search(content)
    return match.group(1).lower() if match else ""


def load_artifact_impl():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "sc-artifact-impl.py")
    spec = importlib.util.spec_from_file_location("sc_artifact_impl", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def active_issue_ids(impl, product_base) -> set[str]:
    active: set[str] = set()
    for path in impl._artifact_files(product_base, "issue", "ISSUE"):
        match = ISSUE_FILE.match(path.name)
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if match and issue_status(content) == "active":
            active.add(match.group(1).upper())
    return active


def bash_activated_issue(command: str) -> str | None:
    tokens = tokenize_shell(command)
    for index, token in enumerate(tokens):
        name = os.path.basename(token)
        if name == "sc_artifact_write" and index + 2 < len(tokens):
            issue_id, payload_json = tokens[index + 1], tokens[index + 2]
        elif name == "sc-artifact-impl.py" and index + 6 < len(tokens) and tokens[index + 1] == "write":
            issue_id, payload_json = tokens[index + 5], tokens[index + 6]
        elif name == "sc_artifact_create" and index + 2 < len(tokens):
            issue_id, payload_json = "", tokens[index + 2]
        elif name == "sc-artifact-impl.py" and index + 6 < len(tokens) and tokens[index + 1] == "create":
            issue_id, payload_json = "", tokens[index + 6]
        else:
            continue
        try:
            fields = json.loads(payload_json)
        except ValueError:
            continue
        if isinstance(fields, dict) and str(fields.get("status", "")).lower() == "active":
            return issue_id.upper()
    return None


def edited_content(path: str, tool_input: dict) -> str:
    try:
        with open(path, encoding="utf-8") as handle:
            current = handle.read()
    except OSError:
        return str(tool_input.get("new_string") or "")
    old, new = str(tool_input.get("old_string") or ""), str(tool_input.get("new_string") or "")
    return current.replace(old, new) if tool_input.get("replace_all") else current.replace(old, new, 1)


def wip_limit_denial(data: dict) -> str | None:
    project = project_dir(data)
    gates_path = os.path.join(project, ".sweetclaude", "state", "effective-gates.yaml")
    if not os.path.isfile(gates_path):
        return None
    try:
        import yaml
        with open(gates_path, encoding="utf-8") as handle:
            gates = yaml.safe_load(handle) or {}
        if gates.get("mode", "flow") != "kanban":
            return None
        limit = int(gates.get("wip_limit", 3))
        impl = load_artifact_impl()
    except Exception:
        return None
    tool = str(data.get("tool_name") or "")
    tool_input = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    product_base = impl.resolve_product_base(pathlib.Path(project))
    issue_id: str | None = None
    if tool == "Bash":
        issue_id = bash_activated_issue(str(tool_input.get("command") or ""))
    elif tool in {"Write", "Edit"}:
        path = str(tool_input.get("file_path") or "")
        match = ISSUE_FILE.match(os.path.basename(path))
        within_issues = any(os.path.realpath(path).startswith(str(directory.resolve()) + os.sep)
                            for directory in impl._search_dirs(product_base, "issue"))
        if match and within_issues:
            content = str(tool_input.get("content") or "") if tool == "Write" else edited_content(path, tool_input)
            if issue_status(content) == "active":
                issue_id = match.group(1).upper()
    if issue_id is None:
        return None
    active = active_issue_ids(impl, product_base)
    if issue_id in active or len(active) < limit:
        return None
    return (f"WIP limit reached ({len(active)}/{limit} items active). "
            "Complete or move an item before starting new work.")


def deny_output(reason: str) -> dict:
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}


def allow_output(reason: str = "") -> dict:
    output = {"hookEventName": "PreToolUse", "permissionDecision": "allow"}
    if reason:
        output["permissionDecisionReason"] = reason
    return {"hookSpecificOutput": output}


def context_output(event: str, text: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}


def block_output(reason: str) -> dict:
    return {"decision": "block", "reason": reason}


def emit(output: dict) -> None:
    sys.stdout.write(json.dumps(output) + "\n")


def main(argv: list[str]) -> int:
    command = argv[0] if argv else ""
    if command == "field" and len(argv) >= 2:
        sys.stdout.write(get_field(read_input(), argv[1], argv[2] if len(argv) > 2 else ""))
        return 0
    if command == "project-dir":
        sys.stdout.write(project_dir(read_input()))
        return 0
    if command == "deny" and len(argv) == 2:
        emit(deny_output(argv[1]))
        return 0
    if command == "allow":
        emit(allow_output(argv[1] if len(argv) > 1 else ""))
        return 0
    if command == "context" and len(argv) == 3:
        emit(context_output(argv[1], argv[2]))
        return 0
    if command == "block" and len(argv) == 2:
        emit(block_output(argv[1]))
        return 0
    if command == "rel-path" and len(argv) == 2:
        sys.stdout.write(relative_path(argv[1], project_dir(read_input())))
        return 0
    if command == "is-git-commit":
        return 0 if is_git_commit(get_field(read_input(), "tool_input.command")) else 1
    if command == "flag-root" and len(argv) == 2:
        sys.stdout.write(flag_root(argv[1]))
        return 0
    if command == "run-tests" and len(argv) == 4:
        output = run_tests(argv[1], argv[2], int(argv[3]))
        if output:
            emit(output)
        return 0
    if command == "wip-limit":
        reason = wip_limit_denial(read_input())
        if reason:
            emit(deny_output(reason))
        return 0
    if command == "test-targets":
        sys.stdout.write("\n".join(test_targets(read_input())))
        return 0
    if command == "tdd-state" and len(argv) == 3:
        try:
            phase, tdd, released = tdd_state(argv[1], argv[2])
        except ImportError:
            return 3
        sys.stdout.write("\n".join([phase, tdd, *released]))
        return 0
    if command == "detect-test-command" and len(argv) == 2:
        sys.stdout.write(detect_test_command(argv[1]))
        return 0
    sys.stderr.write("usage: hook_io.py field|project-dir|deny|allow|context|block|rel-path|flag-root|run-tests|wip-limit|test-targets|tdd-state|detect-test-command\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
