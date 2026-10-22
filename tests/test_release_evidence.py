"""Phase 6 release gate: local release-proof receipts.

The release gate requires four committed local proof receipts under
docs/release-evidence/<version>/ for a stable-channel release: live-enforcement,
routing, upgrade-path and docs-claims. Only scripts/release_evidence_local.py
writes them, from real run outputs; generate-evidence never self-asserts them.
"""
import json
import subprocess
import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

_SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import release_evidence_local as rel  # noqa: E402
from control_receipts import (  # noqa: E402
    DOCS_CLAIMS_RECEIPT_TYPE,
    LIVE_ENFORCEMENT_RECEIPT_TYPE,
    RELEASE_PROOF_RECEIPT_TYPES,
    RELEASE_PROOF_SPEND_CAP_USD,
    ROUTING_RECEIPT_TYPE,
    UPGRADE_PATH_RECEIPT_TYPE,
    hash_file,
    validate_release_proof_receipt,
)
from maintenance.capability_manifest import (  # noqa: E402
    LOCAL_PROOF_KINDS,
    required_local_proofs,
    validate_manifest,
)
import release_gate  # noqa: E402

ROOT = Path(__file__).parents[1]
LIVE_CASES = ("test_gate_blocks_source_write", "test_gate_reports_test_failure")
LIVE_SUITE_TEXT = (
    "def test_gate_blocks_source_write():\n    pass\n\n\ndef test_gate_reports_test_failure():\n    pass\n"
)
ROUTING_CASES_TEXT = (
    "schema_version: 1\n"
    "cases:\n"
    "  - id: plan-fixture\n"
    "    story: Plan fixture\n"
    "    prompt: fixture\n"
    "    category: plan\n"
    "    workflows: [product-brief]\n"
    "  - id: design-fixture\n"
    "    story: Design fixture\n"
    "    prompt: fixture\n"
    "    category: design\n"
    "    workflows: [design-architecture]\n"
)
FIXTURE_CLI_VERSION = "1.0.99-fixture"
FIXTURE_BRANCH = "main"
FIXTURE_COMMIT = "f" * 40


def _git(project_dir, *args):
    return subprocess.run(
        ["git", "-C", str(project_dir), *args],
        capture_output=True,
        text=True,
        check=True,
    )


def _make_project(tmp_path, *, git=False):
    (tmp_path / "tests" / "live").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "live" / "test_fixture_live.py").write_text(LIVE_SUITE_TEXT, encoding="utf-8")
    (tmp_path / "tests" / "behavioral").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests" / "behavioral" / "routing_cases.yaml").write_text(ROUTING_CASES_TEXT, encoding="utf-8")
    (tmp_path / "skill-library").mkdir(exist_ok=True)
    if git:
        _git(tmp_path, "init")
        _git(tmp_path, "config", "user.email", "tests@sweetclaude.local")
        _git(tmp_path, "config", "user.name", "SweetClaude Tests")
        _git(tmp_path, "checkout", "-b", FIXTURE_BRANCH)
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "proof fixture baseline")
    return tmp_path


def _junit(case_names=LIVE_CASES, *, failures=0, errors=0, skipped=0):
    cases = "".join(
        f'  <testcase classname="tests.live.test_fixture_live" name="{name}"/>\n'
        for name in case_names
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<testsuites><testsuite name="tests.live" tests="{len(case_names)}" '
        f'failures="{failures}" errors="{errors}" skipped="{skipped}">\n'
        f"{cases}</testsuite></testsuites>\n"
    )


def _routing_summary(*, tier="full", planned=2, passed=2, cost=4.5):
    return {
        "executed_at": "20261021T000000Z",
        "model": "sonnet",
        "tier": tier,
        "summary": {
            "planned": planned,
            "runs": planned,
            "passed": passed,
            "graded": planned,
            "statuses": {"pass": passed},
            "cost_usd": cost,
            "unpriced_runs": 0,
        },
        "results": [],
        "diagnostics": [],
    }


def _stage(root, name, content):
    inputs = root / "proof-inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    path = inputs / name
    path.write_text(content, encoding="utf-8")
    return path


