#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Report skill outcomes from the metrics log (ISSUE-276).

`.sweetclaude/metrics/events.log` recorded that skills ran and never whether
they worked. This pairs invocations with completions and reports the result.

Three properties this is built around:

  * An invocation with no completion is reported as `unknown`, never as a
    success. Silence is not evidence of working, and treating it as such is
    how a log that logs nothing useful still reads as green.
  * A skill that has never been observed at all is `unobserved`, which is a
    different statement from "zero failures". 113 of the framework's skills
    had never appeared in this project's log.
  * Historic events written before outcomes existed are `unknown`, and are
    distinguishable from a completion that recorded `unknown` deliberately.

The log is append-only YAML documents, so outcome cannot be attached to the
invocation record after the fact. It rides on a paired `skill_completed`
event instead.

Usage:
    python3 scripts/usage_report.py --project-dir .
    python3 scripts/usage_report.py --project-dir . --format json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

COMPLETED, FAILED, ABANDONED, BLOCKED = "completed", "failed", "abandoned", "blocked"
UNKNOWN, UNOBSERVED = "unknown", "unobserved"
RECORDED_OUTCOMES = {COMPLETED, FAILED, ABANDONED, BLOCKED}


def parse_events(log_path: Path) -> list[dict]:
    """Parse the append-only `---`-delimited event log.

    Hand-parsed rather than via yaml.safe_load_all because a single malformed
    record written by a half-finished shell redirect must not discard the rest
    of the file.
    """
    if not log_path.is_file():
        return []
    events, current = [], None
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip() == "---":
            if current:
                events.append(current)
            current = {}
            continue
        if current is None or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if key and not key.startswith("-"):
            current[key] = value
    if current:
        events.append(current)
    return [e for e in events if e.get("event")]


def pair_invocations(events: list[dict]) -> list[dict]:
    """Match each skill_invoked with the next skill_completed for that skill.

    Pairing is per-skill and in order. A second invocation of the same skill
    before the first completes leaves the earlier one unknown, which is the
    honest reading — nothing recorded that it finished.
    """
    pending: dict[str, list[dict]] = {}
    records: list[dict] = []

    for event in events:
        etype, skill = event.get("event"), event.get("skill")
        if not skill:
            continue
        if etype == "skill_invoked":
            record = {"skill": skill, "invoked_at": event.get("timestamp"),
                      "phase": event.get("phase"), "outcome": UNKNOWN,
                      "detail": None, "completed_at": None}
            records.append(record)
            pending.setdefault(skill, []).append(record)
        elif etype == "skill_completed":
            outcome = event.get("outcome", UNKNOWN)
            if outcome not in RECORDED_OUTCOMES:
                outcome = UNKNOWN
            queue = pending.get(skill) or []
            if queue:
                record = queue.pop(0)
                record["outcome"] = outcome
                record["detail"] = event.get("detail")
                record["completed_at"] = event.get("timestamp")
            else:
                # A completion with no matching invocation still happened.
                records.append({"skill": skill, "invoked_at": None,
                                "phase": event.get("phase"), "outcome": outcome,
                                "detail": event.get("detail"),
                                "completed_at": event.get("timestamp"),
                                "unpaired": True})
    return records


def known_skills(skills_dir: Path) -> set[str]:
    if not skills_dir.is_dir():
        return set()
    return {f"sweetclaude:{d.name}" for d in skills_dir.iterdir() if d.is_dir()}


def build_report(project_dir: Path, skills_dir: Path | None = None) -> dict:
    log = project_dir / ".sweetclaude" / "metrics" / "events.log"
    events = parse_events(log)
    records = pair_invocations(events)

    by_skill: dict[str, dict] = {}
    for r in records:
        entry = by_skill.setdefault(r["skill"], {o: 0 for o in
                                                (COMPLETED, FAILED, ABANDONED,
                                                 BLOCKED, UNKNOWN)})
        entry[r["outcome"]] += 1

    all_skills = known_skills(skills_dir or (REPO_ROOT / "skills"))
    observed = set(by_skill)
    unobserved = sorted(all_skills - observed)

    totals = {o: sum(e[o] for e in by_skill.values())
              for o in (COMPLETED, FAILED, ABANDONED, BLOCKED, UNKNOWN)}
    recorded = sum(totals[o] for o in RECORDED_OUTCOMES)

    return {
        "schema_version": 1,
        "events_parsed": len(events),
        "invocations": len(records),
        "totals": totals,
        # Rates are over records that actually carry an outcome. Dividing by
        # everything would let unknowns silently inflate the success rate.
        "recorded_outcomes": recorded,
        "success_rate": round(totals[COMPLETED] / recorded, 3) if recorded else None,
        "by_skill": dict(sorted(by_skill.items())),
        "observed_skills": len(observed),
        "known_skills": len(all_skills),
        "unobserved_skills": unobserved,
        "failures": [r for r in records if r["outcome"] == FAILED],
    }


def render(report: dict) -> str:
    t = report["totals"]
    out = ["SweetClaude skill outcomes", ""]
    out.append(f"  events parsed     : {report['events_parsed']}")
    out.append(f"  invocations       : {report['invocations']}")
    out.append("")
    out.append(f"  completed         : {t[COMPLETED]}")
    out.append(f"  failed            : {t[FAILED]}")
    out.append(f"  abandoned         : {t[ABANDONED]}")
    out.append(f"  blocked           : {t[BLOCKED]}")
    out.append(f"  unknown           : {t[UNKNOWN]}  (no completion recorded — "
               f"not a success)")
    out.append("")
    rate = report["success_rate"]
    out.append("  success rate      : "
               + (f"{rate:.0%} of {report['recorded_outcomes']} recorded outcomes"
                  if rate is not None else "no outcomes recorded yet"))
    out.append("")
    out.append(f"  skills observed   : {report['observed_skills']} of "
               f"{report['known_skills']}")
    out.append(f"  never observed    : {len(report['unobserved_skills'])}  "
               f"(unobserved, not zero-failure)")

    if report["failures"]:
        out += ["", "  Failures:"]
        for f in report["failures"]:
            out.append(f"    {f['skill']}  {f.get('detail') or '(no detail recorded)'}")

    if report["by_skill"]:
        out += ["", "  Per skill:"]
        for skill, counts in report["by_skill"].items():
            parts = [f"{k}={v}" for k, v in counts.items() if v]
            out.append(f"    {skill:<44} {'  '.join(parts)}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Report skill outcomes from the metrics log.")
    p.add_argument("--project-dir", type=Path, default=Path("."))
    p.add_argument("--skills-dir", type=Path, default=None)
    p.add_argument("--format", choices=["text", "json"], default="text")
    args = p.parse_args(argv)

    report = build_report(args.project_dir.resolve(), args.skills_dir)
    print(json.dumps(report, indent=2) if args.format == "json" else render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
