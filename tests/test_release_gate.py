import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from control_receipts import hash_file, write_control_lint_receipt
from release_gate import (
    check_release_readiness,
    _validate_issue_closeout,
    _extract_issue_ids_from_commits,
    _issue_is_terminal,
    _previous_tag,
)


ROOT = Path(__file__).parents[1]
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
EFFORT_ROOT = Path(".sweetclaude") / "efforts" / "ms-007-failure-mode-controls"


def _write_release_project(project_dir: Path, version: str) -> None:
    (project_dir / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (project_dir / "skills" / "recover").mkdir(parents=True, exist_ok=True)
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
    (project_dir / "skills" / "recover" / "SKILL.md").write_text(
        "Invoke /sweetclaude:recover for recovery.\n",
        encoding="utf-8",
    )
    (project_dir / "config" / "capability-manifest.yaml").write_text(
        "capabilities:\n  slash-commands: true\n  hooks: true\n",
        encoding="utf-8",
    )
    (project_dir / "config" / "controls-map.md").write_text(
        "# Controls Map\n\n| Control | Description |\n| CTL-001 | Test control |\n",
        encoding="utf-8",
    )
    (project_dir / "hooks" / "session-preflight.sh").write_text(
        "#!/bin/sh\nexit 0\n",
        encoding="utf-8",
    )
    (project_dir / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## [{version}] -- 2026-05-25\n\n- Test release.\n",
        encoding="utf-8",
    )
    (project_dir / "dist" / f"sweetclaude-{version}.tgz").write_text(
        "artifact\n",
        encoding="utf-8",
    )
    (project_dir / "dist" / "sweetclaude-4.99.0.tgz").write_text(
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


def _write_release_receipt(project_dir: Path, tag: str, checks=None, status="pass") -> Path:
    checks = checks or REQUIRED_CHECKS
    version = tag.removeprefix("v")
    if "-" in version:
        channel, branch = "beta", "beta-4.x"
    elif version.split(".", 1)[0] == "3":
        channel, branch = "legacy", "stable-3.x"
    else:
        channel, branch = "stable", "main"
    commit = _current_test_commit(project_dir) or "abc123"
    check_entries = []
    for name in checks:
        entry = {
            "name": name,
            "status": "pass",
            "command": f"verify {name}",
            "summary": f"{name} passed",
        }
        if name == "release-identity":
            entry["evidence_path"] = str(
                _write_release_identity_receipt(
                    project_dir,
                    version=version,
                    tag=tag,
                    channel=channel,
                    branch=branch,
                    commit=commit,
                )
            )
        if name == "docs-capability":
            entry["evidence_path"] = str(
                _write_docs_capability_receipt(
                    project_dir,
                    branch=branch,
                    commit=commit,
                )
            )
        if name == "public-distribution":
            entry["evidence_path"] = str(_write_public_distribution_receipt(project_dir))
        check_entries.append(entry)
    receipt = {
        "schema_version": 1,
        "receipt_type": "release",
        "subject_id": f"release:{tag}",
        "status": status,
        "created_at": "2026-05-25T12:00:00Z",
        "commit": commit,
        "checks": check_entries,
    }
    path = project_dir / ".sweetclaude" / "state" / "evidence" / f"{tag}-release.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return path


def _write_control_receipt(path: Path, receipt_type: str, **overrides) -> Path:
    data = {
        "schema_version": 2,
        "receipt_type": receipt_type,
        "receipt_id": path.stem,
        "generated_at": "2026-05-26T12:00:00Z",
        "command_or_workflow_step": "test",
        "cwd": str(path.parent),
        "repo_root": str(path.parent),
        "branch": "beta-4.x",
        "commit": "abc123",
        "result": "pass",
        "input_artifacts": [],
    }
    data.update(overrides)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


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


def _write_release_identity_receipt(
    project_dir: Path,
    *,
    version: str,
    tag: str,
    channel: str,
    branch: str,
    commit: str,
) -> Path:
    artifact = project_dir / "dist" / f"sweetclaude-{version}.tgz"
    build_receipt = _write_release_artifact_build_receipt(
        project_dir,
        artifact,
        branch=branch,
        commit=commit,
        tag=tag,
    )
    channel_defaults = {
        "stable": ("v4.99.0", project_dir / "dist" / "sweetclaude-4.99.0.tgz"),
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
        branch=branch,
        repo_root=str(project_dir),
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
    branch = (
        subprocess.run(
            ["git", "-C", str(project_dir), "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        or "beta-4.x"
    )
    inventory = _write_public_distribution_inventory_receipt(
        project_dir,
        branch=branch,
        commit=commit,
    )
    return _write_control_receipt(
        project_dir / ".sweetclaude" / "state" / "evidence" / "public-distribution.json",
        "public-distribution",
        repo_root=str(project_dir),
        branch=branch,
        commit=commit,
        permissions=["read project files", "write approved maintenance outputs"],
        installed_user_file_access=[".sweetclaude/", ".claude/"],
        network_access=["git remote tag/update discovery"],
        hooks=["hooks/session-preflight.sh"],
        project_mutation_commands=["/sweetclaude:migrate", "/sweetclaude:recover"],
        provider_bound_data=["Claude Code prompt and local project context"],
        auth_assumptions=["Claude Code local user approval gates mutating commands"],
        secrets_handling="does not require or persist provider secrets",
        channel_visibility="stable and beta channels are separately visible",
        marketplace_or_distribution_visibility="public plugin distribution",
        evidence_source="release distribution review",
        approved_trust_model="public plugin may inspect project files only for declared maintenance commands",
        inventory_receipt_path=str(inventory),
    )


def _write_public_distribution_inventory_receipt(
    project_dir: Path,
    *,
    branch: str,
    commit: str,
) -> Path:
    return _write_control_receipt(
        project_dir / ".sweetclaude" / "state" / "evidence" / "public-distribution-inventory.json",
        "public-distribution-inventory",
        repo_root=str(project_dir),
        branch=branch,
        commit=commit,
        manifest_capabilities=["slash-commands", "hooks"],
        installed_plugin_files=[
            ".claude-plugin/plugin.json",
            "skills/recover/SKILL.md",
        ],
        hook_files=["hooks/session-preflight.sh"],
        mutation_commands=["/sweetclaude:migrate", "/sweetclaude:recover"],
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
                "path": "skills/recover/SKILL.md",
                "sha256": hash_file(project_dir / "skills" / "recover" / "SKILL.md"),
            },
            {
                "path": "hooks/session-preflight.sh",
                "sha256": hash_file(project_dir / "hooks" / "session-preflight.sh"),
            },
        ],
    )


def _write_docs_capability_receipt(project_dir: Path, *, branch: str, commit: str) -> Path:
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
        branch=branch,
        commit=commit,
        installed_entrypoint="/sweetclaude:recover",
        installed_path=str(project_dir),
        plugin_identity="sweetclaude",
        installed_manifest_path=str(project_dir / ".claude-plugin" / "plugin.json"),
        installed_manifest_sha256=hash_file(project_dir / ".claude-plugin" / "plugin.json"),
        command="claude /sweetclaude:recover --help",
        run_at="2026-05-26T12:00:00Z",
        exit_code=0,
        stdout_path=str(smoke_output),
        stdout_sha256=hash_file(smoke_output),
        stderr_path=str(stderr),
        stderr_sha256=hash_file(stderr),
        entrypoint_lookup_result="/sweetclaude:recover found in installed plugin",
        entrypoint_source_paths=[
            {
                "path": str(project_dir / "skills" / "recover" / "SKILL.md"),
                "sha256": hash_file(project_dir / "skills" / "recover" / "SKILL.md"),
            }
        ],
        release_artifact_path=str(artifact),
        release_artifact_sha256=hash_file(artifact),
    )
    return _write_control_receipt(
        project_dir / ".sweetclaude" / "state" / "evidence" / "docs-capability.json",
        "docs-capability",
        repo_root=str(project_dir),
        branch=branch,
        commit=commit,
        claims=[
            {
                "claim": "/sweetclaude:recover repairs project state",
                "status": "proven",
                "installed_entrypoint": "/sweetclaude:recover",
                "installed_path": str(project_dir),
                "plugin_identity": "sweetclaude",
                "smoke_command": "claude /sweetclaude:recover --help",
                "run_at": "2026-05-26T12:00:00Z",
                "last_run_result": "pass",
                "exit_code": 0,
                "smoke_output_path": str(smoke_output),
                "smoke_output_sha256": hash_file(smoke_output),
                "installed_smoke_receipt_path": str(installed_smoke),
            }
        ],
    )


def _write_ms007_control_artifacts(
    project_dir: Path,
    *,
    strategy_text: str = "Controls: CTL-001\n",
    implementation_text: str = "Controls: CTL-001\n",
) -> None:
    effort = project_dir / EFFORT_ROOT
    (effort / "02-design").mkdir(parents=True, exist_ok=True)
    (effort / "04-test-strategy").mkdir(parents=True, exist_ok=True)
    (effort / "03-implementation-plan").mkdir(parents=True, exist_ok=True)
    (effort / "02-design" / "controls-map.md").write_text(
        "| Control ID | Acceptance Criteria |\n"
        "|---|---|\n"
        "| CTL-001 | Receipt includes required identity fields. |\n",
        encoding="utf-8",
    )
    (effort / "04-test-strategy" / "beta-4x-control-test-strategy.md").write_text(
        strategy_text,
        encoding="utf-8",
    )
    (
        effort
        / "03-implementation-plan"
        / "beta-4x-control-implementation-plan.md"
    ).write_text(
        implementation_text,
        encoding="utf-8",
    )


def _write_control_lint_receipt(
    project_dir: Path,
    tag: str,
    *,
    branch: str = "beta-4.x",
    commit: str | None = None,
) -> Path:
    commit = commit or _current_test_commit(project_dir) or "abc123"
    return write_control_lint_receipt(
        project_dir,
        subject_id=f"release:{tag}",
        branch=branch,
        commit=commit,
        controls_map_path=project_dir / EFFORT_ROOT / "02-design" / "controls-map.md",
        artifact_paths=[
            project_dir
            / EFFORT_ROOT
            / "04-test-strategy"
            / "beta-4x-control-test-strategy.md",
            project_dir
            / EFFORT_ROOT
            / "03-implementation-plan"
            / "beta-4x-control-implementation-plan.md",
        ],
    )


def _git(project_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(project_dir), *args],
        capture_output=True,
        text=True,
        check=True,
    )


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


def _init_release_git_state(
    project_dir: Path,
    *,
    branch: str,
    tag: str | None = None,
    upstream: str | None = None,
) -> None:
    _git(project_dir, "init")
    _git(project_dir, "config", "user.email", "tests@sweetclaude.local")
    _git(project_dir, "config", "user.name", "SweetClaude Tests")
    _git(project_dir, "remote", "add", "origin", "https://example.invalid/sweetclaude.git")
    _git(project_dir, "checkout", "-b", branch)
    _git(project_dir, "add", ".")
    _git(project_dir, "commit", "-m", "release candidate")
    if tag:
        _git(project_dir, "tag", tag)
    upstream = upstream or f"origin/{branch}"
    _git(project_dir, "update-ref", f"refs/remotes/{upstream}", "HEAD")
    remote, remote_branch = upstream.split("/", 1)
    _git(project_dir, "config", f"branch.{branch}.remote", remote)
    _git(project_dir, "config", f"branch.{branch}.merge", f"refs/heads/{remote_branch}")


def test_beta_release_readiness_accepts_valid_receipt_and_metadata(tmp_path):
    _write_release_project(tmp_path, "4.1.7-beta")
    _write_ms007_control_artifacts(tmp_path)
    _init_release_git_state(tmp_path, branch="beta-4.x", tag="v4.1.7-beta")
    receipt = _write_release_receipt(tmp_path, "v4.1.7-beta")
    control_lint_receipt = _write_control_lint_receipt(tmp_path, "v4.1.7-beta")

    result = check_release_readiness(
        tmp_path,
        tag="v4.1.7-beta",
        channel="beta",
        branch="beta-4.x",
        receipt_path=receipt,
        control_lint_receipt_path=control_lint_receipt,
    )

    assert result["ok"] is True
    assert result["version"] == "4.1.7-beta"
    assert result["git"]["checked"] is True
    assert result["checks"] == sorted(REQUIRED_CHECKS)


def test_release_readiness_accepts_matching_git_branch_upstream_and_tag(tmp_path):
    _write_release_project(tmp_path, "4.1.7-beta")
    _write_ms007_control_artifacts(tmp_path)
    _init_release_git_state(tmp_path, branch="beta-4.x", tag="v4.1.7-beta")
    commit = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    receipt = _write_release_receipt(tmp_path, "v4.1.7-beta")
    control_lint_receipt = _write_control_lint_receipt(
        tmp_path,
        "v4.1.7-beta",
        commit=commit,
    )

    result = check_release_readiness(
        tmp_path,
        tag="v4.1.7-beta",
        channel="beta",
        branch="beta-4.x",
        receipt_path=receipt,
        control_lint_receipt_path=control_lint_receipt,
    )

    assert result["ok"] is True
    assert result["git"]["checked"] is True
    assert result["git"]["branch"] == "beta-4.x"
    assert result["git"]["upstream"] == "origin/beta-4.x"
    assert "v4.1.7-beta" in result["git"]["head_tags"]


@pytest.mark.parametrize("actual_branch", ["main", "evidence-gates-beta"])
def test_release_readiness_rejects_wrong_actual_git_branch(tmp_path, actual_branch):
    _write_release_project(tmp_path, "4.1.7-beta")
    _write_ms007_control_artifacts(tmp_path)
    _init_release_git_state(tmp_path, branch=actual_branch, tag="v4.1.7-beta")
    commit = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    receipt = _write_release_receipt(tmp_path, "v4.1.7-beta")
    control_lint_receipt = _write_control_lint_receipt(
        tmp_path,
        "v4.1.7-beta",
        commit=commit,
    )

    with pytest.raises(ValueError, match="branch mismatch"):
        check_release_readiness(
            tmp_path,
            tag="v4.1.7-beta",
            channel="beta",
            branch="beta-4.x",
            receipt_path=receipt,
            control_lint_receipt_path=control_lint_receipt,
        )


def test_release_readiness_rejects_wrong_git_upstream(tmp_path):
    _write_release_project(tmp_path, "4.1.7-beta")
    _write_ms007_control_artifacts(tmp_path)
    _init_release_git_state(
        tmp_path,
        branch="beta-4.x",
        tag="v4.1.7-beta",
        upstream="origin/evidence-gates-beta",
    )
    commit = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    receipt = _write_release_receipt(tmp_path, "v4.1.7-beta")
    control_lint_receipt = _write_control_lint_receipt(
        tmp_path,
        "v4.1.7-beta",
        commit=commit,
    )

    with pytest.raises(ValueError, match="upstream mismatch"):
        check_release_readiness(
            tmp_path,
            tag="v4.1.7-beta",
            channel="beta",
            branch="beta-4.x",
            receipt_path=receipt,
            control_lint_receipt_path=control_lint_receipt,
        )


def test_release_readiness_rejects_missing_head_tag(tmp_path):
    _write_release_project(tmp_path, "4.1.7-beta")
    _write_ms007_control_artifacts(tmp_path)
    _init_release_git_state(tmp_path, branch="beta-4.x")
    commit = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    receipt = _write_release_receipt(tmp_path, "v4.1.7-beta")
    control_lint_receipt = _write_control_lint_receipt(
        tmp_path,
        "v4.1.7-beta",
        commit=commit,
    )

    with pytest.raises(ValueError, match="must point at HEAD"):
        check_release_readiness(
            tmp_path,
            tag="v4.1.7-beta",
            channel="beta",
            branch="beta-4.x",
            receipt_path=receipt,
            control_lint_receipt_path=control_lint_receipt,
        )


def test_stable_release_rejects_beta_version(tmp_path):
    _write_release_project(tmp_path, "4.1.7-beta")
    receipt = _write_release_receipt(tmp_path, "v4.1.7-beta")

    with pytest.raises(ValueError, match="stable channel cannot release prerelease"):
        check_release_readiness(
            tmp_path,
            tag="v4.1.7-beta",
            channel="stable",
            branch="stable-3.x",
            receipt_path=receipt,
        )


def test_beta_release_rejects_stable_version(tmp_path):
    _write_release_project(tmp_path, "4.1.7")
    receipt = _write_release_receipt(tmp_path, "v4.1.7")

    with pytest.raises(ValueError, match="beta channel releases must use"):
        check_release_readiness(
            tmp_path,
            tag="v4.1.7",
            channel="beta",
            branch="beta-4.x",
            receipt_path=receipt,
        )


def test_release_readiness_rejects_metadata_drift(tmp_path):
    _write_release_project(tmp_path, "4.1.7-beta")
    (tmp_path / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "sweetclaude", "version": "4.1.6-beta"}) + "\n",
        encoding="utf-8",
    )
    receipt = _write_release_receipt(tmp_path, "v4.1.7-beta")

    with pytest.raises(ValueError, match="plugin.json version mismatch"):
        check_release_readiness(
            tmp_path,
            tag="v4.1.7-beta",
            channel="beta",
            branch="beta-4.x",
            receipt_path=receipt,
        )


