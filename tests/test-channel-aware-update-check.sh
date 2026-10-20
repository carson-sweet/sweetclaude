#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# ISSUE-248 regression tests: the update-availability check must be
# channel-aware. Stable installs must never be offered prerelease versions,
# and only strictly-newer versions may be offered on any channel.
#
# Unlike test-update-discovery.sh (which tests an extracted copy of the
# resolver), these tests drive the real hooks/sweetclaude-health-check.sh
# end-to-end against a fixture HOME and project, with git/gh PATH shims so
# the network paths are deterministic.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$REPO_ROOT/hooks/sweetclaude-health-check.sh"
FAILED=0
fail() { echo "  FAIL: $1"; FAILED=$((FAILED + 1)); }
pass() { echo "  PASS: $1"; }

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

NOW_ISO=$(python3 -c "from datetime import datetime,timezone; print(datetime.now(timezone.utc).isoformat(timespec='seconds'))")

# --- git/gh shims ----------------------------------------------------------
# gh: always fails (no auth) so the hook falls through to git ls-remote.
# git: answers `ls-remote --tags <url>` with the tag list in $FAKE_TAGS_FILE.
SHIMS="$WORK/shims"
mkdir -p "$SHIMS"
cat > "$SHIMS/gh" << 'SH'
#!/bin/bash
exit 1
SH
cat > "$SHIMS/git" << 'SH'
#!/bin/bash
if [ "${1:-}" = "ls-remote" ]; then
  cat "${FAKE_TAGS_FILE:?}"
  exit 0
fi
exit 1
SH
chmod +x "$SHIMS/gh" "$SHIMS/git"

# --- fixture builders ------------------------------------------------------

# make_fixture <name> <plugin_key> <installed_version> [prior_available]
# Creates $WORK/<name> as HOME and $WORK/<name>/project as PROJECT_DIR.
make_fixture() {
  local name="$1" key="$2" version="$3" prior="${4:-null}"
  local home="$WORK/$name"
  mkdir -p "$home/.claude/plugins" "$home/project/.sweetclaude/state"
  cat > "$home/.claude/plugins/installed_plugins.json" << JSON
{"plugins": {"$key": [{"installPath": "/nonexistent", "version": "$version", "scope": "user", "lastUpdated": "2026-08-01T00:00:00Z"}]}}
JSON
  cat > "$home/project/.sweetclaude/state/sweetclaude.yaml" << YAML
schema_version: 2
framework:
  installed_version: $version
  consistency:
    last_checked: '$NOW_ISO'
  update:
    available: $prior
    declined: null
    last_checked: null
YAML
}

# add_dev_clone <name> <clone_version>
# Adds ~/.claude/sweetclaude-install.json pointing at a fake clone whose
# package.json carries <clone_version> (the hook's Path 1).
add_dev_clone() {
  local name="$1" clone_version="$2"
  local home="$WORK/$name"
  mkdir -p "$home/dev/sweetclaude"
  printf '{"name": "sweetclaude", "version": "%s"}\n' "$clone_version" \
    > "$home/dev/sweetclaude/package.json"
  printf '{"repo_path": "%s/dev/sweetclaude"}\n' "$home" \
    > "$home/.claude/sweetclaude-install.json"
}

# set_tags <tag>...
set_tags() {
  FAKE_TAGS_FILE="$WORK/tags.txt"
  : > "$FAKE_TAGS_FILE"
  local i=0
  for tag in "$@"; do
    printf 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa%x\trefs/tags/%s\n' "$i" "$tag" >> "$FAKE_TAGS_FILE"
    i=$((i + 1))
  done
  export FAKE_TAGS_FILE
}

# run_hook <name>
run_hook() {
  local home="$WORK/$1"
  HOME="$home" PROJECT_DIR="$home/project" PATH="$SHIMS:$PATH" bash "$HOOK" >/dev/null 2>&1
}

# read_available <name>
read_available() {
  python3 -c "
import yaml
d = yaml.safe_load(open('$WORK/$1/project/.sweetclaude/state/sweetclaude.yaml')) or {}
print(repr((d.get('framework') or {}).get('update', {}).get('available')))
"
}

# ---------------------------------------------------------------------------
# Test 1: observed reproduction — stable install, dev clone on a beta branch
# ---------------------------------------------------------------------------

