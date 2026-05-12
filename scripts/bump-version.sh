#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# bump-version.sh — explicit operator-driven version bump for SweetClaude.
#
# Replaces the deleted auto-bump hook (hooks/version-bump.sh). That hook
# fired on every conventional-commit `feat:` / `fix:` / `perf:` and pushed
# the version forward aggressively. This script bumps versions ONLY when
# you explicitly invoke it at release time.
#
# Usage:
#   scripts/bump-version.sh patch              # 3.65.0 → 3.65.1
#   scripts/bump-version.sh minor              # 3.65.0 → 3.66.0
#   scripts/bump-version.sh major              # 3.65.0 → 4.0.0
#   scripts/bump-version.sh 3.66.0             # explicit version
#
# What it does:
#   - Reads the current version from package.json.
#   - Computes the new version (patch / minor / major bump, or accepts
#     an explicit version argument).
#   - Writes the new version into:
#       package.json
#       .claude-plugin/plugin.json (if present)
#       any additional files listed in scripts/version-files.txt (if present)
#   - Stages those files and creates a single
#     `chore(release): vX.Y.Z` commit.
#   - Tags the commit `vX.Y.Z`.
#   - Does NOT push. Operator runs `git push origin main && git push origin vX.Y.Z`
#     separately, after reviewing the commit and tag.
#
# Refuses to run if:
#   - The working tree is dirty (other uncommitted changes present).
#   - The current branch is not `main`.
#   Both can be overridden with `--force` for unusual cases.

set -euo pipefail

usage() {
    cat << 'EOF'
Usage: bump-version.sh <patch|minor|major|X.Y.Z> [--force]

  patch | minor | major   Compute the next version from package.json.
  X.Y.Z                   Set the explicit version (semver-shaped).
  --force                 Skip dirty-tree and branch-name checks.

Example:
  scripts/bump-version.sh minor
  scripts/bump-version.sh 3.66.0
EOF
    exit 2
}

[ $# -ge 1 ] || usage

ARG="$1"
FORCE=0
shift || true
while [ $# -gt 0 ]; do
    case "$1" in
        --force) FORCE=1 ;;
        *) usage ;;
    esac
    shift
done

# ------------------------------------------------------------------
# Pre-checks
# ------------------------------------------------------------------

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$REPO_ROOT"

if [ ! -f package.json ]; then
    echo "ERROR: package.json not found at $REPO_ROOT" >&2
    exit 1
fi

if [ "$FORCE" -ne 1 ]; then
    BRANCH=$(git rev-parse --abbrev-ref HEAD)
    if [ "$BRANCH" != "main" ]; then
        echo "ERROR: not on main (current: $BRANCH). Use --force to override." >&2
        exit 1
    fi
    if [ -n "$(git status --porcelain)" ]; then
        echo "ERROR: working tree dirty. Commit or stash changes first." >&2
        echo "       (or use --force to override)" >&2
        exit 1
    fi
fi

# ------------------------------------------------------------------
# Compute new version
# ------------------------------------------------------------------

CURRENT=$(python3 -c "import json; print(json.load(open('package.json'))['version'])")

bump_part() {
    local cur="$1" part="$2"
    local major minor patch
    IFS=. read -r major minor patch <<< "$cur"
    case "$part" in
        major) major=$((major + 1)); minor=0; patch=0 ;;
        minor) minor=$((minor + 1)); patch=0 ;;
        patch) patch=$((patch + 1)) ;;
        *) echo "ERROR: unknown bump part: $part" >&2; exit 1 ;;
    esac
    echo "$major.$minor.$patch"
}

case "$ARG" in
    patch|minor|major)
        NEW=$(bump_part "$CURRENT" "$ARG")
        ;;
    [0-9]*.[0-9]*.[0-9]*)
        NEW="$ARG"
        ;;
    *)
        usage
        ;;
esac

if [ "$NEW" = "$CURRENT" ]; then
    echo "ERROR: new version equals current ($CURRENT). Nothing to do." >&2
    exit 1
fi

echo "Bump: $CURRENT → $NEW"

# ------------------------------------------------------------------
# Write the new version to each tracked file
# ------------------------------------------------------------------

FILES=(package.json)
[ -f .claude-plugin/plugin.json ] && FILES+=(.claude-plugin/plugin.json)
if [ -f scripts/version-files.txt ]; then
    while IFS= read -r line; do
        line="${line%%#*}"
        line="${line## }"; line="${line%% }"
        [ -z "$line" ] && continue
        [ -f "$line" ] && FILES+=("$line")
    done < scripts/version-files.txt
fi

for f in "${FILES[@]}"; do
    python3 - "$f" "$CURRENT" "$NEW" << 'PY'
import json, sys
path, cur, new = sys.argv[1], sys.argv[2], sys.argv[3]
if path.endswith(".json"):
    d = json.load(open(path))
    if d.get("version") == cur:
        d["version"] = new
        with open(path, "w") as f:
            json.dump(d, f, indent=2)
            f.write("\n")
        print(f"  wrote {path}: {cur} -> {new}")
    else:
        print(f"  skipped {path}: version is {d.get('version')!r}, expected {cur!r}")
else:
    # For non-JSON files, do a plain string replace of the version.
    content = open(path).read()
    if cur in content:
        open(path, "w").write(content.replace(cur, new))
        print(f"  wrote {path}: {cur} -> {new}")
    else:
        print(f"  skipped {path}: {cur!r} not found")
PY
done

# ------------------------------------------------------------------
# Commit and tag
# ------------------------------------------------------------------

git add "${FILES[@]}"
git commit -m "chore(release): v$NEW"
git tag -a "v$NEW" -m "v$NEW"

echo
echo "Done. Created commit + tag for v$NEW."
echo "Next: review with"
echo "  git show v$NEW"
echo "Then push when ready:"
echo "  git push origin main"
echo "  git push origin v$NEW"
