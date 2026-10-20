#!/usr/bin/env python3
"""Run live, model-backed acceptance checks against the current checkout.

This intentionally is not part of pytest: it calls Claude Code and incurs API
usage. It uses an isolated temporary Git project, project/local settings only,
and this checkout passed through ``--plugin-dir``. Its transcript report is
the evidence; a nonzero exit means a required behavioral assertion failed.

Usage:
    python3 scripts/run_live_tiered_behavior.py
    python3 scripts/run_live_tiered_behavior.py --keep
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Scenario:
    name: str
    prompt: str
    required: tuple[str, ...]
    forbidden: tuple[str, ...] = ()


ROUTING_SCENARIOS = (
    Scenario("plan-product-brief", "/sweetclaude:plan We need a product brief for a catalog that helps independent bookstores manage event inventory. State the selected Tier 2 workflow and category before acting; do not write files.", ("executive summary", "audience")),
    Scenario("design-architecture", "/sweetclaude:design We need an architecture for a small API that synchronizes bookstore event inventory. State the selected Tier 2 workflow and category before acting; do not write files.", ("design-architecture", "design")),
    Scenario("build-code-review", "/sweetclaude:build Review the existing Python service for correctness and security. State the selected Tier 2 workflow and category before acting; do not write files.", ("code review", "security review")),
    Scenario("maintain-incident", "/sweetclaude:maintain Production is returning 500 errors after an inventory import. State the selected Tier 2 workflow and category before acting; do not write files.", ("triage questions", "rollback")),
    Scenario("configure-diagnostics", "/sweetclaude:configure Diagnose this SweetClaude installation. State the selected Tier 2 workflow and category before acting; do not write files.", ("doctor", "configure")),
    Scenario("utils-meeting", "/sweetclaude:utils Prepare an agenda for a 30-minute inventory-launch planning meeting. State the selected Tier 2 workflow and category before acting; do not write files.", ("agenda", "meeting")),
    # The Go dispatcher delegates to the same secondary workflow. The review
    # itself names that workflow "Security Review", rather than echoing its
    # internal directory name, so assert the delivered behaviour.
    Scenario("go-natural-language", "/sweetclaude:go We need to review this codebase for security issues. State the selected Tier 2 workflow and category before acting; do not write files.", ("security review",)),
)


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=180)


def _create_project(root: Path) -> Path:
    project = root / "faux-bookstore"
    project.mkdir()
    _run(["git", "init", "-q"], project).check_returncode()
    state = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
    state.parent.mkdir(parents=True)
    _run([
        sys.executable, str(REPO_ROOT / "scripts" / "sweetclaude-yaml-template.py"),
        "--name", "Faux Bookstore", "--type", "existing-code",
        "--issue-tracker", "local", "--output", str(state),
    ], project).check_returncode()
    (project / ".sweetclaude" / "artifact-privacy.yaml").write_text(
        yaml.safe_dump({"categories": {"product": {"base_path": ".sweetclaude/product"}}}),
        encoding="utf-8",
    )
    (project / ".sweetclaude" / "product" / "backlog").mkdir(parents=True)
    (project / "inventory.py").write_text("def import_inventory(rows):\n    return len(rows)\n", encoding="utf-8")
    return project


def _ask(project: Path, prompt: str) -> dict:
    command = [
        "claude", "-p", "--no-session-persistence", "--setting-sources", "project,local",
        "--plugin-dir", str(REPO_ROOT), "--model", "sonnet",
        "--permission-mode", "bypassPermissions", "--dangerously-skip-permissions",
        "--max-budget-usd", "1.50", "--output-format", "json", prompt,
    ]
    completed = _run(command, project)
    if completed.returncode != 0:
        raise RuntimeError(f"Claude Code failed: {completed.stderr.strip() or completed.stdout.strip()}")
    result = json.loads(completed.stdout)
    if result.get("is_error"):
        raise RuntimeError(result.get("result", "Claude Code returned an error"))
    return result


def _assert_contains(name: str, text: str, required: tuple[str, ...], forbidden: tuple[str, ...] = ()) -> None:
    folded = text.casefold()
    absent = [token for token in required if token.casefold() not in folded]
    present = [token for token in forbidden if token.casefold() in folded]
    if absent or present:
        raise AssertionError(f"{name}: absent={absent!r}, forbidden-present={present!r}\n{text}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true", help="Keep the faux project and transcript report.")
    parser.add_argument("--complete-e2e", action="store_true", help="Exercise real write paths, including a disposable private GitHub repository.")
    parser.add_argument(
        "--cost-record-dir",
        type=Path,
        default=REPO_ROOT / ".sweetclaude" / "live-behavioral-costs",
        help="Durable local directory for JSON cost receipts (default: .sweetclaude/live-behavioral-costs).",
    )
    args = parser.parse_args()

    root = Path(tempfile.mkdtemp(prefix="sweetclaude-live-tiered-"))
    report: list[dict] = []
    total_cost_usd = 0.0
    succeeded = False
    github_repo: str | None = None
    try:
        project = _create_project(root)
        inventory_before = (project / "inventory.py").read_bytes()
        def record(name: str, result: dict, status: str, detail: str | None = None) -> None:
            nonlocal total_cost_usd
            cost = float(result.get("total_cost_usd") or 0.0)
            total_cost_usd += cost
            report.append({"scenario": name, "status": status, "detail": detail,
                           "response": result["result"], "cost_usd": cost,
                           "running_total_cost_usd": total_cost_usd})
            print(f"COST {name}: ${cost:.4f} (running total: ${total_cost_usd:.4f})", flush=True)

        for scenario in ROUTING_SCENARIOS:
            result = _ask(project, scenario.prompt)
            text = result["result"]
            try:
                _assert_contains(scenario.name, text, scenario.required, scenario.forbidden)
                status, detail = "passed", None
            except AssertionError as exc:
                status, detail = "failed", str(exc)
            record(scenario.name, result, status, detail)

        assert (project / "inventory.py").read_bytes() == inventory_before, (
            "a read-only routing scenario changed the faux project's source file"
        )

        # Error path 1: GitHub is requested but neither auth nor an origin is
        # provisioned in this isolated repository. The model must stop instead
        # of silently falling back to local files or mutating the tracker.
        github = _ask(project, "/sweetclaude:build Use GitHub for this project's issues. Do not bypass missing GitHub authentication or origin.")
        state = yaml.safe_load((project / ".sweetclaude" / "state" / "sweetclaude.yaml").read_text(encoding="utf-8"))
        try:
            _assert_contains(
                "github-unavailable", github["result"],
                ("github", "origin", "tracker"),
                ("switched to github",),
            )
            assert state["project"]["issue_tracker"] == "local", state
            status, detail = "passed", None
        except AssertionError as exc:
            status, detail = "failed", str(exc)
        record("github-unavailable", github, status, detail)

        # Error path 2: an invalid persisted tracker must fail closed.
        state["project"]["issue_tracker"] = "not-a-tracker"
        state_path = project / ".sweetclaude" / "state" / "sweetclaude.yaml"
        state_path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")
        invalid = _ask(project, "/sweetclaude:build List this project's issues. Do not repair configuration automatically.")
        try:
            _assert_contains("invalid-tracker", invalid["result"], ("invalid", "not-a-tracker"))
            status, detail = "passed", None
        except AssertionError as exc:
            status, detail = "failed", str(exc)
        record("invalid-tracker", invalid, status, detail)

        if args.complete_e2e:
            # Make a disposable remote only after all fail-closed checks.
            state["project"]["issue_tracker"] = "local"
            state_path.write_text(yaml.safe_dump(state, sort_keys=False), encoding="utf-8")
            for command in (("git", "config", "user.email", "sweetclaude-e2e@example.invalid"),
                            ("git", "config", "user.name", "SweetClaude E2E"),
                            ("git", "add", "."), ("git", "commit", "-qm", "e2e fixture")):
                _run(list(command), project).check_returncode()
            github_repo = f"carson-sweet/sweetclaude-e2e-{uuid.uuid4().hex[:10]}"
            _run(["gh", "repo", "create", github_repo, "--private", "--source", ".", "--remote", "origin", "--push"], project).check_returncode()

            switch = _ask(project, "/sweetclaude:build Use GitHub for this project's issues. Verify auth and origin, then change only the tracker setting.")
            state = yaml.safe_load(state_path.read_text(encoding="utf-8"))
            status, detail = ("passed", None) if state["project"]["issue_tracker"] == "github" else ("failed", str(state))
            record("github-tracker-switch", switch, status, detail)

            issue = _ask(project, "/sweetclaude:build Create a GitHub issue titled 'Validate inventory imports' with acceptance criteria that invalid rows are rejected and accepted rows are counted. Do not implement it.")
            issue_list = _run(["gh", "issue", "list", "--repo", github_repo, "--state", "open", "--json", "number,title"], project)
            issues = json.loads(issue_list.stdout)
            status, detail = ("passed", None) if any(i["title"] == "Validate inventory imports" for i in issues) else ("failed", issue_list.stdout)
            record("github-issue-create", issue, status, detail)

            brief = _ask(project, "/sweetclaude:plan Write a product brief for bookstore event inventory. Persist the brief and its state artifacts.")
            status, detail = ("passed", None) if (project / ".sweetclaude" / "state" / "brief.yaml").is_file() else ("failed", "brief.yaml missing")
            record("product-brief-write", brief, status, detail)

            implement = _ask(project, "/sweetclaude:build Implement GitHub issue #1. Add tests, run them, and commit the implementation.")
            tests = _run([sys.executable, "-m", "unittest", "-v"], project)
            committed = _run(["git", "log", "-1", "--format=%s"], project)
            status, detail = ("passed", None) if tests.returncode == 0 and "e2e fixture" not in committed.stdout else ("failed", tests.stdout + tests.stderr)
            record("implementation-test-commit", implement, status, detail)

        output = root / "live-tiered-behavior-report.json"
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        args.cost_record_dir.mkdir(parents=True, exist_ok=True)
        receipt = args.cost_record_dir / f"live-tiered-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        receipt.write_text(json.dumps({"schema_version": 1, "total_cost_usd": total_cost_usd,
                                       "scenario_count": len(report), "scenarios": report}, indent=2) + "\n", encoding="utf-8")
        failures = [row for row in report if row["status"] != "passed"]
        print(f"{'PASS' if not failures else 'FAIL'}: {len(report) - len(failures)}/{len(report)} live behavioral scenarios")
        print(f"Report: {output}")
        print(f"Cost receipt: {receipt}")
        print(f"TOTAL COST: ${total_cost_usd:.4f}")
        if failures:
            return 1
        succeeded = True
        return 0
    except Exception as exc:
        (root / "live-tiered-behavior-failure.txt").write_text(str(exc), encoding="utf-8")
        print(f"FAIL: {exc}", file=sys.stderr)
        print(f"Evidence retained: {root}", file=sys.stderr)
        return 1
    finally:
        if github_repo:
            cleanup = _run(["gh", "repo", "delete", github_repo, "--yes"], root)
            if cleanup.returncode:
                print(f"CLEANUP FAILED for {github_repo}: {cleanup.stderr}", file=sys.stderr)
            else:
                print(f"CLEANUP PASS: deleted {github_repo}")
        if succeeded and not args.keep:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
