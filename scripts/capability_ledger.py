#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate the SweetClaude capability ledger (ISSUE-266).

Reads config/capability-manifest.yaml, the coverage JSON, and the behavioral
contract map, and emits the truth table: every declared capability, the tier
that verifies it, and whether it works.

The point is that a capability with no verification path is reported as
`broken`, never omitted. An omitted capability is indistinguishable from a
working one, which is the failure this ledger exists to prevent.

Usage:
    python3 scripts/capability_ledger.py --format markdown
    python3 scripts/capability_ledger.py --format json
    python3 scripts/capability_ledger.py --coverage coverage.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "config" / "capability-manifest.yaml"
RULES = REPO_ROOT / "rules" / "interaction-model.md"
BEHAVIORAL = REPO_ROOT / "skills" / "behavioral-regression" / "SKILL.md"

WORKS = "works"
COMPROMISED = "compromised"
BROKEN = "broken"
UNVERIFIABLE = "not-mechanically-verifiable"

TIER_STRUCTURAL = "tier-1-structural"
TIER_EXECUTABLE = "tier-2-executable"
TIER_BEHAVIORAL = "tier-3-behavioral"


class LedgerError(Exception):
    """Raised when the manifest declares something that does not resolve."""


def _load_manifest(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _skill_exists(delegate: str | None) -> bool:
    if not delegate:
        return False
    name = delegate.split(":", 1)[-1]
    return (REPO_ROOT / "skills" / name).is_dir()


def _executable_exists(entry: dict) -> bool:
    ep = entry.get("command_entrypoint") or {}
    script = ep.get("script") or entry.get("executable")
    if not script:
        return False
    return (REPO_ROOT / script).is_file()


def _coverage_for(entry: dict, coverage: dict | None) -> float | None:
    """Line coverage of the capability's executable, if measured."""
    if not coverage:
        return None
    ep = entry.get("command_entrypoint") or {}
    script = ep.get("script") or entry.get("executable")
    if not script:
        return None
    for path, info in (coverage.get("files") or {}).items():
        if path.endswith(script) or Path(path).as_posix().endswith(script):
            return info["summary"]["percent_covered"]
    return None


def _classify(entry: dict, coverage: dict | None, min_coverage: float) -> tuple[str, list[str]]:
    """Return (status, reasons). Never returns 'omitted'."""
    reasons: list[str] = []

    delegate = entry.get("delegate_skill")
    if delegate and not _skill_exists(delegate):
        reasons.append(f"delegate_skill {delegate} does not resolve to a skill")

    ep = entry.get("command_entrypoint") or {}
    script = ep.get("script") or entry.get("executable")
    if script and not _executable_exists(entry):
        reasons.append(f"entrypoint script {script} not found")

    if reasons:
        return BROKEN, reasons

    if not entry.get("verification_commands"):
        reasons.append("no verification_commands declared")
        return BROKEN, reasons

    if entry.get("mutates_project"):
        rollback = entry.get("rollback_support") or {}
        if not rollback.get("supported"):
            reasons.append("mutating capability declares no working rollback")
            return BROKEN, reasons
        if rollback.get("limitations"):
            reasons.append(
                "rollback carries limitations: " + "; ".join(rollback["limitations"])
            )

    # A declared unsupported state with a defined behavior is graceful
    # handling, not a compromise. Penalising it would discourage the honest
    # declaration this ledger exists to reward. Only an undeclared behavior,
    # or one that admits data risk, downgrades the capability.
    # Vocabulary is fixed by the manifest schema (block / diagnose_only /
    # escalate) and validated by tests/test_capability_manifest.py.
    HANDLED = {"escalate", "diagnose_only", "block"}
    unhandled = [
        u for u in (entry.get("unsupported_states") or [])
        if str(u.get("behavior") or "") not in HANDLED
    ]
    if unhandled:
        reasons.append(
            f"{len(unhandled)} unsupported state(s) with no defined handling: "
            + ", ".join(str(u.get("condition")) for u in unhandled)
        )

    pct = _coverage_for(entry, coverage)
    if pct is not None and pct < min_coverage:
        reasons.append(f"entrypoint coverage {pct:.0f}% is below {min_coverage:.0f}%")

    return (COMPROMISED if reasons else WORKS), reasons


def _tier_for(entry: dict) -> str:
    """An explicit verification_tier always wins.

    Inferring the tier from "does it have a script" cannot express a
    capability that is non-deterministic by nature. The rubric judge has an
    executable and is still Tier 3: it needs a live model, so CI can never
    report it as passing. Declaring the tier is the only way to say that.
    """
    declared = entry.get("verification_tier")
    if declared in {TIER_STRUCTURAL, TIER_EXECUTABLE, TIER_BEHAVIORAL}:
        return declared
    ep = entry.get("command_entrypoint") or {}
    if ep.get("script") or entry.get("executable"):
        return TIER_EXECUTABLE
    return TIER_STRUCTURAL


def _behavioral_rows() -> list[dict]:
    """Interaction-model rules are Tier 3 — enumerable, never a CI pass."""
    if not RULES.is_file() or not BEHAVIORAL.is_file():
        return []
    sections = re.findall(r"^##\s+(.+?)\s*$", RULES.read_text(encoding="utf-8"), re.M)
    contracts = re.findall(
        r"^###\s+(CONTRACT-\d+):\s*(.+?)\s*$", BEHAVIORAL.read_text(encoding="utf-8"), re.M
    )
    by_id = dict(contracts)
    rows = []
    for section in sections:
        rows.append({
            "capability": f"interaction-model.{section}",
            "title": section,
            "tier": TIER_BEHAVIORAL,
            "status": UNVERIFIABLE,
            "reasons": ["scored only by /sweetclaude:behavioral-regression against a live model"],
            "contracts": sorted(by_id),
        })
    return rows


def build_ledger(
    manifest_path: Path = MANIFEST,
    coverage_path: Path | None = None,
    min_coverage: float = 80.0,
    include_behavioral: bool = True,
) -> dict:
    manifest = _load_manifest(manifest_path)
    capabilities = manifest.get("capabilities") or {}

    coverage = None
    if coverage_path and coverage_path.is_file():
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))

    rows = []
    for name, entry in sorted(capabilities.items()):
        status, reasons = _classify(entry, coverage, min_coverage)
        tier = _tier_for(entry)
        if tier == TIER_BEHAVIORAL and status == WORKS:
            # A live-model capability cannot be certified by a CI run. Reporting
            # it as working would be the exact over-claim this ledger exists to
            # prevent. A genuine defect (broken/compromised) still shows.
            status = UNVERIFIABLE
            reasons = reasons + ["Tier 3: scored only against a live model"]
        rows.append({
            "capability": name,
            "title": entry.get("title", ""),
            "tier": tier,
            "status": status,
            "reasons": reasons,
            "delegate_skill": entry.get("delegate_skill"),
            "mutates_project": bool(entry.get("mutates_project")),
            "coverage": _coverage_for(entry, coverage),
        })

    if include_behavioral:
        rows.extend(_behavioral_rows())

    counts = {s: 0 for s in (WORKS, COMPROMISED, BROKEN, UNVERIFIABLE)}
    for row in rows:
        counts[row["status"]] += 1

    return {
        "schema_version": 1,
        "declared_capabilities": len(capabilities),
        "rows": rows,
        "counts": counts,
        "coverage_source": str(coverage_path) if coverage else None,
    }


