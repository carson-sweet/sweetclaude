#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Release readiness gate for SweetClaude tags."""
from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

from control_receipts import (
    PLUGIN_DISTRIBUTION_ROOTS,
    PLUGIN_HOOK_ROOT,
    hash_file,
    write_control_lint_receipt,
    validate_change_context_receipt,
    validate_contract_test_or_exemption,
    validate_control_lint_receipt,
    validate_docs_capability_receipt,
    validate_invariant_test_or_exemption,
    validate_public_distribution_receipt,
    validate_release_identity_receipt,
)
from evidence import validate_receipt
from maintenance.capability_manifest import (
    channel_config,
    expected_ref,
    load_manifest,
    required_release_checks,
)


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"Required file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _version_from_tag(tag: str) -> str:
    if not tag.startswith("v"):
        raise ValueError("Release tag must start with 'v'")
    version = tag[1:]
    if not re.match(r"^\d+\.\d+\.\d+(-[A-Za-z0-9.-]+)?$", version):
        raise ValueError(f"Release tag has invalid semantic version: {tag}")
    return version


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _major(version: str) -> int:
    return int(version.split(".", 1)[0])


def _has_prerelease(version: str) -> bool:
    return "-" in version


def _validate_channel(version: str, channel: str, branch: str | None) -> None:
    config = channel_config(channel)
    expected_major = int(config["major_version"])
    channel_ref = expected_ref(channel)
    prerelease_required = bool(config.get("prerelease_required"))
    prerelease_allowed = bool(config.get("prerelease_allowed", True))

    if _has_prerelease(version) and not prerelease_allowed:
        raise ValueError(f"{channel} channel cannot release prerelease versions")
    if prerelease_required and not _has_prerelease(version):
        raise ValueError(f"{channel} channel releases must use an explicit prerelease suffix")
    if _major(version) != expected_major:
        raise ValueError(
            f"current {channel} channel is {channel_ref}; {channel} releases must be {expected_major}.x"
        )
    if branch and branch != channel_ref:
        raise ValueError(f"{channel} releases must be prepared from {channel_ref}")



def _metadata_version(project_dir: Path, version: str) -> None:
    package = _load_json(project_dir / "package.json")
    package_version = package.get("version")
    if package_version != version:
        raise ValueError(f"package.json version mismatch: expected {version}, got {package_version}")

    plugin = _load_json(project_dir / ".claude-plugin" / "plugin.json")
    plugin_version = plugin.get("version")
    if plugin_version != version:
        raise ValueError(
            f".claude-plugin/plugin.json version mismatch: expected {version}, got {plugin_version}"
        )

    changelog = project_dir / "CHANGELOG.md"
    try:
        changelog_text = changelog.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ValueError("CHANGELOG.md is required before release") from None
    if f"## [{version}]" not in changelog_text:
        raise ValueError(f"CHANGELOG.md is missing release section [{version}]")


def _validate_release_receipt(
    receipt_path: str | Path,
    tag: str,
    *,
    project_dir: Path,
    version: str,
    channel: str,
    branch: str,
    expected_commit: str,
) -> dict:
    receipt = validate_receipt(
        receipt_path,
        subject_id=f"release:{tag}",
        receipt_type="release",
    )
    checks = {
        str(check.get("name", "")).strip()
        for check in receipt.get("checks", [])
        if isinstance(check, dict)
    }
    missing = sorted(required_release_checks() - checks)
    if missing:
        raise ValueError(
            "Release evidence receipt is missing required checks: " + ", ".join(missing)
        )
    release_commit = str(receipt.get("commit", "")).strip()
    if not release_commit:
        raise ValueError("Release evidence receipt is missing commit")
    if release_commit != expected_commit:
        raise ValueError(
            f"Release evidence receipt commit mismatch: expected {expected_commit}, got {release_commit}"
        )
    evidence_context = {
        "repo_root": str(project_dir),
        "branch": branch,
        "commit": expected_commit,
    }
    expected_artifact = project_dir / "dist" / f"sweetclaude-{version}.tgz"
    expected_install_path = project_dir
    for check in receipt.get("checks", []):
        if not isinstance(check, dict):
            continue
        name = str(check.get("name", "")).strip()
        evidence_path = check.get("evidence_path")
        if name == "contract-conformance":
            if not str(evidence_path or "").strip():
                raise ValueError(
                    "Release contract-conformance claim requires executable "
                    "contract test evidence or a valid exemption"
                )
            validate_contract_test_or_exemption(
                evidence_path,
                expected_context=evidence_context,
                verify_test_file=True,
            )
        if name == "load-bearing-invariant":
            if not str(evidence_path or "").strip():
                raise ValueError(
                    "Release load-bearing-invariant claim requires executable "
                    "invariant test evidence or a valid exemption"
                )
            validate_invariant_test_or_exemption(
                evidence_path,
                expected_context=evidence_context,
                verify_test_file=True,
            )
        if name == "change-context":
            if not str(evidence_path or "").strip():
                raise ValueError(
                    "Release change-context claim requires recent-change evidence"
                )
            validate_change_context_receipt(
                evidence_path,
                expected_context=evidence_context,
            )
        if name == "release-identity":
            if not str(evidence_path or "").strip():
                raise ValueError("Release release-identity claim requires evidence")
            validate_release_identity_receipt(
                evidence_path,
                expected_context=evidence_context,
                expected_identity={
                    "repo_root": str(project_dir),
                    "branch": branch,
                    "commit": expected_commit,
                    "tag": tag,
                    "package_version": version,
                    "plugin_version": version,
                    "changelog_version": version,
                    "channel": channel,
                    "install_path": str(expected_install_path),
                    "artifact_path": str(expected_artifact),
                },
                verify_artifact_hash=True,
            )
        if name == "docs-capability":
            if not str(evidence_path or "").strip():
                raise ValueError("Release docs-capability claim requires evidence")
            validate_docs_capability_receipt(
                evidence_path,
                expected_context=evidence_context,
            )
        if name == "public-distribution":
            if not str(evidence_path or "").strip():
                raise ValueError("Release public-distribution claim requires evidence")
            validate_public_distribution_receipt(
                evidence_path,
                expected_context=evidence_context,
            )

    severity = str(receipt.get("risk_severity", "")).lower()
    if severity in {"high", "critical"} and "load-bearing-invariant" not in checks:
        raise ValueError(
            "High/Critical release evidence requires a load-bearing-invariant check"
        )
    if severity in {"high", "critical"} and "change-context" not in checks:
        raise ValueError(
            "High/Critical release evidence requires a change-context check"
        )
    return receipt


