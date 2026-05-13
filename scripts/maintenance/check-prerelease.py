#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Check whether a SweetClaude prerelease tag is available and the user has not
already declined it. Called by sweetclaude:update Step 2c.

Emits JSON on stdout describing the decision the skill should make:

  {
    "prerelease_available": "v4.0.0-beta" | null,
    "installed_version": "3.68.4",
    "declined": "v4.0.0-beta" | null,
    "should_prompt": true | false,
    "reason": "..."
  }

CLI:
  check-prerelease.py --installed-version X.Y.Z [--declined TAG]
                      [--tags-file FILE | --repo-dir DIR]

  --tags-file is for tests (one tag per line). When omitted and --repo-dir is
  provided, runs `git ls-remote --tags <repo>` from that working tree.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys


PRERELEASE_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)-(beta|rc|alpha)([0-9.\-]*)$")
STABLE_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def _stable_tuple(version: str) -> tuple[int, int, int] | None:
    m = STABLE_RE.match(version)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _prerelease_tuple(tag: str) -> tuple[int, int, int, str, str] | None:
    """Return (major, minor, patch, channel, suffix) or None if not a prerelease."""
    m = PRERELEASE_RE.match(tag)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4), m.group(5)


def _is_newer_prerelease_than_installed(tag: str, installed: str) -> bool:
    """A prerelease X.Y.Z-channel is newer than installed if its X.Y.Z > installed
    OR if installed is itself a prerelease of the same X.Y.Z with a lower suffix."""
    pre = _prerelease_tuple(tag)
    if pre is None:
        return False
    pre_xyz = pre[:3]
    pre_channel = pre[3]
    pre_suffix = pre[4]

    # If installed is a stable version, prerelease is "newer" if its X.Y.Z is strictly greater
    stable = _stable_tuple(installed)
    if stable is not None:
        return pre_xyz > stable

    # If installed is a prerelease, compare against it
    installed_pre = _prerelease_tuple(installed if installed.startswith("v") else f"v{installed}")
    if installed_pre is None:
        # Unknown installed format — assume new prerelease is offerable
        return True
    inst_xyz = installed_pre[:3]
    inst_channel = installed_pre[3]
    inst_suffix = installed_pre[4]

    if pre_xyz != inst_xyz:
        return pre_xyz > inst_xyz
    # Same X.Y.Z. Channel ordering: alpha < beta < rc.
    channel_order = {"alpha": 0, "beta": 1, "rc": 2}
    if channel_order.get(pre_channel, 0) != channel_order.get(inst_channel, 0):
        return channel_order.get(pre_channel, 0) > channel_order.get(inst_channel, 0)
    # Same channel — compare suffix (lexically, since the formats vary)
    return pre_suffix > inst_suffix


def _latest_prerelease(tags: list[str], installed: str) -> str | None:
    candidates = [t for t in tags if _prerelease_tuple(t) is not None]
    candidates = [t for t in candidates if _is_newer_prerelease_than_installed(t, installed)]
    if not candidates:
        return None
    candidates.sort(key=lambda t: _prerelease_tuple(t) or (0, 0, 0, "", ""))
    return candidates[-1]


def check_prerelease(installed: str, declined: str, tags: list[str]) -> dict:
    """Pure function. No I/O. Returns the decision dict."""
    if not installed:
        return {
            "prerelease_available": None,
            "installed_version": installed,
            "declined": declined or None,
            "should_prompt": False,
            "reason": "installed version unknown",
        }
    latest = _latest_prerelease(tags, installed)
    if latest is None:
        return {
            "prerelease_available": None,
            "installed_version": installed,
            "declined": declined or None,
            "should_prompt": False,
            "reason": "no prerelease tags newer than installed",
        }
    if declined and declined == latest:
        return {
            "prerelease_available": latest,
            "installed_version": installed,
            "declined": declined,
            "should_prompt": False,
            "reason": f"user declined {declined}; no newer prerelease available",
        }
    return {
        "prerelease_available": latest,
        "installed_version": installed,
        "declined": declined or None,
        "should_prompt": True,
        "reason": f"prerelease {latest} available; not yet declined",
    }


def _read_tags_from_remote(repo_dir: pathlib.Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_dir), "ls-remote", "--tags", "origin"],
            capture_output=True, text=True, timeout=15, check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    tags = []
    for line in result.stdout.splitlines():
        parts = line.split("refs/tags/")
        if len(parts) != 2:
            continue
        tag = parts[1].strip().split("^{}")[0]  # strip annotated-tag suffix
        if tag:
            tags.append(tag)
    return list(dict.fromkeys(tags))  # dedupe, preserve order


def _read_tags_from_file(path: pathlib.Path) -> list[str]:
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check for SweetClaude prerelease availability")
    parser.add_argument("--installed-version", required=True)
    parser.add_argument("--declined", default="")
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--tags-file", type=pathlib.Path)
    src.add_argument("--repo-dir", type=pathlib.Path)

    args = parser.parse_args(argv)

    if args.tags_file:
        tags = _read_tags_from_file(args.tags_file)
    elif args.repo_dir:
        tags = _read_tags_from_remote(args.repo_dir)
    else:
        tags = []

    result = check_prerelease(args.installed_version, args.declined, tags)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
