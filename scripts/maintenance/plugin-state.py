#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Inspect and repair SweetClaude Claude Code plugin install metadata."""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

MAINTENANCE_DIR = Path(__file__).resolve().parent
if str(MAINTENANCE_DIR) not in sys.path:
    sys.path.insert(0, str(MAINTENANCE_DIR))

from capability_manifest import (
    channel_retired,
    expected_marketplace,
    expected_ref,
    minimum_safe_version,
    retirement_target_channel,
)

PRERELEASE_RE = re.compile(r"-([A-Za-z]+)")
VERSION_MAJOR_RE = re.compile(r"^v?(\d+)")


def _plugins_path(home: Path) -> Path:
    return home / ".claude" / "plugins" / "installed_plugins.json"


def _load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"version": 2, "plugins": {}}
    if not isinstance(data, dict):
        return {"version": 2, "plugins": {}}
    data.setdefault("version", 2)
    data.setdefault("plugins", {})
    if not isinstance(data["plugins"], dict):
        data["plugins"] = {}
    return data


def _atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=str(path.parent), suffix=".tmp", delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(data, tmp, indent=2)
            tmp.write("\n")
            tmp_name = tmp.name
        os.replace(tmp_name, path)
        tmp_name = None
    finally:
        if tmp_name:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


def _major(version: str) -> int | None:
    m = VERSION_MAJOR_RE.match(str(version or ""))
    return int(m.group(1)) if m else None


def _version_parts(version: str) -> tuple[int, int, int] | None:
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", str(version or ""))
    if not m:
        return None
    return tuple(int(part) for part in m.groups())


def _version_lt(left: str, right: str) -> bool:
    left_parts = _version_parts(left)
    right_parts = _version_parts(right)
    if left_parts is None or right_parts is None:
        return False
    return left_parts < right_parts


def _is_stale_beta(channel: str, version: str) -> bool:
    minimum = minimum_safe_version(channel)
    return bool(minimum) and _version_lt(version, minimum)


def _switch_commands(retired_channel: str, target_channel: str) -> list[str]:
    """One-time switch off a retired channel, ordered so the user is never
    double-installed (matches beta_stable_migration_notice in update.py)."""
    target_marketplace = expected_marketplace(target_channel)
    target_ref = expected_ref(target_channel)
    retired_marketplace = expected_marketplace(retired_channel)
    return [
        f"/plugin marketplace add carson-sweet/sweetclaude@{target_ref}",
        f"/plugin install sweetclaude@{target_marketplace}",
        f"/plugin marketplace remove {retired_marketplace}",
    ]


def _marketplace(plugin_key: str) -> str:
    return plugin_key.split("@", 1)[1] if "@" in plugin_key else plugin_key


def _channel(plugin_key: str, entry: dict[str, Any]) -> str:
    """Post-promotion model (decision log #35, ISSUE-241): marketplace name
    is authoritative; for the bare legacy marketplace, a prerelease version
    means beta, 4.x or later means stable, and 3.x means legacy."""
    market = _marketplace(plugin_key).lower()
    version = str(entry.get("version") or "")
    major = _major(version)
    if "beta" in market:
        return "beta"
    if "legacy" in market:
        return "legacy"
    if "stable" in market:
        return "stable"
    if PRERELEASE_RE.search(version):
        return "beta"
    if major is not None and major >= 4:
        return "stable"
    if major == 3:
        return "legacy"
    return "unknown"


def _entry_exists(entry: dict[str, Any]) -> bool:
    ip = entry.get("installPath")
    return bool(ip and Path(str(ip)).is_dir())


def _entry_matches_project(entry: dict[str, Any], project_dir: Path | None) -> bool:
    if entry.get("scope") != "local":
        return True
    if project_dir is None:
        return False
    project_path = entry.get("projectPath")
    if not project_path:
        return False
    try:
        return Path(str(project_path)).resolve() == project_dir.resolve()
    except OSError:
        return False