def _stamp_all_proofs(project, root, *, tag="v5.1.0", live_cost=1.1, routing_cost=4.5):
    rel.write_live_enforcement_receipt(
        project,
        tag=tag,
        junit_path=_stage(root, "live-junit.xml", _junit()),
        cost_usd=live_cost,
        claude_cli_version=FIXTURE_CLI_VERSION,
        branch=FIXTURE_BRANCH,
        commit=FIXTURE_COMMIT,
    )
    routing_summary = _routing_summary(cost=routing_cost)
    rel.write_routing_receipt(
        project,
        tag=tag,
        summary_path=_stage(root, "routing.json", json.dumps(routing_summary)),
        claude_cli_version=FIXTURE_CLI_VERSION,
        branch=FIXTURE_BRANCH,
        commit=FIXTURE_COMMIT,
    )
    rel.write_upgrade_path_receipt(
        project,
        tag=tag,
        commands=["/plugin marketplace add ./sweetclaude-marketplace", "/plugin install sweetclaude@sweetclaude-stable"],
        library_dirs=["skill-library"],
        claude_cli_version=FIXTURE_CLI_VERSION,
        branch=FIXTURE_BRANCH,
        commit=FIXTURE_COMMIT,
    )
    rel.write_docs_claims_receipt(
        project,
        tag=tag,
        findings_path=_stage(root, "docs-findings.json", "[]\n"),
        claude_cli_version=FIXTURE_CLI_VERSION,
        branch=FIXTURE_BRANCH,
        commit=FIXTURE_COMMIT,
    )


def _evidence_dir(project, version="5.1.0"):
    return project / "docs" / "release-evidence" / version


def _receipt(project, kind, version="5.1.0"):
    return json.loads((_evidence_dir(project, version) / f"{kind}.json").read_text(encoding="utf-8"))


# --- manifest plumbing ---------------------------------------------------------


def test_required_local_proofs_pin_phase6_kinds_for_stable():
    assert set(required_local_proofs("stable")) == {
        LIVE_ENFORCEMENT_RECEIPT_TYPE,
        ROUTING_RECEIPT_TYPE,
        UPGRADE_PATH_RECEIPT_TYPE,
        DOCS_CLAIMS_RECEIPT_TYPE,
    }


def test_required_local_proofs_empty_for_non_stable_channels():
    assert required_local_proofs("legacy") == []
    assert required_local_proofs("beta") == []


def test_proof_receipt_types_match_manifest_local_proof_kinds():
    assert RELEASE_PROOF_RECEIPT_TYPES == frozenset(LOCAL_PROOF_KINDS)


def test_manifest_rejects_unknown_local_proof_kind():
    manifest = yaml.safe_load((ROOT / "config" / "capability-manifest.yaml").read_text(encoding="utf-8"))
    manifest["release"]["required_local_proofs"]["stable"] = ["carrier-pigeon"]
    with pytest.raises(ValueError, match="unknown local proof kinds"):
        validate_manifest(manifest)


def test_manifest_rejects_local_proofs_for_undefined_channel():
    manifest = yaml.safe_load((ROOT / "config" / "capability-manifest.yaml").read_text(encoding="utf-8"))
    manifest["release"]["required_local_proofs"]["imaginary"] = ["routing"]
    with pytest.raises(ValueError, match="defined channel"):
        validate_manifest(manifest)


def test_manifest_rejects_duplicate_local_proof_kinds():
    manifest = yaml.safe_load((ROOT / "config" / "capability-manifest.yaml").read_text(encoding="utf-8"))
    manifest["release"]["required_local_proofs"]["stable"] = ["routing", "routing"]
    with pytest.raises(ValueError, match="duplicate"):
        validate_manifest(manifest)


# --- live-enforcement receipts --------------------------------------------------


