#!/usr/bin/env python3
"""Live Tier 1 and Tier 2 routing checks for the tiered skill library."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Iterable

import yaml


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "tests" / "behavioral" / "routing_cases.yaml"
RESULTS = ROOT / ".sweetclaude" / "routing-results"
CATEGORIES = ("plan", "design", "build", "maintain", "configure", "utils")
UTILITIES = ("status", "help")
PUBLIC = {f"sweetclaude:{name}" for name in (*CATEGORIES, "go", *UTILITIES)}
ROUTERS = {"sweetclaude:find-skill", "sweetclaude:_route", "sweetclaude:library-load", *(f"sweetclaude:{c}" for c in CATEGORIES)}
INDEX_READ = re.compile(r"skill-library/([^/]+)/INDEX\.md$")
WORKFLOW_READ = re.compile(r"skill-library/([^/]+)/([^/]+)/SKILL\.md$")
PRELOAD = re.compile(r"^!`([^`]+)`", re.MULTILINE)
FIXTURE_STATE = """schema_version: 2
framework:
  setup_complete: true
  migration_status: complete
  hook_last_ran: '{now}'
  consistency:
    last_checked: '{now}'
  update:
    declined: 99.0.0
    last_checked: '{now}'
project:
  name: ShiftBoard
  type: new-project
  trunk_branch: main
session:
  deference_level: collaborative
