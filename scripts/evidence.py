#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""SweetClaude evidence receipts for high-stakes workflow claims."""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path


PASS_STATUSES = {"pass", "passed", "ok", "success"}
SUPPORTED_RECEIPT_TYPES = {
    "completion",
    "verification",
    "ship",
    "release",
    "external-close",
}


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")
    return slug or "receipt"


def _receipt_dir(project_dir: Path) -> Path:
    return project_dir / ".sweetclaude" / "state" / "evidence"


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"Evidence receipt not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"Evidence receipt is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Evidence receipt must be a JSON object")
    return data


def validate_receipt(
    receipt_path: str | Path,
    *,
    subject_id: str | None = None,
    receipt_type: str | None = None,
    require_verified: bool = False,
) -> dict:
    """Validate a receipt and return the parsed receipt.

    Receipts intentionally use a small schema so skills can create them from
    real command output without depending on a database.
    """
    path = Path(receipt_path)
    data = _load_json(path)

    if data.get("schema_version") != 1:
        raise ValueError("Evidence receipt schema_version must be 1")

    actual_subject = data.get("subject_id")
    if subject_id and actual_subject != subject_id:
        raise ValueError(
            f"Evidence receipt subject mismatch: expected {subject_id}, got {actual_subject}"
        )

    actual_type = data.get("receipt_type")
    if actual_type not in SUPPORTED_RECEIPT_TYPES:
        raise ValueError(
            f"Unsupported evidence receipt_type {actual_type!r}; "
            f"supported: {sorted(SUPPORTED_RECEIPT_TYPES)}"
        )
    if receipt_type and actual_type != receipt_type:
        raise ValueError(
            f"Evidence receipt type mismatch: expected {receipt_type}, got {actual_type}"
        )

    status = str(data.get("status", "")).lower()
    if status not in PASS_STATUSES:
        raise ValueError(f"Evidence receipt status must be pass, got {status!r}")

    checks = data.get("checks")
    if not isinstance(checks, list) or not checks:
        raise ValueError("Evidence receipt must include at least one check")

    for index, check in enumerate(checks, start=1):
        if not isinstance(check, dict):
            raise ValueError(f"Evidence check #{index} must be an object")
        name = str(check.get("name", "")).strip()
        if not name:
            raise ValueError(f"Evidence check #{index} is missing name")
        check_status = str(check.get("status", "")).lower()
        if check_status not in PASS_STATUSES:
            raise ValueError(
                f"Evidence check {name!r} must pass before completion; got {check_status!r}"
            )
        evidence_fields = ("command", "summary", "evidence_path")
        if not any(str(check.get(key, "")).strip() for key in evidence_fields):
            raise ValueError(
                f"Evidence check {name!r} needs command, summary, or evidence_path"
            )

    # Last, so a receipt that is wrong in a more specific way — wrong subject,
    # wrong type, failing status — reports that instead. "Re-run with --run" is
    # unhelpful advice when the real problem is that this is another item's
    # receipt.
    if require_verified and not data.get("verified"):
        raise ValueError(
            "Evidence receipt was not verified: its command was recorded but "
            "never executed. Re-run with `evidence.py write --run`, or via "
            "sweetclaude:code-verify, so the result is observed rather than "
            "asserted."
        )

    return data


OUTPUT_TAIL_CHARS = 2000


def run_check(command: str, project_dir: Path, timeout: int = 1800) -> dict:
    """Execute a check and report what actually happened (ISSUE-283).

    Until this existed, a receipt recorded whatever it was told. A passing
    receipt for `npm test` was written against a project with no test script
    and nothing objected — the completion gate accepted an assertion.
    """
    import subprocess

    try:
        proc = subprocess.run(command, shell=True, cwd=str(project_dir),
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": "fail", "verified": True, "exit_code": None,
                "output_tail": f"timed out after {timeout}s"}
    except OSError as exc:
        return {"status": "fail", "verified": True, "exit_code": None,
                "output_tail": f"could not execute: {exc}"}

    combined = (proc.stdout or "") + (proc.stderr or "")
    return {
        "status": "pass" if proc.returncode == 0 else "fail",
        "verified": True,
        "exit_code": proc.returncode,
        "output_tail": combined[-OUTPUT_TAIL_CHARS:],
    }