def render_markdown(ledger: dict) -> str:
    counts = ledger["counts"]
    out = [
        "# SweetClaude Capability Ledger",
        "",
        f"**Declared capabilities:** {ledger['declared_capabilities']}",
        f"**Works:** {counts[WORKS]}  ·  **Compromised:** {counts[COMPROMISED]}  ·  "
        f"**Broken:** {counts[BROKEN]}  ·  **Not mechanically verifiable:** "
        f"{counts[UNVERIFIABLE]}",
        "",
        "A capability with no verification path is reported as broken, never",
        "omitted — an omitted capability is indistinguishable from a working one.",
        "",
        "| Capability | Tier | Status | Notes |",
        "|---|---|---|---|",
    ]
    for row in ledger["rows"]:
        notes = "; ".join(row["reasons"]) if row["reasons"] else ""
        out.append(
            f"| `{row['capability']}` | {row['tier']} | **{row['status']}** | {notes} |"
        )
    out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the capability ledger.")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--coverage", type=Path, default=None,
                        help="coverage JSON report (from pytest --cov-report=json)")
    parser.add_argument("--min-coverage", type=float, default=80.0)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--fail-on-broken", action="store_true",
                        help="exit 1 if any capability is broken")
    parser.add_argument("--no-behavioral", action="store_true")
    args = parser.parse_args(argv)

    if not args.manifest.is_file():
        print(f"capability manifest not found: {args.manifest}", file=sys.stderr)
        return 2

    ledger = build_ledger(
        manifest_path=args.manifest,
        coverage_path=args.coverage,
        min_coverage=args.min_coverage,
        include_behavioral=not args.no_behavioral,
    )

    text = (json.dumps(ledger, indent=2) if args.format == "json"
            else render_markdown(ledger))

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"ledger written: {args.out}")
    else:
        print(text)

    if args.fail_on_broken and ledger["counts"][BROKEN]:
        broken = [r["capability"] for r in ledger["rows"] if r["status"] == BROKEN]
        print(f"\nbroken capabilities: {', '.join(broken)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
