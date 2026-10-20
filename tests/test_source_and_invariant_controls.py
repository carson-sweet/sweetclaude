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
    CONTRACT_TEST_RECEIPT_TYPE,
    HIGH_CRITICAL_EXEMPTION_RECEIPT_TYPE,
    INVARIANT_TEST_RECEIPT_TYPE,
    SOURCE_DISCOVERY_RECEIPT_TYPE,
    SOURCE_PRECEDENCE_RECEIPT_TYPE,
    hash_file,
    validate_source_discovery_receipt,
    validate_source_precedence_receipt,
)
from release_gate import check_release_readiness


REQUIRED_CHECKS = [
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


def _discovery_entry(
    project_dir: Path,
    path: Path,
    *,
    branch: str,
    commit: str,
    channel: str,
    tag: str,
) -> dict:
    command = f"git ls-remote --tags origin {tag}"
    execution_receipt = _write_update_discovery_execution_receipt(
        project_dir,
        path,
        branch=branch,
        commit=commit,
        channel=channel,
        tag=tag,
        command=command,
    )
    return {
        "channel": channel,
        "tag": tag,
        "artifact": str(path),
        "artifact_sha256": hash_file(path),
        "source": f"{channel} release discovery",
        "command": command,
        "last_run_result": "pass",
        "execution_receipt_path": str(execution_receipt),
    }


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
        update_discovery[discovery_channel] = _discovery_entry(
            project_dir,
            discovery_artifact,
            branch=branch,
            commit=commit,
            channel=discovery_channel,
            tag=discovery_tag,
        )
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
    tag: str = "v3.9.0",
    *,
    checks: list[dict] | None = None,
    risk_severity: str | None = None,
) -> Path:
    version = tag.removeprefix("v")
    if "-" in version:
        channel, branch = "beta", "beta-4.x"
    elif version.split(".", 1)[0] == "3":
        channel, branch = "legacy", "stable-3.x"
    else:
        channel, branch = "stable", "main"
    release_checks = checks or [
        {
            "name": name,
            "status": "pass",
            "command": f"verify {name}",
            "summary": f"{name} passed",
        }
        for name in REQUIRED_CHECKS
    ]
    for check in release_checks:
        if not isinstance(check, dict) or check.get("evidence_path"):
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
        "subject_id": f"release:{tag}",
        "status": "pass",
        "created_at": "2026-05-26T12:00:00Z",
        "commit": commit,
        "checks": release_checks,
    }
    if risk_severity:
        receipt["risk_severity"] = risk_severity
    path = project_dir / ".sweetclaude" / "state" / "evidence" / f"{tag}-release.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return path


def _change_context_receipt(tmp_path: Path) -> Path:
    return _write_control_receipt(
        tmp_path / "change-context.json",
        "change-context",
        recent_commits=["abc123 release hardening"],
        dirty_state=[],
        branch_divergence="none",
        open_prs=[],
        touched_files=["scripts/release_gate.py"],
        impact_classification="high",
        decision="proceed",
    )


def test_t013_source_discovery_requires_governing_source_classes(tmp_path):
    receipt = _write_control_receipt(
        tmp_path / "source-discovery.json",
        SOURCE_DISCOVERY_RECEIPT_TYPE,
        searched_locations=["docs/adr", "contracts", "tests"],
        governing_sources=[
            {
                "path": "docs/adr/ADR-001.md",
                "source_class": "ADR",
                "summary": "Governs token claims.",
            }
        ],
        excluded_likely_sources=[],
        confidence="medium",
        help_needed=False,
    )

    with pytest.raises(ValueError, match="contract"):
        validate_source_discovery_receipt(
            receipt,
            required_source_classes={"ADR", "contract"},
        )


def test_t013_source_discovery_accepts_complete_high_stakes_receipt(tmp_path):
    receipt = _write_control_receipt(
        tmp_path / "source-discovery.json",
        SOURCE_DISCOVERY_RECEIPT_TYPE,
        searched_locations=["docs/adr", "contracts", "tests"],
        governing_sources=[
            {
                "path": "docs/adr/ADR-001.md",
                "source_class": "ADR",
                "summary": "Governs token claims.",
            },
            {
                "path": "contracts/auth.md",
                "source_class": "contract",
                "summary": "Defines service token behavior.",
            },
        ],
        excluded_likely_sources=[],
        confidence="high",
        help_needed=False,
    )

    parsed = validate_source_discovery_receipt(
        receipt,
        required_source_classes={"ADR", "contract"},
    )

    assert parsed["receipt_type"] == SOURCE_DISCOVERY_RECEIPT_TYPE