"""


@dataclass
class Trace:
    plugin_paths: list[str] = field(default_factory=list)
    public_skills: list[str] = field(default_factory=list)
    skills: list[tuple[str, str]] = field(default_factory=list)
    index_reads: list[str] = field(default_factory=list)
    workflow: tuple[str, str] | None = None
    asked: bool = False
    texts: list[str] = field(default_factory=list)
    preflight_stop: str | None = None
    cost_usd: float | None = None
    finished: bool = False

    @property
    def routing_started(self) -> bool:
        return bool(self.index_reads) or any(name in ROUTERS for name, _ in self.skills)

    @property
    def category(self) -> str | None:
        if self.workflow:
            return self.workflow[0]
        if self.index_reads:
            return self.index_reads[0]
        for name, args in self.skills:
            short = name.removeprefix("sweetclaude:")
            if short in CATEGORIES or short in UTILITIES:
                return short
            if name == "sweetclaude:library-load":
                head = re.split(r"[\s=]+", args.strip())
                for token in head[:3]:
                    if token in CATEGORIES:
                        return token
        return None


def load_cases(path: Path = CASES) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data["cases"]


def validate_cases(cases: list[dict[str, Any]], library: Path = ROOT / "skill-library") -> list[str]:
    errors = []
    seen = set()
    for case in cases:
        cid = case.get("id")
        if cid in seen:
            errors.append(f"{cid}: duplicate id")
        seen.add(cid)
        category = case.get("category")
        if category not in CATEGORIES:
            errors.append(f"{cid}: unknown category {category!r}")
            continue
        if not case.get("prompt") or not case.get("workflows"):
            errors.append(f"{cid}: prompt and workflows are required")
            continue
        index = (library / category / "INDEX.md").read_text(encoding="utf-8")
        for workflow in case["workflows"]:
            if not isinstance(workflow, str):
                errors.append(f"{cid}: workflow {workflow!r} is not a string")
            elif not (library / category / workflow / "SKILL.md").is_file():
                errors.append(f"{cid}: {category}/{workflow} has no SKILL.md")
            elif f"`{workflow}`" not in index:
                errors.append(f"{cid}: {workflow} is not listed in {category}/INDEX.md")
    return errors


def observe(trace: Trace, event: dict[str, Any]) -> None:
    kind = event.get("type")
    if kind == "system" and event.get("subtype") == "init":
        trace.plugin_paths = [p.get("path", "") for p in event.get("plugins") or [] if p.get("name") == "sweetclaude"]
        trace.public_skills = sorted(s for s in event.get("skills") or [] if s.startswith("sweetclaude:"))
    elif kind == "system" and event.get("subtype") == "hook_response":
        output = event.get("output") or ""
        if "STOP" in output and "DO NOT invoke any SweetClaude skill" in output:
            trace.preflight_stop = output
    elif kind == "assistant":
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "text":
                trace.texts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                observe_tool(trace, block.get("name", ""), block.get("input") or {})
    elif kind == "result":
        trace.finished = True
        cost = event.get("total_cost_usd")
        if isinstance(cost, (int, float)):
            trace.cost_usd = float(cost)


def observe_tool(trace: Trace, name: str, payload: dict[str, Any]) -> None:
    if name == "Skill":
        trace.skills.append((payload.get("skill", ""), str(payload.get("args", ""))))
    elif name == "Read" and trace.workflow is None:
        path = payload.get("file_path", "")
        if match := WORKFLOW_READ.search(path):
            trace.workflow = (match.group(1), match.group(2))
        elif match := INDEX_READ.search(path):
            trace.index_reads.append(match.group(1))
    elif name == "AskUserQuestion" and trace.routing_started and trace.workflow is None:
        trace.asked = True


def parse(events: Iterable[dict[str, Any]]) -> Trace:
    trace = Trace()
    for event in events:
        observe(trace, event)
    if not trace.asked and trace.workflow is None and trace.routing_started and trace.texts and "?" in trace.texts[-1]:
        trace.asked = True
    return trace


def classify(case: dict[str, Any], trace: Trace, repo: str | None = None) -> tuple[str, str]:
    if trace.preflight_stop:
        return "harness-error", "SessionStart preflight told the model not to invoke SweetClaude skills; the fixture is invalid"
    if not trace.plugin_paths:
        return "harness-error", "sweetclaude plugin was not loaded"
    if repo and repo not in trace.plugin_paths:
        return "harness-error", f"sweetclaude plugin loaded from {trace.plugin_paths}, not {repo}"
    missing = PUBLIC - set(trace.public_skills)
    if missing:
        return "harness-error", f"Tier 1 commands missing from the catalog: {sorted(missing)}"
    exposed = set(trace.public_skills) - PUBLIC
    if exposed:
        return "harness-error", f"commands beyond Tier 1 are exposed in the catalog: {sorted(exposed)}"
    expected = case["category"]
    if trace.workflow:
        category, workflow = trace.workflow
        if category != expected:
            return "wrong-category", f"loaded {category}/{workflow}, expected {expected}"
        if workflow not in case["workflows"]:
            return "wrong-workflow", f"loaded {category}/{workflow}, expected one of {case['workflows']}"
        return "pass", f"loaded {category}/{workflow}"
    observed = trace.category
    if observed and observed != expected:
        return "wrong-category", f"routed to {observed} without loading a workflow, expected {expected}"
    if trace.asked:
        if case.get("clarify_ok"):
            return "pass-clarified", f"asked a clarifying question in {observed or 'an unselected category'}"
        return "clarified", f"asked instead of loading a workflow ({observed or 'no category selected'})"
    if not trace.finished:
        return "harness-error", "run ended before a workflow was loaded or a result was reported"
    return "no-route", f"no workflow loaded ({observed or 'no category selected'})"


def passed(status: str) -> bool:
    return status in {"pass", "pass-clarified"}


def prompt_for(case: dict[str, Any], entry: str) -> str:
    command = "go" if entry == "go" else case["category"]
    return f"/sweetclaude:{command} {case['prompt']}"


def make_project(root: Path) -> Path:
    project = root / "project"
    state = project / ".sweetclaude" / "state"
    state.mkdir(parents=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (state / "sweetclaude.yaml").write_text(FIXTURE_STATE.format(now=now), encoding="utf-8")
    (state / "last-doctor-run.json").write_text(json.dumps({"timestamp": now}), encoding="utf-8")
    (project / "README.md").write_text("# ShiftBoard\n\nStaff shift scheduling for small veterinary clinics.\n", encoding="utf-8")
    git = ["git", "-c", "user.email=routing-fixture@example.invalid", "-c", "user.name=Routing Fixture"]
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=project, check=True)
    subprocess.run([*git, "add", "."], cwd=project, check=True)
    subprocess.run([*git, "commit", "-qm", "fixture baseline"], cwd=project, check=True)
    digest = hashlib.md5(str(project.resolve()).encode()).hexdigest()
    Path(f"/tmp/.sweetclaude-bootstrap-ran-{digest}").write_text("", encoding="utf-8")
    return project


def preflight(project: Path, repo: Path = ROOT) -> str | None:
    hook = repo / "hooks" / "session-preflight.sh"
    proc = subprocess.run(["bash", str(hook)], cwd=project, input="{}", capture_output=True, text=True, timeout=60, env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)})
    output = proc.stdout
    if '"continue":false' in output.replace(" ", ""):
        return "preflight blocks session start"
    if "DO NOT invoke any SweetClaude skill" in output:
        reason = re.search(r"health check detected: ([^.]*)", output)
        return f"preflight rejects the fixture: {reason.group(1) if reason else 'unknown reason'}"
    return None


def preload_commands(repo: Path) -> list[str]:
    allowed = []
    for skill in sorted((repo / "skills").glob("*/SKILL.md")):
        for line in PRELOAD.findall(skill.read_text(encoding="utf-8")):
            allowed.append(f"Bash({line.replace('${CLAUDE_SKILL_DIR}', str(skill.parent))})")
    return allowed


def gate_commands(repo: Path) -> list[str]:
    return [f"Bash(python3 {repo}/scripts/gate_check.py:*)"]


def command(prompt_text: str, repo: Path, model: str, budget: float, executable: str = "claude") -> list[str]:
    return [
        executable, "-p", "--verbose",
        "--input-format", "stream-json", "--output-format", "stream-json",
        "--setting-sources", "project,local", "--strict-mcp-config", "--no-session-persistence",
        "--plugin-dir", str(repo), "--add-dir", str(repo),
        "--model", model, "--max-budget-usd", f"{budget:.2f}",
        "--permission-mode", "default",
        "--allowedTools", "Skill", "Read", "Glob", "Grep", *preload_commands(repo), *gate_commands(repo),
        "--disallowedTools", "Write", "Edit", "NotebookEdit",
    ]


def user_message(text: str) -> str:
    return json.dumps({"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": text}]}}) + "\n"


def interrupt_message() -> str:
    return json.dumps({"type": "control_request", "request_id": "routing-stop", "request": {"subtype": "interrupt"}}) + "\n"


def pump(stream: Any, lines: queue.Queue[str]) -> None:
    for line in stream:
        lines.put(line)
    lines.put("")


def run_case(case: dict[str, Any], entry: str, args: argparse.Namespace) -> dict[str, Any]:
    started = time.monotonic()
    events: list[dict[str, Any]] = []
    trace = Trace()
    with tempfile.TemporaryDirectory(prefix="sweetclaude-routing-") as tmp, tempfile.TemporaryFile("w+") as errors:
        project = make_project(Path(tmp))
        problem = preflight(project, args.repo)
        if problem:
            return record(case, entry, "harness-error", problem, None, events, started)
        proc = subprocess.Popen(command(prompt_for(case, entry), args.repo, args.model, args.case_budget, args.claude), cwd=project, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors, text=True, bufsize=1)
        assert proc.stdin and proc.stdout
        try:
            proc.stdin.write(user_message(prompt_for(case, entry)))
            proc.stdin.flush()
        except BrokenPipeError:
            pass
        lines: queue.Queue[str] = queue.Queue()
        threading.Thread(target=pump, args=(proc.stdout, lines), daemon=True).start()
        stopping = False
        deadline = started + args.timeout
        while time.monotonic() < deadline:
            try:
                line = lines.get(timeout=1.0)
            except queue.Empty:
                continue
            if not line:
                break
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            events.append(event)
            observe(trace, event)
            if trace.finished:
                break
            if not stopping and (trace.workflow or trace.preflight_stop):
                stopping = True
                deadline = min(deadline, time.monotonic() + args.stop_grace)
                try:
                    proc.stdin.write(interrupt_message())
                    proc.stdin.flush()
                except BrokenPipeError:
                    break
        try:
            proc.stdin.close()
        except BrokenPipeError:
            pass
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=10)
        errors.seek(0)
        stderr = errors.read()
    trace = parse(events)
    if not events:
        return record(case, entry, "harness-error", f"claude produced no events (exit {proc.returncode}): {stderr.strip()[:400]}", None, events, started)
    status, detail = classify(case, trace, str(args.repo))
    if status == "harness-error" and not trace.finished and time.monotonic() >= started + args.timeout:
        detail = f"timed out after {args.timeout}s; {detail}"
    return record(case, entry, status, detail, trace.cost_usd, events, started)


def record(case: dict[str, Any], entry: str, status: str, detail: str, cost: float | None, events: list[dict[str, Any]], started: float) -> dict[str, Any]:
    return {"case": case["id"], "entry": entry, "status": status, "passed": passed(status), "detail": detail, "cost_usd": cost, "seconds": round(time.monotonic() - started, 1), "trace": asdict(parse(events)) if events else None}


def select_runs(cases: list[dict[str, Any]], tier: str, entry: str | None, only: list[str]) -> list[tuple[dict[str, Any], str]]:
    entry = entry or "go"
    if only:
        chosen = [c for c in cases if c["id"] in only]
        unknown = set(only) - {c["id"] for c in chosen}
        if unknown:
            raise SystemExit(f"Unknown case ids: {sorted(unknown)}")
    elif tier == "smoke":
        chosen = [next(c for c in cases if c["category"] == cat) for cat in CATEGORIES]
    else:
        chosen = cases
    entries = {"go": ["go"], "category": ["category"], "both": ["go", "category"]}[entry]
    return [(case, e) for case in chosen for e in entries]


def summarise(results: list[dict[str, Any]], planned: int) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for row in results:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    graded = [r for r in results if r["status"] != "harness-error"]
    return {
        "planned": planned,
        "runs": len(results),
        "passed": sum(r["passed"] for r in results),
        "graded": len(graded),
        "statuses": counts,
        "cost_usd": round(sum(r["cost_usd"] or 0 for r in results), 4),
        "unpriced_runs": sum(r["cost_usd"] is None for r in results),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", choices=("smoke", "full"), default="smoke")
    parser.add_argument("--entry", choices=("go", "category", "both"))
    parser.add_argument("--only", nargs="*", default=[])
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--case-budget", type=float, default=0.25)
    parser.add_argument("--run-budget", type=float, default=5.0)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--stop-grace", type=float, default=20.0)
    parser.add_argument("--cases", type=Path, default=CASES)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--claude", default="claude")
    parser.add_argument("--out", type=Path, default=RESULTS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-diagnose", dest="diagnose", action="store_false", help="do not re-run go failures through the category command")
    args = parser.parse_args(argv)
    args.repo = args.repo.resolve()
    cases = load_cases(args.cases)
    errors = validate_cases(cases, args.repo / "skill-library")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 2
    runs = select_runs(cases, args.tier, args.entry, args.only) * args.repeat
    if args.dry_run:
        for case, entry in runs:
            print(f"{case['id']}\t{entry}\t{prompt_for(case, entry)}")
        print(f"{len(runs)} runs; worst case ${len(runs) * args.case_budget:.2f}, capped at ${args.run_budget:.2f}")
        return 0
    results: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    spent = 0.0
    pending = [(case, entry, results) for case, entry in runs]
    while pending:
        case, entry, sink = pending.pop(0)
        if spent + args.case_budget > args.run_budget:
            print(f"Stopping: run budget ${args.run_budget:.2f} would be exceeded (${spent:.2f} committed)", file=sys.stderr)
            break
        row = run_case(case, entry, args)
        sink.append(row)
        spent += row["cost_usd"] if row["cost_usd"] is not None else args.case_budget
        price = f"${row['cost_usd']:.3f}" if row["cost_usd"] is not None else "unpriced"
        label = entry if sink is results else f"{entry}*"
        print(f"{row['status']:<15} {case['id']:<28} {label:<9} {price:<9} {row['detail']}", flush=True)
        if sink is results and entry == "go" and args.diagnose and not row["passed"] and row["status"] != "harness-error":
            pending.insert(0, (case, "category", diagnostics))
    summary = summarise(results, len(runs))
    summary["diagnostics"] = {row["case"]: row["status"] for row in diagnostics}
    summary["cost_usd"] = round(summary["cost_usd"] + sum(r["cost_usd"] or 0 for r in diagnostics), 4)
    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = args.out / f"routing-{args.tier}-{stamp}.json"
    path.write_text(json.dumps({"executed_at": stamp, "model": args.model, "tier": args.tier, "summary": summary, "results": results, "diagnostics": diagnostics}, indent=2), encoding="utf-8")
    print(json.dumps(summary))
    print(f"Results: {path}")
    return 0 if summary["runs"] == summary["planned"] and summary["passed"] == summary["planned"] else 1


if __name__ == "__main__":
    sys.exit(main())