def _collect_entries(
    data: dict[str, Any], *, project_dir: Path | None, current_root: Path | None
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for plugin_key, versions in data.get("plugins", {}).items():
        if not isinstance(plugin_key, str) or "sweetclaude" not in plugin_key.lower():
            continue
        if not isinstance(versions, list):
            continue
        for index, entry in enumerate(versions):
            if not isinstance(entry, dict):
                continue
            if entry.get("scope") not in {"user", "local", "project", "managed"}:
                continue
            if not _entry_matches_project(entry, project_dir):
                continue
            row = dict(entry)
            row["plugin_key"] = plugin_key
            row["entry_index"] = index
            row["marketplace"] = _marketplace(plugin_key)
            row["channel"] = _channel(plugin_key, entry)
            row["legacy_marketplace"] = row["marketplace"] == "sweetclaude"
            row["install_exists"] = _entry_exists(entry)
            score = 0
            install_path = row.get("installPath")
            if current_root and install_path:
                try:
                    if Path(str(install_path)).resolve() == current_root.resolve():
                        score += 1000
                except OSError:
                    pass
            if entry.get("scope") == "user":
                score += 100
            if entry.get("scope") == "local":
                score += 50
            if row["install_exists"]:
                score += 10
            row["score"] = score
            rows.append(row)
    rows.sort(key=lambda r: (r.get("score", 0), str(r.get("lastUpdated", ""))), reverse=True)
    return rows


def inspect_state(home: Path, project_dir: Path | None, current_root: Path | None) -> dict[str, Any]:
    path = _plugins_path(home)
    data = _load(path)
    rows = _collect_entries(data, project_dir=project_dir, current_root=current_root)
    selected = rows[0] if rows else None
    if not selected:
        return {
            "ok": False,
            "installed_plugins_path": str(path),
            "reason": "no SweetClaude plugin install found",
            "entries": [],
        }
    channel = selected["channel"]
    channel_ref = expected_ref(channel) if channel != "unknown" else ""
    channel_marketplace = expected_marketplace(channel) if channel != "unknown" else ""
    version = str(selected.get("version", "") or "")
    stale_beta = _is_stale_beta(channel, version)
    retired = channel_retired(channel) if channel != "unknown" else False
    target = retirement_target_channel(channel) if retired else ""
    switch_commands = _switch_commands(channel, target) if retired else []
    plugin_key = selected["plugin_key"]
    return {
        "ok": True,
        "installed_plugins_path": str(path),
        "plugin_key": plugin_key,
        "marketplace": selected["marketplace"],
        "legacy_marketplace": bool(selected["legacy_marketplace"]),
        "channel": channel,
        "expected_ref": channel_ref,
        "expected_marketplace": channel_marketplace,
        "install_path": selected.get("installPath", ""),
        "version": version,
        "git_commit_sha": selected.get("gitCommitSha", ""),
        "scope": selected.get("scope", ""),
        "install_exists": bool(selected["install_exists"]),
        "project_path": selected.get("projectPath", ""),
        "stale_beta_install": stale_beta,
        "channel_retired": retired,
        "retirement_target_channel": target,
        "retirement_switch_commands": switch_commands,
        "minimum_safe_beta_version": minimum_safe_version("beta"),
        "plugin_update_command": f"/plugin update {plugin_key}" if plugin_key else "",
        "restart_required_after_plugin_update": stale_beta,
        "entries": rows,
    }


def repair_state(
    home: Path,
    *,
    plugin_key: str,
    install_path: str,
    version: str,
    sha: str,
    project_dir: Path | None,
) -> dict[str, Any]:
    path = _plugins_path(home)
    data = _load(path)
    plugins = data.setdefault("plugins", {})
    versions = plugins.get(plugin_key)
    if not isinstance(versions, list):
        raise ValueError(f"SweetClaude plugin key not found: {plugin_key}")

    target_index = None
    for index, entry in enumerate(versions):
        if not isinstance(entry, dict):
            continue
        if project_dir and entry.get("scope") == "local":
            if not _entry_matches_project(entry, project_dir):
                continue
        current_path = str(entry.get("installPath") or "")
        if current_path == install_path or target_index is None:
            target_index = index
            if current_path == install_path:
                break
    if target_index is None:
        raise ValueError(f"No repairable SweetClaude entry found for {plugin_key}")

    now = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    entry = versions[target_index]
    entry["installPath"] = install_path
    entry["version"] = version
    entry["gitCommitSha"] = sha
    entry["lastUpdated"] = now
    if project_dir and entry.get("scope") == "local":
        entry["projectPath"] = str(project_dir.resolve())
    _atomic_write(path, data)
    return {
        "ok": True,
        "plugin_key": plugin_key,
        "entry_index": target_index,
        "install_path": install_path,
        "version": version,
        "git_commit_sha": sha,
        "last_updated": now,
    }


def _shell_quote(value: Any) -> str:
    text = str(value if value is not None else "")
    return "'" + text.replace("'", "'\\''") + "'"


def _emit_shell(result: dict[str, Any]) -> None:
    mapping = {
        "SC_PLUGIN_OK": "ok",
        "SC_PLUGIN_KEY": "plugin_key",
        "SC_PLUGIN_MARKETPLACE": "marketplace",
        "SC_PLUGIN_LEGACY_MARKETPLACE": "legacy_marketplace",
        "SC_PLUGIN_CHANNEL": "channel",
        "SC_PLUGIN_EXPECTED_REF": "expected_ref",
        "SC_PLUGIN_EXPECTED_MARKETPLACE": "expected_marketplace",
        "SC_PLUGIN_INSTALL_PATH": "install_path",
        "SC_PLUGIN_VERSION": "version",
        "SC_PLUGIN_GIT_SHA": "git_commit_sha",
        "SC_PLUGIN_SCOPE": "scope",
        "SC_PLUGIN_INSTALL_EXISTS": "install_exists",
        "SC_PLUGIN_STALE_BETA": "stale_beta_install",
        "SC_PLUGIN_CHANNEL_RETIRED": "channel_retired",
        "SC_PLUGIN_RETIREMENT_TARGET_CHANNEL": "retirement_target_channel",
        "SC_PLUGIN_MIN_SAFE_BETA_VERSION": "minimum_safe_beta_version",
        "SC_PLUGIN_UPDATE_COMMAND": "plugin_update_command",
        "SC_PLUGIN_RESTART_REQUIRED_AFTER_UPDATE": "restart_required_after_plugin_update",
        "SC_PLUGIN_REASON": "reason",
    }
    for key, field in mapping.items():
        value = result.get(field, "")
        if isinstance(value, bool):
            value = "true" if value else "false"
        print(f"{key}={_shell_quote(value)}")


def _fail_closed_shell_state(
    home: Path,
    project_dir: Path | None,
    current_root: Path | None,
    error: str,
) -> dict[str, Any]:
    path = _plugins_path(home)
    data = _load(path)
    rows = _collect_entries(data, project_dir=project_dir, current_root=current_root)
    selected = rows[0] if rows else {}
    channel = selected.get("channel", "")
    plugin_key = selected.get("plugin_key", "")
    # If the manifest cannot be loaded, any beta install is treated as unsafe
    # and retired (fail closed on both guards).
    stale_beta = channel == "beta"
    return {
        "ok": False,
        "installed_plugins_path": str(path),
        "reason": f"plugin state inspection failed closed: {error}",
        "plugin_key": plugin_key,
        "marketplace": selected.get("marketplace", ""),
        "legacy_marketplace": bool(selected.get("legacy_marketplace", False)),
        "channel": channel,
        "expected_ref": "",
        "expected_marketplace": "",
        "install_path": selected.get("installPath", ""),
        "version": selected.get("version", ""),
        "git_commit_sha": selected.get("gitCommitSha", ""),
        "scope": selected.get("scope", ""),
        "install_exists": bool(selected.get("install_exists", False)),
        "project_path": selected.get("projectPath", ""),
        "stale_beta_install": stale_beta,
        "channel_retired": channel == "beta",
        "retirement_target_channel": "",
        "retirement_switch_commands": [],
        "minimum_safe_beta_version": "",
        "plugin_update_command": f"/plugin update {plugin_key}" if plugin_key else "",
        "restart_required_after_plugin_update": stale_beta,
        "entries": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect or repair SweetClaude plugin metadata")
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--project-dir", type=Path, default=None)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_inspect = sub.add_parser("inspect")
    p_inspect.add_argument("--current-root", type=Path, default=None)
    p_inspect.add_argument("--shell", action="store_true")

    p_repair = sub.add_parser("repair")
    p_repair.add_argument("--plugin-key", required=True)
    p_repair.add_argument("--install-path", required=True)
    p_repair.add_argument("--version", required=True)
    p_repair.add_argument("--sha", required=True)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "inspect":
            result = inspect_state(args.home, args.project_dir, args.current_root)
            if args.shell:
                _emit_shell(result)
            else:
                print(json.dumps(result, indent=2))
            return 0 if result.get("ok") else 1
        if args.cmd == "repair":
            result = repair_state(
                args.home,
                plugin_key=args.plugin_key,
                install_path=args.install_path,
                version=args.version,
                sha=args.sha,
                project_dir=args.project_dir,
            )
            print(json.dumps(result, indent=2))
            return 0
    except Exception as exc:
        if args.cmd == "inspect" and getattr(args, "shell", False):
            _emit_shell(_fail_closed_shell_state(
                args.home,
                args.project_dir,
                getattr(args, "current_root", None),
                str(exc),
            ))
            return 1
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