def test_release_readiness_rejects_missing_required_receipt_checks(tmp_path):
    _write_release_project(tmp_path, "4.1.7-beta")
    _write_ms007_control_artifacts(tmp_path)
    _init_release_git_state(tmp_path, branch="beta-4.x", tag="v4.1.7-beta")
    receipt = _write_release_receipt(
        tmp_path,
        "v4.1.7-beta",
        checks=["tests", "channel-isolation"],
    )
    control_lint_receipt = _write_control_lint_receipt(tmp_path, "v4.1.7-beta")

    with pytest.raises(ValueError, match="missing required checks"):
        check_release_readiness(
            tmp_path,
            tag="v4.1.7-beta",
            channel="beta",
            branch="beta-4.x",
            receipt_path=receipt,
            control_lint_receipt_path=control_lint_receipt,
        )


def test_release_readiness_rejects_undefined_control_in_active_artifacts(tmp_path):
    _write_release_project(tmp_path, "4.1.7-beta")
    _write_ms007_control_artifacts(tmp_path, implementation_text="Controls: CTL-999\n")

    with pytest.raises(ValueError, match="undefined control.*CTL-999"):
        _write_control_lint_receipt(
            tmp_path,
            "v4.1.7-beta",
        )


def test_release_readiness_rejects_control_range_in_active_artifacts(tmp_path):
    _write_release_project(tmp_path, "4.1.7-beta")
    bad_range = "T-001 " + "thr" + "ough T-002"
    _write_ms007_control_artifacts(tmp_path, implementation_text=f"Fixtures: {bad_range}\n")

    with pytest.raises(ValueError, match="numeric range"):
        _write_control_lint_receipt(
            tmp_path,
            "v4.1.7-beta",
        )


