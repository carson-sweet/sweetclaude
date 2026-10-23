import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from control_receipts import (
    BACKLOG_PROMOTION_RECEIPT_TYPE,
    CHANGE_CONTEXT_RECEIPT_TYPE,
    FINDING_DISPOSITION_RECEIPT_TYPE,
    INVARIANT_TEST_RECEIPT_TYPE,
    OBJECTIVE_CRITERIA_RECEIPT_TYPE,
    PHASE_EXIT_RECEIPT_TYPE,
    hash_file,
    validate_backlog_promotion_receipt,
    validate_change_context_receipt,
    validate_finding_disposition_gate,
    validate_phase_exit_receipt,
    validate_status_closure_gate,
)


REQUIRED_RELEASE_CHECKS = [
    "tests",
    "channel-isolation",
    "installation-smoke",
    "static-checks",
    "release-metadata",
    "manifest-validation",
    "release-identity",
    "docs-capability",
    "public-distribution",
]


def _current_test_commit(project_dir: Path) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(project_dir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def _current_test_branch(project_dir: Path) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(project_dir), "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def _write_control_receipt(path: Path, receipt_type: str, **overrides) -> Path:
    commit = _current_test_commit(path.parent) or "abc123"
    branch = _current_test_branch(path.parent) or "beta-4.x"
    data = {
        "schema_version": 2,
        "receipt_type": receipt_type,
        "receipt_id": path.stem,
        "generated_at": "2026-05-26T12:00:00Z",
        "command_or_workflow_step": "test",
        "cwd": str(path.parent),
        "repo_root": str(path.parent),
        "branch": branch,
        "commit": commit,
        "result": "pass",
        "input_artifacts": [],
    }
    data.update(overrides)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _objective_receipt(tmp_path: Path) -> Path:
    return _write_control_receipt(
        tmp_path / "objective.json",
        OBJECTIVE_CRITERIA_RECEIPT_TYPE,
        criteria=[
            {
                "id": "C-001",
                "description": "all high-risk findings dispositioned",
                "evidence_type": "phase_exit_receipt",
            }
        ],
    )


def _phase_exit_receipt(tmp_path: Path) -> Path:
    return _write_control_receipt(
        tmp_path / "phase-exit.json",
        PHASE_EXIT_RECEIPT_TYPE,
        required_artifacts=["story-packet", "test-output"],
        checks=[
            {
                "name": "focused-tests",
                "status": "pass",
                "evidence": "pytest -q tests/test_workflow_closure_controls.py",
            }
        ],
        findings=[],
        outcome="pass",
    )


def _finding_disposition_receipt(tmp_path: Path, finding_id: str, status: str = "backlogged") -> Path:
    return _write_control_receipt(
        tmp_path / f"{finding_id}-disposition.json",
        FINDING_DISPOSITION_RECEIPT_TYPE,
        finding_id=finding_id,
        severity="High",
        disposition_status=status,
        owner="release-owner",
        evidence="review packet and failing test output",
        authority="release-owner",
        rationale="tracked before phase closure",
    )


def _backlog_promotion_receipt(tmp_path: Path, discovery_id: str) -> Path:
    return _write_control_receipt(
        tmp_path / f"{discovery_id}-backlog.json",
        BACKLOG_PROMOTION_RECEIPT_TYPE,
        discovery_id=discovery_id,
        discovery_type="failing_test",
        backlog_item_id="ISSUE-999",
        backlog_item_path=".sweetclaude/product/backlog/ISSUE-999-example.md",
    )


def _change_context_receipt(tmp_path: Path) -> Path:
    return _write_control_receipt(
        tmp_path / "change-context.json",
        CHANGE_CONTEXT_RECEIPT_TYPE,
        recent_commits=["abc123 harden workflow gates"],
        dirty_state=["scripts/control_receipts.py"],
        branch_divergence="none",
        open_prs=[],
        touched_files=["scripts/control_receipts.py", "scripts/release_gate.py"],
        impact_classification="high",
        decision="proceed",
    )


def test_t017_status_closure_rejects_artifact_only_completion(tmp_path):
    phase_exit = _phase_exit_receipt(tmp_path)

    with pytest.raises(ValueError, match="objective criteria"):
        validate_status_closure_gate(
            subject_id="MS-007",
            objective_criteria_receipt_path=None,
            phase_exit_receipt_path=phase_exit,
            findings=[],
            finding_disposition_receipt_paths=[],
            discoveries=[],
            backlog_promotion_receipt_paths=[],
        )


def test_t017_status_closure_accepts_objective_criteria_and_phase_exit(tmp_path):
    result = validate_status_closure_gate(
        subject_id="MS-007",
        objective_criteria_receipt_path=_objective_receipt(tmp_path),
        phase_exit_receipt_path=_phase_exit_receipt(tmp_path),
        findings=[],
        finding_disposition_receipt_paths=[],
        discoveries=[],
        backlog_promotion_receipt_paths=[],
    )

    assert result["ok"] is True


def test_t017a_phase_exit_requires_artifacts_checks_findings_and_outcome(tmp_path):
    receipt = _write_control_receipt(
        tmp_path / "phase-exit.json",
        PHASE_EXIT_RECEIPT_TYPE,
        required_artifacts=["story-packet"],
        checks=[],
        findings=[],
        outcome="pass",
    )

    with pytest.raises(ValueError, match="checks"):
        validate_phase_exit_receipt(receipt)


def test_t018_high_finding_blocks_without_disposition(tmp_path):
    findings = [{"id": "GNG-001", "severity": "High", "status": "open"}]

    with pytest.raises(ValueError, match="GNG-001"):
        validate_finding_disposition_gate(
            findings,
            disposition_receipt_paths=[],
        )


def test_t018_high_finding_passes_with_backlogged_disposition(tmp_path):
    findings = [{"id": "GNG-001", "severity": "High", "status": "open"}]

    result = validate_finding_disposition_gate(
        findings,
        disposition_receipt_paths=[_finding_disposition_receipt(tmp_path, "GNG-001")],
    )

    assert result["ok"] is True


def test_t018_finding_disposition_must_match_finding_severity(tmp_path):
    findings = [{"id": "GNG-001", "severity": "Critical", "status": "open"}]

    with pytest.raises(ValueError, match="severity mismatch"):
        validate_finding_disposition_gate(
            findings,
            disposition_receipt_paths=[_finding_disposition_receipt(tmp_path, "GNG-001")],
        )


def test_t019_backlog_capture_blocks_untracked_discovery(tmp_path):
    discoveries = [
        {"id": "pytest-full-suite", "type": "failing_test", "severity": "High"}
    ]

    with pytest.raises(ValueError, match="pytest-full-suite"):
        validate_status_closure_gate(
            subject_id="MS-007",
            objective_criteria_receipt_path=_objective_receipt(tmp_path),
            phase_exit_receipt_path=_phase_exit_receipt(tmp_path),
            findings=[],
            finding_disposition_receipt_paths=[],
            discoveries=discoveries,
            backlog_promotion_receipt_paths=[],
        )


def test_t019_backlog_capture_passes_with_backlog_item(tmp_path):
    discoveries = [
        {"id": "pytest-full-suite", "type": "failing_test", "severity": "High"}
    ]

    result = validate_status_closure_gate(
        subject_id="MS-007",
        objective_criteria_receipt_path=_objective_receipt(tmp_path),
        phase_exit_receipt_path=_phase_exit_receipt(tmp_path),
        findings=[],
        finding_disposition_receipt_paths=[],
        discoveries=discoveries,
        backlog_promotion_receipt_paths=[
            _backlog_promotion_receipt(tmp_path, "pytest-full-suite")
        ],
    )

    assert result["ok"] is True


def test_t019_backlog_promotion_accepts_no_action_rationale(tmp_path):
    receipt = _write_control_receipt(
        tmp_path / "no-action.json",
        BACKLOG_PROMOTION_RECEIPT_TYPE,
        discovery_id="known-flake",
        discovery_type="failing_test",
        no_action_rationale="known external flake already tracked upstream",
        no_action_authority="test-owner",
        no_action_scope="this validation run",
    )

    parsed = validate_backlog_promotion_receipt(receipt)

    assert parsed["discovery_id"] == "known-flake"


def test_t019_no_action_rationale_requires_authority_and_scope(tmp_path):
    receipt = _write_control_receipt(
        tmp_path / "weak-no-action.json",
        BACKLOG_PROMOTION_RECEIPT_TYPE,
        discovery_id="known-flake",
        discovery_type="failing_test",
        no_action_rationale="known external flake",
    )

    with pytest.raises(ValueError, match="no-action authority"):
        validate_backlog_promotion_receipt(receipt)


def test_t025_change_context_requires_decision_and_impact(tmp_path):
    receipt = _write_control_receipt(
        tmp_path / "change-context.json",
        CHANGE_CONTEXT_RECEIPT_TYPE,
        recent_commits=[],
        dirty_state=[],
        branch_divergence="none",
        open_prs=[],
        touched_files=["scripts/status.py"],
    )

    with pytest.raises(ValueError, match="impact_classification"):
        validate_change_context_receipt(receipt)


def test_t025_change_context_accepts_complete_receipt(tmp_path):
    parsed = validate_change_context_receipt(_change_context_receipt(tmp_path))

    assert parsed["decision"] == "proceed"


def _write_release_project(project_dir: Path, version: str = "3.9.0") -> None:
    (project_dir / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (project_dir / "skill-library" / "configure" / "recover").mkdir(parents=True, exist_ok=True)
    (project_dir / "config").mkdir(parents=True, exist_ok=True)
    (project_dir / "hooks").mkdir(parents=True, exist_ok=True)
    (project_dir / "dist").mkdir(parents=True, exist_ok=True)
    (project_dir / "package.json").write_text(
        json.dumps({"name": "sweetclaude", "version": version}, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_dir / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "sweetclaude", "version": version}, indent=2) + "\n",
        encoding="utf-8",
    )
    (project_dir / "skill-library" / "configure" / "recover" / "SKILL.md").write_text(
        "Invoke /sweetclaude:configure recover for recovery.\n",
        encoding="utf-8",
    )
    (project_dir / "config" / "capability-manifest.yaml").write_text(
        "capabilities:\n  slash-commands: true\n  hooks: true\n",
        encoding="utf-8",
    )
    (project_dir / "hooks" / "session-preflight.sh").write_text(
        "#!/bin/sh\nexit 0\n",
        encoding="utf-8",
    )
    (project_dir / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## [{version}] -- 2026-05-26\n\n- Test release.\n",
        encoding="utf-8",
    )
    (project_dir / "dist" / f"sweetclaude-{version}.tgz").write_text(
        "artifact\n",
        encoding="utf-8",
    )
    (project_dir / "dist" / "sweetclaude-5.99.0.tgz").write_text(
        "stable artifact\n",
        encoding="utf-8",
    )
    (project_dir / "dist" / "sweetclaude-4.1.99-beta.tgz").write_text(
        "beta artifact\n",
        encoding="utf-8",
    )
    (project_dir / "dist" / "sweetclaude-3.99.0.tgz").write_text(
        "legacy artifact\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(project_dir), "init"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(project_dir), "config", "user.email", "tests@sweetclaude.local"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(project_dir), "config", "user.name", "SweetClaude Tests"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(project_dir), "remote", "add", "origin", "https://example.invalid/sweetclaude.git"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(project_dir), "checkout", "-b", "stable-3.x"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(project_dir), "add", "package.json", ".claude-plugin", "skill-library", "CHANGELOG.md", "config", "dist", "hooks"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(project_dir), "commit", "-m", "release candidate"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(project_dir), "tag", f"v{version}"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(project_dir), "update-ref", "refs/remotes/origin/stable-3.x", "HEAD"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(project_dir), "config", "branch.stable-3.x.remote", "origin"], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(project_dir), "config", "branch.stable-3.x.merge", "refs/heads/stable-3.x"], check=True, capture_output=True, text=True)


def _release_check(name: str, **fields) -> dict:
    check = {
        "name": name,
        "status": "pass",
        "command": f"verify {name}",
        "summary": f"{name} passed",
    }
    check.update(fields)
    return check


def _write_release_identity_receipt(
    project_dir: Path,
    *,
    version: str,
    tag: str,
    channel: str,
    branch: str,
) -> Path:
    commit = _current_test_commit(project_dir) or "abc123"
    artifact = project_dir / "dist" / f"sweetclaude-{version}.tgz"
    build_receipt = _write_release_artifact_build_receipt(
        project_dir,
        artifact,
        branch=branch,
        commit=commit,
        tag=tag,
    )
    channel_defaults = {
        "stable": ("v5.99.0", project_dir / "dist" / "sweetclaude-5.99.0.tgz"),
        "beta": ("v4.1.99-beta", project_dir / "dist" / "sweetclaude-4.1.99-beta.tgz"),
        "legacy": ("v3.99.0", project_dir / "dist" / "sweetclaude-3.99.0.tgz"),
    }
    update_discovery: dict[str, dict] = {}
    for discovery_channel, (default_tag, default_artifact) in channel_defaults.items():
        if discovery_channel == channel:
            discovery_tag, discovery_artifact = tag, artifact
        else:
            discovery_tag, discovery_artifact = default_tag, default_artifact
        if not discovery_artifact.exists():
            discovery_artifact.write_text(f"{discovery_channel} artifact\n", encoding="utf-8")
        command = f"git ls-remote --tags origin {discovery_tag}"
        execution = _write_update_discovery_execution_receipt(
            project_dir,
            discovery_artifact,
            branch=branch,
            commit=commit,
            channel=discovery_channel,
            tag=discovery_tag,
            command=command,
        )
        update_discovery[discovery_channel] = {
            "channel": discovery_channel,
            "tag": discovery_tag,
            "artifact": str(discovery_artifact),
            "artifact_sha256": hash_file(discovery_artifact),
            "source": f"{discovery_channel} release discovery",
            "command": command,
            "last_run_result": "pass",
            "execution_receipt_path": str(execution),
        }
    return _write_control_receipt(
        project_dir / ".sweetclaude" / "state" / "evidence" / f"{tag}-release-identity.json",
        "release-identity",
        repo_root=str(project_dir),
        branch=branch,
        commit=commit,
        tag=tag,
        package_version=version,
        plugin_version=version,
        changelog_version=version,
        channel=channel,
        update_discovery=update_discovery,
        install_path=str(project_dir),
        artifact_path=str(artifact),
        artifact_sha256=hash_file(artifact),
        build_receipt_path=str(build_receipt),
    )


def _write_release_artifact_build_receipt(
    project_dir: Path,
    artifact: Path,
    *,
    branch: str,
    commit: str,
    tag: str,
) -> Path:
    return _write_control_receipt(
        project_dir / ".sweetclaude" / "state" / "evidence" / f"{tag}-{artifact.name}-build.json",
        "release-artifact-build",
        repo_root=str(project_dir),
        branch=branch,
        commit=commit,
        tag=tag,
        build_command=f"python -m build {artifact.name}",
        run_at="2026-05-26T12:00:00Z",
        exit_code=0,
        source_clean_state="clean",
        artifact_path=str(artifact),
        artifact_sha256=hash_file(artifact),
    )


def _write_update_discovery_execution_receipt(
    project_dir: Path,
    artifact: Path,
    *,
    branch: str,
    commit: str,
    channel: str,
    tag: str,
    command: str,
) -> Path:
    stdout = project_dir / ".sweetclaude" / "state" / "evidence" / f"{channel}-{tag}-discovery.stdout"
    stderr = project_dir / ".sweetclaude" / "state" / "evidence" / f"{channel}-{tag}-discovery.stderr"
    stdout.parent.mkdir(parents=True, exist_ok=True)
    stdout.write_text(
        json.dumps(
            {
                "channel": channel,
                "tag": tag,
                "artifact": str(artifact),
                "artifact_sha256": hash_file(artifact),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    stderr.write_text("", encoding="utf-8")
    return _write_control_receipt(
        project_dir / ".sweetclaude" / "state" / "evidence" / f"{channel}-{tag}-discovery-execution.json",
        "update-discovery-execution",
        repo_root=str(project_dir),
        branch=branch,
        commit=commit,
        channel=channel,
        command=command,
        run_at="2026-05-26T12:00:00Z",
        exit_code=0,
        stdout_path=str(stdout),
        stdout_sha256=hash_file(stdout),
        stderr_path=str(stderr),
        stderr_sha256=hash_file(stderr),
        resolved_channel=channel,
        resolved_tag=tag,
        resolved_artifact=str(artifact),
        resolved_artifact_sha256=hash_file(artifact),
    )


def _write_public_distribution_receipt(project_dir: Path) -> Path:
    commit = _current_test_commit(project_dir) or "abc123"
    inventory = _write_public_distribution_inventory_receipt(project_dir, commit=commit)
    return _write_control_receipt(
        project_dir / ".sweetclaude" / "state" / "evidence" / "public-distribution.json",
        "public-distribution",
        repo_root=str(project_dir),
        branch="stable-3.x",
        commit=commit,
        permissions=["read project files", "write approved maintenance outputs"],
        installed_user_file_access=[".sweetclaude/", ".claude/"],
        network_access=["git remote tag/update discovery"],
        hooks=["hooks/session-preflight.sh"],
        project_mutation_commands=["/sweetclaude:configure migrate", "/sweetclaude:configure recover"],
        provider_bound_data=["Claude Code prompt and local project context"],
        auth_assumptions=["Claude Code local user approval gates mutating commands"],
        secrets_handling="does not require or persist provider secrets",
        channel_visibility="stable and beta channels are separately visible",
        marketplace_or_distribution_visibility="public plugin distribution",
        evidence_source="release distribution review",
        approved_trust_model="public plugin may inspect project files only for declared maintenance commands",
        inventory_receipt_path=str(inventory),
    )


def _write_public_distribution_inventory_receipt(project_dir: Path, *, commit: str) -> Path:
    return _write_control_receipt(
        project_dir / ".sweetclaude" / "state" / "evidence" / "public-distribution-inventory.json",
        "public-distribution-inventory",
        repo_root=str(project_dir),
        branch="stable-3.x",
        commit=commit,
        manifest_capabilities=["slash-commands", "hooks"],
        installed_plugin_files=[
            ".claude-plugin/plugin.json",
            "skill-library/configure/recover/SKILL.md",
        ],
        hook_files=["hooks/session-preflight.sh"],
        mutation_commands=["/sweetclaude:configure migrate", "/sweetclaude:configure recover"],
        network_commands=["git ls-remote --tags origin"],
        generated_from=["config/capability-manifest.yaml", ".claude-plugin/plugin.json"],
        capability_manifest_path="config/capability-manifest.yaml",
        input_artifacts=[
            {
                "path": "config/capability-manifest.yaml",
                "sha256": hash_file(project_dir / "config" / "capability-manifest.yaml"),
            },
            {
                "path": ".claude-plugin/plugin.json",
                "sha256": hash_file(project_dir / ".claude-plugin" / "plugin.json"),
            },
            {
                "path": "skill-library/configure/recover/SKILL.md",
                "sha256": hash_file(project_dir / "skill-library" / "configure" / "recover" / "SKILL.md"),
            },
            {
                "path": "hooks/session-preflight.sh",
                "sha256": hash_file(project_dir / "hooks" / "session-preflight.sh"),
            },
        ],
    )


def _write_docs_capability_receipt(project_dir: Path) -> Path:
    commit = _current_test_commit(project_dir) or "abc123"
    smoke_output = project_dir / ".sweetclaude" / "state" / "evidence" / "docs-smoke.txt"
    smoke_output.parent.mkdir(parents=True, exist_ok=True)
    smoke_output.write_text("installed command smoke passed\n", encoding="utf-8")
    stderr = project_dir / ".sweetclaude" / "state" / "evidence" / "docs-smoke.stderr"
    stderr.write_text("", encoding="utf-8")
    version_data = json.loads((project_dir / "package.json").read_text(encoding="utf-8"))
    artifact = project_dir / "dist" / f"sweetclaude-{version_data['version']}.tgz"
    installed_smoke = _write_control_receipt(
        project_dir / ".sweetclaude" / "state" / "evidence" / "installed-smoke.json",
        "installed-smoke",
        repo_root=str(project_dir),
        branch="stable-3.x",
        commit=commit,
        installed_entrypoint="/sweetclaude:configure recover",
        installed_path=str(project_dir),
        plugin_identity="sweetclaude",
        installed_manifest_path=str(project_dir / ".claude-plugin" / "plugin.json"),
        installed_manifest_sha256=hash_file(project_dir / ".claude-plugin" / "plugin.json"),
        command="claude /sweetclaude:configure recover --help",
        run_at="2026-05-26T12:00:00Z",
        exit_code=0,
        stdout_path=str(smoke_output),
        stdout_sha256=hash_file(smoke_output),
        stderr_path=str(stderr),
        stderr_sha256=hash_file(stderr),
        entrypoint_lookup_result="/sweetclaude:configure recover found in installed plugin",
        entrypoint_source_paths=[
            {
                "path": str(project_dir / "skill-library" / "configure" / "recover" / "SKILL.md"),
                "sha256": hash_file(project_dir / "skill-library" / "configure" / "recover" / "SKILL.md"),
            }
        ],
        release_artifact_path=str(artifact),
        release_artifact_sha256=hash_file(artifact),
    )
    return _write_control_receipt(
        project_dir / ".sweetclaude" / "state" / "evidence" / "docs-capability.json",
        "docs-capability",
        repo_root=str(project_dir),
        branch="stable-3.x",
        commit=commit,
        claims=[
            {
                "claim": "/sweetclaude:configure repairs project state",
                "status": "proven",
                "installed_entrypoint": "/sweetclaude:configure recover",
                "installed_path": str(project_dir),
                "plugin_identity": "sweetclaude",
                "smoke_command": "claude /sweetclaude:configure recover --help",
                "run_at": "2026-05-26T12:00:00Z",
                "last_run_result": "pass",
                "exit_code": 0,
                "smoke_output_path": str(smoke_output),
                "smoke_output_sha256": hash_file(smoke_output),
                "installed_smoke_receipt_path": str(installed_smoke),
            }
        ],
    )


def _write_release_receipt(
    project_dir: Path,
    *,
    checks: list[dict],
    risk_severity: str = "High",
) -> Path:
    version = "3.9.0"
    tag = "v3.9.0"
    channel = "legacy"
    branch = "stable-3.x"
    for check in checks:
        if check.get("evidence_path"):
            continue
        if check.get("name") == "release-identity":
            check["evidence_path"] = str(
                _write_release_identity_receipt(
                    project_dir,
                    version=version,
                    tag=tag,
                    channel=channel,
                    branch=branch,
                )
            )
        if check.get("name") == "public-distribution":
            check["evidence_path"] = str(_write_public_distribution_receipt(project_dir))
        if check.get("name") == "docs-capability":
            check["evidence_path"] = str(_write_docs_capability_receipt(project_dir))
    commit = _current_test_commit(project_dir) or "abc123"
    receipt = {
        "schema_version": 1,
        "receipt_type": "release",
        "subject_id": "release:v3.9.0",
        "status": "pass",
        "created_at": "2026-05-26T12:00:00Z",
        "commit": commit,
        "risk_severity": risk_severity,
        "checks": checks,
    }
    path = project_dir / ".sweetclaude" / "state" / "evidence" / "v3.9.0-release.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return path


def _invariant_receipt(tmp_path: Path) -> Path:
    test_file = tmp_path / "tests" / "test_invariant.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_invariant():\n    assert True\n", encoding="utf-8")
    return _write_control_receipt(
        tmp_path / "invariant-test.json",
        INVARIANT_TEST_RECEIPT_TYPE,
        test_file="tests/test_invariant.py",
        test_command="pytest -q tests/test_invariant.py",
        expected_assertion="historical bypass is blocked",
        last_run_result="pass",
    )


def test_status_closure_gate_cli_accepts_complete_receipts(tmp_path):
    completed = __import__("subprocess").run(
        [
            "python3",
            str(Path(__file__).parents[1] / "scripts" / "control_receipts.py"),
            "validate-status-closure",
            "--subject-id",
            "MS-007",
            "--objective-criteria-receipt",
            str(_objective_receipt(tmp_path)),
            "--phase-exit-receipt",
            str(_phase_exit_receipt(tmp_path)),
            "--findings-json",
            json.dumps([{"id": "GNG-001", "severity": "High", "status": "open"}]),
            "--finding-disposition-receipt",
            str(_finding_disposition_receipt(tmp_path, "GNG-001")),
            "--discoveries-json",
            json.dumps([{"id": "pytest-full-suite", "type": "failing_test"}]),
            "--backlog-promotion-receipt",
            str(_backlog_promotion_receipt(tmp_path, "pytest-full-suite")),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert json.loads(completed.stdout)["ok"] is True
