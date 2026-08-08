#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Rubric judge for the semantic artifact criteria (ISSUE-273).

Tier 3. Non-deterministic, reports rather than gates, and is not permitted to
be trusted until it has been measured against the falsification corpus.

The design point is that the harness can detect a useless judge. An
always-pass backend and an always-fail backend both produce confident-looking
per-criterion verdicts; only running them against a corpus with artifacts on
both sides exposes them. `discriminate` does exactly that and reports a
confusion matrix, so a judge that cannot tell good from bad is visible rather
than quietly authoritative.

Backends:
    stub          — deterministic keyword heuristic. For testing the harness,
                    never for real evaluation.
    always-pass   — degenerate. Exists so the discrimination check can prove
                    it catches one.
    always-fail   — degenerate, same reason.
    command       — shell out to a real model via --command. The template gets
                    {prompt_file} substituted and must emit the JSON verdict
                    described in VERDICT_SCHEMA on stdout.

Usage:
    python3 scripts/artifact_judge.py judge <file> --criterion BRIEF-CONCRETE-SCENARIO
    python3 scripts/artifact_judge.py discriminate --backend stub
    python3 scripts/artifact_judge.py discriminate --backend command \\
        --command 'claude -p --output-format json < {prompt_file}'
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
RUBRICS = REPO_ROOT / "config" / "artifact-rubrics.yaml"
CORPUS = REPO_ROOT / "tests" / "fixtures" / "artifact-quality"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import artifact_lint as lint  # noqa: E402

VERDICT_SCHEMA = {
    "verdict": "pass | fail",
    "citation": "verbatim span from the artifact that justifies the verdict",
    "reason": "one sentence",
}


class JudgeError(Exception):
    pass