def test_beta_release_readiness_fails_closed_without_control_lint_receipt(tmp_path):
    _write_release_project(tmp_path, "4.1.7-beta")
    _write_ms007_control_artifacts(tmp_path)
    _init_release_git_state(tmp_path, branch="beta-4.x", tag="v4.1.7-beta")
    receipt = _write_release_receipt(tmp_path, "v4.1.7-beta")

    with pytest.raises(ValueError, match="control-lint receipt is required"):
        check_release_readiness(
            tmp_path,
            tag="v4.1.7-beta",
            channel="beta",
            branch="beta-4.x",
            receipt_path=receipt,
        )


def test_release_readiness_rejects_stale_control_lint_receipt_commit(tmp_path):
    _write_release_project(tmp_path, "4.1.7-beta")
    _write_ms007_control_artifacts(tmp_path)
    _init_release_git_state(tmp_path, branch="beta-4.x", tag="v4.1.7-beta")
    receipt = _write_release_receipt(tmp_path, "v4.1.7-beta")
    control_lint_receipt = _write_control_lint_receipt(
        tmp_path,
        "v4.1.7-beta",
        commit="old",
    )

    with pytest.raises(ValueError, match="commit mismatch"):
        check_release_readiness(
            tmp_path,
            tag="v4.1.7-beta",
            channel="beta",
            branch="beta-4.x",
            receipt_path=receipt,
            control_lint_receipt_path=control_lint_receipt,
            expected_commit="new",
        )