def test_writer_stamps_live_enforcement_receipt_from_junit(tmp_path):
    project = _make_project(tmp_path)
    junit_path = _stage(tmp_path, "live-junit.xml", _junit())

    receipt_path = rel.write_live_enforcement_receipt(
        project,
        tag="v5.1.0",
        junit_path=junit_path,
        cost_usd=1.1,
        claude_cli_version=FIXTURE_CLI_VERSION,
        branch=FIXTURE_BRANCH,
        commit=FIXTURE_COMMIT,
    )

    assert receipt_path == _evidence_dir(project) / "live-enforcement.json"
    receipt = _receipt(project, "live-enforcement")
    assert receipt["schema_version"] == 2
    assert receipt["receipt_type"] == "live-enforcement"
    assert receipt["tag"] == "v5.1.0"
    assert receipt["version"] == "5.1.0"
    assert receipt["claude_cli_version"] == FIXTURE_CLI_VERSION
    assert receipt["cost_usd"] == 1.1
    evidence = _evidence_dir(project) / "live-enforcement-junit.xml"
    assert evidence.is_file()
    assert receipt["evidence_path"] == "docs/release-evidence/5.1.0/live-enforcement-junit.xml"
    assert receipt["evidence_sha256"] == hash_file(evidence)
    parsed = validate_release_proof_receipt(
        receipt_path,
        project_dir=project,
        kind="live-enforcement",
        expected_tag="v5.1.0",
    )
    assert parsed["result"] == "pass"


def test_writer_refuses_live_junit_with_skips(tmp_path):
    project = _make_project(tmp_path)
    with pytest.raises(ValueError, match="skips"):
        rel.write_live_enforcement_receipt(
            project,
            tag="v5.1.0",
            junit_path=_stage(tmp_path, "live-junit.xml", _junit(skipped=1)),
            cost_usd=1.1,
            claude_cli_version=FIXTURE_CLI_VERSION,
        )


def test_writer_refuses_live_junit_with_failures(tmp_path):
    project = _make_project(tmp_path)
    with pytest.raises(ValueError, match="failures"):
        rel.write_live_enforcement_receipt(
            project,
            tag="v5.1.0",
            junit_path=_stage(tmp_path, "live-junit.xml", _junit(failures=1)),
            cost_usd=1.1,
            claude_cli_version=FIXTURE_CLI_VERSION,
        )


def test_writer_refuses_live_case_set_mismatch(tmp_path):
    project = _make_project(tmp_path)
    with pytest.raises(ValueError, match="case set mismatch"):
        rel.write_live_enforcement_receipt(
            project,
            tag="v5.1.0",
            junit_path=_stage(tmp_path, "live-junit.xml", _junit([LIVE_CASES[0]])),
            cost_usd=1.1,
            claude_cli_version=FIXTURE_CLI_VERSION,
        )


def test_writer_refuses_live_overspend_against_existing_routing_receipt(tmp_path):
    project = _make_project(tmp_path)
    rel.write_routing_receipt(
        project,
        tag="v5.1.0",
        summary_path=_stage(tmp_path, "routing.json", json.dumps(_routing_summary(cost=5.5))),
        claude_cli_version=FIXTURE_CLI_VERSION,
        branch=FIXTURE_BRANCH,
        commit=FIXTURE_COMMIT,
    )

    with pytest.raises(ValueError, match="spend cap"):
        rel.write_live_enforcement_receipt(
            project,
            tag="v5.1.0",
            junit_path=_stage(tmp_path, "live-junit.xml", _junit()),
            cost_usd=1.1,
            claude_cli_version=FIXTURE_CLI_VERSION,
        )


# --- routing receipts -----------------------------------------------------------


def test_writer_stamps_routing_receipt_from_full_tier_summary(tmp_path):
    project = _make_project(tmp_path)
    receipt_path = rel.write_routing_receipt(
        project,
        tag="v5.1.0",
        summary_path=_stage(tmp_path, "routing.json", json.dumps(_routing_summary())),
        claude_cli_version=FIXTURE_CLI_VERSION,
        branch=FIXTURE_BRANCH,
        commit=FIXTURE_COMMIT,
    )

    assert receipt_path == _evidence_dir(project) / "routing.json"
    receipt = _receipt(project, "routing")
    assert receipt["receipt_type"] == "routing"
    assert receipt["tier"] == "full"
    assert receipt["planned"] == 2
    assert receipt["passed"] == 2
    assert receipt["cost_usd"] == 4.5
    assert (_evidence_dir(project) / "routing-summary.json").is_file()
    validate_release_proof_receipt(
        receipt_path,
        project_dir=project,
        kind="routing",
        expected_tag="v5.1.0",
    )


def test_writer_refuses_routing_below_full_tier(tmp_path):
    project = _make_project(tmp_path)
    with pytest.raises(ValueError, match="full-tier"):
        rel.write_routing_receipt(
            project,
            tag="v5.1.0",
            summary_path=_stage(tmp_path, "routing.json", json.dumps(_routing_summary(tier="smoke", planned=2, passed=2, cost=0.9))),
            claude_cli_version=FIXTURE_CLI_VERSION,
        )


