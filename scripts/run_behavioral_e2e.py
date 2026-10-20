#!/usr/bin/env python3
"""Compile selected behavioral cases and, with --execute, run them through Claude stream-json."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import select
import time
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from behavioral_e2e import PACKAGE, ROOT, base_environment, expand_plan, make_fixture, manifest, read_json, route_result, snapshot

SPEC = importlib.util.spec_from_file_location("behavioral_selection", ROOT / "scripts" / "select_behavioral_clusters.py")
selection = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(selection)


def selected_plan(args: argparse.Namespace) -> dict[str, Any]:
    catalog = read_json(args.catalog)
    inventory = read_json(args.inventory)
    if hashlib.sha256(args.inventory.read_bytes()).hexdigest() != catalog.get("inventory_sha256"):
        raise ValueError("Catalog does not match this inventory snapshot; reconcile cluster membership first.")
    config = read_json(args.config) if args.config else {}
    unknown = set(config) - {"schema_version", "preset", "enable", "disable", "switches", "operation", "exclude_operation"}
    if unknown or config.get("schema_version", 1) != 1:
        raise ValueError(f"Invalid selection config schema or keys: {sorted(unknown)}")
    enabled = selection.strings(config.get("enable", []), "enable") + args.include
    disabled = selection.strings(config.get("disable", []), "disable") + args.exclude
    configured_operations = selection.strings(config.get("operation", []), "operation")
    configured_exclusions = selection.strings(config.get("exclude_operation", []), "exclude_operation")
    switches = config.get("switches", {})
    if not isinstance(switches, dict) or any(not isinstance(name, str) or not isinstance(value, bool) for name, value in switches.items()):
        raise ValueError("switches must map cluster-name strings to true/false")
    enabled += [name for name, value in switches.items() if value]
    disabled += [name for name, value in switches.items() if not value]
    preset = args.preset if args.preset is not None else config.get("preset")
    chosen, included, excluded = selection.resolve_selection(catalog, preset, enabled, disabled)
    return selection.plan_selection(inventory, catalog, chosen, included, excluded, configured_operations + args.operation, configured_exclusions + args.exclude_operation)


def event_cost(events: list[dict[str, Any]]) -> float:
    values: list[float] = []
    for event in events:
        for name in ("total_cost_usd", "cost_usd"):
            value = event.get(name)
            if isinstance(value, (int, float)):
                values.append(float(value))
    return max(values, default=0.0)


def run_case(case: Any, keep: bool, model: str, budget: float, shared_auth: bool = False, timeout_seconds: int = 180) -> dict[str, Any]:
    root = Path(tempfile.mkdtemp(prefix=f"sweetclaude-{case.id.lower()}-"))
    project, isolated_env = make_fixture(root, case.fixture)
    before = snapshot(project)
    command = ["claude", "-p", "--verbose", "--input-format", "stream-json", "--output-format", "stream-json", "--setting-sources", "project,local", "--plugin-dir", str(ROOT), "--model", model, "--permission-mode", "bypassPermissions", "--dangerously-skip-permissions", "--max-budget-usd", str(budget)]
    events: list[dict[str, Any]] = []
    status = "blocked-environment"
    details: list[str] = []
    try:
        process = subprocess.Popen(command, cwd=project, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, env=base_environment(isolated_env, shared_auth=shared_auth))
        assert process.stdin and process.stdout
        process.stdin.write(json.dumps({"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": case.prompt}]}}) + "\n")
        process.stdin.flush()
        for reply in case.responses:
            process.stdin.write(json.dumps({"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": reply}]}}) + "\n")
        process.stdin.flush()
        process.stdin.close()
        replies = iter(())
        deadline = time.monotonic() + timeout_seconds
        while True:
            wait = deadline - time.monotonic()
            if wait <= 0:
                process.terminate()
                details.append(f"Claude stream timed out after {timeout_seconds} seconds.")
                break
            readable, _, _ = select.select([process.stdout], [], [], min(wait, 1.0))
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
                details.append("The case requested an unplanned user decision after scripted replies were supplied.")
        stdout, stderr = process.communicate(timeout=30) if process.stdin and not process.stdin.closed else (process.stdout.read(), process.stderr.read())
        process.wait(timeout=30)
        if stdout:
            details.append("Claude emitted output after stream closure.")
        if process.returncode not in (0, None):
            details.append(stderr.strip() or f"Claude exited {process.returncode}")
        elif not details:
            status, details = route_result(case, events)
    except (OSError, subprocess.SubprocessError) as exc:
        details.append(str(exc))
    after = snapshot(project)
    if case.layer == "routing" and before != after:
        status = "fail-effect"
        details.append("Routing case mutated its fixture.")
    evidence = {"fixture": case.fixture, "root": str(root), "command": command, "auth_boundary": "shared-cli-home-for-auth" if shared_auth else "isolated-no-auth", "before": before, "after": after, "events": events}
    if status == "blocked-environment" and not details:
        details.append("No terminal result from Claude.")
    record = {"case": case.id, "operation_id": case.operation_id, "status": status, "cost_usd": event_cost(events), "details": details, "evidence": evidence}
    if status == "pass" and not keep:
        shutil.rmtree(root)
        record["evidence"]["root"] = "cleaned"
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=PACKAGE / "clusters.json")
    parser.add_argument("--inventory", type=Path, default=PACKAGE / "inventory.json")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--preset")
    parser.add_argument("--include", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--operation", action="append", default=[])
    parser.add_argument("--exclude-operation", action="append", default=[])
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--keep-fixtures", action="store_true")
    parser.add_argument("--repeat", type=int, default=1, help="Independent executions of each selected case.")
    parser.add_argument("--shared-auth", action="store_true", help="Use the logged-in Claude account only for authentication; fixture settings remain isolated.")
    parser.add_argument("--case-timeout-seconds", type=int, default=180)
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--max-run-budget-usd", type=float, default=25.0, help="Maximum API cost for the entire test run.")
    parser.add_argument("--allow-incomplete", action="store_true", help="Allow execution when the manifest has unimplemented obligations; results remain incomplete.")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        plan = selected_plan(args)
        cases = expand_plan(plan, read_json(args.inventory))
        report = manifest(cases, plan)
        if args.repeat <= 0 or args.case_timeout_seconds <= 0:
            raise ValueError("repeat and case timeout must be positive")
        report["repeat"] = args.repeat
        report["attempt_count"] = len(cases) * args.repeat
        if args.execute:
            if args.max_run_budget_usd <= 0:
                raise ValueError("--max-run-budget-usd must be positive")
            if report["unimplemented_obligations"] and not args.allow_incomplete:
                raise ValueError(f"Selection has {len(report['unimplemented_obligations'])} unimplemented obligations; implement them or use --allow-incomplete for a partial run.")
            results = []
            running_cost = 0.0
            attempts = [(attempt, case) for attempt in range(1, args.repeat + 1) for case in cases]
            for index, (attempt, case) in enumerate(attempts, start=1):
                remaining_budget = args.max_run_budget_usd - running_cost
                if remaining_budget <= 0:
                    print(f"STOP {index}/{len(attempts)}: run budget ${args.max_run_budget_usd:.2f} exhausted; running total ${running_cost:.4f}", flush=True)
                    break
                result = run_case(case, args.keep_fixtures, args.model, remaining_budget, shared_auth=args.shared_auth, timeout_seconds=args.case_timeout_seconds)
                running_cost += result["cost_usd"]
                result["attempt"] = attempt
                result["running_total_cost_usd"] = running_cost
                results.append(result)
                if args.output:
                    checkpoint = {**report, "status": "running", "results": results, "cost_usd": running_cost}
                    args.output.with_suffix(args.output.suffix + ".partial.json").write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                print(f"CASE {index}/{len(attempts)} attempt {attempt} {case.id}: {result['status']}; cost ${result['cost_usd']:.4f}; running total ${running_cost:.4f}", flush=True)
            counts = {name: sum(row["status"] == name for row in results) for name in ("pass", "fail-routing", "fail-effect", "blocked-environment", "oracle-gap")}
            report.update({"status": "executed" if len(results) == len(attempts) else "budget-stopped", "executed_at": datetime.now(timezone.utc).isoformat(), "results": results, "cost_usd": running_cost, "coverage": {"required": len(attempts), "executed": len(results), "passed": counts["pass"], "failed": counts["fail-routing"] + counts["fail-effect"], "blocked": counts["blocked-environment"], "oracle_gap": counts["oracle-gap"], "not_run": len(attempts) - len(results), "unimplemented": len(report["unimplemented_obligations"])}})
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
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Behavioral E2E error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