echo "[1] stable install + beta dev clone -> no beta offer, stale value cleared"

make_fixture t1 "sweetclaude@sweetclaude-stable" "4.5.1" "4.5.1-beta"
add_dev_clone t1 "4.5.1-beta"
set_tags v4.5.0 v4.5.1 v4.5.1-beta
run_hook t1
AVAILABLE=$(read_available t1)
if [ "$AVAILABLE" = "None" ]; then
  pass "stable install not offered 4.5.1-beta; stale available cleared"
else
  fail "stable install offered prerelease: available=$AVAILABLE"
fi

# ---------------------------------------------------------------------------
# Test 2: stable install, remote beta tag numerically ahead of stable
# ---------------------------------------------------------------------------

echo "[2] stable install + newer beta tag on remote -> no offer"

make_fixture t2 "sweetclaude@sweetclaude-stable" "4.5.1"
set_tags v4.5.0 v4.5.1 v4.5.2-beta
run_hook t2
AVAILABLE=$(read_available t2)
if [ "$AVAILABLE" = "None" ]; then
  pass "v4.5.2-beta tag not offered to stable install"
else
  fail "stable install offered prerelease tag: available=$AVAILABLE"
fi

# ---------------------------------------------------------------------------
# Test 3: equal-or-lower remote version is never offered
# ---------------------------------------------------------------------------

echo "[3] remote version lower than installed -> no offer"

make_fixture t3 "sweetclaude@sweetclaude-stable" "4.5.1"
set_tags v4.4.0 v4.5.0
run_hook t3
AVAILABLE=$(read_available t3)
if [ "$AVAILABLE" = "None" ]; then
  pass "older remote 4.5.0 not offered as update"
else
  fail "downgrade offered: available=$AVAILABLE"
fi

# ---------------------------------------------------------------------------
# Test 4: beta install still gets beta updates
# ---------------------------------------------------------------------------

echo "[4] beta install + newer beta dev clone -> beta offered"

make_fixture t4 "sweetclaude@sweetclaude-beta" "4.5.0-beta"
add_dev_clone t4 "4.5.1-beta"
set_tags v4.5.0 v4.5.1-beta
run_hook t4
AVAILABLE=$(read_available t4)
if [ "$AVAILABLE" = "'4.5.1-beta'" ]; then
  pass "beta install offered 4.5.1-beta"
else
  fail "beta install expected 4.5.1-beta, got available=$AVAILABLE"
fi

# ---------------------------------------------------------------------------
# Test 5: stable install still gets stable updates
# ---------------------------------------------------------------------------

echo "[5] stable install + newer stable tag -> stable offered"

make_fixture t5 "sweetclaude@sweetclaude-stable" "4.5.0"
set_tags v4.5.0 v4.5.1 v4.5.1-beta
run_hook t5
AVAILABLE=$(read_available t5)
if [ "$AVAILABLE" = "'4.5.1'" ]; then
  pass "stable install offered 4.5.1"
else
  fail "stable install expected 4.5.1, got available=$AVAILABLE"
fi

# ---------------------------------------------------------------------------
# Test 6: bootstrap Step 6 decision block — prerelease guard (defense in depth)
# ---------------------------------------------------------------------------
# Extracts the real decision heredoc from skills/bootstrap/SKILL.md and runs
# it against fixture state: a prerelease `available` on a stable (non-
# prerelease) install must decide silent, never prompt.

echo "[6] bootstrap Step 6 -> prerelease available on stable install is silent"

DECISION_BLOCK=$(awk "/<< 'PY'/{buf=\"\"; cap=1; next} /^PY\$/{if(cap && buf ~ /DECISION=/){print buf; exit} cap=0; next} cap{buf=buf \$0 \"\n\"}" \
  "$REPO_ROOT/skills/bootstrap/SKILL.md")

if [ -z "$DECISION_BLOCK" ]; then
  fail "could not extract Step 6 decision block from skills/bootstrap/SKILL.md"