def test_writer_refuses_routing_passed_below_planned(tmp_path):
    project = _make_project(tmp_path)
    with pytest.raises(ValueError, match="noise floor"):
        rel.write_routing_receipt(
            project,
            tag="v5.1.0",
            summary_path=_stage(tmp_path, "routing.json", json.dumps(_routing_summary(passed=1))),
            claude_cli_version=FIXTURE_CLI_VERSION,
        )


def _routing_summary_with_failures(*, planned, passed, diagnostics):
    rows = []
    failed = planned - passed
    for index in range(planned):
        rows.append(
            {
                "case": f"case-{index:02d}",
                "entry": "go",
                "status": "pass" if index >= failed else "no-route",
                "passed": index >= failed,
                "cost_usd": 0.1,
            }
        )
    return {
        "executed_at": "20261021T000000Z",
        "model": "sonnet",
        "tier": "full",
        "summary": {
            "planned": planned,
            "runs": planned,
            "passed": passed,
            "graded": planned,
            "statuses": {"pass": passed},
            "cost_usd": 1.0,
            "unpriced_runs": 0,
        },
        "results": rows,
        "diagnostics": diagnostics,
    }


def _expand_routing_cases(project, count):
    text = "schema_version: 1\ncases:\n" + "".join(
        f"  - id: case-{index:02d}\n    story: Case {index}\n    prompt: fixture\n"
        f"    category: plan\n    workflows: [product-brief]\n"
        for index in range(count)
    )
    (project / "tests" / "behavioral" / "routing_cases.yaml").write_text(text, encoding="utf-8")


def test_writer_stamps_routing_receipt_from_harness_diagnostics_shape(tmp_path):
    project = _make_project(tmp_path)
    _expand_routing_cases(project, 10)
    summary = _routing_summary_with_failures(planned=10, passed=9, diagnostics={})
    summary["diagnostics"] = [
        {
            "case": "case-00",
            "entry": "category",
            "status": "pass",
            "passed": True,
            "detail": "loaded plan/product-discovery",
        }
    ]
    summary["summary"]["diagnostics"] = {"case-00": "pass"}
    receipt_path = rel.write_routing_receipt(
        project,
        tag="v5.1.1",
        summary_path=_stage(tmp_path, "routing.json", json.dumps(summary)),
        claude_cli_version=FIXTURE_CLI_VERSION,
        branch=FIXTURE_BRANCH,
        commit=FIXTURE_COMMIT,
    )
    receipt = _receipt(project, "routing", version="5.1.1")
    assert receipt["passed"] == 10 - 1
    assert receipt["diagnosed_pass"] == 1
    validate_release_proof_receipt(
        receipt_path,
        project_dir=project,
        kind="routing",
        expected_tag="v5.1.1",
    )


def test_writer_stamps_routing_receipt_with_passing_diagnostics(tmp_path):
    project = _make_project(tmp_path)
    _expand_routing_cases(project, 10)
    summary = _routing_summary_with_failures(
        planned=10,
        passed=9,
        diagnostics={f"case-{index:02d}": "pass" for index in range(1)},
    )
    receipt_path = rel.write_routing_receipt(
        project,
        tag="v5.1.0",
        summary_path=_stage(tmp_path, "routing.json", json.dumps(summary)),
        claude_cli_version=FIXTURE_CLI_VERSION,
        branch=FIXTURE_BRANCH,
        commit=FIXTURE_COMMIT,
    )
    receipt = _receipt(project, "routing")
    assert receipt["planned"] == 10
    assert receipt["passed"] == 9
    assert receipt["diagnosed_pass"] == 1
    validate_release_proof_receipt(
        receipt_path,
        project_dir=project,
        kind="routing",
        expected_tag="v5.1.0",
    )


def test_writer_refuses_routing_below_noise_floor(tmp_path):
    project = _make_project(tmp_path)
    _expand_routing_cases(project, 10)
    summary = _routing_summary_with_failures(
        planned=10,
        passed=8,
        diagnostics={f"case-{index:02d}": "pass" for index in range(2)},
    )
    with pytest.raises(ValueError, match="noise floor"):
        rel.write_routing_receipt(
            project,
            tag="v5.1.0",
            summary_path=_stage(tmp_path, "routing.json", json.dumps(summary)),
            claude_cli_version=FIXTURE_CLI_VERSION,
        )