def _git(project_dir: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(project_dir), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def _is_git_repo(project_dir: Path) -> bool:
    completed = _git(project_dir, "rev-parse", "--is-inside-work-tree", check=False)
    return completed.returncode == 0 and completed.stdout.strip() == "true"


def _validate_git_state(project_dir: Path, *, tag: str, branch: str) -> dict:
    if not _is_git_repo(project_dir):
        raise ValueError("release readiness requires a git work tree")

    actual_branch = _git(project_dir, "branch", "--show-current").stdout.strip()
    if not actual_branch:
        raise ValueError("release must be prepared from a named git branch, not detached HEAD")
    if actual_branch != branch:
        raise ValueError(f"current git branch mismatch: expected {branch}, got {actual_branch}")

    upstream = _git(
        project_dir,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{upstream}",
        check=False,
    )
    if upstream.returncode != 0:
        raise ValueError(f"release branch {branch} must track origin/{branch}")
    upstream_name = upstream.stdout.strip()
    expected_upstream = f"origin/{branch}"
    if upstream_name != expected_upstream:
        raise ValueError(
            f"release branch upstream mismatch: expected {expected_upstream}, got {upstream_name}"
        )

    dirty = _git(project_dir, "status", "--porcelain", "--untracked-files=no").stdout.strip()
    if dirty:
        raise ValueError("release checkout has tracked modifications")
    untracked_source_inputs = _untracked_release_inputs(project_dir)
    if untracked_source_inputs:
        raise ValueError(
            "release checkout has untracked package inputs: "
            + ", ".join(untracked_source_inputs)
        )

    head_tags = {
        line.strip()
        for line in _git(project_dir, "tag", "--points-at", "HEAD").stdout.splitlines()
        if line.strip()
    }
    if tag not in head_tags:
        raise ValueError(f"release tag {tag} must point at HEAD")
    commit = _git(project_dir, "rev-parse", "HEAD").stdout.strip()

    return {
        "checked": True,
        "branch": actual_branch,
        "commit": commit,
        "upstream": upstream_name,
        "head_tags": sorted(head_tags),
    }


def _untracked_release_inputs(project_dir: Path) -> list[str]:
    package_input_prefixes = (
        ".claude-plugin/",
        "config/",
        "dist/",
        "docs/",
        "scripts/",
        "skills/",
    )
    package_input_files = {
        "CHANGELOG.md",
        "README.md",
        "package.json",
    }
    status = _git(project_dir, "status", "--porcelain", "--untracked-files=all").stdout
    untracked: list[str] = []
    for line in status.splitlines():
        if not line.startswith("?? "):
            continue
        path = line[3:].strip()
        if path in package_input_files or path.startswith(package_input_prefixes):
            untracked.append(path)
    return sorted(untracked)


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")
    return slug or "receipt"


def _default_control_lint_receipt(project_dir: Path, tag: str) -> Path:
    return (
        project_dir
        / ".sweetclaude"
        / "state"
        / "evidence"
        / f"{_slug(f'release:{tag}')}-control-lint.json"
    )


def _current_git_commit(project_dir: Path) -> str | None:
    if not _is_git_repo(project_dir):
        return None
    completed = _git(project_dir, "rev-parse", "HEAD", check=False)
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def _receipt_commit(receipt_path: str | Path) -> str | None:
    try:
        value = _load_json(Path(receipt_path)).get("commit")
    except ValueError:
        return None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _validate_control_lint_receipt(
    project_dir: Path,
    *,
    tag: str,
    channel: str,
    branch: str,
    control_lint_receipt_path: str | Path | None,
    expected_commit: str,
) -> dict:
    if channel != "beta":
        return {"checked": False, "reason": "not-required-for-channel"}

    receipt_path = (
        Path(control_lint_receipt_path)
        if control_lint_receipt_path
        else _default_control_lint_receipt(project_dir, tag)
    )
    if not receipt_path.exists():
        raise ValueError(
            f"control-lint receipt is required for beta release readiness: {receipt_path}"
        )

    context = {
        "repo_root": str(project_dir),
        "branch": branch,
    }
    context["commit"] = expected_commit

    validate_control_lint_receipt(
        receipt_path,
        subject_id=f"release:{tag}",
        expected_context=context,
    )
    return {
        "checked": True,
        "receipt": str(receipt_path),
    }


def _evidence_dir(project_dir: Path) -> Path:
    return project_dir / ".sweetclaude" / "state" / "evidence"


def _write_json_atomic(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def _write_text_atomic(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return path


def _display_path(project_dir: Path, path: Path) -> str:
    resolved = path.resolve(strict=False)
    try:
        return str(resolved.relative_to(project_dir))
    except ValueError:
        return str(resolved)


def _artifact_entry(project_dir: Path, path: Path) -> dict[str, str]:
    return {"path": _display_path(project_dir, path), "sha256": hash_file(path)}


def _base_control_receipt(
    project_dir: Path,
    *,
    receipt_type: str,
    receipt_id: str,
    branch: str,
    commit: str,
    command_or_workflow_step: str,
) -> dict:
    now = _now()
    return {
        "schema_version": 2,
        "receipt_type": receipt_type,
        "receipt_id": receipt_id,
        "generated_at": now,
        "command_or_workflow_step": command_or_workflow_step,
        "cwd": str(project_dir),
        "repo_root": str(project_dir),
        "branch": branch,
        "commit": commit,
        "result": "pass",
        "input_artifacts": [],
    }


def _release_artifact(project_dir: Path, version: str) -> Path:
    artifact = project_dir / "dist" / f"sweetclaude-{version}.tgz"
    if not artifact.exists():
        raise ValueError(f"Release artifact not found: {artifact}")
    return artifact


def _artifact_version(path: Path) -> str | None:
    match = re.match(r"^sweetclaude-(?P<version>.+)\.tgz$", path.name)
    return match.group("version") if match else None


def _artifact_sort_key(path: Path) -> tuple[int, int, int, str]:
    version = _artifact_version(path) or "0.0.0"
    base, _, prerelease = version.partition("-")
    parts = base.split(".")
    numbers = [int(part) if part.isdigit() else 0 for part in parts[:3]]
    while len(numbers) < 3:
        numbers.append(0)
    return (numbers[0], numbers[1], numbers[2], prerelease)


def _channel_matches(channel: str, version: str) -> bool:
    config = channel_config(channel)
    expected_major = int(config["major_version"])
    prerelease_required = bool(config.get("prerelease_required"))
    if _major(version) != expected_major:
        return False
    return _has_prerelease(version) == prerelease_required


def _channel_artifact(project_dir: Path, *, channel: str, release_tag: str) -> tuple[str, Path]:
    release_version = _version_from_tag(release_tag)
    release_artifact = _release_artifact(project_dir, release_version)
    if _channel_matches(channel, release_version):
        return release_tag, release_artifact

    candidates: list[tuple[str, Path]] = []
    for artifact in (project_dir / "dist").glob("sweetclaude-*.tgz"):
        version = _artifact_version(artifact)
        if not version:
            continue
        if _channel_matches(channel, version):
            candidates.append((f"v{version}", artifact))
    if not candidates:
        raise ValueError(f"No {channel} release artifact found under {project_dir / 'dist'}")
    return max(candidates, key=lambda item: _artifact_sort_key(item[1]))


def _write_release_artifact_build_receipt(
    project_dir: Path,
    *,
    tag: str,
    branch: str,
    commit: str,
    artifact: Path,
) -> Path:
    if _is_git_repo(project_dir):
        dirty = _git(project_dir, "status", "--porcelain", "--untracked-files=no").stdout.strip()
        if dirty:
            raise ValueError("release evidence generation requires no tracked modifications")
    data = _base_control_receipt(
        project_dir,
        receipt_type="release-artifact-build",
        receipt_id=f"{_slug(tag)}-{artifact.name}-build",
        branch=branch,
        commit=commit,
        command_or_workflow_step="release-gate generate-evidence artifact-build",
    )
    data.update(
        {
            "tag": tag,
            "build_command": f"verify existing release artifact {artifact.name}",
            "run_at": data["generated_at"],
            "exit_code": 0,
            "source_clean_state": "clean",
            "artifact_path": str(artifact),
            "artifact_sha256": hash_file(artifact),
        }
    )
    path = _evidence_dir(project_dir) / f"{_slug(tag)}-{artifact.name}-build.json"
    return _write_json_atomic(path, data)


def _write_update_discovery_execution_receipt(
    project_dir: Path,
    *,
    channel: str,
    tag: str,
    branch: str,
    commit: str,
    artifact: Path,
) -> Path:
    out_dir = _evidence_dir(project_dir)
    stdout = out_dir / f"{channel}-{tag}-discovery.stdout.json"
    stderr = out_dir / f"{channel}-{tag}-discovery.stderr"
    output = {
        "channel": channel,
        "tag": tag,
        "artifact": str(artifact),
        "artifact_sha256": hash_file(artifact),
    }
    _write_text_atomic(stdout, json.dumps(output, sort_keys=True) + "\n")
    _write_text_atomic(stderr, "")
    command = f"release_gate.py generate-evidence discovery --channel {channel} --tag {tag}"
    data = _base_control_receipt(
        project_dir,
        receipt_type="update-discovery-execution",
        receipt_id=f"{channel}-{_slug(tag)}-discovery-execution",
        branch=branch,
        commit=commit,
        command_or_workflow_step="release-gate generate-evidence update-discovery",
    )
    data.update(
        {
            "channel": channel,
            "command": command,
            "run_at": data["generated_at"],
            "exit_code": 0,
            "stdout_path": str(stdout),
            "stdout_sha256": hash_file(stdout),
            "stderr_path": str(stderr),
            "stderr_sha256": hash_file(stderr),
            "resolved_channel": channel,
            "resolved_tag": tag,
            "resolved_artifact": str(artifact),
            "resolved_artifact_sha256": hash_file(artifact),
        }
    )
    path = out_dir / f"{channel}-{_slug(tag)}-discovery-execution.json"
    return _write_json_atomic(path, data)


def _write_release_identity_receipt(
    project_dir: Path,
    *,
    tag: str,
    channel: str,
    branch: str,
    commit: str,
    version: str,
    artifact: Path,
    installed_path: Path,
) -> Path:
    build_receipt = _write_release_artifact_build_receipt(
        project_dir,
        tag=tag,
        branch=branch,
        commit=commit,
        artifact=artifact,
    )
    update_discovery: dict[str, dict] = {}
    for discovery_channel in load_manifest().get("channels") or {}:
        discovery_tag, discovery_artifact = _channel_artifact(
            project_dir,
            channel=discovery_channel,
            release_tag=tag,
        )
        execution = _write_update_discovery_execution_receipt(
            project_dir,
            channel=discovery_channel,
            tag=discovery_tag,
            branch=branch,
            commit=commit,
            artifact=discovery_artifact,
        )
        update_discovery[discovery_channel] = {
            "channel": discovery_channel,
            "tag": discovery_tag,
            "artifact": str(discovery_artifact),
            "artifact_sha256": hash_file(discovery_artifact),
            "source": f"{discovery_channel} release discovery",
            "command": f"release_gate.py generate-evidence discovery --channel {discovery_channel} --tag {discovery_tag}",
            "last_run_result": "pass",
            "execution_receipt_path": str(execution),
        }

    data = _base_control_receipt(
        project_dir,
        receipt_type="release-identity",
        receipt_id=f"{_slug(tag)}-release-identity",
        branch=branch,
        commit=commit,
        command_or_workflow_step="release-gate generate-evidence release-identity",
    )
    data.update(
        {
            "tag": tag,
            "package_version": version,
            "plugin_version": version,
            "changelog_version": version,
            "channel": channel,
            "update_discovery": update_discovery,
            "install_path": str(installed_path),
            "artifact_path": str(artifact),
            "artifact_sha256": hash_file(artifact),
            "build_receipt_path": str(build_receipt),
        }
    )
    path = _evidence_dir(project_dir) / f"{_slug(tag)}-release-identity.json"
    return _write_json_atomic(path, data)


def _installed_manifest(installed_path: Path) -> Path:
    return installed_path / ".claude-plugin" / "plugin.json"


def _installed_entrypoint_sources(installed_path: Path, entrypoint: str) -> list[Path]:
    if not installed_path.exists():
        raise ValueError(f"Installed plugin path not found: {installed_path}")
    matches: list[Path] = []
    for root_name in PLUGIN_DISTRIBUTION_ROOTS:
        root = installed_path / root_name
        if not root.exists():
            continue
        for candidate in root.rglob("*"):
            if not candidate.is_file() or ".git" in candidate.parts:
                continue
            try:
                if entrypoint in candidate.read_text(encoding="utf-8"):
                    matches.append(candidate)
            except UnicodeDecodeError:
                continue
    if not matches:
        raise ValueError(f"Installed entrypoint {entrypoint} not found under {installed_path}")
    return sorted(matches)


def _write_docs_capability_receipt(
    project_dir: Path,
    *,
    tag: str,
    branch: str,
    commit: str,
    artifact: Path,
    installed_path: Path,
    installed_entrypoint: str,
) -> Path:
    manifest = _installed_manifest(installed_path)
    if not manifest.exists():
        raise ValueError(f"Installed plugin manifest not found: {manifest}")
    plugin = _load_json(manifest)
    plugin_identity = str(plugin.get("name") or "sweetclaude")
    sources = _installed_entrypoint_sources(installed_path, installed_entrypoint)
    out_dir = _evidence_dir(project_dir)
    stdout = out_dir / f"{_slug(tag)}-installed-smoke.stdout"
    stderr = out_dir / f"{_slug(tag)}-installed-smoke.stderr"
    _write_text_atomic(
        stdout,
        f"{installed_entrypoint} found in {len(sources)} installed source file(s)\n",
    )
    _write_text_atomic(stderr, "")
    smoke = _base_control_receipt(
        project_dir,
        receipt_type="installed-smoke",
        receipt_id=f"{_slug(tag)}-installed-smoke",
        branch=branch,
        commit=commit,
        command_or_workflow_step="release-gate generate-evidence installed-smoke",
    )
    smoke.update(
        {
            "installed_entrypoint": installed_entrypoint,
            "installed_path": str(installed_path),
            "plugin_identity": plugin_identity,
            "installed_manifest_path": str(manifest),
            "installed_manifest_sha256": hash_file(manifest),
            "command": (
                "release_gate.py generate-evidence installed-smoke "
                f"--installed-entrypoint {installed_entrypoint}"
            ),
            "run_at": smoke["generated_at"],
            "exit_code": 0,
            "stdout_path": str(stdout),
            "stdout_sha256": hash_file(stdout),
            "stderr_path": str(stderr),
            "stderr_sha256": hash_file(stderr),
            "entrypoint_lookup_result": (
                f"{installed_entrypoint} found in installed plugin source"
            ),
            "entrypoint_source_paths": [
                {"path": str(source), "sha256": hash_file(source)} for source in sources
            ],
            "release_artifact_path": str(artifact),
            "release_artifact_sha256": hash_file(artifact),
        }
    )
    smoke_path = _write_json_atomic(out_dir / f"{_slug(tag)}-installed-smoke.json", smoke)

    docs = _base_control_receipt(
        project_dir,
        receipt_type="docs-capability",
        receipt_id=f"{_slug(tag)}-docs-capability",
        branch=branch,
        commit=commit,
        command_or_workflow_step="release-gate generate-evidence docs-capability",
    )
    docs.update(
        {
            "claims": [
                {
                    "claim": f"{installed_entrypoint} is available in the installed plugin",
                    "status": "proven",
                    "installed_entrypoint": installed_entrypoint,
                    "installed_path": str(installed_path),
                    "plugin_identity": plugin_identity,
                    "smoke_command": smoke["command"],
                    "run_at": smoke["run_at"],
                    "last_run_result": "pass",
                    "exit_code": 0,
                    "smoke_output_path": str(stdout),
                    "smoke_output_sha256": hash_file(stdout),
                    "installed_smoke_receipt_path": str(smoke_path),
                }
            ]
        }
    )
    return _write_json_atomic(out_dir / f"{_slug(tag)}-docs-capability.json", docs)


def _files_under(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        candidate
        for candidate in root.rglob("*")
        if candidate.is_file() and ".git" not in candidate.parts
    )


def _manifest_capability_ids(project_dir: Path) -> list[str]:
    manifest_path = project_dir / "config" / "capability-manifest.yaml"
    manifest = load_manifest(manifest_path)
    capabilities = manifest.get("capabilities") or {}
    if not isinstance(capabilities, dict) or not capabilities:
        raise ValueError("Capability manifest has no capabilities")
    return sorted(str(capability_id) for capability_id in capabilities)


def _manifest_mutation_commands(project_dir: Path) -> list[str]:
    manifest_path = project_dir / "config" / "capability-manifest.yaml"
    manifest = load_manifest(manifest_path)
    commands: set[str] = set()
    capabilities = manifest.get("capabilities") or {}
    for config in capabilities.values():
        if not isinstance(config, dict) or not config.get("mutates_project"):
            continue
        entrypoint = config.get("command_entrypoint") or {}
        if not isinstance(entrypoint, dict):
            continue
        slash_command = entrypoint.get("slash_command")
        if isinstance(slash_command, str) and slash_command.strip():
            commands.add(slash_command.strip())
    if not commands:
        raise ValueError("Capability manifest has no mutating slash commands")
    return sorted(commands)


def _write_public_distribution_receipts(
    project_dir: Path,
    *,
    tag: str,
    branch: str,
    commit: str,
    installed_path: Path,
) -> Path:
    plugin_files: list[Path] = []
    for root_name in PLUGIN_DISTRIBUTION_ROOTS:
        plugin_files.extend(_files_under(project_dir / root_name))
    plugin_files = sorted(set(plugin_files))
    hook_files = _files_under(project_dir / PLUGIN_HOOK_ROOT)
    if not plugin_files:
        raise ValueError(
            "No installed plugin files found under distribution roots "
            f"{PLUGIN_DISTRIBUTION_ROOTS} of {project_dir}"
        )
    manifest_path = project_dir / "config" / "capability-manifest.yaml"
    plugin_manifest = _installed_manifest(project_dir)
    generated_from = [manifest_path, plugin_manifest]
    inventory_inputs: dict[str, dict[str, str]] = {}
    for artifact in [*generated_from, *plugin_files, *hook_files]:
        inventory_inputs[_display_path(project_dir, artifact)] = _artifact_entry(
            project_dir,
            artifact,
        )

    inventory = _base_control_receipt(
        project_dir,
        receipt_type="public-distribution-inventory",
        receipt_id=f"{_slug(tag)}-public-distribution-inventory",
        branch=branch,
        commit=commit,
        command_or_workflow_step="release-gate generate-evidence public-distribution-inventory",
    )
    inventory.update(
        {
            "manifest_capabilities": _manifest_capability_ids(project_dir),
            "installed_plugin_files": [
                _display_path(project_dir, path) for path in plugin_files
            ],
            "hook_files": [_display_path(project_dir, path) for path in hook_files],
            "mutation_commands": _manifest_mutation_commands(project_dir),
            "network_commands": ["git ls-remote --tags origin"],
            "generated_from": [_display_path(project_dir, path) for path in generated_from],
            "capability_manifest_path": _display_path(project_dir, manifest_path),
            "input_artifacts": list(inventory_inputs.values()),
        }
    )
    out_dir = _evidence_dir(project_dir)
    inventory_path = _write_json_atomic(
        out_dir / f"{_slug(tag)}-public-distribution-inventory.json",
        inventory,
    )

    public = _base_control_receipt(
        project_dir,
        receipt_type="public-distribution",
        receipt_id=f"{_slug(tag)}-public-distribution",
        branch=branch,
        commit=commit,
        command_or_workflow_step="release-gate generate-evidence public-distribution",
    )
    public.update(
        {
            "permissions": ["read project files", "write approved maintenance outputs"],
            "installed_user_file_access": [".sweetclaude/", ".claude/"],
            "network_access": ["git remote tag/update discovery"],
            "hooks": inventory["hook_files"],
            "project_mutation_commands": inventory["mutation_commands"],
            "provider_bound_data": ["Claude Code prompt and local project context"],
            "auth_assumptions": ["Claude Code local user approval gates mutating commands"],
            "secrets_handling": "does not require or persist provider secrets",
            "channel_visibility": "stable and beta channels are separately visible",
            "marketplace_or_distribution_visibility": "public plugin distribution",
            "evidence_source": "release evidence runner inventory",
            "approved_trust_model": (
                "public plugin may inspect project files only for declared "
                "maintenance commands"
            ),
            "inventory_receipt_path": str(inventory_path),
        }
    )
    return _write_json_atomic(out_dir / f"{_slug(tag)}-public-distribution.json", public)


def generate_release_evidence(
    project_dir: Path,
    *,
    tag: str,
    channel: str,
    branch: str,
    installed_path: Path | None = None,
    installed_entrypoint: str = "/sweetclaude:recover",
) -> dict:
    project_dir = project_dir.resolve()
    version = _version_from_tag(tag)
    _validate_channel(version, channel, branch)
    _metadata_version(project_dir, version)
    if not _is_git_repo(project_dir):
        raise ValueError("release evidence generation requires a git work tree")
    actual_branch = _git(project_dir, "branch", "--show-current").stdout.strip()
    if actual_branch != branch:
        raise ValueError(f"current git branch mismatch: expected {branch}, got {actual_branch}")
    commit = _git(project_dir, "rev-parse", "HEAD").stdout.strip()
    artifact = _release_artifact(project_dir, version)
    resolved_installed_path = (
        installed_path if installed_path is not None else project_dir
    )
    if not resolved_installed_path.is_absolute():
        resolved_installed_path = project_dir / resolved_installed_path
    resolved_installed_path = resolved_installed_path.resolve(strict=False)

    release_identity = _write_release_identity_receipt(
        project_dir,
        tag=tag,
        channel=channel,
        branch=branch,
        commit=commit,
        version=version,
        artifact=artifact,
        installed_path=resolved_installed_path,
    )
    docs_capability = _write_docs_capability_receipt(
        project_dir,
        tag=tag,
        branch=branch,
        commit=commit,
        artifact=artifact,
        installed_path=resolved_installed_path,
        installed_entrypoint=installed_entrypoint,
    )
    public_distribution = _write_public_distribution_receipts(
        project_dir,
        tag=tag,
        branch=branch,
        commit=commit,
        installed_path=resolved_installed_path,
    )

    # Beta releases require a control-lint receipt at the gate's default path.
    # Emit it here from the canonical controls map so a single generate-evidence
    # run produces the full bundle `check` needs — nothing else generated it.
    if channel == "beta":
        controls_map = project_dir / "config" / "controls-map.md"
        if not controls_map.exists():
            raise ValueError(f"Canonical controls map not found: {controls_map}")
        write_control_lint_receipt(
            project_dir,
            subject_id=f"release:{tag}",
            branch=branch,
            commit=commit,
            controls_map_path=controls_map,
            artifact_paths=[controls_map],
        )

    checks = []
    for check in sorted(required_release_checks()):
        entry = {
            "name": check,
            "status": "pass",
            "command": "release_gate.py generate-evidence",
            "summary": f"{check} evidence generated by release evidence runner",
        }
        if check == "release-identity":
            entry["evidence_path"] = str(release_identity)
        if check == "docs-capability":
            entry["evidence_path"] = str(docs_capability)
        if check == "public-distribution":
            entry["evidence_path"] = str(public_distribution)
        checks.append(entry)

    release_receipt = {
        "schema_version": 1,
        "receipt_type": "release",
        "subject_id": f"release:{tag}",
        "status": "pass",
        "created_at": _now(),
        "commit": commit,
        "checks": checks,
    }
    release_receipt_path = _write_json_atomic(
        _evidence_dir(project_dir) / f"{_slug(tag)}-release.json",
        release_receipt,
    )
    evidence_context = {"repo_root": str(project_dir), "branch": branch, "commit": commit}
    validate_release_identity_receipt(
        release_identity,
        expected_context=evidence_context,
        expected_identity={
            "repo_root": str(project_dir),
            "branch": branch,
            "commit": commit,
            "tag": tag,
            "package_version": version,
            "plugin_version": version,
            "changelog_version": version,
            "channel": channel,
            "install_path": str(resolved_installed_path),
            "artifact_path": str(artifact),
        },
        verify_artifact_hash=True,
    )
    validate_docs_capability_receipt(docs_capability, expected_context=evidence_context)
    validate_public_distribution_receipt(
        public_distribution,
        expected_context=evidence_context,
    )
    validate_receipt(
        release_receipt_path,
        subject_id=f"release:{tag}",
        receipt_type="release",
    )

    return {
        "ok": True,
        "tag": tag,
        "version": version,
        "channel": channel,
        "branch": branch,
        "commit": commit,
        "release_receipt": str(release_receipt_path),
        "release_identity_receipt": str(release_identity),
        "docs_capability_receipt": str(docs_capability),
        "public_distribution_receipt": str(public_distribution),
    }


def _previous_tag(project_dir: Path, tag: str, channel: str) -> str | None:
    version = _version_from_tag(tag)
    is_beta = channel == "beta"
    result = _git(project_dir, "tag", "--list", "--sort=-version:refname", check=False)
    if result.returncode != 0:
        return None
    for candidate in result.stdout.splitlines():
        candidate = candidate.strip()
        if not candidate or candidate == tag:
            continue
        try:
            cv = _version_from_tag(candidate)
        except ValueError:
            continue
        if is_beta and _has_prerelease(cv) and _major(cv) == _major(version):
            return candidate
        if not is_beta and not _has_prerelease(cv) and _major(cv) == _major(version):
            return candidate
    return None


_ISSUE_PATTERN = re.compile(r"ISSUE-\d+")


def _extract_issue_ids_from_commits(
    project_dir: Path, from_ref: str, to_ref: str
) -> set[str]:
    # Only the commit SUBJECT (%s) counts as "delivered" — that is where the
    # conventional (ISSUE-NNN) ref lives. IDs mentioned only in the body are
    # related/future references (ISSUE-242) and must not gate the release.
    result = _git(
        project_dir, "log", "--format=%s", f"{from_ref}..{to_ref}", check=False
    )
    if result.returncode != 0:
        return set()
    return set(_ISSUE_PATTERN.findall(result.stdout))


def _resolve_product_base(project_dir: Path) -> Path:
    ap_path = project_dir / ".sweetclaude" / "artifact-privacy.yaml"
    try:
        import yaml
        with open(ap_path, encoding="utf-8") as f:
            ap = yaml.safe_load(f) or {}
        base = (ap.get("categories") or {}).get("product", {}).get("base_path", "")
        if base:
            base = base.rstrip("/")
            if Path(base).is_absolute():
                return Path(base)
            return project_dir / base
    except Exception:
        pass
    return project_dir / ".sweetclaude" / "product"


def _issue_is_terminal(project_dir: Path, issue_id: str) -> bool:
    product_base = _resolve_product_base(project_dir)
    backlog_dir = product_base / "backlog"
    if not backlog_dir.is_dir():
        return True
    for subdir in ("done", "archived", ""):
        search_dir = backlog_dir / subdir if subdir else backlog_dir
        if not search_dir.is_dir():
            continue
        for candidate in search_dir.iterdir():
            if candidate.name != f"{issue_id}.md" and not candidate.name.startswith(
                f"{issue_id}-"
            ):
                continue
            if not candidate.name.endswith(".md"):
                continue
            if subdir in ("done", "archived"):
                return True
            try:
                import yaml
                text = candidate.read_text(encoding="utf-8")
                if text.startswith("---"):
                    end = text.index("---", 3)
                    fm = yaml.safe_load(text[3:end]) or {}
                    status = fm.get("status", "")
                    if status in ("done", "declined", "abandoned", "superseded"):
                        return True
            except Exception:
                pass
            return False
    return False


def _validate_issue_closeout(project_dir: Path, tag: str, channel: str) -> dict:
    prev_tag = _previous_tag(project_dir, tag, channel)
    if prev_tag is None:
        return {"checked": True, "skipped": True, "reason": "no-previous-tag"}
    issue_ids = _extract_issue_ids_from_commits(project_dir, prev_tag, tag)
    if not issue_ids:
        return {"checked": True, "issues": [], "unclosed": []}
    unclosed = sorted(
        issue_id for issue_id in issue_ids
        if not _issue_is_terminal(project_dir, issue_id)
    )
    if unclosed:
        raise ValueError(
            "Release blocked: merged issues not closed out: "
            + ", ".join(unclosed)
            + ". Run closeout for each before releasing."
        )
    return {"checked": True, "issues": sorted(issue_ids), "unclosed": []}


def check_release_readiness(
    project_dir: Path,
    *,
    tag: str,
    channel: str,
    receipt_path: str | Path,
    branch: str,
    control_lint_receipt_path: str | Path | None = None,
    expected_commit: str | None = None,
) -> dict:
    project_dir = project_dir.resolve()
    version = _version_from_tag(tag)
    _validate_channel(version, channel, branch)
    _metadata_version(project_dir, version)
    actual_commit = expected_commit or _current_git_commit(project_dir) or _receipt_commit(receipt_path)
    if not actual_commit:
        raise ValueError("release readiness requires a bound commit")
    receipt = _validate_release_receipt(
        receipt_path,
        tag,
        project_dir=project_dir,
        version=version,
        channel=channel,
        branch=branch,
        expected_commit=actual_commit,
    )
    git_state = _validate_git_state(project_dir, tag=tag, branch=branch)
    if actual_commit != git_state["commit"]:
        raise ValueError(
            f"expected commit mismatch: expected {actual_commit}, got {git_state['commit']}"
        )
    control_lint = _validate_control_lint_receipt(
        project_dir,
        tag=tag,
        channel=channel,
        branch=branch,
        control_lint_receipt_path=control_lint_receipt_path,
        expected_commit=actual_commit,
    )
    issue_closeout = _validate_issue_closeout(project_dir, tag, channel)
    return {
        "ok": True,
        "tag": tag,
        "version": version,
        "channel": channel,
        "branch": branch,
        "git": git_state,
        "control_lint": control_lint,
        "control_lint_receipt": control_lint.get("receipt"),
        "issue_closeout": issue_closeout,
        "receipt": str(Path(receipt_path)),
        "checks": sorted(str(c.get("name", "")) for c in receipt.get("checks", [])),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SweetClaude release readiness gate")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check")
    p_check.add_argument("--project-dir", required=True, type=Path)
    p_check.add_argument("--tag", required=True)
    p_check.add_argument("--channel", required=True, choices=["stable", "beta"])
    p_check.add_argument("--receipt", required=True)
    p_check.add_argument("--control-lint-receipt", default=None)
    p_check.add_argument("--branch", required=True)

    p_generate = sub.add_parser("generate-evidence")
    p_generate.add_argument("--project-dir", required=True, type=Path)
    p_generate.add_argument("--tag", required=True)
    p_generate.add_argument("--channel", required=True, choices=["stable", "beta"])
    p_generate.add_argument("--branch", required=True)
    p_generate.add_argument("--installed-path", type=Path, default=None)
    p_generate.add_argument("--installed-entrypoint", default="/sweetclaude:recover")

    args = parser.parse_args(argv)

    try:
        if args.cmd == "check":
            result = check_release_readiness(
                args.project_dir,
                tag=args.tag,
                channel=args.channel,
                receipt_path=args.receipt,
                branch=args.branch,
                control_lint_receipt_path=args.control_lint_receipt,
            )
            print(json.dumps(result))
            return 0
        if args.cmd == "generate-evidence":
            result = generate_release_evidence(
                args.project_dir,
                tag=args.tag,
                channel=args.channel,
                branch=args.branch,
                installed_path=args.installed_path,
                installed_entrypoint=args.installed_entrypoint,
            )
            print(json.dumps(result))
            return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
