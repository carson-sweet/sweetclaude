#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Phase 6: stamp committed local release-proof receipts from real run outputs.

The release gate requires one receipt per proof kind under
docs/release-evidence/<version>/ for a stable-channel release. This script is
the only writer for those receipts; it validates the passed-in run outputs and
refuses to stamp anything that does not satisfy the gate's proof rules.
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

from control_receipts import (
    DOCS_CLAIMS_RECEIPT_TYPE,
    LIVE_ENFORCEMENT_RECEIPT_TYPE,
    RELEASE_PROOF_RECEIPT_TYPES,
    RELEASE_PROOF_SPEND_CAP_USD,
    ROUTING_PROOF_MIN_DIRECT_PASS_RATE,
    ROUTING_RECEIPT_TYPE,
    UPGRADE_BASELINE_VERSION,
    UPGRADE_PATH_RECEIPT_TYPE,
    UPGRADE_SOURCE_LOCAL_MARKETPLACE,
    hash_file,
    live_suite_case_names,
    parse_junit_report,
    parse_release_tag,
    routing_case_ids,
    validate_release_proof_receipt,
)

DEFAULT_PROJECT_DIR = Path(__file__).resolve().parents[1]
EVIDENCE_FILE_NAMES = {
    LIVE_ENFORCEMENT_RECEIPT_TYPE: "live-enforcement-junit.xml",
    ROUTING_RECEIPT_TYPE: "routing-summary.json",
    DOCS_CLAIMS_RECEIPT_TYPE: "docs-claims-findings.json",
}


def _now(now: datetime.datetime | None = None) -> str:
    current = now or datetime.datetime.now(datetime.timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=datetime.timezone.utc)
    return current.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git(project_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(project_dir), *args],
        capture_output=True,
        text=True,
        check=True,
    )


def _is_git_repo(project_dir: Path) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(project_dir), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0 and completed.stdout.strip() == "true"


def _proof_context(
    project_dir: Path,
    *,
    kind: str,
    branch: str | None,
    commit: str | None,
) -> tuple[str, str]:
    if branch is None or commit is None:
        if not _is_git_repo(project_dir):
            raise ValueError(f"{kind} release proof requires a git work tree")
        branch = branch or _git(project_dir, "branch", "--show-current").stdout.strip()
        commit = commit or _git(project_dir, "rev-parse", "HEAD").stdout.strip()
    if not str(branch).strip():
        raise ValueError(f"{kind} release proof requires a named git branch")
    if not str(commit).strip():
        raise ValueError(f"{kind} release proof requires a bound commit")
    return str(branch).strip(), str(commit).strip()


def release_evidence_dir(project_dir: Path, version: str) -> Path:
    return project_dir / "docs" / "release-evidence" / version


def _relative_to_project(project_dir: Path, path: Path) -> str:
    return path.resolve(strict=False).relative_to(project_dir.resolve(strict=False)).as_posix()


def _evidence_entry(project_dir: Path, evidence_path: Path) -> dict[str, str]:
    return {
        "path": _relative_to_project(project_dir, evidence_path),
        "sha256": hash_file(evidence_path),
    }


def _committed_sibling_spend(project_dir: Path, evidence_dir: Path, tag: str) -> float:
    spend = 0.0
    for kind in sorted(RELEASE_PROOF_RECEIPT_TYPES):
        path = evidence_dir / f"{kind}.json"
        if not path.is_file():
            continue
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
            cost = receipt.get("cost_usd")
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Existing release proof receipt is invalid: {path}: {exc}") from exc
        if not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0:
            raise ValueError(f"Existing release proof receipt {path} has an invalid cost_usd")
        validate_release_proof_receipt(
            path,
            project_dir=project_dir,
            kind=kind,
            expected_tag=tag,
        )
        spend += float(cost)
    return spend


def _enforce_spend_cap(
    project_dir: Path,
    evidence_dir: Path,
    *,
    kind: str,
    tag: str,
    cost: float,
) -> None:
    total = _committed_sibling_spend(project_dir, evidence_dir, tag) + cost
    if total > RELEASE_PROOF_SPEND_CAP_USD:
        raise ValueError(
            f"{kind} release proof would exceed the ${RELEASE_PROOF_SPEND_CAP_USD:.2f} "
            f"live+routing spend cap (total ${total:.2f})"
        )