def test_writer_refuses_routing_with_failing_diagnostic(tmp_path):
    project = _make_project(tmp_path)
    _expand_routing_cases(project, 10)
    summary = _routing_summary_with_failures(
        planned=10,
        passed=9,
        diagnostics={"case-00": "no-route"},
    )
    with pytest.raises(ValueError, match="no passing diagnostic"):
        rel.write_routing_receipt(
            project,
            tag="v5.1.0",
            summary_path=_stage(tmp_path, "routing.json", json.dumps(summary)),
            claude_cli_version=FIXTURE_CLI_VERSION,
        )


def test_writer_refuses_routing_with_undiagnosed_failure(tmp_path):
    project = _make_project(tmp_path)
    _expand_routing_cases(project, 10)
    summary = _routing_summary_with_failures(planned=10, passed=9, diagnostics={})
    with pytest.raises(ValueError, match="no passing diagnostic"):
        rel.write_routing_receipt(
            project,
            tag="v5.1.0",
            summary_path=_stage(tmp_path, "routing.json", json.dumps(summary)),
            claude_cli_version=FIXTURE_CLI_VERSION,
        )


# --- upgrade-path receipts -------------------------------------------------------


def test_writer_stamps_upgrade_path_receipt(tmp_path):
    project = _make_project(tmp_path)
    receipt_path = rel.write_upgrade_path_receipt(
        project,
        tag="v5.1.0",
        commands=["/plugin marketplace add ./sweetclaude-marketplace", "/plugin install sweetclaude@sweetclaude-stable"],
        library_dirs=["skill-library"],
        claude_cli_version=FIXTURE_CLI_VERSION,
        branch=FIXTURE_BRANCH,
        commit=FIXTURE_COMMIT,
    )

    assert receipt_path == _evidence_dir(project) / "upgrade-path.json"
    receipt = _receipt(project, "upgrade-path")
    assert receipt["receipt_type"] == "upgrade-path"
    assert receipt["from_version"] == "4.5.3"
    assert receipt["to_version"] == "5.1.0"
    assert receipt["upgrade_source"] == "local-marketplace-clone"
    assert receipt["commands"] == [
        "/plugin marketplace add ./sweetclaude-marketplace",
        "/plugin install sweetclaude@sweetclaude-stable",
    ]
    assert receipt["library_dirs"] == ["skill-library"]
    validate_release_proof_receipt(
        receipt_path,
        project_dir=project,
        kind="upgrade-path",
        expected_tag="v5.1.0",
    )


def test_writer_refuses_upgrade_library_dir_missing(tmp_path):
    project = _make_project(tmp_path)
    with pytest.raises(ValueError, match="library dir does not exist"):
        rel.write_upgrade_path_receipt(
            project,
            tag="v5.1.0",
            commands=["/plugin install sweetclaude@sweetclaude-stable"],
            library_dirs=["skill-library", "gone-library"],
            claude_cli_version=FIXTURE_CLI_VERSION,
        )


def test_writer_refuses_upgrade_without_commands(tmp_path):
    project = _make_project(tmp_path)
    with pytest.raises(ValueError, match="commands"):
        rel.write_upgrade_path_receipt(
            project,
            tag="v5.1.0",
            commands=[],
            library_dirs=["skill-library"],
            claude_cli_version=FIXTURE_CLI_VERSION,
        )


# --- docs-claims receipts --------------------------------------------------------


def test_writer_stamps_docs_claims_receipt_with_zero_findings(tmp_path):
    project = _make_project(tmp_path)
    receipt_path = rel.write_docs_claims_receipt(
        project,
        tag="v5.1.0",
        findings_path=_stage(tmp_path, "docs-findings.json", "[]\n"),
        claude_cli_version=FIXTURE_CLI_VERSION,
        branch=FIXTURE_BRANCH,
        commit=FIXTURE_COMMIT,
    )

    assert receipt_path == _evidence_dir(project) / "docs-claims.json"
    receipt = _receipt(project, "docs-claims")
    assert receipt["receipt_type"] == "docs-claims"
    assert receipt["findings_count"] == 0
    assert receipt["cost_usd"] == 0.0
    assert (_evidence_dir(project) / "docs-claims-findings.json").is_file()
    validate_release_proof_receipt(
        receipt_path,
        project_dir=project,
        kind="docs-claims",
        expected_tag="v5.1.0",
    )