def test_t012_source_precedence_rejects_drifted_code_as_authority(tmp_path):
    receipt = _write_control_receipt(
        tmp_path / "source-precedence.json",
        SOURCE_PRECEDENCE_RECEIPT_TYPE,
        precedence_checks=[
            {
                "governing_source_type": "ADR",
                "governing_source": "docs/adr/ADR-001.md",
                "observed_behavior": "implementation includes org_id in service token",
                "decision": "follow_governing_source",
                "implementation_source_treated_as_authority": True,
            }
        ],
    )

    with pytest.raises(ValueError, match="treats implementation"):
        validate_source_precedence_receipt(receipt)


def test_t012_source_precedence_accepts_spec_amendment_route(tmp_path):
    receipt = _write_control_receipt(
        tmp_path / "source-precedence.json",
        SOURCE_PRECEDENCE_RECEIPT_TYPE,
        precedence_checks=[
            {
                "governing_source_type": "contract",
                "governing_source": "contracts/auth.md",
                "observed_behavior": "implementation contradicts the contract",
                "decision": "spec_amendment_required",
                "implementation_source_treated_as_authority": False,
            }
        ],
    )

    parsed = validate_source_precedence_receipt(receipt)

    assert parsed["receipt_type"] == SOURCE_PRECEDENCE_RECEIPT_TYPE


def test_t014_release_rejects_contract_claim_without_executable_evidence(tmp_path):
    _write_release_project(tmp_path)
    checks = [
        *[
            {
                "name": name,
                "status": "pass",
                "command": f"verify {name}",
                "summary": f"{name} passed",
            }
            for name in REQUIRED_CHECKS
        ],
        {
            "name": "contract-conformance",
            "status": "pass",
            "summary": "Contract reviewed by supervisor.",
        },
    ]
    receipt = _write_release_receipt(tmp_path, checks=checks)

    with pytest.raises(ValueError, match="contract-conformance claim requires"):
        check_release_readiness(
            tmp_path,
            tag="v3.9.0",
            channel="legacy",
            branch="stable-3.x",
            receipt_path=receipt,
        )


def test_t014_release_accepts_contract_claim_with_executable_evidence(tmp_path):
    _write_release_project(tmp_path)
    test_file = tmp_path / "tests" / "test_contract.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_contract():\n    assert True\n", encoding="utf-8")
    contract_receipt = _write_control_receipt(
        tmp_path / "contract-test.json",
        CONTRACT_TEST_RECEIPT_TYPE,
        test_file="tests/test_contract.py",
        test_command="pytest -q tests/test_contract.py",
        expected_assertion="contract behavior matches implementation",
        last_run_result="pass",
    )
    checks = [
        *[
            {
                "name": name,
                "status": "pass",
                "command": f"verify {name}",
                "summary": f"{name} passed",
            }
            for name in REQUIRED_CHECKS
        ],
        {
            "name": "contract-conformance",
            "status": "pass",
            "evidence_path": str(contract_receipt),
        },
    ]
    receipt = _write_release_receipt(tmp_path, checks=checks)

    result = check_release_readiness(
        tmp_path,
        tag="v3.9.0",
        channel="legacy",
        branch="stable-3.x",
        receipt_path=receipt,
    )

    assert result["ok"] is True


def test_t015_high_critical_release_requires_invariant_check(tmp_path):
    _write_release_project(tmp_path)
    receipt = _write_release_receipt(tmp_path, risk_severity="High")

    with pytest.raises(ValueError, match="requires a load-bearing-invariant check"):
        check_release_readiness(
            tmp_path,
            tag="v3.9.0",
            channel="legacy",
            branch="stable-3.x",
            receipt_path=receipt,
        )


