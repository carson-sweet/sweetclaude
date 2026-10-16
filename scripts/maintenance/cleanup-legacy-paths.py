#!/usr/bin/env python3
"""
Detect, back up, and remove legacy versionless SweetClaude directories.

Legacy directories (pre-plugin-only era):
  ~/.claude/skills/sweetclaude/
  ~/.claude/hooks/sweetclaude/
  ~/.claude/scripts/sweetclaude/
  ~/.claude/config/sweetclaude/
  ~/.claude/rules/sweetclaude/

Also detects stale plugin cache version directories that don't match
the currently installed version.

Usage:
  python3 cleanup-legacy-paths.py detect              # list what would be cleaned
  python3 cleanup-legacy-paths.py clean [--no-backup] [--only PATH]
                                                     # back up and remove
"""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

LEGACY_DIRS = [
    "skills/sweetclaude",
    "hooks/sweetclaude",
    "scripts/sweetclaude",
    "config/sweetclaude",
    "rules/sweetclaude",
]

BACKUP_ROOT = Path.home() / ".claude" / ".sweetclaude-legacy-backup"


def get_installed_version() -> tuple[str, str]:
    plugins_path = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    if not plugins_path.exists():
        return "", ""
    try:
        data = json.loads(plugins_path.read_text())
        for versions in data.get("plugins", {}).values():
            for entry in versions:
                if entry.get("scope") != "user":
                    continue
                ip = entry.get("installPath", "")
                if "sweetclaude" in ip.lower():
                    return entry.get("version", ""), ip
    except Exception:
        pass
    return "", ""


def find_legacy_dirs(only: str | None = None) -> list[Path]:
    if only is not None and only not in LEGACY_DIRS:
        raise ValueError(f"unsupported legacy path: {only}")
    home_claude = Path.home() / ".claude"
    found = []
    for rel in ([only] if only else LEGACY_DIRS):
        d = home_claude / rel
        if d.is_dir():
            found.append(d)
    return found


def find_stale_cache_dirs(current_version: str, current_install_path: str) -> list[Path]:
    if not current_install_path:
        return []
    cache_parent = Path(current_install_path).parent
    if not cache_parent.is_dir():
        return []
    stale = []
    current_dir = Path(current_install_path).name
    for child in cache_parent.iterdir():
        if child.is_dir() and child.name != current_dir and child.name != current_version:
            stale.append(child)
    return stale


def detect(args: argparse.Namespace) -> int:
    legacy = find_legacy_dirs(getattr(args, "only", None))
    version, install_path = get_installed_version()
    stale = [] if getattr(args, "only", None) else find_stale_cache_dirs(version, install_path)

    output = {"legacy_dirs": [], "stale_cache_dirs": [], "installed_version": version}

    for d in legacy:
        size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        output["legacy_dirs"].append({"path": str(d), "size_bytes": size})

    for d in stale:
        size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        output["stale_cache_dirs"].append({"path": str(d), "size_bytes": size})

    json.dump(output, sys.stdout, indent=2)
    print()
    return 0


def clean(args: argparse.Namespace) -> int:
    legacy = find_legacy_dirs(args.only)
    version, install_path = get_installed_version()
    stale = [] if args.only else find_stale_cache_dirs(version, install_path)

    if not legacy and not stale:
        print(json.dumps({"status": "clean", "removed": []}))
        return 0

    removed = []
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    if not args.no_backup and (legacy or stale):
        backup_dir = BACKUP_ROOT / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)

        for d in legacy:
            dest = backup_dir / "legacy" / d.parent.name / d.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(d, dest)

        for d in stale:
            dest = backup_dir / "cache" / d.name
            shutil.copytree(d, dest)

        backup_path = str(backup_dir)
    else:
        backup_path = None

    for d in legacy:
        shutil.rmtree(d)
        removed.append(str(d))

    for d in stale:
        shutil.rmtree(d)
        removed.append(str(d))

    result = {"status": "cleaned", "removed": removed}
    if backup_path:
        result["backup"] = backup_path
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean up legacy SweetClaude paths")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("detect", help="List legacy dirs and stale cache entries")

    clean_p = sub.add_parser("clean", help="Back up and remove legacy dirs")
    clean_p.add_argument("--no-backup", action="store_true", help="Skip backup")
    clean_p.add_argument("--only", choices=LEGACY_DIRS,
                        help="Clean exactly one legacy directory")

    args = parser.parse_args()
    if args.command == "detect":
        return detect(args)
    elif args.command == "clean":
        return clean(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
