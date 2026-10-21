#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Report which protections cannot run, and why.

Three protections turned out to be switched off with no signal at all — the
work-in-progress limit, the phase-dwelling guard, and test-file immutability.
Each disabled itself because the state it needed was unreadable, allowed
whatever was happening, and said nothing. Allowing looked identical to
approving.

The specific causes are fixed. This exists so the next one is visible on the
day it happens rather than months later.

Checking at session start rather than plumbing a notice through every hook is
deliberate. There are 122 early-exit paths across the hooks; instrumenting each
would be fragile and easy to forget in a new one. A single check that asks
"could this protection run right now?" catches a newly broken protection
whether or not anyone remembered to instrument it, and reports before the
protection is needed instead of after it silently skipped.

Usage:
    python3 scripts/protection_status.py --project-dir .
    python3 scripts/protection_status.py --project-dir . --format json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ACTIVE = "active"
INACTIVE = "inactive"
NOT_APPLICABLE = "not_applicable"


def _load(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}


def check_protections(project_dir: Path) -> list[dict]:
    state = project_dir / ".sweetclaude" / "state"
    sc = _load(state / "sweetclaude.yaml")
    mirror = _load(state / "phase.yaml")
    gates = _load(state / "effective-gates.yaml")
    active_work = (sc.get("work") or {}).get("active") or {}
    guardian_on = (state / "guardian-enabled").is_file()

    results: list[dict] = []

    def add(name, status, reason, fix=None):
        results.append({"protection": name, "status": status,
                        "reason": reason, "fix": fix})

    # --- test-file immutability (ISSUE-282) ---
    tdd_phase = active_work.get("tdd_phase") or mirror.get("tdd_phase")
    if not (sc or mirror):
        add("test-file immutability", NOT_APPLICABLE,
            "project is not configured for SweetClaude")
    elif tdd_phase is None:
        add("test-file immutability", NOT_APPLICABLE,
            "no TDD cycle in progress — tests are only frozen while implementing")
    elif tdd_phase == "implementing":
        add("test-file immutability", ACTIVE, "tests are frozen")
    else:
        add("test-file immutability", NOT_APPLICABLE,
            f"TDD phase is {tdd_phase}, so tests are intentionally editable")

    # --- work-in-progress limit (ISSUE-281) ---
    mode = gates.get("mode")
    if not gates:
        add("work-in-progress limit", NOT_APPLICABLE,
            "no compiled gates — the project has not chosen a working mode")
    elif mode != "kanban":
        add("work-in-progress limit", NOT_APPLICABLE,
            f"limit applies to kanban mode only; this project is {mode}")
    else:
        add("work-in-progress limit", ACTIVE,
            f"enforced at {gates.get('wip_limit', 3)} concurrent items")

    # --- phase-dwelling guard (ISSUE-281) ---
    if not guardian_on:
        add("phase-dwelling guard", NOT_APPLICABLE,
            "Protocol Guardian is off; this guard is guardian-only")
    elif not (sc or mirror):
        add("phase-dwelling guard", INACTIVE,
            "Protocol Guardian is on but no project state is readable",
            "run /sweetclaude:configure doctor")
    else:
        add("phase-dwelling guard", ACTIVE, "advancement-pushing language is blocked")

    # --- artifact placement ---
    privacy = state / "artifact-privacy.yaml"
    legacy_privacy = project_dir / ".sweetclaude" / "artifact-privacy.yaml"
    if not sc:
        add("artifact placement", NOT_APPLICABLE, "project is not configured")
    elif not privacy.is_file() and not legacy_privacy.is_file():
        add("artifact placement", INACTIVE,
            "no artifact privacy manifest, so skills cannot resolve where "
            "product artifacts belong",
            "run /sweetclaude:configure doctor to repair the artifact privacy configuration")
    else:
        add("artifact placement", ACTIVE, "artifact paths resolve from the manifest")

    return results


def inactive_only(results: list[dict]) -> list[dict]:
    """Only genuinely broken protections. `not_applicable` is a protection
    correctly standing down, not a fault, and reporting it as one would train
    people to ignore the notice."""
    return [r for r in results if r["status"] == INACTIVE]


def render(results: list[dict]) -> str:
    broken = inactive_only(results)
    if not broken:
        return ""
    lines = ["Some protections cannot run:"]
    for r in broken:
        lines.append(f"  - {r['protection']}: {r['reason']}")
        if r.get("fix"):
            lines.append(f"    fix: {r['fix']}")
    lines.append("They are allowing rather than blocking. This notice appears "
                 "once per session.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Report protections that cannot run.")
    p.add_argument("--project-dir", type=Path, default=Path("."))
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.add_argument("--all", action="store_true",
                   help="include protections that are active or not applicable")
    args = p.parse_args(argv)

    results = check_protections(args.project_dir.resolve())

    if args.format == "json":
        payload = results if args.all else inactive_only(results)
        print(json.dumps({"protections": payload,
                          "inactive_count": len(inactive_only(results))}, indent=2))
    else:
        if args.all:
            for r in results:
                print(f"  [{r['status']:<15}] {r['protection']:<28} {r['reason']}")
        else:
            text = render(results)
            if text:
                print(text)
    # Exit 1 when something is inactive, so a caller can branch without parsing.
    return 1 if inactive_only(results) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