def test_t015_release_accepts_invariant_claim_with_executable_evidence(tmp_path):
    _write_release_project(tmp_path)
    test_file = tmp_path / "tests" / "test_invariant.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_invariant():\n    assert True\n", encoding="utf-8")
    invariant_receipt = _write_control_receipt(
        tmp_path / "invariant-test.json",
        INVARIANT_TEST_RECEIPT_TYPE,
        test_file="tests/test_invariant.py",
        test_command="pytest -q tests/test_invariant.py",
        expected_assertion="fabricated claim cannot bypass org isolation",
        last_run_result="pass",
    )
    checks = [
        *[
            {
                "name": name,
                "status": "pass",
                "command": f"verify {name}",
                "summary": f"{name} passed",
            }
            for name in REQUIRED_CHECKS
        ],
        {
            "name": "load-bearing-invariant",
            "status": "pass",
            "evidence_path": str(invariant_receipt),
        },
        {
            "name": "change-context",
            "status": "pass",
            "evidence_path": str(_change_context_receipt(tmp_path)),
        },
    ]
    receipt = _write_release_receipt(tmp_path, checks=checks, risk_severity="Critical")

    result = check_release_readiness(
        tmp_path,
        tag="v3.9.0",
        channel="legacy",
        branch="stable-3.x",
        receipt_path=receipt,
    )

    assert result["ok"] is True


def test_t016_release_rejects_vague_exemption_for_missing_evidence(tmp_path):
    _write_release_project(tmp_path)
    vague_exemption = _write_control_receipt(
        tmp_path / "vague-exemption.json",
        HIGH_CRITICAL_EXEMPTION_RECEIPT_TYPE,
        severity="High",
        authority="supervisor",
        reason="reviewed by supervisor",
    )
    checks = [
        *[
            {
                "name": name,
                "status": "pass",
                "command": f"verify {name}",
                "summary": f"{name} passed",
            }
            for name in REQUIRED_CHECKS
        ],
        {
            "name": "load-bearing-invariant",
            "status": "pass",
            "evidence_path": str(vague_exemption),
        },
    ]
    receipt = _write_release_receipt(tmp_path, checks=checks, risk_severity="High")

    with pytest.raises(ValueError, match="valid High/Critical exemption"):
        check_release_readiness(
            tmp_path,
            tag="v3.9.0",
            channel="legacy",
            branch="stable-3.x",
            receipt_path=receipt,
        )


def test_t016_release_rejects_expired_high_critical_exemption(tmp_path):
    _write_release_project(tmp_path)
    expired_exemption = _write_control_receipt(
        tmp_path / "expired-exemption.json",
        HIGH_CRITICAL_EXEMPTION_RECEIPT_TYPE,
        severity="High",
        authority="release-owner",
        scope="single release",
        reason="temporary external dependency outage",
        expires_at="2026-05-25T12:00:00Z",
        accepted_risk="contract regression could be missed",
        finding_disposition="accepted until expiry",
    )
    checks = [
        *[
            {
                "name": name,
                "status": "pass",
                "command": f"verify {name}",
                "summary": f"{name} passed",
            }
            for name in REQUIRED_CHECKS
        ],
        {
            "name": "load-bearing-invariant",
            "status": "pass",
            "evidence_path": str(expired_exemption),
        },
    ]
    receipt = _write_release_receipt(tmp_path, checks=checks, risk_severity="High")

    with pytest.raises(ValueError, match="valid High/Critical exemption"):
        check_release_readiness(
            tmp_path,
            tag="v3.9.0",
            channel="legacy",
            branch="stable-3.x",
            receipt_path=receipt,
        )


def test_t016_release_accepts_valid_high_critical_exemption(tmp_path):
    _write_release_project(tmp_path)
    exemption = _write_control_receipt(
        tmp_path / "valid-exemption.json",
        HIGH_CRITICAL_EXEMPTION_RECEIPT_TYPE,
        severity="Critical",
        authority="release-owner",
        scope="single release",
        reason="temporary external dependency outage",
        expires_at="2099-01-01T00:00:00Z",
        accepted_risk="invariant regression could be missed",
        finding_disposition="accepted for this release only",
    )
    checks = [
        *[
            {
                "name": name,
                "status": "pass",
                "command": f"verify {name}",
                "summary": f"{name} passed",
            }
            for name in REQUIRED_CHECKS
        ],
        {
            "name": "load-bearing-invariant",
            "status": "pass",
            "evidence_path": str(exemption),
        },
        {
            "name": "change-context",
            "status": "pass",
            "evidence_path": str(_change_context_receipt(tmp_path)),
        },
    ]
    receipt = _write_release_receipt(tmp_path, checks=checks, risk_severity="High")

    result = check_release_readiness(
        tmp_path,
        tag="v3.9.0",
        channel="legacy",
        branch="stable-3.x",
        receipt_path=receipt,
    )

    assert result["ok"] is True
