#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Reconciles SweetClaude required global hooks in ~/.claude/settings.json.
#
# Strips SweetClaude-owned entries that are broken (${CLAUDE_PLUGIN_ROOT}
# literals) or stale (older plugin version paths), then registers the
# required globals with absolute paths from the current install. Scoped
# strictly to SweetClaude-owned commands so it never touches other plugins'
# entries or user-authored hooks.
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
        d = json.load(open(os.path.join(CLAUDE_DIR, "plugins", "installed_plugins.json")))
        entries = [
            e
            for versions in d.get("plugins", {}).values()
            for e in versions
            if e.get("scope") == "user"
        ]
        entries.sort(key=lambda e: e.get("lastUpdated", ""), reverse=True)
        for e in entries:
            ip = e.get("installPath", "")
            if ip and os.path.isdir(ip) and "sweetclaude" in ip.lower():
                return ip
    except Exception:
        pass
    return ""


def load_manifest(plugin_root):
    candidates = []
    if plugin_root:
        candidates.append(os.path.join(plugin_root, "hooks", "hooks-manifest.json"))
    candidates.append(os.path.join(CLAUDE_DIR, "hooks", "sweetclaude", "hooks-manifest.json"))
    for path in candidates:
        try:
            return json.load(open(path))
        except Exception:
            continue
    return None


def is_sweetclaude_command(cmd, basenames):
    if not cmd:
        return False
    base = os.path.basename(cmd)
    if base not in basenames:
        return False
    cmd_lower = cmd.lower()
    return "${claude_plugin_root}" in cmd_lower or "sweetclaude" in cmd_lower


def main():
    plugin_root = find_plugin_root()
    manifest = load_manifest(plugin_root)

    if not manifest:
        if plugin_root or os.path.exists(os.path.join(CLAUDE_DIR, "hooks", "sweetclaude")):
            print("warning: no SweetClaude manifest found; nothing to do", file=sys.stderr)
        sys.exit(0)

    basenames = {h["file"] for h in manifest.get("hooks", []) if h.get("file")}
    if not basenames:
        print("warning: manifest has no hook entries; nothing to do", file=sys.stderr)
        sys.exit(0)

    settings_path = os.path.realpath(os.path.expanduser("~/.claude/settings.json"))

    try:
        settings = json.load(open(settings_path))
    except FileNotFoundError:
        settings = {}
    except Exception as e:
        print(f"error: could not parse {settings_path}: {e}", file=sys.stderr)
        sys.exit(1)

    hooks_section = settings.setdefault("hooks", {})

    should_have = set()
    required_globals = []
    if plugin_root:
        for h in manifest.get("hooks", []):
            if not h.get("required") or h.get("scope") != "global":
                continue
            event = h.get("event")
            cmd_path = h.get("command_path", "")
            if not event or not cmd_path:
                continue
            resolved = cmd_path.replace("${CLAUDE_PLUGIN_ROOT}", plugin_root)
            should_have.add(resolved)
            required_globals.append((event, h.get("matcher", ""), resolved))

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
                if not is_sweetclaude_command(cmd, basenames):
                    new_hooks.append(h)
                    continue
                if cmd in should_have:
                    new_hooks.append(h)
                    continue
                stripped.append(cmd)
            if new_hooks:
                entry["hooks"] = new_hooks
                new_entries.append(entry)
        hooks_section[event] = new_entries

    present = set()
    for event_hooks in hooks_section.values():
        for entry in event_hooks:
            for h in entry.get("hooks", []):
                cmd = h.get("command", "")
                if cmd:
                    present.add(cmd)

    added = []
    for event, matcher, resolved in required_globals:
        if resolved in present:
            continue
        entry = {"hooks": [{"type": "command", "command": resolved}]}
        if matcher and matcher != ".*":
            entry["matcher"] = matcher
        hooks_section.setdefault(event, []).append(entry)
        added.append(resolved)

    if not plugin_root:
        print(
            "warning: plugin install path not found; cleanup ran but no hooks were re-registered",
            file=sys.stderr,
        )

    if stripped or added:
        settings_dir = os.path.dirname(settings_path)
        with tempfile.NamedTemporaryFile(
            "w", dir=settings_dir, suffix=".tmp", delete=False
        ) as tmp:
            json.dump(settings, tmp, indent=2)
            tmp_name = tmp.name
        try:
            os.replace(tmp_name, settings_path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except Exception:
                pass
            raise

    if stripped:
        print(f"cleaned: removed {len(stripped)} broken or stale SweetClaude hook entries")
        for s in stripped:
            print(f"  - {s}")
    for a in added:
        print(f"registered: {a}")
    if not stripped and not added:
        print("ok: hooks already up to date")


if __name__ == "__main__":
    main()
