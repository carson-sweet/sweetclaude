#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Extracts every fenced ```bash``` block from every SKILL.md under skills/
# and runs syntactic validation + targeted execution checks. Catches the
# class of failure that crashed v3.67.0 in production: heredocs nested
# inside if/fi where `fi` ended up parsed as Python (NameError on 'fi').
#
# This test runs without Sonnet. Bash blocks that fail `bash -n` or fail
# a smoke-execution in a fixture environment are reported as failures.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAILED=0
fail() { echo "  FAIL: $1"; FAILED=$((FAILED + 1)); }
pass() { echo "  PASS: $1"; }

# Where to find SKILL.md files. Excluded: any *.bak, archived.
SKILL_FILES=$(find "$REPO_ROOT/skills" -name "SKILL.md" -not -path "*/archive/*" | sort)

extract_blocks() {
  # awk: emit each fenced ```bash...``` block to its own file
  local skill="$1"
  local outdir="$2"
  awk -v out="$outdir" -v skill="$skill" '
    /^```bash$/ { in_block=1; idx++; file=sprintf("%s/block-%03d.sh", out, idx); next }
    /^```$/ && in_block { in_block=0; next }
    in_block { print > file }
  ' "$skill"
}

# ---------------------------------------------------------------------------
# Test 1: every extracted bash block must pass `bash -n` (syntax check)
# ---------------------------------------------------------------------------

echo "[1] bash -n on every SKILL.md bash block"

TMPROOT=$(mktemp -d)
trap "rm -rf $TMPROOT" EXIT

# Heuristic: skip blocks that are obviously example/template — contain
# placeholder syntax like `<UPPERCASE-NAME>` or `{var}` outside parameter
# expansion. These are illustrative shell snippets, not directly runnable.
is_template_block() {
  local block="$1"
  # Angle-bracket placeholder: <NAME>, <foo_bar>, <FOO-BAR>, <number>, etc.
  # Excludes redirection like 2>&1 (no closing >) and `<<` heredoc operators.
  grep -qE '<[A-Za-z][A-Za-z0-9_-]*>' "$block" && return 0
  # Curly-brace placeholder like {var} that's not bash parameter expansion
  # (parameter expansion is ${var} — leading $)
  grep -qE '[^$]\{[a-z_][a-z0-9_]*\}' "$block" && return 0
  return 1
}

