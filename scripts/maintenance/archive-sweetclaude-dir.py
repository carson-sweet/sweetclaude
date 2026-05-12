#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Mirrors artifact base_paths outside .sweetclaude/ into a legacy archive tree.
# Called by bootstrap and update re-onboarding flows after .sweetclaude/ has been
# moved aside. Usage: archive-sweetclaude-dir.py <legacy_dir>
import os, sys, shutil, yaml


def main():
    if len(sys.argv) < 2:
        print("Usage: archive-sweetclaude-dir.py <legacy_dir>", file=sys.stderr)
        sys.exit(1)
    legacy = sys.argv[1]
    privacy = os.path.join(legacy, "artifact-privacy.yaml")
    if not os.path.exists(privacy):
        return
    try:
        d = yaml.safe_load(open(privacy)) or {}
    except Exception:
        return
    for cat, entry in (d.get("categories") or {}).items():
        if not isinstance(entry, dict):
            continue
        base = entry.get("base_path", "")
        if not base or base.startswith(".sweetclaude"):
            continue
        if os.path.exists(base):
            target = os.path.join(legacy, base)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.move(base, target)


if __name__ == "__main__":
    main()
