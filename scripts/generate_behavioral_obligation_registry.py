#!/usr/bin/env python3
"""Write the checked-in full behavioral obligation registry without executing tests."""

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
    parser.add_argument("--output", type=Path, default=PACKAGE / "obligations.json")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"Refusing to overwrite existing registry: {args.output}")
    namespace = argparse.Namespace(catalog=PACKAGE / "clusters.json", inventory=PACKAGE / "inventory.json", config=None, preset="full", include=[], exclude=[], operation=[], exclude_operation=[])
    plan = runner.selected_plan(namespace)
    from behavioral_e2e import expand_plan, manifest, read_json
    report = manifest(expand_plan(plan, read_json(namespace.inventory)), plan)
    data = {"schema_version": 1, "inventory_sha256": report["inventory_sha256"], "count": len(report["obligations"]), "obligations": report["obligations"]}
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {data['count']} obligations to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