def _base_proof_receipt(
    project_dir: Path,
    *,
    kind: str,
    tag: str,
    version: str,
    branch: str,
    commit: str,
    claude_cli_version: str,
    cost_usd: float,
    evidence_path: Path | None,
) -> dict:
    receipt = {
        "schema_version": 2,
        "receipt_type": kind,
        "receipt_id": f"release-{version}-{kind}",
        "subject_id": f"release:{tag}",
        "generated_at": _now(),
        "command_or_workflow_step": f"release_evidence_local.py {kind} --tag {tag}",
        "cwd": str(project_dir),
        "repo_root": str(project_dir),
        "branch": branch,
        "commit": commit,
        "result": "pass",
        "tag": tag,
        "version": version,
        "claude_cli_version": claude_cli_version,
        "cost_usd": round(float(cost_usd), 4),
        "input_artifacts": [],
    }
    if evidence_path is not None:
        entry = _evidence_entry(project_dir, evidence_path)
        receipt["evidence_path"] = entry["path"]
        receipt["evidence_sha256"] = entry["sha256"]
        receipt["input_artifacts"] = [entry]
    return receipt


def _write_kind_receipt(
    project_dir: Path,
    *,
    kind: str,
    tag: str,
    receipt: dict,
    now: datetime.datetime | None,
) -> Path:
    version = parse_release_tag(tag, context=f"{kind} release proof")
    evidence_dir = release_evidence_dir(project_dir, version)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    path = evidence_dir / f"{kind}.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    validate_release_proof_receipt(
        path,
        project_dir=project_dir,
        kind=kind,
        expected_tag=tag,
        now=now,
    )
    return path


def _copy_evidence(
    project_dir: Path,
    *,
    kind: str,
    version: str,
    source_path: Path,
) -> Path:
    target = release_evidence_dir(project_dir, version) / EVIDENCE_FILE_NAMES[kind]
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, target)
    return target


def write_live_enforcement_receipt(
    project_dir: Path,
    *,
    tag: str,
    junit_path: str | Path,
    cost_usd: float,
    claude_cli_version: str,
    branch: str | None = None,
    commit: str | None = None,
    now: datetime.datetime | None = None,
) -> Path:
    project_dir = Path(project_dir).resolve(strict=False)
    version = parse_release_tag(tag, context="Live enforcement release proof")
    kind = LIVE_ENFORCEMENT_RECEIPT_TYPE
    stats = parse_junit_report(junit_path)
    if stats["failures"] or stats["errors"] or stats["skipped"]:
        raise ValueError(
            "Live enforcement run reports failures, errors or skips, so no receipt "
            "can be stamped"
        )
    expected_cases = live_suite_case_names(project_dir)
    if stats["cases"] != expected_cases:
        raise ValueError(
            "Live enforcement case set mismatch: "
            f"expected {sorted(expected_cases)}, got {sorted(stats['cases'])}"
        )
    cost = float(cost_usd)
    if cost < 0:
        raise ValueError("Live enforcement release proof cost_usd must be non-negative")
    _enforce_spend_cap(
        project_dir,
        release_evidence_dir(project_dir, version),
        kind=kind,
        tag=tag,
        cost=cost,
    )
    evidence_path = _copy_evidence(
        project_dir, kind=kind, version=version, source_path=Path(junit_path)
    )
    branch_value, commit_value = _proof_context(
        project_dir, kind=kind, branch=branch, commit=commit
    )
    receipt = _base_proof_receipt(
        project_dir,
        kind=kind,
        tag=tag,
        version=version,
        branch=branch_value,
        commit=commit_value,
        claude_cli_version=claude_cli_version,
        cost_usd=cost,
        evidence_path=evidence_path,
    )
    receipt["case_count"] = len(stats["cases"])
    receipt["suite_dir"] = "tests/live"
    return _write_kind_receipt(
        project_dir, kind=kind, tag=tag, receipt=receipt, now=now
    )