def test_writer_refuses_docs_claims_findings_present(tmp_path):
    project = _make_project(tmp_path)
    with pytest.raises(ValueError, match="findings"):
        rel.write_docs_claims_receipt(
            project,
            tag="v5.1.0",
            findings_path=_stage(
                tmp_path,
                "docs-findings.json",
                json.dumps([{"path": "README.md", "line": 1, "kind": "slash", "claim": "x", "reason": "y"}]),
            ),
            claude_cli_version=FIXTURE_CLI_VERSION,
        )


# --- proof validator unit checks --------------------------------------------------


def test_proof_validator_rejects_wrong_receipt_kind(tmp_path):
    project = _make_project(tmp_path)
    receipt_path = rel.write_routing_receipt(
        project,
        tag="v5.1.0",
        summary_path=_stage(tmp_path, "routing.json", json.dumps(_routing_summary())),
        claude_cli_version=FIXTURE_CLI_VERSION,
        branch=FIXTURE_BRANCH,
        commit=FIXTURE_COMMIT,
    )

    with pytest.raises(ValueError, match="receipt type mismatch"):
        validate_release_proof_receipt(
            receipt_path,
            project_dir=project,
            kind="live-enforcement",
            expected_tag="v5.1.0",
        )


def test_proof_validator_rejects_missing_receipt(tmp_path):
    project = _make_project(tmp_path)
    with pytest.raises(ValueError, match="not found"):
        validate_release_proof_receipt(
            project / "docs" / "release-evidence" / "5.1.0" / "routing.json",
            project_dir=project,
            kind="routing",
            expected_tag="v5.1.0",
        )


def test_proof_validator_rejects_stale_receipt(tmp_path):
    project = _make_project(tmp_path)
    receipt_path = rel.write_routing_receipt(
        project,
        tag="v5.1.0",
        summary_path=_stage(tmp_path, "routing.json", json.dumps(_routing_summary())),
        claude_cli_version=FIXTURE_CLI_VERSION,
        branch=FIXTURE_BRANCH,
        commit=FIXTURE_COMMIT,
    )
    path = _evidence_dir(project) / "routing.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    stale = datetime.now(timezone.utc) - timedelta(days=8)
    receipt["generated_at"] = stale.strftime("%Y-%m-%dT%H:%M:%SZ")
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="older than"):
        validate_release_proof_receipt(
            receipt_path,
            project_dir=project,
            kind="routing",
            expected_tag="v5.1.0",
        )


def test_proof_validator_rejects_tampered_evidence_hash(tmp_path):
    project = _make_project(tmp_path)
    receipt_path = rel.write_live_enforcement_receipt(
        project,
        tag="v5.1.0",
        junit_path=_stage(tmp_path, "live-junit.xml", _junit()),
        cost_usd=1.1,
        claude_cli_version=FIXTURE_CLI_VERSION,
        branch=FIXTURE_BRANCH,
        commit=FIXTURE_COMMIT,
    )
    evidence = _evidence_dir(project) / "live-enforcement-junit.xml"
    evidence.write_text(_junit(failures=1), encoding="utf-8")

    with pytest.raises(ValueError, match="evidence_sha256 mismatch"):
        validate_release_proof_receipt(
            receipt_path,
            project_dir=project,
            kind="live-enforcement",
            expected_tag="v5.1.0",
        )


def test_proof_validator_rejects_cli_version_mismatch(tmp_path):
    project = _make_project(tmp_path)
    receipt_path = rel.write_live_enforcement_receipt(
        project,
        tag="v5.1.0",
        junit_path=_stage(tmp_path, "live-junit.xml", _junit()),
        cost_usd=1.1,
        claude_cli_version=FIXTURE_CLI_VERSION,
        branch=FIXTURE_BRANCH,
        commit=FIXTURE_COMMIT,
    )

    with pytest.raises(ValueError, match="claude CLI version"):
        validate_release_proof_receipt(
            receipt_path,
            project_dir=project,
            kind="live-enforcement",
            expected_tag="v5.1.0",
            expected_claude_cli_version="2.0.0-other",
        )


# --- the proof gate ---------------------------------------------------------------


