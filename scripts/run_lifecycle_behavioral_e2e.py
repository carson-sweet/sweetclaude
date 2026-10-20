#!/usr/bin/env python3
"""Execute selected new-SaaS lifecycle behavioral cases and preserve observable evidence."""

from __future__ import annotations

import argparse
import json
import os
import select
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from behavioral_e2e import ROOT, base_environment, event_text, snapshot
from lifecycle_behavioral_e2e import FEATURE, LifecycleCase, compile_cases, parse_feature

PACKAGE = ROOT / "docs" / "testing" / "behavioral-e2e"
DEFAULT_CONFIG = PACKAGE / "lifecycle-standard.json"


def make_lifecycle_fixture(root: Path, case: LifecycleCase) -> tuple[Path, dict[str, str]]:
    project = root / "project"
    home = root / "home"
    config = root / "claude-config"
    project.mkdir(parents=True)
    home.mkdir()
    config.mkdir()
    (project / ".sweetclaude" / "state").mkdir(parents=True)
    (project / "src").mkdir()
    (project / "docs").mkdir()
    (project / "evidence").mkdir()
    (project / "src" / "app.py").write_text("def health():\n    return {'status': 'ok'}\n", encoding="utf-8")
    (project / "README.md").write_text("# New SaaS fixture\n", encoding="utf-8")
    (project / "docs" / "product.md").write_text("# Product\nTenant-scoped SaaS fixture.\n", encoding="utf-8")
    (project / ".sweetclaude" / "state" / "sweetclaude.yaml").write_text("schema_version: 2\nframework:\n  setup_complete: true\nproject:\n  name: New SaaS behavioral fixture\n  type: existing-code\n", encoding="utf-8")
    (project / ".sweetclaude" / "lifecycle-case.json").write_text(json.dumps({
        "story_id": case.story_id,
        "phase": case.phase,
        "title": case.title,
        "givens": case.givens,
        "expected_outcomes": case.expected_outcomes,
        "outcome_kind": case.outcome_kind,
    }, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.email", "behavioral-fixture@example.invalid"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "Behavioral Fixture"], cwd=project, check=True)
    subprocess.run(["git", "add", "."], cwd=project, check=True)
    subprocess.run(["git", "commit", "-qm", "lifecycle fixture baseline"], cwd=project, check=True)
    return project, {"HOME": str(home), "CLAUDE_CONFIG_DIR": str(config), "XDG_CONFIG_HOME": str(config), "XDG_CACHE_HOME": str(root / "cache")}


def event_cost(events: list[dict[str, Any]]) -> float:
    total = 0.0
    for event in events:
        val = _extract_cost(event)
        if isinstance(val, (int, float)):
            total += val
    return total


def _extract_cost(value: Any) -> float | None:
    if isinstance(value, dict):
        for name in ("cost_usd", "total_cost_usd"):
            v = value.get(name)
            if isinstance(v, (int, float)):
                return float(v)
        v = value.get("usage")
        if isinstance(v, dict):
            return _extract_cost(v)
    if isinstance(value, list):
        return sum(float(_extract_cost(item) or 0) for item in value)
    return None


def write_user(process: subprocess.Popen[str], text: str) -> None:
    assert process.stdin is not None
    process.stdin.write(json.dumps({"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": text}]}}) + "\n")
    process.stdin.flush()


def domain_only(root: dict[str, str]) -> dict[str, str]:
    result = {}
    for k, v in root.items():
        if k.startswith(".sweetclaude/state/"):
            continue
        if k.startswith(".sweetclaude/outputs/"):
            continue
        if k == "README.md" or k.startswith("src/") or k.startswith("docs/") or k.startswith("evidence/"):
            result[k] = v
    return result


def evaluate(case: LifecycleCase, events: list[dict[str, Any]], before: dict[str, str], after: dict[str, str], unscripted_questions: int) -> tuple[str, list[str]]:
    if not events:
        return "blocked-environment", ["Claude produced no observable stream events."]
    if unscripted_questions:
        return "driver-gap", [f"Claude requested {unscripted_questions} user decision(s) without a recorded reply for this case."]
    before_domain = domain_only(before)
    after_domain = domain_only(after)
    if case.outcome_kind == "failure" and before_domain != after_domain:
        return "fail-effect", ["Failure case mutated its fixture before the missing condition was resolved."]
    if case.outcome_kind == "happy" and not events:
        return "blocked-environment", ["Happy case produced no observable stream events."]
    response = event_text(events).strip()
    if not response:
        return "blocked-environment", ["Claude produced no observable response text."]
    return "pass", ["Observable stream completed without an unexpected decision request or forbidden failure-case mutation."]