TOTAL_BLOCKS=0
SKIPPED_BLOCKS=0
SYNTAX_FAILED=0
for skill in $SKILL_FILES; do
  rel=${skill#$REPO_ROOT/}
  outdir="$TMPROOT/$rel"
  mkdir -p "$outdir"
  extract_blocks "$skill" "$outdir"
  for block in "$outdir"/block-*.sh; do
    [ -f "$block" ] || continue
    TOTAL_BLOCKS=$((TOTAL_BLOCKS + 1))
    if is_template_block "$block"; then
      SKIPPED_BLOCKS=$((SKIPPED_BLOCKS + 1))
      continue
    fi
    if ! bash -n "$block" 2>"$TMPROOT/bash-n.err"; then
      err=$(cat "$TMPROOT/bash-n.err")
      fail "syntax error in $rel block $(basename "$block"): $err"
      SYNTAX_FAILED=$((SYNTAX_FAILED + 1))
    fi
  done
done

if [ "$SYNTAX_FAILED" -eq 0 ]; then
  pass "all $((TOTAL_BLOCKS - SKIPPED_BLOCKS)) directly-executable bash blocks pass bash -n (skipped $SKIPPED_BLOCKS template blocks with <PLACEHOLDER> syntax)"
fi

# ---------------------------------------------------------------------------
# Test 2: no SKILL.md may contain `if ... ; then\n  python3 ... << 'PY'`
# pattern — this is the structural bug that crashed v3.67.0. Catch it
# statically so it can never regress.
# ---------------------------------------------------------------------------

echo "[2] forbidden pattern: heredoc nested inside if/fi"

HEREDOC_VIOLATIONS=0
for skill in $SKILL_FILES; do
  rel=${skill#$REPO_ROOT/}
  # Pattern: an `if ...; then` line followed within 10 lines by a `<< 'XX'`
  # heredoc opener, before any closing `fi`. This is the structurally
  # fragile shape — agents re-typing the bash mangle the `fi` boundary.
  violations=$(python3 - "$skill" << 'PY'
import re, sys
text = open(sys.argv[1]).read()
# Walk fenced bash blocks
blocks = re.findall(r"```bash\n(.*?)\n```", text, re.DOTALL)
count = 0
for block in blocks:
    lines = block.splitlines()
    for i, line in enumerate(lines):
        if re.search(r"\bif\b.*;\s*then\s*$", line):
            # look forward up to 10 lines for a heredoc opener
            window = lines[i+1:i+15]
            for w in window:
                if re.search(r"<<\s*'[A-Z_]+'", w) or re.search(r"<<\s*[A-Z_]+\s*$", w):
                    count += 1
                    break
                if re.match(r"\s*fi\s*$", w):
                    break
print(count)
PY
)
  if [ "$violations" -gt 0 ]; then
    fail "heredoc-inside-if-fi in $rel: $violations occurrence(s)"
    HEREDOC_VIOLATIONS=$((HEREDOC_VIOLATIONS + violations))
  fi
done

if [ "$HEREDOC_VIOLATIONS" -eq 0 ]; then
  pass "no heredoc-inside-if-fi patterns in any SKILL.md"
fi

# ---------------------------------------------------------------------------
# Test 3: no SKILL.md may use `find ~/.claude -name "*.py" ... | head -1`
# for runner/script discovery. Use absolute paths or installed_plugins.json.
# This is the structural bug that picked the wrong installed mirror.
# ---------------------------------------------------------------------------

echo "[3] forbidden pattern: find-based runner/script discovery"

FIND_VIOLATIONS=0
for skill in $SKILL_FILES; do
  rel=${skill#$REPO_ROOT/}
  if grep -q 'find.*~/.claude.*\.\(py\|sh\)' "$skill" 2>/dev/null; then
    grep -n 'find.*~/.claude.*\.\(py\|sh\)' "$skill" | while read line; do
      fail "find-based discovery in $rel: $line"
    done
    FIND_VIOLATIONS=$((FIND_VIOLATIONS + 1))
  fi
done

if [ "$FIND_VIOLATIONS" -eq 0 ]; then
  pass "no find-based script discovery in any SKILL.md"
fi

# ---------------------------------------------------------------------------
# Test 4: hooks.json and hooks-manifest.json declare drift-gate.sh and
# master-preflight.sh with the correct events, matchers, and scope.
# ---------------------------------------------------------------------------

echo "[4] hook-config: drift-gate.sh and master-preflight.sh declared correctly"

HOOKS_JSON="$REPO_ROOT/hooks/hooks.json"
MANIFEST="$REPO_ROOT/hooks/hooks-manifest.json"

HOOK_CFG_RESULT=$(python3 - "$HOOKS_JSON" "$MANIFEST" << 'PY'
import sys, json
errors = []

with open(sys.argv[1]) as f:
    hooks = json.load(f)
with open(sys.argv[2]) as f:
    manifest = json.load(f)

session_cmds = [
    h.get("command", "")
    for entry in hooks.get("hooks", {}).get("SessionStart", [])
    for h in entry.get("hooks", [])
]
pre_entries = [
    (entry.get("matcher", ""), h.get("command", ""))
    for entry in hooks.get("hooks", {}).get("PreToolUse", [])
    for h in entry.get("hooks", [])
]

if not any("drift-gate.sh" in c for c in session_cmds):
    errors.append("hooks.json: drift-gate.sh not in SessionStart")
if not any("master-preflight.sh" in c and m == "Skill" for m, c in pre_entries):
    errors.append("hooks.json: master-preflight.sh not in PreToolUse matcher=Skill")

m_hooks = {h["file"]: h for h in manifest.get("hooks", []) if "file" in h}
for name, want_event, want_scope in [
    ("drift-gate.sh", "SessionStart", "global"),
    ("master-preflight.sh", "PreToolUse", "global"),
]:
    if name not in m_hooks:
        errors.append("hooks-manifest.json: " + name + " missing")
        continue
    h = m_hooks[name]
    if not h.get("required"):
        errors.append("hooks-manifest.json: " + name + " not marked required")
    if h.get("scope") != want_scope:
        errors.append("hooks-manifest.json: " + name + " scope=" + repr(h.get("scope")) + " want " + repr(want_scope))
    if h.get("event") != want_event:
        errors.append("hooks-manifest.json: " + name + " event=" + repr(h.get("event")) + " want " + repr(want_event))

print("COUNT=" + str(len(errors)))
for e in errors:
    print(e)
PY
)

HOOK_CFG_COUNT=$(printf '%s\n' "$HOOK_CFG_RESULT" | grep '^COUNT=' | cut -d= -f2)
if [ "${HOOK_CFG_COUNT:-0}" -eq 0 ]; then
  pass "drift-gate.sh and master-preflight.sh correctly declared in hooks.json + manifest"
else
  printf '%s\n' "$HOOK_CFG_RESULT" | grep -v '^COUNT=' | while read -r line; do
    fail "$line"
  done
fi

echo
if [ "$FAILED" -eq 0 ]; then
  echo "ALL TESTS PASSED ($TOTAL_BLOCKS bash blocks examined across $(echo $SKILL_FILES | wc -w | tr -d ' ') SKILL.md files)"
  exit 0
else
  echo "FAILURES: $FAILED"
  exit 1
fi