def test_gate_accepts_valid_proof_bundle(tmp_path):
    project = _make_project(tmp_path)
    _stamp_all_proofs(project, tmp_path)

    result = release_gate.validate_required_release_proofs(
        project,
        channel="stable",
        tag="v5.1.0",
    )

    assert result["checked"] is True
    assert result["kinds"] == sorted(RELEASE_PROOF_RECEIPT_TYPES)
    assert result["spend_usd"] == pytest.approx(5.6)
    assert result["claude_cli_version"] == FIXTURE_CLI_VERSION
    for kind in RELEASE_PROOF_RECEIPT_TYPES:
        assert result["receipts"][kind] == str(_evidence_dir(project) / f"{kind}.json")


def test_gate_rejects_missing_proof_receipt(tmp_path):
    project = _make_project(tmp_path)
    _stamp_all_proofs(project, tmp_path)
    (_evidence_dir(project) / "docs-claims.json").unlink()

    with pytest.raises(ValueError, match="docs-claims"):
        release_gate.validate_required_release_proofs(
            project,
            channel="stable",
            tag="v5.1.0",
        )


def test_gate_rejects_spend_over_cap(tmp_path):
    project = _make_project(tmp_path)
    _stamp_all_proofs(project, tmp_path, live_cost=1.1, routing_cost=4.5)
    summary_path = _evidence_dir(project) / "routing-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["summary"]["cost_usd"] = 5.5
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    receipt_path = _evidence_dir(project) / "routing.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["cost_usd"] = 5.5
    receipt["evidence_sha256"] = hash_file(summary_path)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="\\$6"):
        release_gate.validate_required_release_proofs(
            project,
            channel="stable",
            tag="v5.1.0",
        )

    assert RELEASE_PROOF_SPEND_CAP_USD == 6.0


def test_gate_rejects_mixed_claude_cli_versions(tmp_path):
    project = _make_project(tmp_path)
    _stamp_all_proofs(project, tmp_path)
    path = _evidence_dir(project) / "upgrade-path.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["claude_cli_version"] = "0.0.1-drifted"
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="claude CLI version"):
        release_gate.validate_required_release_proofs(
            project,
            channel="stable",
            tag="v5.1.0",
        )


def test_gate_requires_no_local_proofs_for_legacy_channel(tmp_path):
    project = _make_project(tmp_path)

    result = release_gate.validate_required_release_proofs(
        project,
        channel="legacy",
        tag="v3.9.9",
    )

    assert result["checked"] is False


# --- generate-evidence never self-asserts local proofs ----------------------------


def test_generate_evidence_refuses_self_asserted_local_proof_kinds(tmp_path, monkeypatch):
    monkeypatch.setattr(
        release_gate,
        "required_release_checks",
        lambda: {"tests", ROUTING_RECEIPT_TYPE},
    )
    (tmp_path / "package.json").write_text(json.dumps({"name": "sweetclaude", "version": "5.1.0"}), encoding="utf-8")

    with pytest.raises(ValueError, match="release_evidence_local"):
        release_gate.generate_release_evidence(
            tmp_path,
            tag="v5.1.0",
            channel="stable",
            branch="main",
        )


# --- CLI ---------------------------------------------------------------------------


def test_cli_stamps_docs_claims_receipt(tmp_path):
    project = _make_project(tmp_path, git=True)
    findings = _stage(tmp_path, "docs-findings.json", "[]\n")

    completed = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "release_evidence_local.py"),
            "docs-claims",
            "--project-dir",
            str(project),
            "--tag",
            "v5.1.0",
            "--findings",
            str(findings),
            "--claude-cli-version",
            FIXTURE_CLI_VERSION,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    out = json.loads(completed.stdout)
    assert out["ok"] is True
    assert (_evidence_dir(project) / "docs-claims.json").is_file()


def test_cli_rejects_invalid_tag(tmp_path):
    project = _make_project(tmp_path, git=True)

    completed = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "release_evidence_local.py"),
            "docs-claims",
            "--project-dir",
            str(project),
            "--tag",
            "5.1.0",
            "--findings",
            str(_stage(tmp_path, "docs-findings.json", "[]\n")),
            "--claude-cli-version",
            FIXTURE_CLI_VERSION,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    out = json.loads(completed.stdout)
    assert out["ok"] is False