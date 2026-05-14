#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Reconciles SweetClaude hook entries in ~/.claude/settings.json.
#
# After v3.68.2: SweetClaude's three preflight hooks (session-preflight,
# drift-gate, master-preflight) are plugin-native — declared in hooks/hooks.json
# and auto-loaded by Claude Code's plugin system. They no longer belong in
# ~/.claude/settings.json. This script's job is to keep settings.json clean of:
#   - broken ${CLAUDE_PLUGIN_ROOT} literals (do not resolve in global settings)
#   - stale plugin-version paths (point to plugin caches that no longer exist)
# It also registers any future scope=global hooks if any are declared (currently
# none — see hooks-manifest.json).
#
# Called by sweetclaude:update Step 4b and sweetclaude:fix-sweetclaude Step 7a.
import json
import os
import sys
import tempfile

CLAUDE_DIR = os.path.expanduser("~/.claude")


def find_plugin_root():
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if env_root and os.path.isdir(env_root):
        return env_root
    try:
        with open(os.path.join(CLAUDE_DIR, "plugins", "installed_plugins.json")) as f:
            d = json.load(f)
    except (FileNotFoundError, PermissionError, json.JSONDecodeError):
        return ""
    entries = []
    for plugin_key, versions in d.get("plugins", {}).items():
        if not isinstance(plugin_key, str) or "sweetclaude" not in plugin_key.lower():
            continue
        if not isinstance(versions, list):
            continue
        for v in versions:
            if isinstance(v, dict) and v.get("scope") == "user":
                entries.append(v)
    entries.sort(key=lambda e: e.get("lastUpdated", ""), reverse=True)
    for e in entries:
        ip = e.get("installPath", "")
        if ip and os.path.isdir(ip):
            return ip
    return ""


def load_manifest(plugin_root):
    candidates = []
    if plugin_root:
        candidates.append(os.path.join(plugin_root, "hooks", "hooks-manifest.json"))
    candidates.append(os.path.join(CLAUDE_DIR, "hooks", "sweetclaude", "hooks-manifest.json"))
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            with open(path) as f:
                return json.load(f)
        except (PermissionError, json.JSONDecodeError) as e:
            print(f"error: cannot read manifest at {path}: {e}", file=sys.stderr)
            return None
    return None


def is_sweetclaude_command(cmd, basenames):
    if not cmd:
        return False
    base = os.path.basename(cmd)
    if base not in basenames:
        return False
    cmd_lower = cmd.lower()
    return "${claude_plugin_root}" in cmd_lower or "sweetclaude" in cmd_lower


def strip_reason(cmd, basenames, plugin_native_basenames, plugin_installed):
    """Return one of: 'broken', 'plugin-native', 'stale', or None to keep."""
    if not is_sweetclaude_command(cmd, basenames):
        return None
    if "${claude_plugin_root}" in cmd.lower():
        return "broken"
    base = os.path.basename(cmd)
    if base in plugin_native_basenames and plugin_installed:
        return "plugin-native"
    if not os.path.exists(cmd):
        return "stale"
    return None


def atomic_write_json(path, data):
    settings_dir = os.path.dirname(path)
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=settings_dir, suffix=".tmp", delete=False
        ) as tmp:
            tmp_name = tmp.name
            json.dump(data, tmp, indent=2)
        os.replace(tmp_name, path)
    except Exception:
        if tmp_name and os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
        raise


def main():
    plugin_root = find_plugin_root()
    manifest = load_manifest(plugin_root)

    if manifest is None:
        if plugin_root or os.path.exists(os.path.join(CLAUDE_DIR, "hooks", "sweetclaude")):
            print(
                "error: SweetClaude manifest not found or unreadable; aborting",
                file=sys.stderr,
            )
            sys.exit(1)
        sys.exit(0)

    basenames = {h["file"] for h in manifest.get("hooks", []) if h.get("file")}
    plugin_native_basenames = {
        h["file"]
        for h in manifest.get("hooks", [])
        if h.get("file") and h.get("scope") == "plugin-native"
    }
    plugin_installed = bool(plugin_root)
    if not basenames:
        print("warning: manifest has no hook entries; nothing to do", file=sys.stderr)
        sys.exit(0)

    settings_path = os.path.realpath(os.path.expanduser("~/.claude/settings.json"))

    try:
        with open(settings_path) as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {}
    except (PermissionError, json.JSONDecodeError) as e:
        print(f"error: cannot read {settings_path}: {e}", file=sys.stderr)
        sys.exit(1)

    hooks_section = settings.setdefault("hooks", {})

    stripped = []
    for event in list(hooks_section.keys()):
        new_entries = []
        for entry in hooks_section[event]:
            if not entry.get("hooks"):
                new_entries.append(entry)
                continue
            new_hooks = []
            for h in entry["hooks"]:
                cmd = h.get("command", "")
                reason = strip_reason(cmd, basenames, plugin_native_basenames, plugin_installed)
                if reason:
                    stripped.append((reason, cmd))
                else:
                    new_hooks.append(h)
            if new_hooks:
                entry["hooks"] = new_hooks
                new_entries.append(entry)
        hooks_section[event] = new_entries

    # Drop event keys that ended up with no entries.
    for event in list(hooks_section.keys()):
        if not hooks_section[event]:
            del hooks_section[event]

    present = set()
    for event_hooks in hooks_section.values():
        for entry in event_hooks:
            for h in entry.get("hooks", []):
                cmd = h.get("command", "")
                if cmd:
                    present.add(cmd)

    added = []
    if plugin_root:
        for h in manifest.get("hooks", []):
            if not h.get("required") or h.get("scope") != "global":
                continue
            event = h.get("event")
            cmd_path = h.get("command_path", "")
            if not event or not cmd_path:
                continue
            resolved = cmd_path.replace("${CLAUDE_PLUGIN_ROOT}", plugin_root)
            if resolved in present:
                continue
            entry = {"hooks": [{"type": "command", "command": resolved}]}
            matcher = h.get("matcher", "")
            if matcher and matcher != ".*":
                entry["matcher"] = matcher
            hooks_section.setdefault(event, []).append(entry)
            added.append(resolved)

    if stripped or added:
        try:
            atomic_write_json(settings_path, settings)
        except Exception as e:
            print(f"error: failed to write {settings_path}: {e}", file=sys.stderr)
            sys.exit(1)

    if stripped:
        buckets = {
            "broken": ("broken ${CLAUDE_PLUGIN_ROOT} entries (do not resolve in settings.json)", []),
            "plugin-native": ("duplicate entries for plugin-native hooks (already registered via hooks.json)", []),
            "stale": ("stale entries (file no longer exists on disk)", []),
        }
        for reason, cmd in stripped:
            buckets[reason][1].append(cmd)
        for label, items in buckets.values():
            if not items:
                continue
            print(f"cleaned: removed {len(items)} {label}")
            for cmd in items:
                print(f"  - {cmd}")
    for a in added:
        print(f"registered: {a}")
    if not stripped and not added:
        print("ok: hooks already up to date")


if __name__ == "__main__":
    main()
