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
    DOCS_CAPABILITY_RECEIPT_TYPE,
    INSTALLED_SMOKE_RECEIPT_TYPE,
    PUBLIC_DISTRIBUTION_RECEIPT_TYPE,
    PUBLIC_DISTRIBUTION_INVENTORY_RECEIPT_TYPE,
    RELEASE_ARTIFACT_BUILD_RECEIPT_TYPE,
    RELEASE_IDENTITY_RECEIPT_TYPE,
    UPDATE_DISCOVERY_EXECUTION_RECEIPT_TYPE,
    hash_file,
    validate_docs_capability_receipt,
    validate_public_distribution_receipt,
    validate_release_identity_receipt,
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


def _write_control_receipt(path: Path, receipt_type: str, **overrides) -> Path:
    data = {
        "schema_version": 2,
        "receipt_type": receipt_type,
        "receipt_id": path.stem,
        "generated_at": "2026-05-26T12:00:00Z",
        "command_or_workflow_step": "test",
        "cwd": str(path.parent),
        "repo_root": str(path.parent),
        "branch": "stable-3.x",
        "commit": "abc123",
        "result": "pass",
        "input_artifacts": [],
    }
    data.update(overrides)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _git(project_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(project_dir), *args],
        capture_output=True,
        text=True,
        check=True,
    )


def _init_release_git_state(project_dir: Path, *, branch: str, tag: str) -> str:
    _git(project_dir, "init")
    _git(project_dir, "config", "user.email", "tests@sweetclaude.local")
    _git(project_dir, "config", "user.name", "SweetClaude Tests")
    _git(project_dir, "remote", "add", "origin", "https://example.invalid/sweetclaude.git")
    _git(project_dir, "checkout", "-b", branch)
    _git(project_dir, "add", ".")
    _git(project_dir, "commit", "-m", "release candidate")
    _git(project_dir, "tag", tag)
    _git(project_dir, "update-ref", f"refs/remotes/origin/{branch}", "HEAD")
    _git(project_dir, "config", f"branch.{branch}.remote", "origin")
    _git(project_dir, "config", f"branch.{branch}.merge", f"refs/heads/{branch}")
    return _git(project_dir, "rev-parse", "HEAD").stdout.strip()


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


def _release_artifact_build_receipt(
    project_dir: Path,
    artifact: Path,
    *,
    branch: str,
    commit: str,
    tag: str,
    artifact_sha256: str | None = None,
) -> Path:
    from control_receipts import hash_file

    return _write_control_receipt(
        project_dir / ".sweetclaude" / "state" / "evidence" / f"{tag}-{artifact.name}-build.json",
        RELEASE_ARTIFACT_BUILD_RECEIPT_TYPE,
        repo_root=str(project_dir),
        branch=branch,
        commit=commit,
        tag=tag,
        build_command=f"python -m build {artifact.name}",
        run_at="2026-05-26T12:00:00Z",
        exit_code=0,
        source_clean_state="clean",
        artifact_path=str(artifact),
        artifact_sha256=artifact_sha256 or hash_file(artifact),
    )