def test_release_readiness_rejects_dirty_control_lint_artifact(tmp_path):
    _write_release_project(tmp_path, "4.1.7-beta")
    _write_ms007_control_artifacts(tmp_path)
    _init_release_git_state(tmp_path, branch="beta-4.x", tag="v4.1.7-beta")
    receipt = _write_release_receipt(tmp_path, "v4.1.7-beta")
    control_lint_receipt = _write_control_lint_receipt(tmp_path, "v4.1.7-beta")
    (
        tmp_path
        / EFFORT_ROOT
        / "03-implementation-plan"
        / "beta-4x-control-implementation-plan.md"
    ).write_text("Controls: CTL-001\n\nChanged after lint.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="tracked modifications"):
        check_release_readiness(
            tmp_path,
            tag="v4.1.7-beta",
            channel="beta",
            branch="beta-4.x",
            receipt_path=receipt,
            control_lint_receipt_path=control_lint_receipt,
        )


def test_release_readiness_rejects_untracked_package_input(tmp_path):
    _write_release_project(tmp_path, "4.1.7-beta")
    _write_ms007_control_artifacts(tmp_path)
    _init_release_git_state(tmp_path, branch="beta-4.x", tag="v4.1.7-beta")
    receipt = _write_release_receipt(tmp_path, "v4.1.7-beta")
    control_lint_receipt = _write_control_lint_receipt(tmp_path, "v4.1.7-beta")
    (tmp_path / "scripts").mkdir(exist_ok=True)
    (tmp_path / "scripts" / "untracked-release-input.sh").write_text(
        "#!/bin/sh\nexit 0\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="untracked package inputs"):
        check_release_readiness(
            tmp_path,
            tag="v4.1.7-beta",
            channel="beta",
            branch="beta-4.x",
            receipt_path=receipt,
            control_lint_receipt_path=control_lint_receipt,
        )


def test_release_readiness_accepts_valid_control_lint_receipt(tmp_path):
    _write_release_project(tmp_path, "4.1.7-beta")
    _write_ms007_control_artifacts(tmp_path)
    _init_release_git_state(tmp_path, branch="beta-4.x", tag="v4.1.7-beta")
    receipt = _write_release_receipt(tmp_path, "v4.1.7-beta")
    control_lint_receipt = _write_control_lint_receipt(tmp_path, "v4.1.7-beta")

    result = check_release_readiness(
        tmp_path,
        tag="v4.1.7-beta",
        channel="beta",
        branch="beta-4.x",
        receipt_path=receipt,
        control_lint_receipt_path=control_lint_receipt,
    )

    assert result["ok"] is True
    assert result["control_lint_receipt"] == str(control_lint_receipt)


def test_release_gate_cli_returns_json_success(tmp_path):
    _write_release_project(tmp_path, "4.1.7-beta")
    _write_ms007_control_artifacts(tmp_path)
    _init_release_git_state(tmp_path, branch="beta-4.x", tag="v4.1.7-beta")
    receipt = _write_release_receipt(tmp_path, "v4.1.7-beta")
    control_lint_receipt = _write_control_lint_receipt(tmp_path, "v4.1.7-beta")

    completed = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "release_gate.py"),
            "check",
            "--project-dir",
            str(tmp_path),
            "--tag",
            "v4.1.7-beta",
            "--channel",
            "beta",
            "--branch",
            "beta-4.x",
            "--receipt",
            str(receipt),
            "--control-lint-receipt",
            str(control_lint_receipt),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert json.loads(completed.stdout)["ok"] is True


def test_release_gate_cli_validates_actual_git_branch(tmp_path):
    _write_release_project(tmp_path, "4.1.7-beta")
    _write_ms007_control_artifacts(tmp_path)
    _init_release_git_state(tmp_path, branch="evidence-gates-beta", tag="v4.1.7-beta")
    commit = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    receipt = _write_release_receipt(tmp_path, "v4.1.7-beta")
    control_lint_receipt = _write_control_lint_receipt(
        tmp_path,
        "v4.1.7-beta",
        commit=commit,
    )

    completed = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "release_gate.py"),
            "check",
            "--project-dir",
            str(tmp_path),
            "--tag",
            "v4.1.7-beta",
            "--channel",
            "beta",
            "--branch",
            "beta-4.x",
            "--receipt",
            str(receipt),
            "--control-lint-receipt",
            str(control_lint_receipt),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    out = json.loads(completed.stdout)
    assert out["ok"] is False
    assert "branch mismatch" in out["error"]