def load_rubrics(path: Path = RUBRICS) -> dict:
    return (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("rubrics", {})


def build_prompt(artifact: str, criterion: str, rubric: dict) -> str:
    section = rubric.get("section")
    body = lint.strip_frontmatter(artifact)
    scoped = lint.split_sections(body).get((section or "").lower(), body)
    return (
        f"Evaluate one criterion. Answer only about this criterion.\n\n"
        f"CRITERION: {criterion}\n"
        f"QUESTION: {rubric['question'].strip()}\n\n"
        f"PASSES WHEN: {rubric['passes_when'].strip()}\n\n"
        f"FAILS WHEN: {rubric['fails_when'].strip()}\n\n"
        f"--- ARTIFACT SECTION: {section} ---\n{scoped}\n--- END ---\n\n"
        f"Reply with JSON only: {json.dumps(VERDICT_SCHEMA)}\n"
        f"The citation must be copied verbatim from the section above. "
        f"A verdict without a citation is discarded.\n"
    )


# --- backends ------------------------------------------------------------

VAGUE = re.compile(
    r"\b(users? will be happy|much better|high quality|improved experience|"
    r"common problem|often|sometimes|can be difficult|frustration)\b", re.I)
CONCRETE = re.compile(r"\b\d+\.\d+|\bv?\d+\.\d+\.\d+|concrete scenario|for example|"
                      r"\bstep \d|\bwhen (?:a|the) \w+", re.I)


def _stub(prompt: str, text: str) -> dict:
    """Keyword heuristic. Good enough to exercise the harness, and honest about
    being nothing more than that."""
    vague, concrete = VAGUE.search(text), CONCRETE.search(text)
    if vague and not concrete:
        return {"verdict": "fail", "citation": vague.group(0),
                "reason": "vague language with nothing concrete behind it"}
    if concrete:
        return {"verdict": "pass", "citation": concrete.group(0),
                "reason": "contains a concrete, checkable detail"}
    return {"verdict": "fail", "citation": text.strip()[:80],
            "reason": "no concrete detail found"}


def _command(prompt: str, template: str) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write(prompt)
        prompt_file = fh.name
    try:
        cmd = template.format(prompt_file=prompt_file)
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            raise JudgeError(f"judge command failed: {proc.stderr.strip()[:200]}")
        m = re.search(r"\{.*\}", proc.stdout, re.S)
        if not m:
            raise JudgeError("judge command emitted no JSON object")
        return json.loads(m.group(0))
    finally:
        Path(prompt_file).unlink(missing_ok=True)


def evaluate(artifact: str, criterion: str, rubric: dict, *,
             backend: str = "stub", command: str | None = None) -> dict:
    prompt = build_prompt(artifact, criterion, rubric)
    section = (rubric.get("section") or "").lower()
    scoped = lint.split_sections(lint.strip_frontmatter(artifact)).get(section, artifact)

    if backend == "stub":
        raw = _stub(prompt, scoped)
    elif backend == "always-pass":
        raw = {"verdict": "pass", "citation": scoped.strip()[:60], "reason": "degenerate backend"}
    elif backend == "always-fail":
        raw = {"verdict": "fail", "citation": scoped.strip()[:60], "reason": "degenerate backend"}
    elif backend == "command":
        if not command:
            raise JudgeError("--command is required for the command backend")
        raw = _command(prompt, command)
    else:
        raise JudgeError(f"unknown backend: {backend}")

    verdict = str(raw.get("verdict", "")).lower()
    citation = (raw.get("citation") or "").strip()
    if verdict not in {"pass", "fail"}:
        raise JudgeError(f"backend returned an unusable verdict: {raw!r}")

    # An uncited verdict is a guess wearing a verdict's clothes.
    discarded = None
    if rubric.get("citation_required", True):
        if not citation:
            discarded = "no citation supplied"
        elif citation not in scoped and citation not in artifact:
            discarded = "citation is not present in the artifact"

    return {"criterion": criterion, "verdict": verdict, "citation": citation,
            "reason": raw.get("reason", ""), "discarded": discarded,
            "counted": discarded is None}


# --- discrimination ------------------------------------------------------

def _meta(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text.split("---", 2)[1]) if text.startswith("---") else {}


def discriminate(*, backend: str = "stub", command: str | None = None,
                 rubrics: dict | None = None) -> dict:
    rubrics = rubrics or load_rubrics()
    rows, matrix = [], {"true_pass": 0, "true_fail": 0, "false_pass": 0, "false_fail": 0,
                        "discarded": 0}

    for group, expect in (("good", "pass"), ("benign", "pass"), ("degraded", "fail")):
        for path in sorted((CORPUS / group).glob("*.md")):
            meta = _meta(path)
            violates = meta.get("violates", "none")
            for criterion, rubric in rubrics.items():
                # A degraded fixture is only evidence for the criterion it targets.
                if expect == "fail" and violates != criterion:
                    continue
                try:
                    r = evaluate(path.read_text(encoding="utf-8"), criterion, rubric,
                                 backend=backend, command=command)
                except JudgeError as exc:
                    rows.append({"file": path.name, "criterion": criterion,
                                 "error": str(exc)})
                    continue
                if not r["counted"]:
                    matrix["discarded"] += 1
                    rows.append({"file": path.name, **r, "expected": expect})
                    continue
                correct = r["verdict"] == expect
                key = ("true_" if correct else "false_") + r["verdict"]
                matrix[key] += 1
                rows.append({"file": path.name, **r, "expected": expect,
                             "correct": correct})

    scored = matrix["true_pass"] + matrix["true_fail"] + matrix["false_pass"] + matrix["false_fail"]
    matrix["accuracy"] = round((matrix["true_pass"] + matrix["true_fail"]) / scored, 3) if scored else 0.0
    matrix["discriminates"] = bool(
        matrix["true_pass"] and matrix["true_fail"]
        and not matrix["false_pass"] and not matrix["false_fail"])
    return {"backend": backend, "matrix": matrix, "rows": rows}


def render(report: dict) -> str:
    m = report["matrix"]
    out = [f"Rubric judge discrimination — backend: {report['backend']}", ""]
    out.append(f"  correctly passed : {m['true_pass']}")
    out.append(f"  correctly failed : {m['true_fail']}")
    out.append(f"  wrongly passed   : {m['false_pass']}")
    out.append(f"  wrongly failed   : {m['false_fail']}")
    out.append(f"  discarded (no citation): {m['discarded']}")
    out.append(f"  accuracy         : {m['accuracy']}")
    out.append("")
    out.append("  DISCRIMINATES" if m["discriminates"] else
               "  DOES NOT DISCRIMINATE — this judge is not evidence")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Rubric judge for semantic artifact criteria.")
    sub = p.add_subparsers(dest="cmd", required=True)

    j = sub.add_parser("judge")
    j.add_argument("file", type=Path)
    j.add_argument("--criterion", required=True)
    j.add_argument("--backend", default="stub")
    j.add_argument("--command", default=None)

    d = sub.add_parser("discriminate")
    d.add_argument("--backend", default="stub")
    d.add_argument("--command", default=None)
    d.add_argument("--format", choices=["text", "json"], default="text")

    args = p.parse_args(argv)
    rubrics = load_rubrics()

    if args.cmd == "judge":
        if args.criterion not in rubrics:
            print(f"no rubric for {args.criterion}", file=sys.stderr)
            return 2
        try:
            r = evaluate(args.file.read_text(encoding="utf-8"), args.criterion,
                         rubrics[args.criterion], backend=args.backend,
                         command=args.command)
        except JudgeError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(json.dumps(r, indent=2))
        return 0 if r["counted"] and r["verdict"] == "pass" else 1

    report = discriminate(backend=args.backend, command=args.command, rubrics=rubrics)
    print(json.dumps(report, indent=2) if args.format == "json" else render(report))
    return 0 if report["matrix"]["discriminates"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