def run_case(case: LifecycleCase, keep: bool, model: str, budget: float, shared_auth: bool, timeout_seconds: int) -> dict[str, Any]:
    root = Path(tempfile.mkdtemp(prefix=f"sweetclaude-{case.id.lower()}-"))
    project, isolated_env = make_lifecycle_fixture(root, case)
    before = snapshot(project)
    command = ["claude", "-p", "--verbose", "--input-format", "stream-json", "--output-format", "stream-json", "--setting-sources", "project,local", "--plugin-dir", str(ROOT), "--model", model, "--permission-mode", "bypassPermissions", "--dangerously-skip-permissions", "--max-budget-usd", str(budget)]
    events: list[dict[str, Any]] = []
    details: list[str] = []
    unscripted_questions = 0
    replies = list(case.decision_script)
    reply_index = 0
    try:
        process = subprocess.Popen(command, cwd=project, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, env=base_environment(isolated_env, shared_auth=shared_auth))
        assert process.stdout is not None
        write_user(process, case.prompt)
        deadline = time.monotonic() + timeout_seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                process.terminate()
                details.append(f"Claude stream timed out after {timeout_seconds} seconds.")
                break
            readable, _, _ = select.select([process.stdout], [], [], min(remaining, 0.25))
            if not readable:
                if process.poll() is not None:
                    break
                continue
            line = process.stdout.readline()
            if not line:
                break
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                events.append({"type": "unparseable", "raw": line})
                continue
            events.append(event)
            if "AskUserQuestion" in json.dumps(event):
                if reply_index < len(replies):
                    write_user(process, replies[reply_index])
                    reply_index += 1
                    if reply_index == len(replies) and process.stdin and not process.stdin.closed:
                        process.stdin.close()
                else:
                    unscripted_questions += 1
                    if process.stdin and not process.stdin.closed:
                        process.stdin.close()
        if process.stdin and not process.stdin.closed:
            process.stdin.close()
        process.wait(timeout=30)
        stderr = process.stderr.read() if process.stderr is not None else ""
        if process.returncode not in (0, None):
            details.append(stderr.strip() or f"Claude exited {process.returncode}")
    except (OSError, subprocess.SubprocessError) as exc:
        details.append(str(exc))
    after = snapshot(project)
    status, result_details = evaluate(case, events, before, after, unscripted_questions)
    details.extend(result_details)
    evidence = {"fixture": case.fixture, "root": str(root), "command": command, "auth_boundary": "shared-cli-home-for-auth" if shared_auth else "isolated-no-auth", "before": before, "after": after, "events": events}
    record = {"case": case.id, "story_id": case.story_id, "cluster": case.cluster, "status": status, "cost_usd": event_cost(events), "details": details, "evidence": evidence}
    if status == "pass" and not keep:
        shutil.rmtree(root)
        record["evidence"]["root"] = "cleaned"
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--include", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--story", action="append", default=[])
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--keep-fixtures", action="store_true")
    parser.add_argument("--shared-auth", action="store_true")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--case-timeout-seconds", type=int, default=180)
    parser.add_argument("--max-run-budget-usd", type=float, default=25.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        if not isinstance(config, dict) or set(config) - {"schema_version", "clusters"} or config.get("schema_version", 1) != 1:
            raise ValueError("Invalid lifecycle config schema or keys")
        configured = config.get("clusters", [])
        if not isinstance(configured, list) or any(not isinstance(value, str) for value in configured):
            raise ValueError("lifecycle config clusters must be a string list")
        clusters = args.include or configured
        clusters = [cluster for cluster in clusters if cluster not in set(args.exclude)]
        cases = compile_cases(parse_feature(FEATURE), clusters)
        if args.story:
            wanted = set(args.story)
            cases = [case for case in cases if case.story_id in wanted]
            unknown = wanted - {case.story_id for case in compile_cases(parse_feature(FEATURE), clusters)}
            if unknown:
                raise ValueError(f"Unknown or unselected lifecycle story: {', '.join(sorted(unknown))}")
        if not cases:
            raise ValueError("Lifecycle selection produces no cases")
        report: dict[str, Any] = {"schema_version": 1, "status": "compiled-not-executed", "feature": str(FEATURE.relative_to(ROOT)), "selected_clusters": sorted({case.cluster for case in cases}), "case_count": len(cases), "cases": [{"id": case.id, "story_id": case.story_id, "cluster": case.cluster, "prompt": case.prompt, "expected_outcomes": case.expected_outcomes, "outcome_kind": case.outcome_kind, "decision_script": case.decision_script} for case in cases]}
        if args.execute:
            if args.max_run_budget_usd <= 0 or args.case_timeout_seconds <= 0:
                raise ValueError("run budget and case timeout must be positive")
            results = []
            running_cost = 0.0
            for index, case in enumerate(cases, start=1):
                remaining = args.max_run_budget_usd - running_cost
                if remaining <= 0:
                    print(f"STOP {index}/{len(cases)}: run budget ${args.max_run_budget_usd:.2f} exhausted; running total ${running_cost:.4f}", flush=True)
                    break
                result = run_case(case, args.keep_fixtures, args.model, remaining, args.shared_auth, args.case_timeout_seconds)
                running_cost += result["cost_usd"]
                result["running_total_cost_usd"] = running_cost
                results.append(result)
                if args.output:
                    checkpoint = {**report, "status": "running", "results": results, "cost_usd": running_cost}
                    args.output.with_suffix(args.output.suffix + ".partial.json").write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                print(f"CASE {index}/{len(cases)} {case.id}: {result['status']}; cost ${result['cost_usd']:.4f}; running total ${running_cost:.4f}", flush=True)
            report.update({"status": "executed" if len(results) == len(cases) else "budget-stopped", "executed_at": datetime.now(timezone.utc).isoformat(), "results": results, "cost_usd": running_cost})
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            if args.output.exists():
                raise ValueError(f"Output already exists: {args.output}")
            args.output.write_text(rendered, encoding="utf-8")
            partial = args.output.with_suffix(args.output.suffix + ".partial.json")
            if partial.exists():
                partial.unlink()
        else:
            print(rendered)
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(f"Lifecycle behavioral E2E error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
