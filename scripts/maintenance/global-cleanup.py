#!/usr/bin/env python3
"""Preview and explicitly remove legacy SweetClaude global hooks and rules."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path


def claude_dir(home: Path) -> Path:
    config = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(config).expanduser() if config else home / ".claude"


def plan(home: Path) -> tuple[dict, dict | None]:
    claude = claude_dir(home)
    settings = claude / "settings.json"
    rules = claude / "rules" / "sweetclaude"
    if claude.is_symlink() or settings.is_symlink() or rules.parent.is_symlink() or rules.is_symlink():
        raise ValueError("Refusing symlinked global settings or rules")
    if settings.exists():
        raw = settings.read_bytes()
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("Global settings must be a JSON object")
    else:
        raw, data = b"", None
    updated = copy.deepcopy(data)
    removed = []
    removed_entries = []
    manifest = json.loads((Path(__file__).resolve().parents[2] / "hooks/hooks-manifest.json").read_text())
    native = {h["file"] for h in manifest.get("hooks", []) if h.get("scope") == "plugin-native" and h.get("file")}
    if updated is not None:
        hooks = updated.get("hooks", {})
        if not isinstance(hooks, dict):
            raise ValueError("Global hooks must be an object")
        for event, entries in list(hooks.items()):
            if not isinstance(entries, list):
                raise ValueError(f"Global hook entries for {event} must be a list")
            kept_entries = []
            for entry in entries:
                if not isinstance(entry, dict) or not isinstance(entry.get("hooks", []), list):
                    raise ValueError(f"Invalid global hook entry for {event}")
                before = len(entry.get("hooks", []))
                for hook in list(entry.get("hooks", [])):
                    if not isinstance(hook, dict):
                        raise ValueError("Global hook must be an object")
                    command = hook.get("command", "")
                    if not isinstance(command, str):
                        raise ValueError("Global hook command must be a string")
                    plugin_path = command.startswith("${CLAUDE_PLUGIN_ROOT}/hooks/")
                    legacy_path = command.startswith(str(claude / "hooks/sweetclaude") + "/")
                    if (plugin_path or legacy_path) and Path(command).name in native:
                        removed.append(command)
                        removed_entries.append({"event": event, "matcher": entry.get("matcher"), "hook": copy.deepcopy(hook)})
                        entry["hooks"].remove(hook)
                if entry.get("hooks") or before == 0:
                    kept_entries.append(entry)
            if kept_entries or not entries:
                hooks[event] = kept_entries
            else:
                del hooks[event]
    files = []
    fingerprints = []
    if rules.exists():
        if not rules.is_dir():
            raise ValueError("Legacy rules path is not a directory")
        for path in sorted(rules.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Refusing symlink in legacy rules: {path}")
            if path.is_file():
                files.append(str(path))
                fingerprints.append([str(path.relative_to(rules)), hashlib.sha256(path.read_bytes()).hexdigest()])
    state = {"settings_sha256": hashlib.sha256(raw).hexdigest(), "settings_exists": settings.exists(),
             "rules_exists": rules.exists(), "rules": fingerprints, "hooks": removed}
    digest = hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
    return {"plan_hash": digest, "settings": str(settings), "remove_hooks": removed, "remove_hook_entries": removed_entries,
            "remove_rules_directory": str(rules) if rules.exists() else None, "remove_files": files}, updated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preview", "apply"))
    parser.add_argument("--plan-hash")
    args = parser.parse_args()
    home = Path.home()
    try:
        preview, updated = plan(home)
        if args.action == "preview":
            print(json.dumps(preview, indent=2))
            return 0
        if not args.plan_hash or args.plan_hash != preview["plan_hash"]:
            raise ValueError("Configuration changed or approval hash missing; preview again")
        claude = claude_dir(home)
        settings = claude / "settings.json"
        rules = claude / "rules/sweetclaude"
        if not preview["remove_hooks"] and not rules.exists():
            print(json.dumps({"status": "unchanged"}))
            return 0
        backup_root = claude / ".sweetclaude-legacy-backup"
        if backup_root.is_symlink():
            raise ValueError("Refusing symlinked backup directory")
        backup = backup_root / ("explicit-cleanup-" + uuid.uuid4().hex)
        backup.mkdir(parents=True)
        if settings.exists():
            shutil.copy2(settings, backup / "settings.json")
        if rules.exists():
            (backup / "rules").mkdir()
            shutil.copytree(rules, backup / "rules/sweetclaude")
        try:
            if preview["remove_hooks"]:
                with tempfile.NamedTemporaryFile("w", dir=claude, delete=False, encoding="utf-8") as f:
                    json.dump(updated, f, indent=2)
                    f.write("\n")
                    temp = f.name
                os.replace(temp, settings)
            if rules.exists():
                shutil.rmtree(rules)
        except Exception:
            if (backup / "settings.json").exists():
                shutil.copy2(backup / "settings.json", settings)
            if (backup / "rules/sweetclaude").exists():
                shutil.copytree(backup / "rules/sweetclaude", rules, dirs_exist_ok=True)
            raise
        print(json.dumps({"status": "cleaned", "backup": str(backup), **preview}, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
