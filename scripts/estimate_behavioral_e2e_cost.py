#!/usr/bin/env python3
"""Estimate selected behavioral E2E cost from recorded live receipts without model calls."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs" / "testing" / "behavioral-e2e"
spec = importlib.util.spec_from_file_location("runner", ROOT / "scripts" / "run_behavioral_e2e.py")
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=PACKAGE / "standard.json")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--receipts", type=Path, default=ROOT / ".sweetclaude" / "live-behavioral-costs")
    parser.add_argument("--run-cap-usd", type=float, default=25.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repeat <= 0 or args.run_cap_usd <= 0:
        raise SystemExit("repeat and run cap must be positive")
    namespace = argparse.Namespace(catalog=PACKAGE / "clusters.json", inventory=PACKAGE / "inventory.json", config=args.config, preset=None, include=[], exclude=[], operation=[], exclude_operation=[])
    plan = runner.selected_plan(namespace)
    from behavioral_e2e import expand_plan, read_json
    cases = expand_plan(plan, read_json(namespace.inventory))
    observed = []
    for receipt in sorted(args.receipts.glob("*.json")):
        value = json.loads(receipt.read_text(encoding="utf-8"))
        observed.extend(float(row["cost_usd"]) for row in value.get("scenarios", []) if isinstance(row.get("cost_usd"), (int, float)))
    if not observed:
        raise SystemExit(f"No cost observations in {args.receipts}")
    attempts = len(cases) * args.repeat
    data = {
        "schema_version": 1,
        "selection_config": str(args.config),
        "inventory_sha256": plan["inventory_sha256"],
        "base_cases": len(cases),
        "repeat": args.repeat,
        "attempts": attempts,
        "observations": len(observed),
        "per_case_usd": {"mean": sum(observed) / len(observed), "maximum_observed": max(observed)},
        "estimated_run_usd": {"mean": attempts * sum(observed) / len(observed), "maximum_observed": attempts * max(observed)},
        "run_cap_usd": args.run_cap_usd,
        "within_cap_at_mean": attempts * sum(observed) / len(observed) <= args.run_cap_usd,
        "within_cap_at_maximum_observed": attempts * max(observed) <= args.run_cap_usd,
        "note": "Estimate from prior live receipts; actual model cost can differ. The runner stops when its actual cumulative total reaches the run cap.",
    }
    rendered = json.dumps(data, indent=2) + "\n"
    if args.output:
        if args.output.exists():
            raise SystemExit(f"Refusing to overwrite {args.output}")
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