def test_release_gate_cli_fails_closed_without_receipt(tmp_path):
    _write_release_project(tmp_path, "4.1.7-beta")
    _init_release_git_state(tmp_path, branch="beta-4.x", tag="v4.1.7-beta")

    completed = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "release_gate.py"),
            "check",
            "--project-dir",
            str(tmp_path),
            "--tag",
            "v4.1.7-beta",
            "--channel",
            "beta",
            "--branch",
            "beta-4.x",
            "--receipt",
            str(tmp_path / "missing.json"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    out = json.loads(completed.stdout)
    assert out["ok"] is False
    assert "not found" in out["error"].lower()


def test_release_gate_generate_evidence_cli_writes_usable_beta_packet(tmp_path):
    _write_release_project(tmp_path, "4.1.7-beta")
    _write_ms007_control_artifacts(tmp_path)
    (tmp_path / "config" / "capability-manifest.yaml").write_text(
        (ROOT / "config" / "capability-manifest.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    _init_release_git_state(tmp_path, branch="beta-4.x", tag="v4.1.7-beta")
    control_lint_receipt = _write_control_lint_receipt(tmp_path, "v4.1.7-beta")

    completed = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "release_gate.py"),
            "generate-evidence",
            "--project-dir",
            str(tmp_path),
            "--tag",
            "v4.1.7-beta",
            "--channel",
            "beta",
            "--branch",
            "beta-4.x",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    generated = json.loads(completed.stdout)
    assert generated["ok"] is True
    release_receipt = Path(generated["release_receipt"])
    parsed_release = json.loads(release_receipt.read_text(encoding="utf-8"))
    evidence_by_check = {
        check["name"]: check.get("evidence_path")
        for check in parsed_release["checks"]
    }
    assert evidence_by_check["release-identity"] == generated["release_identity_receipt"]
    assert evidence_by_check["docs-capability"] == generated["docs_capability_receipt"]
    assert evidence_by_check["public-distribution"] == generated["public_distribution_receipt"]

    result = check_release_readiness(
        tmp_path,
        tag="v4.1.7-beta",
        channel="beta",
        branch="beta-4.x",
        receipt_path=release_receipt,
        control_lint_receipt_path=control_lint_receipt,
    )

    assert result["ok"] is True


def test_release_gate_generate_evidence_derives_distribution_inventory_from_disk(tmp_path):
    _write_release_project(tmp_path, "4.1.7-beta")
    _write_ms007_control_artifacts(tmp_path)
    (tmp_path / "config" / "capability-manifest.yaml").write_text(
        (ROOT / "config" / "capability-manifest.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    extra_hook = tmp_path / "hooks" / "extra-release-hook.sh"
    extra_hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    _init_release_git_state(tmp_path, branch="beta-4.x", tag="v4.1.7-beta")

    completed = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "release_gate.py"),
            "generate-evidence",
            "--project-dir",
            str(tmp_path),
            "--tag",
            "v4.1.7-beta",
            "--channel",
            "beta",
            "--branch",
            "beta-4.x",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    public_receipt = Path(json.loads(completed.stdout)["public_distribution_receipt"])
    public_data = json.loads(public_receipt.read_text(encoding="utf-8"))
    inventory_path = Path(public_data["inventory_receipt_path"])
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    input_hashes = {
        artifact["path"]: artifact["sha256"]
        for artifact in inventory["input_artifacts"]
    }

    assert ".claude-plugin/plugin.json" in inventory["installed_plugin_files"]
    assert "skills/recover/SKILL.md" in inventory["installed_plugin_files"]
    assert "hooks/session-preflight.sh" in inventory["hook_files"]
    assert "hooks/extra-release-hook.sh" in inventory["hook_files"]
    assert input_hashes["hooks/extra-release-hook.sh"] == hash_file(extra_hook)


def test_generate_evidence_resolves_recover_skill_at_canonical_root_layout(tmp_path):
    """Regression (ISSUE-203): the gate only ever modeled the fabricated
    .claude-plugin/skills/ layout. In the canonical layout skills live at root
    skills/, and generate-evidence (default installed-path) must still resolve
    the /sweetclaude:recover entrypoint and inventory the skill from root."""
    _write_release_project(tmp_path, "4.1.7-beta")
    _write_ms007_control_artifacts(tmp_path)
    (tmp_path / "config" / "capability-manifest.yaml").write_text(
        (ROOT / "config" / "capability-manifest.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    _init_release_git_state(tmp_path, branch="beta-4.x", tag="v4.1.7-beta")

    completed = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "release_gate.py"),
            "generate-evidence",
            "--project-dir",
            str(tmp_path),
            "--tag",
            "v4.1.7-beta",
            "--channel",
            "beta",
            "--branch",
            "beta-4.x",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    generated = json.loads(completed.stdout)
    assert generated["ok"] is True

    public_receipt = Path(generated["public_distribution_receipt"])
    inventory_path = Path(json.loads(public_receipt.read_text(encoding="utf-8"))["inventory_receipt_path"])
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    assert "skills/recover/SKILL.md" in inventory["installed_plugin_files"]
    assert ".claude-plugin/skills/recover/SKILL.md" not in inventory["installed_plugin_files"]


def test_generate_evidence_emits_control_lint_receipt_for_beta(tmp_path):
    """ISSUE-203: beta `check` requires a control-lint receipt, and nothing
    generated it. generate-evidence must now emit it (from config/controls-map.md)
    so `check` passes for beta WITHOUT an explicitly supplied receipt."""
    _write_release_project(tmp_path, "4.1.7-beta")
    _write_ms007_control_artifacts(tmp_path)
    (tmp_path / "config" / "capability-manifest.yaml").write_text(
        (ROOT / "config" / "capability-manifest.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    _init_release_git_state(tmp_path, branch="beta-4.x", tag="v4.1.7-beta")

    completed = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "release_gate.py"),
            "generate-evidence",
            "--project-dir",
            str(tmp_path),
            "--tag",
            "v4.1.7-beta",
            "--channel",
            "beta",
            "--branch",
            "beta-4.x",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    release_receipt = Path(json.loads(completed.stdout)["release_receipt"])

    # No explicit control-lint receipt: must use the one generate-evidence emitted.
    result = check_release_readiness(
        tmp_path,
        tag="v4.1.7-beta",
        channel="beta",
        branch="beta-4.x",
        receipt_path=release_receipt,
        control_lint_receipt_path=None,
    )
    assert result["ok"] is True


def test_distribution_roots_cover_every_present_load_dir_in_real_repo():
    """Re-rot guard (ISSUE-203): every Claude Code plugin component directory
    that exists at the real repo root must be covered by the gate's
    distribution model. If a new load dir is added to the repo (or skills move),
    this fails until the gate's roots are updated — the exact silent drift that
    let the gate inventory the wrong tree for releases."""
    from control_receipts import PLUGIN_DISTRIBUTION_ROOTS, PLUGIN_HOOK_ROOT

    known_load_dirs = {"skills", "agents", "commands", "hooks"}
    covered = set(PLUGIN_DISTRIBUTION_ROOTS) | {PLUGIN_HOOK_ROOT}
    present = {name for name in known_load_dirs if (ROOT / name).is_dir()}
    uncovered = present - covered
    assert not uncovered, f"load dirs present in repo but absent from gate distribution model: {uncovered}"


def test_recover_entrypoint_is_findable_in_real_repo_distribution_surface():
    """Re-rot guard (ISSUE-203): the /sweetclaude:recover entrypoint the gate
    proves must actually be discoverable under the gate's distribution roots in
    the real repo — not just in a fixture."""
    from control_receipts import PLUGIN_DISTRIBUTION_ROOTS

    entrypoint = "/sweetclaude:recover"
    found = False
    for root_name in PLUGIN_DISTRIBUTION_ROOTS:
        root = ROOT / root_name
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            try:
                if entrypoint in path.read_text(encoding="utf-8"):
                    found = True
                    break
            except (UnicodeDecodeError, OSError):
                continue
        if found:
            break
    assert found, f"{entrypoint} not findable under {PLUGIN_DISTRIBUTION_ROOTS} in the real repo"


# --- Issue closeout gate (ISSUE-214) ------------------------------------------


def _init_closeout_git(project_dir, *, prev_tag=None, messages=None, tag=None):
    _git(project_dir, "init")
    _git(project_dir, "config", "user.email", "tests@sweetclaude.local")
    _git(project_dir, "config", "user.name", "SweetClaude Tests")
    _git(project_dir, "checkout", "-b", "beta-4.x")
    (project_dir / "base.txt").write_text("base\n", encoding="utf-8")
    _git(project_dir, "add", ".")
    _git(project_dir, "commit", "-m", "initial")
    if prev_tag:
        _git(project_dir, "tag", prev_tag)
    for i, msg in enumerate(messages or []):
        (project_dir / f"file-{i}.txt").write_text(f"{i}\n", encoding="utf-8")
        _git(project_dir, "add", ".")
        _git(project_dir, "commit", "-m", msg)
    if tag:
        _git(project_dir, "tag", tag)


def _write_backlog_issue(project_dir, issue_id, *, status="new", subdir=""):
    backlog = project_dir / ".sweetclaude" / "product" / "backlog"
    if subdir:
        backlog = backlog / subdir
    backlog.mkdir(parents=True, exist_ok=True)
    (backlog / f"{issue_id}-test.md").write_text(
        f"---\nid: {issue_id}\nstatus: {status}\n---\nTest.\n",
        encoding="utf-8",
    )


def test_extract_issue_ids_from_commits(tmp_path):
    _init_closeout_git(
        tmp_path,
        prev_tag="v4.2.0-beta",
        messages=[
            "fix(hooks): stop guard UX (ISSUE-208)",
            "fix(ISSUE-207): eliminate legacy paths",
            "chore: unrelated change",
            "fix(controllers): ownership filter (ISSUE-211, ISSUE-213)",
        ],
        tag="v4.2.1-beta",
    )
    ids = _extract_issue_ids_from_commits(tmp_path, "v4.2.0-beta", "v4.2.1-beta")
    assert ids == {"ISSUE-208", "ISSUE-207", "ISSUE-211", "ISSUE-213"}


def test_extract_ignores_body_only_mentions(tmp_path):
    """ISSUE-242: an issue merely mentioned in a commit BODY (related/future
    work) is not a delivered issue and must not gate the release. Only IDs in
    the commit subject count as delivered."""
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@t.local")
    _git(tmp_path, "config", "user.name", "T")
    _git(tmp_path, "checkout", "-b", "main")
    (tmp_path / "base.txt").write_text("base\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")
    _git(tmp_path, "tag", "v4.5.0")
    (tmp_path / "f.txt").write_text("x\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    # delivered ID in subject; a future-work ID only in the body
    _git(tmp_path, "commit",
         "-m", "fix(x): real change (ISSUE-244)",
         "-m", "Also noted for the ISSUE-242 gate-faithfulness family.")
    _git(tmp_path, "tag", "v4.5.1")
    ids = _extract_issue_ids_from_commits(tmp_path, "v4.5.0", "v4.5.1")
    assert "ISSUE-244" in ids, "delivered subject ID must be extracted"
    assert "ISSUE-242" not in ids, "body-only mention must NOT gate the release"


def test_previous_tag_finds_beta_predecessor(tmp_path):
    _init_closeout_git(tmp_path, prev_tag="v4.2.0-beta", messages=["next"], tag="v4.2.1-beta")
    assert _previous_tag(tmp_path, "v4.2.1-beta", "beta") == "v4.2.0-beta"


def test_previous_tag_returns_none_for_first_release(tmp_path):
    _init_closeout_git(tmp_path, messages=["first"], tag="v4.0.0-beta")
    assert _previous_tag(tmp_path, "v4.0.0-beta", "beta") is None


def test_issue_is_terminal_in_done_dir(tmp_path):
    _write_backlog_issue(tmp_path, "ISSUE-100", status="done", subdir="done")
    assert _issue_is_terminal(tmp_path, "ISSUE-100") is True


def test_issue_is_terminal_in_archived_dir(tmp_path):
    _write_backlog_issue(tmp_path, "ISSUE-100", status="done", subdir="archived")
    assert _issue_is_terminal(tmp_path, "ISSUE-100") is True


def test_issue_is_not_terminal_when_active(tmp_path):
    _write_backlog_issue(tmp_path, "ISSUE-100", status="new")
    assert _issue_is_terminal(tmp_path, "ISSUE-100") is False


def test_issue_is_not_terminal_when_missing(tmp_path):
    """Fail-closed (ISSUE-233 Story B, decision log #33): when the backlog
    exists but the referenced issue has no file, the gate blocks — a typo'd
    or unfiled ID must not sail through closeout validation."""
    backlog = tmp_path / ".sweetclaude" / "product" / "backlog"
    backlog.mkdir(parents=True)
    assert _issue_is_terminal(tmp_path, "ISSUE-999") is False


def test_issue_is_terminal_when_no_backlog_dir(tmp_path):
    """CI pin: a checkout without the gitignored backlog directory stays
    non-blocking (the tag workflow runs release_gate.py check there)."""
    assert _issue_is_terminal(tmp_path, "ISSUE-999") is True


def test_issue_id_matching_is_exact_boundary(tmp_path):
    """Accepted matching rule (plan v1.3): a file matches only when named
    exactly {ISSUE-ID}.md or beginning {ISSUE-ID}- . No prefix collisions."""
    # ISSUE-23 must not match ISSUE-233-foo.md
    _write_backlog_issue(tmp_path, "ISSUE-233", status="done", subdir="done")
    assert _issue_is_terminal(tmp_path, "ISSUE-23") is False
    assert _issue_is_terminal(tmp_path, "ISSUE-233") is True

    # ISSUE-23 must not match ISSUE-23foo.md
    done = tmp_path / ".sweetclaude" / "product" / "backlog" / "done"
    (done / "ISSUE-23foo.md").write_text(
        "---\nid: ISSUE-23foo\nstatus: done\n---\nTest.\n", encoding="utf-8"
    )
    assert _issue_is_terminal(tmp_path, "ISSUE-23") is False

    # ISSUE-23 matches ISSUE-23-foo.md
    (done / "ISSUE-23-foo.md").write_text(
        "---\nid: ISSUE-23\nstatus: done\n---\nTest.\n", encoding="utf-8"
    )
    assert _issue_is_terminal(tmp_path, "ISSUE-23") is True


def test_issue_id_matching_exact_filename(tmp_path):
    """ISSUE-23 matches ISSUE-23.md (bare id, no slug)."""
    done = tmp_path / ".sweetclaude" / "product" / "backlog" / "done"
    done.mkdir(parents=True)
    (done / "ISSUE-23.md").write_text(
        "---\nid: ISSUE-23\nstatus: done\n---\nTest.\n", encoding="utf-8"
    )
    assert _issue_is_terminal(tmp_path, "ISSUE-23") is True


def test_same_prefix_issues_resolve_independently(tmp_path):
    """ISSUE-23 open in the backlog and ISSUE-233 done coexist: each id
    resolves against its own file only."""
    _write_backlog_issue(tmp_path, "ISSUE-23", status="new")
    _write_backlog_issue(tmp_path, "ISSUE-233", status="done", subdir="done")
    assert _issue_is_terminal(tmp_path, "ISSUE-23") is False
    assert _issue_is_terminal(tmp_path, "ISSUE-233") is True


def test_validate_issue_closeout_passes_when_all_closed(tmp_path):
    _init_closeout_git(
        tmp_path,
        prev_tag="v4.2.0-beta",
        messages=["fix: thing (ISSUE-100)", "fix: other (ISSUE-101)"],
        tag="v4.2.1-beta",
    )
    _write_backlog_issue(tmp_path, "ISSUE-100", status="done", subdir="done")
    _write_backlog_issue(tmp_path, "ISSUE-101", status="done", subdir="done")
    result = _validate_issue_closeout(tmp_path, "v4.2.1-beta", "beta")
    assert result["checked"] is True
    assert result["unclosed"] == []


def test_validate_issue_closeout_fails_on_unclosed_issue(tmp_path):
    _init_closeout_git(
        tmp_path,
        prev_tag="v4.2.0-beta",
        messages=["fix: thing (ISSUE-100)", "fix: other (ISSUE-101)"],
        tag="v4.2.1-beta",
    )
    _write_backlog_issue(tmp_path, "ISSUE-100", status="done", subdir="done")
    _write_backlog_issue(tmp_path, "ISSUE-101", status="new")
    with pytest.raises(ValueError, match="ISSUE-101"):
        _validate_issue_closeout(tmp_path, "v4.2.1-beta", "beta")


def test_validate_issue_closeout_skips_when_no_previous_tag(tmp_path):
    _init_closeout_git(tmp_path, messages=["fix: thing (ISSUE-100)"], tag="v4.0.0-beta")
    result = _validate_issue_closeout(tmp_path, "v4.0.0-beta", "beta")
    assert result["skipped"] is True


def test_validate_issue_closeout_error_lists_all_unclosed(tmp_path):
    _init_closeout_git(
        tmp_path,
        prev_tag="v4.2.0-beta",
        messages=["fix: A (ISSUE-100)", "fix: B (ISSUE-101)", "fix: C (ISSUE-102)"],
        tag="v4.2.1-beta",
    )
    _write_backlog_issue(tmp_path, "ISSUE-100", status="new")
    _write_backlog_issue(tmp_path, "ISSUE-102", status="active")
    _write_backlog_issue(tmp_path, "ISSUE-101", status="done", subdir="done")
    with pytest.raises(ValueError, match="ISSUE-100.*ISSUE-102"):
        _validate_issue_closeout(tmp_path, "v4.2.1-beta", "beta")


def test_release_readiness_fails_on_unclosed_issues(tmp_path):
    _write_release_project(tmp_path, "4.2.1-beta")
    _write_ms007_control_artifacts(tmp_path)
    _init_release_git_state(tmp_path, branch="beta-4.x")
    _git(tmp_path, "tag", "v4.2.0-beta")
    _write_backlog_issue(tmp_path, "ISSUE-100", status="new")
    (tmp_path / "fix.txt").write_text("fix\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "fix: thing (ISSUE-100)")
    _git(tmp_path, "tag", "v4.2.1-beta")
    _git(tmp_path, "update-ref", "refs/remotes/origin/beta-4.x", "HEAD")
    receipt = _write_release_receipt(tmp_path, "v4.2.1-beta")
    control_lint = _write_control_lint_receipt(tmp_path, "v4.2.1-beta")

    with pytest.raises(ValueError, match="ISSUE-100"):
        check_release_readiness(
            tmp_path,
            tag="v4.2.1-beta",
            channel="beta",
            branch="beta-4.x",
            receipt_path=receipt,
            control_lint_receipt_path=control_lint,
        )