def _update_discovery_execution_receipt(
    project_dir: Path,
    artifact: Path,
    *,
    branch: str,
    commit: str,
    channel: str,
    tag: str,
    command: str,
) -> Path:
    from control_receipts import hash_file

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
        UPDATE_DISCOVERY_EXECUTION_RECEIPT_TYPE,
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
    branch: str = "stable-3.x",
    commit: str = "abc123",
    channel: str,
    tag: str,
) -> dict:
    from control_receipts import hash_file

    command = f"git ls-remote --tags origin {tag}"
    execution_receipt = _update_discovery_execution_receipt(
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


def _release_identity_receipt(
    project_dir: Path,
    version: str = "3.9.0",
    *,
    commit: str = "abc123",
    **overrides,
) -> Path:
    artifact = project_dir / "dist" / f"sweetclaude-{version}.tgz"
    branch = str(overrides.get("branch", "stable-3.x"))
    channel = str(overrides.get("channel", "legacy"))
    tag = str(overrides.get("tag", f"v{version}"))
    channel_defaults = {
        "stable": ("v5.99.0", project_dir / "dist" / "sweetclaude-5.99.0.tgz"),
        "beta": ("v4.1.99-beta", project_dir / "dist" / "sweetclaude-4.1.99-beta.tgz"),
        "legacy": ("v3.99.0", project_dir / "dist" / "sweetclaude-3.99.0.tgz"),
    }
    default_discovery: dict[str, dict] = {}
    for disc_channel, (default_tag, default_artifact) in channel_defaults.items():
        if disc_channel == channel:
            disc_tag, disc_artifact = tag, artifact
        else:
            disc_tag, disc_artifact = default_tag, default_artifact
        if not disc_artifact.exists():
            disc_artifact.write_text(f"{disc_channel} artifact\n", encoding="utf-8")
        default_discovery[disc_channel] = _discovery_entry(
            project_dir,
            disc_artifact,
            branch=branch,
            commit=commit,
            channel=disc_channel,
            tag=disc_tag,
        )
    data = {
        "branch": branch,
        "commit": commit,
        "tag": tag,
        "package_version": version,
        "plugin_version": version,
        "changelog_version": version,
        "channel": channel,
        "update_discovery": default_discovery,
        "install_path": str(project_dir),
        "artifact_path": str(artifact),
        "artifact_sha256": "will-be-overwritten",
    }
    data.update(overrides)
    from control_receipts import hash_file

    if data["artifact_sha256"] == "will-be-overwritten":
        data["artifact_sha256"] = hash_file(data["artifact_path"])
    if "build_receipt_path" not in data:
        build_receipt = _release_artifact_build_receipt(
            project_dir,
            Path(str(data["artifact_path"])),
            branch=str(data["branch"]),
            commit=str(data["commit"]),
            tag=str(data["tag"]),
            artifact_sha256=str(data["artifact_sha256"]),
        )
        data["build_receipt_path"] = str(build_receipt)
    return _write_control_receipt(
        project_dir / ".sweetclaude" / "state" / "evidence" / "release-identity.json",
        RELEASE_IDENTITY_RECEIPT_TYPE,
        repo_root=str(project_dir),
        **data,
    )


def _public_distribution_receipt(project_dir: Path, **overrides) -> Path:
    completed = subprocess.run(
        ["git", "-C", str(project_dir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    commit = completed.stdout.strip() if completed.returncode == 0 else "abc123"
    inventory = None
    if "inventory_receipt_path" not in overrides:
        inventory = _public_distribution_inventory_receipt(project_dir, commit=commit)
    data = {
        "permissions": ["read project files", "write approved maintenance outputs"],
        "installed_user_file_access": [".sweetclaude/", ".claude/"],
        "network_access": ["git remote tag/update discovery"],
        "hooks": ["hooks/session-preflight.sh"],
        "project_mutation_commands": ["/sweetclaude:configure migrate", "/sweetclaude:configure recover"],
        "provider_bound_data": ["Claude Code prompt and local project context"],
        "auth_assumptions": ["Claude Code local user approval gates mutating commands"],
        "secrets_handling": "does not require or persist provider secrets",
        "channel_visibility": "stable and beta channels are separately visible",
        "marketplace_or_distribution_visibility": "public plugin distribution",
        "evidence_source": "release distribution review",
        "approved_trust_model": "public plugin may inspect project files only for declared maintenance commands",
        "inventory_receipt_path": str(inventory) if inventory is not None else "",
    }
    data.update(overrides)
    return _write_control_receipt(
        project_dir / ".sweetclaude" / "state" / "evidence" / "public-distribution.json",
        PUBLIC_DISTRIBUTION_RECEIPT_TYPE,
        repo_root=str(project_dir),
        commit=commit,
        **data,
    )


def _public_distribution_inventory_receipt(
    project_dir: Path,
    *,
    commit: str = "abc123",
    **overrides,
) -> Path:
    branch = overrides.pop("branch", "stable-3.x")
    data = {
        "manifest_capabilities": ["slash-commands", "hooks"],
        "installed_plugin_files": [
            ".claude-plugin/plugin.json",
            "skill-library/configure/recover/SKILL.md",
        ],
        "hook_files": ["hooks/session-preflight.sh"],
        "mutation_commands": ["/sweetclaude:configure migrate", "/sweetclaude:configure recover"],
        "network_commands": ["git ls-remote --tags origin"],
        "generated_from": ["config/capability-manifest.yaml", ".claude-plugin/plugin.json"],
        "capability_manifest_path": "config/capability-manifest.yaml",
        "input_artifacts": [
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
    }
    data.update(overrides)
    return _write_control_receipt(
        project_dir / ".sweetclaude" / "state" / "evidence" / "public-distribution-inventory.json",
        PUBLIC_DISTRIBUTION_INVENTORY_RECEIPT_TYPE,
        repo_root=str(project_dir),
        branch=branch,
        commit=commit,
        **data,
    )


def _release_check(name: str, **fields) -> dict:
    check = {
        "name": name,
        "status": "pass",
        "command": f"verify {name}",
        "summary": f"{name} passed",
    }
    check.update(fields)
    return check


def _release_receipt(project_dir: Path, checks: list[dict], tag: str = "v3.9.0") -> Path:
    commit = _git(project_dir, "rev-parse", "HEAD").stdout.strip()
    receipt = {
        "schema_version": 1,
        "receipt_type": "release",
        "subject_id": f"release:{tag}",
        "status": "pass",
        "created_at": "2026-05-26T12:00:00Z",
        "commit": commit,
        "checks": checks,
    }
    path = project_dir / ".sweetclaude" / "state" / "evidence" / f"{tag}-release.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return path


def _base_release_checks(project_dir: Path) -> list[dict]:
    commit = _git(project_dir, "rev-parse", "HEAD").stdout.strip()
    return [
        *[
            _release_check(name)
            for name in REQUIRED_CHECKS
            if name not in {"release-identity", "docs-capability", "public-distribution"}
        ],
        _release_check("release-identity", evidence_path=str(_release_identity_receipt(project_dir, commit=commit))),
        _release_check("docs-capability", evidence_path=str(_docs_capability_receipt(project_dir, commit=commit))),
        _release_check("public-distribution", evidence_path=str(_public_distribution_receipt(project_dir))),
    ]


def _docs_capability_receipt(project_dir: Path, *, commit: str = "abc123") -> Path:
    smoke_output = project_dir / ".sweetclaude" / "state" / "evidence" / "recover-smoke.txt"
    smoke_output.parent.mkdir(parents=True, exist_ok=True)
    smoke_output.write_text("recover smoke passed\n", encoding="utf-8")
    stderr = project_dir / ".sweetclaude" / "state" / "evidence" / "recover-smoke.stderr"
    stderr.write_text("", encoding="utf-8")
    version_data = json.loads((project_dir / "package.json").read_text(encoding="utf-8"))
    artifact = project_dir / "dist" / f"sweetclaude-{version_data['version']}.tgz"
    from control_receipts import hash_file

    installed_smoke = _write_control_receipt(
        project_dir / ".sweetclaude" / "state" / "evidence" / "installed-smoke.json",
        INSTALLED_SMOKE_RECEIPT_TYPE,
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
        DOCS_CAPABILITY_RECEIPT_TYPE,
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


def test_t021_release_identity_rejects_missing_artifact_hash(tmp_path):
    _write_release_project(tmp_path)
    receipt = _release_identity_receipt(tmp_path, artifact_sha256="")

    with pytest.raises(ValueError, match="artifact_sha256"):
        validate_release_identity_receipt(receipt)


def test_t021_release_identity_rejects_stale_artifact_hash(tmp_path):
    _write_release_project(tmp_path)
    receipt = _release_identity_receipt(tmp_path)
    (tmp_path / "dist" / "sweetclaude-3.9.0.tgz").write_text("changed\n", encoding="utf-8")

    with pytest.raises(ValueError, match="artifact.*sha256 mismatch"):
        validate_release_identity_receipt(receipt, verify_artifact_hash=True)


def test_t022_release_identity_rejects_stable_update_discovery_to_beta(tmp_path):
    _write_release_project(tmp_path)
    beta_artifact = tmp_path / "dist" / "sweetclaude-4.1.99-beta.tgz"
    beta_artifact.write_text("beta artifact\n", encoding="utf-8")
    receipt = _release_identity_receipt(
        tmp_path,
        update_discovery={
            "stable": _discovery_entry(
                tmp_path,
                beta_artifact,
                channel="beta",
                tag="v4.1.99-beta",
            ),
            "beta": _discovery_entry(
                tmp_path,
                beta_artifact,
                channel="beta",
                tag="v4.1.99-beta",
            ),
        },
    )

    with pytest.raises(ValueError, match="stable update discovery"):
        validate_release_identity_receipt(receipt)


def test_t022_release_identity_rejects_missing_build_receipt(tmp_path):
    _write_release_project(tmp_path)
    receipt = _release_identity_receipt(tmp_path, build_receipt_path="")

    with pytest.raises(ValueError, match="build_receipt_path"):
        validate_release_identity_receipt(receipt)


def test_t022_release_identity_rejects_missing_discovery_execution_receipt(tmp_path):
    _write_release_project(tmp_path)
    receipt = _release_identity_receipt(tmp_path)
    data = json.loads(receipt.read_text(encoding="utf-8"))
    data["update_discovery"]["stable"].pop("execution_receipt_path")
    receipt.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="execution_receipt_path"):
        validate_release_identity_receipt(receipt)


def test_t022_release_identity_rejects_discovery_stdout_drift(tmp_path):
    _write_release_project(tmp_path)
    receipt = _release_identity_receipt(tmp_path)
    data = json.loads(receipt.read_text(encoding="utf-8"))
    stdout = Path(data["update_discovery"]["stable"]["execution_receipt_path"])
    execution = json.loads(stdout.read_text(encoding="utf-8"))
    stdout_path = Path(execution["stdout_path"])
    stdout_path.write_text(
        json.dumps(
            {
                "channel": "beta",
                "tag": "v4.1.99-beta",
                "artifact": data["update_discovery"]["beta"]["artifact"],
                "artifact_sha256": data["update_discovery"]["beta"]["artifact_sha256"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    execution["stdout_sha256"] = hash_file(stdout_path)
    stdout.write_text(json.dumps(execution, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="stdout channel mismatch"):
        validate_release_identity_receipt(receipt)


def test_t022_release_identity_rejects_discovery_stdout_missing_artifact_hash(tmp_path):
    _write_release_project(tmp_path)
    receipt = _release_identity_receipt(tmp_path)
    data = json.loads(receipt.read_text(encoding="utf-8"))
    execution_receipt = Path(data["update_discovery"]["stable"]["execution_receipt_path"])
    execution = json.loads(execution_receipt.read_text(encoding="utf-8"))
    stdout_path = Path(execution["stdout_path"])
    stdout = json.loads(stdout_path.read_text(encoding="utf-8"))
    stdout.pop("artifact_sha256")
    stdout_path.write_text(json.dumps(stdout) + "\n", encoding="utf-8")
    execution["stdout_sha256"] = hash_file(stdout_path)
    execution_receipt.write_text(json.dumps(execution, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="stdout is missing artifact_sha256"):
        validate_release_identity_receipt(receipt)


def test_t023_public_distribution_rejects_missing_provider_bound_data(tmp_path):
    _write_release_project(tmp_path)
    receipt = _public_distribution_receipt(tmp_path, provider_bound_data=[])

    with pytest.raises(ValueError, match="provider_bound_data"):
        validate_public_distribution_receipt(receipt)


def test_t023_public_distribution_rejects_missing_inventory_receipt(tmp_path):
    _write_release_project(tmp_path)
    receipt = _public_distribution_receipt(tmp_path, inventory_receipt_path="")

    with pytest.raises(ValueError, match="inventory_receipt_path"):
        validate_public_distribution_receipt(receipt)


def test_t023_public_distribution_rejects_inventory_mutation_omission(tmp_path):
    _write_release_project(tmp_path)
    inventory = _public_distribution_inventory_receipt(
        tmp_path,
        mutation_commands=["/sweetclaude:configure migrate", "/sweetclaude:configure recover", "/sweetclaude:update"],
    )
    receipt = _public_distribution_receipt(tmp_path, inventory_receipt_path=str(inventory))

    with pytest.raises(ValueError, match="mutation command"):
        validate_public_distribution_receipt(receipt)


def test_t023_public_distribution_rejects_bogus_inventory_source(tmp_path):
    _write_release_project(tmp_path)
    inventory = _public_distribution_inventory_receipt(
        tmp_path,
        generated_from=["config/missing.yaml", ".claude-plugin/plugin.json"],
    )
    receipt = _public_distribution_receipt(tmp_path, inventory_receipt_path=str(inventory))

    with pytest.raises(ValueError, match="generated_from path does not exist"):
        validate_public_distribution_receipt(receipt)


def test_t023_public_distribution_rejects_omitted_real_hook(tmp_path):
    _write_release_project(tmp_path)
    extra_hook = tmp_path / "hooks" / "secret-network-hook.sh"
    extra_hook.write_text("#!/bin/sh\ncurl https://example.invalid\n", encoding="utf-8")
    receipt = _public_distribution_receipt(tmp_path)

    with pytest.raises(ValueError, match="hook_files omits discovered files"):
        validate_public_distribution_receipt(receipt)


def test_t020_docs_capability_rejects_unproven_claim(tmp_path):
    receipt = _write_control_receipt(
        tmp_path / "docs-capability.json",
        DOCS_CAPABILITY_RECEIPT_TYPE,
        claims=[
                {
                    "claim": "/sweetclaude:configure repairs project state",
                    "status": "proven",
                }
        ],
    )

    with pytest.raises(ValueError, match="installed_entrypoint"):
        validate_docs_capability_receipt(receipt)


def test_t020_docs_capability_accepts_installed_entrypoint_proof(tmp_path):
    _write_release_project(tmp_path)
    receipt = _docs_capability_receipt(tmp_path)

    parsed = validate_docs_capability_receipt(receipt)

    assert parsed["receipt_type"] == DOCS_CAPABILITY_RECEIPT_TYPE


def test_t020_docs_capability_rejects_inline_smoke_without_execution_receipt(tmp_path):
    _write_release_project(tmp_path)
    receipt = _docs_capability_receipt(tmp_path)
    data = json.loads(receipt.read_text(encoding="utf-8"))
    data["claims"][0].pop("installed_smoke_receipt_path")
    receipt.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="installed_smoke_receipt_path"):
        validate_docs_capability_receipt(receipt)


def test_t020_docs_capability_rejects_fabricated_entrypoint_lookup(tmp_path):
    _write_release_project(tmp_path)
    receipt = _docs_capability_receipt(tmp_path)
    data = json.loads(receipt.read_text(encoding="utf-8"))
    smoke_receipt = Path(data["claims"][0]["installed_smoke_receipt_path"])
    smoke = json.loads(smoke_receipt.read_text(encoding="utf-8"))
    source_path = Path(smoke["entrypoint_source_paths"][0]["path"])
    source_path.write_text("no recover entrypoint here\n", encoding="utf-8")
    smoke["entrypoint_source_paths"][0]["sha256"] = hash_file(source_path)
    smoke_receipt.write_text(json.dumps(smoke, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="installed_entrypoint was not found"):
        validate_docs_capability_receipt(receipt)


def test_t020_docs_capability_rejects_non_installed_entrypoint_source(tmp_path):
    _write_release_project(tmp_path)
    receipt = _docs_capability_receipt(tmp_path)
    data = json.loads(receipt.read_text(encoding="utf-8"))
    smoke_receipt = Path(data["claims"][0]["installed_smoke_receipt_path"])
    smoke = json.loads(smoke_receipt.read_text(encoding="utf-8"))
    outside = tmp_path / "scratch-entrypoint.md"
    outside.write_text("Invoke /sweetclaude:configure from scratch.\n", encoding="utf-8")
    smoke["entrypoint_source_paths"] = [
        {
            "path": str(outside),
            "sha256": hash_file(outside),
        }
    ]
    smoke_receipt.write_text(json.dumps(smoke, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must be inside the installed plugin load surface"):
        validate_docs_capability_receipt(receipt)


def test_release_readiness_requires_release_identity_and_public_distribution(tmp_path):
    _write_release_project(tmp_path)
    _init_release_git_state(tmp_path, branch="stable-3.x", tag="v3.9.0")
    receipt = _release_receipt(
        tmp_path,
        checks=[_release_check(name) for name in REQUIRED_CHECKS if name not in {"release-identity"}],
    )

    with pytest.raises(ValueError, match="release-identity"):
        check_release_readiness(
            tmp_path,
            tag="v3.9.0",
            channel="legacy",
            branch="stable-3.x",
            receipt_path=receipt,
        )


def test_release_readiness_accepts_identity_and_public_distribution(tmp_path):
    _write_release_project(tmp_path)
    _init_release_git_state(tmp_path, branch="stable-3.x", tag="v3.9.0")
    receipt = _release_receipt(tmp_path, checks=_base_release_checks(tmp_path))

    result = check_release_readiness(
        tmp_path,
        tag="v3.9.0",
        channel="legacy",
        branch="stable-3.x",
        receipt_path=receipt,
    )

    assert result["ok"] is True


def test_release_readiness_rejects_stale_release_identity_commit(tmp_path):
    _write_release_project(tmp_path)
    _init_release_git_state(tmp_path, branch="stable-3.x", tag="v3.9.0")
    checks = _base_release_checks(tmp_path)
    stale_identity = _release_identity_receipt(tmp_path, commit="old")
    for check in checks:
        if check["name"] == "release-identity":
            check["evidence_path"] = str(stale_identity)
    receipt = _release_receipt(tmp_path, checks=checks)

    with pytest.raises(ValueError, match="commit mismatch"):
        check_release_readiness(
            tmp_path,
            tag="v3.9.0",
            channel="legacy",
            branch="stable-3.x",
            receipt_path=receipt,
        )


def test_release_readiness_rejects_missing_docs_capability(tmp_path):
    _write_release_project(tmp_path)
    _init_release_git_state(tmp_path, branch="stable-3.x", tag="v3.9.0")
    receipt = _release_receipt(
        tmp_path,
        checks=[
            check
            for check in _base_release_checks(tmp_path)
            if check["name"] != "docs-capability"
        ],
    )

    with pytest.raises(ValueError, match="docs-capability"):
        check_release_readiness(
            tmp_path,
            tag="v3.9.0",
            channel="legacy",
            branch="stable-3.x",
            receipt_path=receipt,
        )


def test_release_readiness_rejects_wrong_discovery_tag_for_release_channel(tmp_path):
    _write_release_project(tmp_path, version="5.0.0")
    (tmp_path / "dist" / "sweetclaude-3.99.0.tgz").write_text(
        "legacy artifact\n",
        encoding="utf-8",
    )
    _init_release_git_state(tmp_path, branch="main", tag="v5.0.0")
    commit = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    smoke_output = tmp_path / ".sweetclaude" / "state" / "evidence" / "stable-docs-smoke.txt"
    smoke_output.parent.mkdir(parents=True, exist_ok=True)
    smoke_output.write_text("installed command smoke passed\n", encoding="utf-8")

    # The stable (release-channel) discovery entry carries a tag that does not
    # match the release tag — the gate must reject the mismatch.
    stale_identity = _release_identity_receipt(
        tmp_path,
        "5.0.0",
        commit=commit,
        branch="main",
        channel="stable",
        tag="v5.0.0",
        update_discovery={
            "stable": _discovery_entry(
                tmp_path,
                tmp_path / "dist" / "sweetclaude-5.99.0.tgz",
                branch="main",
                commit=commit,
                channel="stable",
                tag="v5.99.0",
            ),
            "legacy": _discovery_entry(
                tmp_path,
                tmp_path / "dist" / "sweetclaude-3.99.0.tgz",
                branch="main",
                commit=commit,
                channel="legacy",
                tag="v3.99.0",
            ),
        },
    )
    docs_receipt = _docs_capability_receipt(tmp_path, commit=commit)
    checks = [
        *[
            _release_check(name)
            for name in REQUIRED_CHECKS
            if name not in {"release-identity", "docs-capability", "public-distribution"}
        ],
        _release_check("release-identity", evidence_path=str(stale_identity)),
        _release_check("docs-capability", evidence_path=str(docs_receipt)),
        _release_check("public-distribution", evidence_path=str(_public_distribution_receipt(tmp_path))),
    ]
    receipt = _release_receipt(tmp_path, checks=checks, tag="v5.0.0")

    with pytest.raises(ValueError, match="update discovery|Update discovery execution"):
        check_release_readiness(
            tmp_path,
            tag="v5.0.0",
            channel="stable",
            branch="main",
            receipt_path=receipt,
        )


def test_release_readiness_rejects_off_project_artifact_path(tmp_path):
    _write_release_project(tmp_path)
    _init_release_git_state(tmp_path, branch="stable-3.x", tag="v3.9.0")
    commit = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    outside = tmp_path.parent / "outside-artifact.tgz"
    outside.write_text("artifact\n", encoding="utf-8")
    from control_receipts import hash_file

    checks = [
        check
        for check in _base_release_checks(tmp_path)
        if check["name"] != "release-identity"
    ]
    stale_identity = _release_identity_receipt(
        tmp_path,
        commit=commit,
        artifact_path=str(outside),
        artifact_sha256=hash_file(outside),
    )
    checks.append(_release_check("release-identity", evidence_path=str(stale_identity)))
    receipt = _release_receipt(tmp_path, checks=checks)

    with pytest.raises(ValueError, match="artifact_path mismatch"):
        check_release_readiness(
            tmp_path,
            tag="v3.9.0",
            channel="legacy",
            branch="stable-3.x",
            receipt_path=receipt,
        )