else
  step6_decide() {
    local installed="$1" available="$2"
    local yml="$WORK/step6.yaml"
    cat > "$yml" << YAML
schema_version: 2
framework:
  installed_version: $installed
  update:
    available: $available
    declined: null
YAML
    python3 -c "$DECISION_BLOCK" "$yml"
  }

  D=$(step6_decide "4.5.1" "4.5.1-beta")
  if [ "$D" = "DECISION=silent" ]; then
    pass "stable 4.5.1 + available 4.5.1-beta -> silent"
  else
    fail "stable 4.5.1 + available 4.5.1-beta -> $D (want DECISION=silent)"
  fi

  D=$(step6_decide "4.5.0-beta" "4.5.1-beta")
  if [ "$D" = "DECISION=prompt" ]; then
    pass "beta 4.5.0-beta + available 4.5.1-beta -> prompt"
  else
    fail "beta install prerelease offer -> $D (want DECISION=prompt)"
  fi

  D=$(step6_decide "4.5.0" "4.5.1")
  if [ "$D" = "DECISION=prompt" ]; then
    pass "stable 4.5.0 + available 4.5.1 -> prompt"
  else
    fail "stable upgrade offer -> $D (want DECISION=prompt)"
  fi
fi

# ---------------------------------------------------------------------------
# Test 7: bootstrap Step 6 decision block — a decline silences its own major
# ---------------------------------------------------------------------------

echo "[7] bootstrap Step 6 -> declined version silences prompts for its major"

if [ -z "$DECISION_BLOCK" ]; then
  fail "could not extract Step 6 decision block from skills/bootstrap/SKILL.md"
else
  step6_decide_declined() {
    local installed="$1" available="$2" declined="$3"
    local yml="$WORK/step6-declined.yaml"
    cat > "$yml" << YAML
schema_version: 2
framework:
  installed_version: $installed
  update:
    available: $available
    declined: $declined
YAML
    python3 -c "$DECISION_BLOCK" "$yml"
  }

  D=$(step6_decide_declined "4.5.3" "5.0.0" "5.0.0")
  if [ "$D" = "DECISION=silent_declined|5" ]; then
    pass "installed 4.5.3 + available 5.0.0 + declined 5.0.0 -> silent_declined|5"
  else
    fail "declined major bump -> $D (want DECISION=silent_declined|5)"
  fi

  D=$(step6_decide_declined "4.5.3" "5.1.0" "5.0.0")
  if [ "$D" = "DECISION=silent_declined|5" ]; then
    pass "installed 4.5.3 + available 5.1.0 + declined 5.0.0 -> silent_declined|5"
  else
    fail "later minor in declined major -> $D (want DECISION=silent_declined|5)"
  fi

  D=$(step6_decide_declined "4.5.3" "6.0.0" "5.0.0")
  if [ "$D" = "DECISION=prompt" ]; then
    pass "installed 4.5.3 + available 6.0.0 + declined 5.0.0 -> prompt"
  else
    fail "next major after declined major -> $D (want DECISION=prompt)"
  fi

  D=$(step6_decide_declined "4.5.3" "5.0.0" "null")
  if [ "$D" = "DECISION=prompt" ]; then
    pass "installed 4.5.3 + available 5.0.0 + no decline -> prompt"
  else
    fail "undeclined major bump -> $D (want DECISION=prompt)"
  fi

  D=$(step6_decide_declined "4.0.0" "5.0.0" "4.0.0")
  if [ "$D" = "DECISION=prompt" ]; then
    pass "installed 4.0.0 + available 5.0.0 + declined 4.0.0 -> prompt"
  else
    fail "decline of an older major -> $D (want DECISION=prompt)"
  fi

  D=$(step6_decide_declined "4.5.3" "5.0.0" "true")
  if [ "$D" = "DECISION=prompt" ]; then
    pass "installed 4.5.3 + available 5.0.0 + legacy declined true -> prompt"
  else
    fail "legacy boolean decline on major bump -> $D (want DECISION=prompt)"
  fi

  D=$(step6_decide_declined "4.5.3" "5.0.0-beta" "5.0.0-beta")
  if [ "$D" = "DECISION=silent" ]; then
    pass "stable 4.5.3 + available 5.0.0-beta -> silent (prerelease rule)"
  else
    fail "prerelease offer on stable install -> $D (want DECISION=silent)"
  fi
fi

# ---------------------------------------------------------------------------

echo ""
if [ "$FAILED" -gt 0 ]; then
  echo "$FAILED test(s) FAILED"
  exit 1
fi
echo "All tests passed"
exit 0