def write_routing_receipt(
    project_dir: Path,
    *,
    tag: str,
    summary_path: str | Path,
    claude_cli_version: str,
    branch: str | None = None,
    commit: str | None = None,
    now: datetime.datetime | None = None,
) -> Path:
    project_dir = Path(project_dir).resolve(strict=False)
    version = parse_release_tag(tag, context="Routing release proof")
    kind = ROUTING_RECEIPT_TYPE
    try:
        summary_doc = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Routing summary is not readable JSON: {summary_path}: {exc}") from exc
    if not isinstance(summary_doc, dict):
        raise ValueError(f"Routing summary must be a JSON object: {summary_path}")
    if summary_doc.get("tier") != "full":
        raise ValueError(
            f"Routing proof requires a full-tier run, got {summary_doc.get('tier')!r}"
        )
    summary = summary_doc.get("summary")
    if not isinstance(summary, dict):
        raise ValueError(f"Routing summary is missing its summary object: {summary_path}")
    planned = summary.get("planned")
    passed = summary.get("passed")
    if not isinstance(planned, int) or not isinstance(passed, int):
        raise ValueError("Routing summary planned and passed must be integers")
    diagnostics = summary_doc.get("diagnostics")
    diagnostics = diagnostics if isinstance(diagnostics, dict) else {}
    failed_rows = [
        row
        for row in (summary_doc.get("results") or [])
        if not isinstance(row, dict) or not row.get("passed")
    ]
    if passed != planned:
        floor = math.ceil(planned * ROUTING_PROOF_MIN_DIRECT_PASS_RATE)
        if passed < floor:
            raise ValueError(
                f"Routing proof direct passes {passed}/{planned} are below the "
                f"{int(ROUTING_PROOF_MIN_DIRECT_PASS_RATE * 100)}% noise floor"
            )
        for row in failed_rows:
            case_id = row.get("case") if isinstance(row, dict) else None
            if diagnostics.get(case_id) != "pass":
                raise ValueError(
                    f"Routing proof case {case_id!r} failed its go entry with no passing diagnostic"
                )
    diagnosed_pass = sum(
        1
        for row in failed_rows
        if diagnostics.get(row.get("case") if isinstance(row, dict) else None) == "pass"
    )
    expected_planned = len(routing_case_ids(project_dir))
    if planned != expected_planned:
        raise ValueError(
            f"Routing proof planned {planned} runs; the full tier has {expected_planned} cases"
        )
    cost_value = summary.get("cost_usd")
    if not isinstance(cost_value, (int, float)) or isinstance(cost_value, bool):
        raise ValueError("Routing summary cost_usd must be a number")
    cost = float(cost_value)
    _enforce_spend_cap(
        project_dir,
        release_evidence_dir(project_dir, version),
        kind=kind,
        tag=tag,
        cost=cost,
    )
    evidence_path = _copy_evidence(
        project_dir, kind=kind, version=version, source_path=Path(summary_path)
    )
    branch_value, commit_value = _proof_context(
        project_dir, kind=kind, branch=branch, commit=commit
    )
    receipt = _base_proof_receipt(
        project_dir,
        kind=kind,
        tag=tag,
        version=version,
        branch=branch_value,
        commit=commit_value,
        claude_cli_version=claude_cli_version,
        cost_usd=cost,
        evidence_path=evidence_path,
    )
    receipt["tier"] = summary_doc.get("tier")
    receipt["planned"] = planned
    receipt["passed"] = passed
    receipt["diagnosed_pass"] = diagnosed_pass
    receipt["model"] = summary_doc.get("model")
    return _write_kind_receipt(
        project_dir, kind=kind, tag=tag, receipt=receipt, now=now
    )


def write_upgrade_path_receipt(
    project_dir: Path,
    *,
    tag: str,
    commands: list[str],
    library_dirs: list[str],
    claude_cli_version: str,
    branch: str | None = None,
    commit: str | None = None,
    now: datetime.datetime | None = None,
) -> Path:
    project_dir = Path(project_dir).resolve(strict=False)
    version = parse_release_tag(tag, context="Upgrade path release proof")
    kind = UPGRADE_PATH_RECEIPT_TYPE
    commands_value = [str(command).strip() for command in commands]
    if not commands_value or not all(commands_value):
        raise ValueError("Upgrade path release proof requires the documented commands as run")
    library_dir_values = sorted({str(entry).strip() for entry in library_dirs})
    if not library_dir_values or not all(library_dir_values):
        raise ValueError("Upgrade path release proof requires the installed plugin library dirs")
    for listed in library_dir_values:
        relative = Path(listed)
        if relative.is_absolute():
            raise ValueError(f"Upgrade path library dir must be project-relative: {listed}")
        if not (project_dir / relative).is_dir():
            raise ValueError(f"Upgrade path library dir does not exist: {listed}")
    cost = 0.0
    _enforce_spend_cap(
        project_dir,
        release_evidence_dir(project_dir, version),
        kind=kind,
        tag=tag,
        cost=cost,
    )
    branch_value, commit_value = _proof_context(
        project_dir, kind=kind, branch=branch, commit=commit
    )
    receipt = _base_proof_receipt(
        project_dir,
        kind=kind,
        tag=tag,
        version=version,
        branch=branch_value,
        commit=commit_value,
        claude_cli_version=claude_cli_version,
        cost_usd=cost,
        evidence_path=None,
    )
    receipt.update(
        {
            "from_version": UPGRADE_BASELINE_VERSION,
            "to_version": version,
            "upgrade_source": UPGRADE_SOURCE_LOCAL_MARKETPLACE,
            "commands": commands_value,
            "library_dirs": library_dir_values,
        }
    )
    return _write_kind_receipt(
        project_dir, kind=kind, tag=tag, receipt=receipt, now=now
    )


