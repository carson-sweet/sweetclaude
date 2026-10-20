#!/usr/bin/env python3
"""Build the concrete non-base behavioral obligation registry."""

from __future__ import annotations

import hashlib
from typing import Any


def obligation_id(subject: str, kind: str) -> str:
    digest = hashlib.sha256(f"{subject}|{kind}".encode()).hexdigest()[:12]
    return f"OB-{digest}"


def fixture_requirements(kind: str, layers: list[str]) -> list[str]:
    if kind == "branch":
        return ["F02 happy baseline", "F05 changed fault fixture"]
    if kind == "profile":
        return ["profile-specific fixture selected from F00-F17"]
    if kind == "hook":
        return ["registered hook event fixture", "owned hook input and output paths"]
    if kind == "capability":
        return ["capability preconditions and owned external substitute"]
    return ["multi-turn journey fixture and frozen participant replies"]


def oracle_requirements(kind: str) -> list[str]:
    common = ["ordered tool and hook transcript", "pre/post owned-resource snapshot", "truthful final response"]
    if kind == "branch":
        return ["route", "process", "effect", "communication", *common]
    if kind == "profile":
        return ["profile-specific route/process/effect oracle", *common]
    if kind == "hook":
        return ["registered event invocation", "hook decision and side-effect oracle", *common]
    if kind == "capability":
        return ["precondition", "approval", "postcondition and rollback oracle", *common]
    return ["multi-turn route/process/effect/communication oracle", *common]


def build(plan: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in plan["operation_plans"]:
        for kind, detail in (("branch", item["branch_obligations"]), ("profile", ", ".join(item["profiles_to_resolve"]))):
            rows.append({
                "id": obligation_id(item["operation_id"], kind),
                "subject": item["operation_id"],
                "workflow": item["workflow"],
                "kind": kind,
                "layers": item["layers"],
                "entry_variants": item["variants"],
                "detail": detail,
                "fixture_requirements": fixture_requirements(kind, item["layers"]),
                "oracle_requirements": oracle_requirements(kind),
                "status": "specified-not-implemented",
            })
    for item in plan["auxiliary_plans"]:
        kind = item["type"]
        rows.append({
            "id": obligation_id(item["subject"], kind),
            "subject": item["subject"],
            "reference": item["reference"],
            "kind": kind,
            "layers": item["layers"],
            "entry_variants": item["entries_to_expand"],
            "wording": item["wording_to_expand"],
            "profiles": item["profiles_to_resolve"],
            "fixture_requirements": fixture_requirements(kind, item["layers"]),
            "oracle_requirements": oracle_requirements(kind),
            "status": "specified-not-implemented",
        })
    return sorted(rows, key=lambda row: row["id"])
