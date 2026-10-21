"""CI workflow contracts (ISSUE-236): pytest runs on pull requests.

The repo's only prior workflow was tag-triggered and ran no tests, so
regressions surfaced only at local full-suite runs (ISSUE-233 Cluster A went
undetected from 2026-06-21 to 2026-07-13). These tests pin the PR-time gate.
"""
import re
from pathlib import Path

import yaml

WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "test.yml"


def _load():
    assert WORKFLOW.is_file(), "PR test workflow .github/workflows/test.yml missing"
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_workflow_triggers_on_prs_to_release_branches():
    data = _load()
    on = data.get("on") or data.get(True)
    assert on, "workflow must declare triggers"
    pr = on.get("pull_request")
    assert pr is not None, "workflow must trigger on pull_request"
    branches = pr.get("branches", [])
    assert "main" in branches
    assert "beta-4.x" not in branches, "beta channel is retired (ISSUE-241)"


def test_workflow_runs_pytest_over_tests_dir():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert re.search(r"pytest\s+tests/", text), (
        "workflow must run pytest over tests/"
    )


def test_workflow_installs_playwright_browsers():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "playwright install" in text, (
        "the UI suite needs chromium — install it, never silently skip"
    )


def test_workflow_actions_are_sha_pinned():
    text = WORKFLOW.read_text(encoding="utf-8")
    uses = re.findall(r"uses:\s*(\S+)", text)
    assert uses, "workflow must use at least checkout"
    for ref in uses:
        assert re.match(r"^[\w./-]+@[0-9a-f]{40}$", ref), (
            f"action not SHA-pinned: {ref}"
        )


def test_workflow_permissions_least_privilege():
    data = _load()
    perms = data.get("permissions")
    assert perms == {"contents": "read"}, (
        "top-level permissions must be contents: read only"
    )


def test_workflow_pins_python_311():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert re.search(r"python-version:\s*['\"]?3\.11", text), (
        "CI must match local dev Python 3.11"
    )


def test_workflow_runs_ruff_lint():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert re.search(r"ruff check", text), (
        "workflow must run the ruff lint gate before the suite"
    )


def test_requirements_dev_pins_ruff():
    reqs = (Path(__file__).parents[1] / "requirements-dev.txt").read_text(encoding="utf-8")
    assert re.search(r"^ruff==\d", reqs, re.MULTILINE), (
        "requirements-dev.txt must pin ruff so CI and local runs match"
    )
