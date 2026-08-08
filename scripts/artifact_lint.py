#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Check a produced artifact against its mechanical quality criteria (ISSUE-271).

rules/phase-gates.md carries 388 exit criteria and nothing checked any of them.
This checks the countable subset — the ones that need no model — and reports
per criterion, by name.

Deliberate non-goals:

  * No composite score. "Brief quality: 8.2/10" cannot be acted on and launders
    judgment into a number. Output is binary per criterion.
  * No silent skipping. Criteria this tool cannot evaluate are reported as
    `judgment` or `blocked`, so the gap between what is checked and what the
    gate demands stays visible.

Usage:
    python3 scripts/artifact_lint.py <file> --type product-brief
    python3 scripts/artifact_lint.py <file> --format json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CRITERIA = REPO_ROOT / "config" / "artifact-criteria.yaml"

PASS, FAIL, JUDGMENT, BLOCKED = "pass", "fail", "judgment", "blocked"

# A criterion is "measurable" if it carries a number, a date, or a binary verb.
MEASURABLE = re.compile(
    r"\b\d+\b|\b\d{4}-\d{2}-\d{2}\b|\b(?:zero|every|no|never|always|all|none)\b",
    re.IGNORECASE,
)
SENTENCE_END = re.compile(r"[.!?](?:\s|$)")


def load_criteria(path: Path = CRITERIA) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) > 2:
            return parts[2]
    return text


def split_sections(text: str) -> dict[str, str]:
    """Map normalised heading -> body. Leading "N." numbering is ignored so a
    renumbered brief is not reported as a restructured one."""
    sections: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^##\s+(?:\d+[a-z]?\.\s*)?(.+?)\s*$", line)
        if m and not line.startswith("###"):
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = m.group(1).strip().lower()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def _subsection(body: str, name: str) -> str | None:
    m = re.search(rf"^###\s+{re.escape(name)}\s*$(.*?)(?=^###\s|\Z)",
                  body, re.M | re.S | re.I)
    return m.group(1).strip() if m else None


def _bullets(text: str) -> list[str]:
    return [l.strip("-* ").strip() for l in text.splitlines()
            if re.match(r"^\s*[-*]\s+\S", l)]


def _numbered(text: str) -> list[str]:
    return [re.sub(r"^\s*\d+\.\s*", "", l).strip() for l in text.splitlines()
            if re.match(r"^\s*\d+\.\s+\S", l)]


def _substance(text: str) -> int:
    """Count units of content: prose sentences plus list items.

    A section built entirely from bullets — a Scope section, typically — is
    substantive without containing a single full stop. Counting only prose
    sentences reports it as a one-liner, which is how the first version of
    this linter failed the known-good brief in the corpus.
    """
    prose_lines, items = [], 0
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^\s*(?:[-*]|\d+\.)\s+\S", line):
            items += 1
        elif not stripped.startswith(("|", "```", "#")):
            prose_lines.append(line)
    prose = "\n".join(prose_lines)
    sentences = len([s for s in SENTENCE_END.split(prose) if s.strip()])
    return sentences + items


def check(text: str, artifact_type: str, criteria: dict) -> list[dict]:
    spec = (criteria.get("artifact_types") or {}).get(artifact_type)
    if spec is None:
        raise KeyError(f"unknown artifact type: {artifact_type}")

    body = strip_frontmatter(text)
    sections = split_sections(body)
    required = [s.lower() for s in spec.get("required_sections", [])]
    results: list[dict] = []

    for crit in spec.get("criteria", []):
        cid, tier = crit["id"], crit["tier"]
        if tier == "judgment":
            results.append({"id": cid, "status": JUDGMENT, "detail":
                            "needs semantic evaluation (ISSUE-273)"})
            continue
        if tier == "blocked":
            results.append({"id": cid, "status": BLOCKED,
                            "detail": crit.get("description", "").strip()})
            continue

        if cid == "BRIEF-SECTIONS":
            missing = [s for s in required if s not in sections]
            results.append({"id": cid, "status": FAIL if missing else PASS,
                            "detail": f"missing sections: {', '.join(missing)}" if missing
                                      else f"all {len(required)} required sections present"})

        elif cid == "BRIEF-SUBSTANTIVE":
            floor = crit.get("min_sentences", 2)
            thin = [s for s in required
                    if s in sections and _substance(sections[s]) < floor]
            results.append({"id": cid, "status": FAIL if thin else PASS,
                            "detail": f"under {floor} units of content: {', '.join(thin)}" if thin
                                      else "every required section carries real content"})

        elif cid == "BRIEF-NO-PLACEHOLDER":
            pats = crit.get("placeholder_patterns", [])
            hits = sorted({p for p in pats
                           if re.search(rf"\b{re.escape(p)}\b", body, re.I)})
            results.append({"id": cid, "status": FAIL if hits else PASS,
                            "detail": f"placeholder text found: {', '.join(hits)}" if hits
                                      else "no placeholder text"})

        elif cid == "BRIEF-OUT-OF-SCOPE-3":
            floor = crit.get("min_items", 3)
            scope = sections.get("scope")
            if scope is None:
                results.append({"id": cid, "status": FAIL,
                                "detail": "no Scope section to read"})
            else:
                sub = _subsection(scope, crit.get("subsection", "Out of scope"))
                items = _bullets(sub) if sub is not None else []
                results.append({"id": cid, "status": PASS if len(items) >= floor else FAIL,
                                "detail": f"{len(items)} out-of-scope item(s), need {floor}"})

        elif cid == "BRIEF-MEASURABLE-CRITERIA":
            floor = crit.get("min_measurable", 1)
            sc = sections.get("success criteria")
            if sc is None:
                results.append({"id": cid, "status": FAIL,
                                "detail": "no Success Criteria section"})
            else:
                items = _numbered(sc) or _bullets(sc)
                good = [i for i in items if MEASURABLE.search(i)]
                results.append({"id": cid, "status": PASS if len(good) >= floor else FAIL,
                                "detail": f"{len(good)} of {len(items)} criteria carry a "
                                          f"countable signal, need {floor}"})
        else:
            results.append({"id": cid, "status": BLOCKED,
                            "detail": "no mechanical check implemented"})
    return results


def render(path: str, results: list[dict]) -> str:
    order = {FAIL: 0, BLOCKED: 1, JUDGMENT: 2, PASS: 3}
    lines = [f"{path}", ""]
    for r in sorted(results, key=lambda r: (order[r["status"]], r["id"])):
        lines.append(f"  [{r['status'].upper():<8}] {r['id']:<28} {r['detail']}")
    counts = {s: sum(1 for r in results if r["status"] == s) for s in (PASS, FAIL, JUDGMENT, BLOCKED)}
    lines += ["", f"  {counts[PASS]} pass · {counts[FAIL]} fail · "
                  f"{counts[JUDGMENT]} need judgment · {counts[BLOCKED]} blocked"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Lint an artifact against its quality criteria.")
    p.add_argument("file", type=Path)
    p.add_argument("--type", default="product-brief")
    p.add_argument("--criteria", type=Path, default=CRITERIA)
    p.add_argument("--format", choices=["text", "json"], default="text")
    args = p.parse_args(argv)

    if not args.file.is_file():
        print(f"artifact not found: {args.file}", file=sys.stderr)
        return 2
    try:
        results = check(args.file.read_text(encoding="utf-8"), args.type,
                        load_criteria(args.criteria))
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps({"file": str(args.file), "results": results}, indent=2))
    else:
        print(render(str(args.file), results))
    return 1 if any(r["status"] == FAIL for r in results) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