def write_receipt(
    project_dir: Path,
    *,
    subject_id: str,
    receipt_type: str,
    check_name: str,
    status: str,
    command: str | None = None,
    summary: str | None = None,
    evidence_path: str | None = None,
    run: bool = False,
) -> Path:
    if receipt_type not in SUPPORTED_RECEIPT_TYPES:
        raise ValueError(
            f"Unsupported evidence receipt_type {receipt_type!r}; "
            f"supported: {sorted(SUPPORTED_RECEIPT_TYPES)}"
        )
    executed = None
    if run:
        if not command:
            raise ValueError("--run needs a --command to execute")
        executed = run_check(command, project_dir)
        # What happened wins over what was claimed. Preserving a caller's
        # optimistic status here would defeat the entire point of running it.
        status = executed["status"]

    check = {
        "name": check_name,
        "status": status,
        "command": command,
        "summary": summary,
        "evidence_path": evidence_path,
        # False means nobody watched this run. It is the difference between
        # evidence and a claim, and it is recorded rather than assumed.
        "verified": bool(executed),
    }
    if executed:
        check["exit_code"] = executed["exit_code"]
        check["output_tail"] = executed["output_tail"]

    receipt = {
        "schema_version": 1,
        "receipt_type": receipt_type,
        "subject_id": subject_id,
        "status": status,
        "verified": bool(executed),
        "created_at": _now(),
        "checks": [{k: v for k, v in check.items() if v is not None}],
    }
    out_dir = _receipt_dir(project_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{_slug(subject_id)}-{_slug(receipt_type)}-{_slug(receipt['created_at'])}.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    validate_receipt(path, subject_id=subject_id, receipt_type=receipt_type)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SweetClaude evidence receipt CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_validate = sub.add_parser("validate")
    p_validate.add_argument("--receipt", required=True)
    p_validate.add_argument("--subject-id", default=None)
    p_validate.add_argument("--receipt-type", default=None)
    p_validate.add_argument("--require-verified", action="store_true",
                            help="reject a receipt whose command was never executed")

    p_write = sub.add_parser("write")
    p_write.add_argument("--project-dir", required=True, type=Path)
    p_write.add_argument("--subject-id", required=True)
    p_write.add_argument("--receipt-type", required=True)
    p_write.add_argument("--check", required=True)
    p_write.add_argument("--status", default="pass")
    p_write.add_argument("--command", default=None)
    p_write.add_argument("--summary", default=None)
    p_write.add_argument("--evidence-path", default=None)
    p_write.add_argument("--run", action="store_true",
                         help="execute --command and record the real result; "
                              "without this the receipt is marked unverified")

    args = parser.parse_args(argv)

    try:
        if args.cmd == "validate":
            receipt = validate_receipt(
                args.receipt,
                subject_id=args.subject_id,
                receipt_type=args.receipt_type,
                require_verified=args.require_verified,
            )
            print(json.dumps({
                "ok": True,
                "subject_id": receipt.get("subject_id"),
                "receipt_type": receipt.get("receipt_type"),
                "verified": receipt.get("verified", False),
            }))
            return 0

        if args.cmd == "write":
            path = write_receipt(
                args.project_dir.resolve(),
                subject_id=args.subject_id,
                receipt_type=args.receipt_type,
                check_name=args.check,
                status=args.status,
                command=args.command,
                summary=args.summary,
                evidence_path=args.evidence_path,
                run=args.run,
            )
            receipt = json.loads(path.read_text(encoding="utf-8"))
            print(json.dumps({"ok": True, "receipt": str(path),
                              "verified": receipt.get("verified", False),
                              "status": receipt.get("status")}))
            return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