def write_docs_claims_receipt(
    project_dir: Path,
    *,
    tag: str,
    findings_path: str | Path,
    claude_cli_version: str,
    branch: str | None = None,
    commit: str | None = None,
    now: datetime.datetime | None = None,
) -> Path:
    project_dir = Path(project_dir).resolve(strict=False)
    version = parse_release_tag(tag, context="Docs claims release proof")
    kind = DOCS_CLAIMS_RECEIPT_TYPE
    try:
        findings = json.loads(Path(findings_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Docs claims findings are not readable JSON: {findings_path}: {exc}") from exc
    if not isinstance(findings, list):
        raise ValueError(f"Docs claims findings must be a JSON list: {findings_path}")
    if findings:
        raise ValueError(
            f"Docs claims check reported {len(findings)} findings, so no receipt can be stamped"
        )
    cost = 0.0
    _enforce_spend_cap(
        project_dir,
        release_evidence_dir(project_dir, version),
        kind=kind,
        tag=tag,
        cost=cost,
    )
    evidence_path = _copy_evidence(
        project_dir, kind=kind, version=version, source_path=Path(findings_path)
    )
    branch_value, commit_value = _proof_context(
        project_dir, kind=kind, branch=branch, commit=commit
    )
    receipt = _base_proof_receipt(
        project_dir,
        kind=kind,
        tag=tag,
        version=version,
        branch=branch_value,
        commit=commit_value,
        claude_cli_version=claude_cli_version,
        cost_usd=cost,
        evidence_path=evidence_path,
    )
    receipt["findings_count"] = len(findings)
    return _write_kind_receipt(
        project_dir, kind=kind, tag=tag, receipt=receipt, now=now
    )


def _result_payload(kind: str, path: Path, tag: str, version: str) -> dict:
    return {
        "ok": True,
        "kind": kind,
        "tag": tag,
        "version": version,
        "receipt": str(path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project-dir", type=Path, default=DEFAULT_PROJECT_DIR)
    common.add_argument("--tag", required=True)
    common.add_argument("--claude-cli-version", required=True)

    sub = parser.add_subparsers(dest="proof", required=True)

    p_live = sub.add_parser(LIVE_ENFORCEMENT_RECEIPT_TYPE, parents=[common])
    p_live.add_argument("--junit", type=Path, required=True)
    p_live.add_argument("--cost-usd", type=float, required=True)

    p_routing = sub.add_parser(ROUTING_RECEIPT_TYPE, parents=[common])
    p_routing.add_argument("--summary", type=Path, required=True)

    p_upgrade = sub.add_parser(UPGRADE_PATH_RECEIPT_TYPE, parents=[common])
    p_upgrade.add_argument("--command", action="append", default=[])
    p_upgrade.add_argument("--library-dir", action="append", default=[])

    p_docs = sub.add_parser(DOCS_CLAIMS_RECEIPT_TYPE, parents=[common])
    p_docs.add_argument("--findings", type=Path, required=True)

    args = parser.parse_args(argv)

    try:
        kind = args.proof
        version = parse_release_tag(str(args.tag), context=f"{kind} release proof")
        if kind == LIVE_ENFORCEMENT_RECEIPT_TYPE:
            path = write_live_enforcement_receipt(
                args.project_dir,
                tag=args.tag,
                junit_path=args.junit,
                cost_usd=args.cost_usd,
                claude_cli_version=args.claude_cli_version,
            )
        elif kind == ROUTING_RECEIPT_TYPE:
            path = write_routing_receipt(
                args.project_dir,
                tag=args.tag,
                summary_path=args.summary,
                claude_cli_version=args.claude_cli_version,
            )
        elif kind == UPGRADE_PATH_RECEIPT_TYPE:
            path = write_upgrade_path_receipt(
                args.project_dir,
                tag=args.tag,
                commands=args.command,
                library_dirs=args.library_dir,
                claude_cli_version=args.claude_cli_version,
            )
        else:
            path = write_docs_claims_receipt(
                args.project_dir,
                tag=args.tag,
                findings_path=args.findings,
                claude_cli_version=args.claude_cli_version,
            )
        print(json.dumps(_result_payload(kind, path, args.tag, version)))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())