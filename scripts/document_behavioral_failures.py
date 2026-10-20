#!/usr/bin/env python3
"""Write every non-pass behavioral attempt with prompt and complete captured output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"Refusing to overwrite {args.output}")
    report = json.loads(args.report.read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in report.get("cases", [])}
    failures = [row for row in report.get("results", []) if row.get("status") != "pass"]
    lines = ["# Standard Behavioral Run Failures", "", f"Source report: `{args.report}`", "", f"Recorded non-pass attempts: {len(failures)}", ""]
    for number, row in enumerate(failures, start=1):
        case = cases.get(row["case"], {})
        evidence = row.get("evidence", {})
        lines += [f"## {number}. {row['case']} — {row['status']}", "", f"- Attempt: {row.get('attempt', 1)}", f"- Operation: `{row.get('operation_id', '')}`", f"- Fixture: `{evidence.get('fixture', '')}`", f"- Cost: `${row.get('cost_usd', 0):.4f}`", f"- Cumulative cost: `${row.get('running_total_cost_usd', 0):.4f}`", f"- Evidence path: `{evidence.get('root', '')}`", "", "### Input", "", "```text", case.get("prompt", "<case prompt unavailable>"), "```", "", "### Result details", "", "```text", "\n".join(row.get("details", [])) or "<none>", "```", "", "### Ordered output and tool evidence", "", "```json", json.dumps(evidence.get("events", []), indent=2, ensure_ascii=False), "```", ""]
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(failures)} non-pass attempts to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
