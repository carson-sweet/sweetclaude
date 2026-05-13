#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Registers required global hooks from hooks-manifest.json that are missing
# from ~/.claude/settings.json.  Called by sweetclaude:update Step 4b.
import json, os, tempfile, sys

CLAUDE_DIR = os.path.expanduser("~/.claude")


def find_plugin_root():
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if env_root and os.path.isdir(env_root):
        return env_root
    try:
        d = json.load(open(os.path.join(CLAUDE_DIR, "plugins", "installed_plugins.json")))
        entries = [e for versions in d.get("plugins", {}).values()
                   for e in versions if e.get("scope") == "user"]
        entries.sort(key=lambda e: e.get("lastUpdated", ""), reverse=True)
        for e in entries:
            ip = e.get("installPath", "")
            if ip and os.path.isdir(ip):
                return ip
    except Exception:
        pass
    return ""


def main():
    plugin_root = find_plugin_root()
    if not plugin_root:
        sys.exit(0)

    manifest_path = os.path.join(plugin_root, "hooks", "hooks-manifest.json")
    settings_path = os.path.join(CLAUDE_DIR, "settings.json")

    try:
        manifest = json.load(open(manifest_path))
    except Exception:
        sys.exit(0)

    try:
        settings = json.load(open(settings_path))
    except Exception:
        settings = {}

    # Remove any entries with literal ${CLAUDE_PLUGIN_ROOT} — these error at runtime
    # because settings.json hooks don't get plugin environment variables.
    hooks_section = settings.setdefault("hooks", {})
    cleaned = False
    for event in list(hooks_section.keys()):
        new_entries = []
        for entry in hooks_section[event]:
            new_hooks = [h for h in entry.get("hooks", [])
                         if "${CLAUDE_PLUGIN_ROOT}" not in h.get("command", "")]
            if len(new_hooks) != len(entry.get("hooks", [])):
                cleaned = True
            if new_hooks:
                entry["hooks"] = new_hooks
                new_entries.append(entry)
        hooks_section[event] = new_entries

    all_cmd_list = [
        h.get("command", "")
        for event_hooks in hooks_section.values()
        for entry in event_hooks
        for h in entry.get("hooks", [])
    ]

    added = []
    for h in manifest.get("hooks", []):
        if not h.get("required") or h.get("scope") != "global":
            continue
        event = h.get("event")
        cmd_path = h.get("command_path", "")
        if not event or not cmd_path:
            continue
        resolved = cmd_path.replace("${CLAUDE_PLUGIN_ROOT}", plugin_root)
        if any(resolved in cmd for cmd in all_cmd_list):
            continue
        entry = {"hooks": [{"type": "command", "command": resolved}]}
        matcher = h.get("matcher", "")
        if matcher and matcher != ".*":
            entry["matcher"] = matcher
        hooks_section.setdefault(event, []).append(entry)
        added.append(resolved)

    if added or cleaned:
        with tempfile.NamedTemporaryFile("w", dir=os.path.dirname(settings_path),
                                         suffix=".tmp", delete=False) as tmp:
            json.dump(settings, tmp, indent=2)
            tmp_name = tmp.name
        os.replace(tmp_name, settings_path)
        for a in added:
            print(f"registered: {a}")
        if cleaned:
            print("cleaned: removed unresolved ${CLAUDE_PLUGIN_ROOT} entries from settings.json")


if __name__ == "__main__":
    main()
