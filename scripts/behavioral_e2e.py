#!/usr/bin/env python3
"""Compile and execute isolated SweetClaude behavioral E2E cases."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from behavioral_obligations import build as build_obligations

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs" / "testing" / "behavioral-e2e"
RESULT_STATES = frozenset({"pass", "fail-routing", "fail-process", "fail-effect", "fail-claim", "blocked-environment", "oracle-gap", "not-run", "unimplemented"})


@dataclass(frozen=True)
class Case:
    id: str
    operation_id: str
    workflow: str
    layer: str
    kind: str
    entry: str
    wording: str
    prompt: str
    fixture: str
    expected: str
    source_obligations: tuple[str, ...]
    routing_edge_ids: tuple[str, ...]
    profiles_to_resolve: tuple[str, ...]
    responses: tuple[str, ...] = ()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected object: {path}")
    return value


def unique(values: list[str]) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


def operation_index(inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {operation["id"]: operation for operation in inventory["operations"]}


def fixture_for(workflow: str, kind: str) -> str:
    if kind == "failure":
        return "F05"
    if workflow.startswith("top/"):
        return "F02"
    return "F07"


def literal_prompt(workflow: str) -> str:
    command = workflow.removeprefix("top/")
    return f"/sweetclaude:{command}"


def expand_plan(plan: dict[str, Any], inventory: dict[str, Any]) -> list[Case]:
    indexed = operation_index(inventory)
    cases: list[Case] = []
    edge_by_owner: dict[str, list[str]] = {}
    for edge in inventory["skill_edges"]:
        edge_by_owner.setdefault(edge["owner"], []).append(edge["id"])
    anchors_by_owner: dict[str, list[str]] = {}
    for anchor in inventory["source_decisions"]:
        anchors_by_owner.setdefault(anchor["owner"], []).append(anchor["id"])
    for item in plan["operation_plans"]:
        operation = indexed[item["operation_id"]]
        for layer in item["layers"]:
            for kind in item["kinds"]:
                for variant in item["variants"]:
                    if variant["entry"] == "literal":
                        prompt = literal_prompt(item["workflow"])
                    else:
                        prompt = operation[variant["wording"]]
                        if variant["entry"] in {"category", "command", "go"}:
                            command = (item["workflow"].split("/", 1)[0] if variant["entry"] == "category" else item["workflow"].split("/")[-1])
                            if variant["entry"] == "go":
                                command = "go"
                            prompt = f"/sweetclaude:{command} {prompt}"
                    digest = hashlib.sha256(f"{item['operation_id']}|{layer}|{kind}|{variant['id']}".encode()).hexdigest()[:12]
                    cases.append(Case(
                        id=f"BE-{digest}", operation_id=item["operation_id"], workflow=item["workflow"],
                        layer=layer, kind=kind, entry=variant["entry"], wording=variant["wording"], prompt=prompt,
                        fixture=fixture_for(item["workflow"], kind),
                        expected=operation["expected"] if kind == "happy" else operation["failure"],
                        source_obligations=unique(anchors_by_owner.get(item["workflow"], [])),
                        routing_edge_ids=unique(edge_by_owner.get(item["workflow"], [])),
                        profiles_to_resolve=tuple(item["profiles_to_resolve"]),
                        responses=("It is a live production issue, not a security vulnerability. Use the fixture repository.",) if item["operation_id"] == "top.go.request" else (),
                    ))
    return sorted(cases, key=lambda case: case.id)


def manifest(cases: list[Case], plan: dict[str, Any]) -> dict[str, Any]:
    obligations = build_obligations(plan)
    return {
        "schema_version": 1,
        "status": "compiled-not-executed",
        "inventory_sha256": plan["inventory_sha256"],
        "enabled_clusters": plan["enabled_clusters"],
        "resolved_facets": plan["resolved_facets"],
        "case_count": len(cases),
        "cases": [asdict(case) for case in cases],
        "obligations": obligations,
        "unimplemented_obligations": [row for row in obligations if row["status"] != "implemented"],
        "coverage": {"required": len(cases), "specified": len(obligations), "executed": 0, "passed": 0, "failed": 0, "blocked": 0, "oracle_gap": 0, "not_run": len(cases), "unimplemented": len(obligations)},
    }


def make_fixture(root: Path, fixture: str) -> tuple[Path, dict[str, str]]:
    project = root / "project"
    home = root / "home"
    config = root / "claude-config"
    project.mkdir(parents=True)
    home.mkdir()
    config.mkdir()
    (project / ".sweetclaude" / "state").mkdir(parents=True)
    if fixture in {"F02", "F07"}:
        (project / "app.py").write_text("def value():\n    return 1\n", encoding="utf-8")
        (project / "README.md").write_text("Fixture project\n", encoding="utf-8")
        (project / ".sweetclaude" / "state" / "sweetclaude.yaml").write_text("schema_version: 2\nframework:\n  setup_complete: true\nproject:\n  name: Behavioral fixture\n  type: existing-code\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)
        subprocess.run(["git", "config", "user.email", "behavioral-fixture@example.invalid"], cwd=project, check=True)
        subprocess.run(["git", "config", "user.name", "Behavioral Fixture"], cwd=project, check=True)
        subprocess.run(["git", "add", "."], cwd=project, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture baseline"], cwd=project, check=True)
    elif fixture == "F05":
        (project / ".sweetclaude" / "state" / "sweetclaude.yaml").write_text("[malformed", encoding="utf-8")
    env = {"HOME": str(home), "CLAUDE_CONFIG_DIR": str(config), "XDG_CONFIG_HOME": str(config), "XDG_CACHE_HOME": str(root / "cache")}
    return project, env


def snapshot(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def event_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(event_text(item) for item in value)
    if isinstance(value, dict):
        return "\n".join(event_text(item) for item in value.values())
    return ""


def route_result(case: Case, events: list[dict[str, Any]]) -> tuple[str, list[str]]:
    transcript = event_text(events)
    missing = [path for path in (case.workflow and [case.workflow] or []) if path not in transcript]
    source = f"skills/{case.workflow.split('/', 1)[1]}/SKILL.md" if case.workflow.startswith("top/") else ""
    if source and source not in transcript:
        missing.append(source)
    if missing:
        return "oracle-gap", [f"No observable source-routing trace for: {', '.join(missing)}. The response may still be semantically plausible; do not classify this as a product routing failure."]
    return "pass", []


def base_environment(extra: dict[str, str], shared_auth: bool = False) -> dict[str, str]:
    env = os.environ.copy()
    env.update(extra)
    if shared_auth:
        env["HOME"] = os.environ["HOME"]
        if "CLAUDE_CONFIG_DIR" in os.environ:
            env["CLAUDE_CONFIG_DIR"] = os.environ["CLAUDE_CONFIG_DIR"]
        else:
            env.pop("CLAUDE_CONFIG_DIR", None)
        for name in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME"):
            if name in os.environ:
                env[name] = os.environ[name]
            else:
                env.pop(name, None)
    return env
