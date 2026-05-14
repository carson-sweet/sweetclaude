#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Tests find_plugin_root() in scripts/maintenance/ensure-global-hooks.py for
# robustness against malformed/edge-case ~/.claude/plugins/installed_plugins.json.
#
# The function is called from update flow, fix-sweetclaude, and elsewhere. If
# it crashes on weird input it breaks the whole flow. This test exercises the
# weird inputs.
#
# Approach: HOME is overridden to a tempdir, so we control installed_plugins.json
# contents per scenario. We import the script's function directly via Python.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/maintenance/ensure-global-hooks.py"
FAILED=0
fail() { echo "  FAIL: $1"; FAILED=$((FAILED + 1)); }
pass() { echo "  PASS: $1"; }

# Run find_plugin_root() under a custom HOME and report the returned path.
# Optional second arg sets CLAUDE_PLUGIN_ROOT env var.
run_find() {
    local home="$1"
    local plugin_env="${2:-}"
    HOME="$home" CLAUDE_PLUGIN_ROOT="$plugin_env" python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT/scripts/maintenance')
spec = __import__('importlib.util', fromlist=['spec_from_file_location']).spec_from_file_location('egh', '$SCRIPT')
mod = __import__('importlib.util', fromlist=['module_from_spec']).module_from_spec(spec)
spec.loader.exec_module(mod)
print(mod.find_plugin_root())
"
}

assert_empty() {
    local label="$1"; local result="$2"
    if [ -z "$result" ]; then pass "$label → empty (expected)"; else fail "$label → '$result' (expected empty)"; fi
}
assert_equals() {
    local label="$1"; local expected="$2"; local result="$3"
    if [ "$expected" = "$result" ]; then pass "$label → matches expected"; else fail "$label → '$result' (expected '$expected')"; fi
}

# ── Scenarios ───────────────────────────────────────────────────────────────

echo "=== find_plugin_root() robustness ==="

# 1. installed_plugins.json doesn't exist at all
echo ""
echo "Case 1: installed_plugins.json missing"
TMP=$(mktemp -d); mkdir -p "$TMP/.claude/plugins"
assert_empty "missing installed_plugins.json" "$(run_find "$TMP")"
rm -rf "$TMP"

# 2. installed_plugins.json is corrupt JSON
echo ""
echo "Case 2: corrupt JSON"
TMP=$(mktemp -d); mkdir -p "$TMP/.claude/plugins"
echo '{not valid json' > "$TMP/.claude/plugins/installed_plugins.json"
assert_empty "corrupt JSON" "$(run_find "$TMP")"
rm -rf "$TMP"

# 3. Valid JSON, but plugins dict empty
echo ""
echo "Case 3: empty plugins dict"
TMP=$(mktemp -d); mkdir -p "$TMP/.claude/plugins"
echo '{"plugins": {}}' > "$TMP/.claude/plugins/installed_plugins.json"
assert_empty "empty plugins dict" "$(run_find "$TMP")"
rm -rf "$TMP"

# 4. Has sweetclaude entry but installPath doesn't exist on disk
echo ""
echo "Case 4: sweetclaude entry, installPath doesn't exist"
TMP=$(mktemp -d); mkdir -p "$TMP/.claude/plugins"
cat > "$TMP/.claude/plugins/installed_plugins.json" <<'JSON'
{"plugins": {"sweetclaude@sweetclaude": [{"scope": "user", "version": "4.0.0", "installPath": "/nonexistent/path/to/sweetclaude"}]}}
JSON
assert_empty "installPath points to nonexistent dir" "$(run_find "$TMP")"
rm -rf "$TMP"

# 5. Valid sweetclaude entry with real installPath → returns it
echo ""
echo "Case 5: valid sweetclaude entry"
TMP=$(mktemp -d); mkdir -p "$TMP/.claude/plugins" "$TMP/plugin-install"
cat > "$TMP/.claude/plugins/installed_plugins.json" <<JSON
{"plugins": {"sweetclaude@sweetclaude": [{"scope": "user", "version": "4.0.0", "installPath": "$TMP/plugin-install", "lastUpdated": "2026-05-13T00:00:00Z"}]}}
JSON
assert_equals "valid installPath" "$TMP/plugin-install" "$(run_find "$TMP")"
rm -rf "$TMP"

# 6. Multiple versions — most recently updated wins
echo ""
echo "Case 6: multiple sweetclaude versions, picks newest by lastUpdated"
TMP=$(mktemp -d); mkdir -p "$TMP/.claude/plugins" "$TMP/v3-install" "$TMP/v4-install"
cat > "$TMP/.claude/plugins/installed_plugins.json" <<JSON
{"plugins": {"sweetclaude@sweetclaude": [
    {"scope": "user", "version": "3.68.4", "installPath": "$TMP/v3-install", "lastUpdated": "2026-01-01T00:00:00Z"},
    {"scope": "user", "version": "4.0.0", "installPath": "$TMP/v4-install", "lastUpdated": "2026-05-13T00:00:00Z"}
]}}
JSON
assert_equals "newest by lastUpdated wins" "$TMP/v4-install" "$(run_find "$TMP")"
rm -rf "$TMP"

# 7. scope != "user" is ignored
echo ""
echo "Case 7: non-user scope is filtered out"
TMP=$(mktemp -d); mkdir -p "$TMP/.claude/plugins" "$TMP/system-install"
cat > "$TMP/.claude/plugins/installed_plugins.json" <<JSON
{"plugins": {"sweetclaude@sweetclaude": [{"scope": "system", "version": "4.0.0", "installPath": "$TMP/system-install"}]}}
JSON
assert_empty "only scope=user is considered" "$(run_find "$TMP")"
rm -rf "$TMP"

# 8. Plugin name doesn't contain "sweetclaude" → skipped
echo ""
echo "Case 8: non-sweetclaude plugin key is skipped"
TMP=$(mktemp -d); mkdir -p "$TMP/.claude/plugins" "$TMP/other-plugin"
cat > "$TMP/.claude/plugins/installed_plugins.json" <<JSON
{"plugins": {"other-plugin@vendor": [{"scope": "user", "version": "1.0", "installPath": "$TMP/other-plugin"}]}}
JSON
assert_empty "non-sweetclaude key skipped" "$(run_find "$TMP")"
rm -rf "$TMP"

# 9. CLAUDE_PLUGIN_ROOT env var set to a real dir → short-circuit, returns it
echo ""
echo "Case 9: CLAUDE_PLUGIN_ROOT env var (real dir) short-circuits"
TMP=$(mktemp -d); mkdir -p "$TMP/.claude/plugins" "$TMP/env-plugin" "$TMP/file-plugin"
cat > "$TMP/.claude/plugins/installed_plugins.json" <<JSON
{"plugins": {"sweetclaude@sweetclaude": [{"scope": "user", "version": "4.0.0", "installPath": "$TMP/file-plugin"}]}}
JSON
assert_equals "env var wins over installed_plugins.json" "$TMP/env-plugin" "$(run_find "$TMP" "$TMP/env-plugin")"
rm -rf "$TMP"

# 10. CLAUDE_PLUGIN_ROOT set to non-existent dir → falls back to installed_plugins lookup
echo ""
echo "Case 10: CLAUDE_PLUGIN_ROOT set to nonexistent → falls back to file lookup"
TMP=$(mktemp -d); mkdir -p "$TMP/.claude/plugins" "$TMP/file-plugin"
cat > "$TMP/.claude/plugins/installed_plugins.json" <<JSON
{"plugins": {"sweetclaude@sweetclaude": [{"scope": "user", "version": "4.0.0", "installPath": "$TMP/file-plugin"}]}}
JSON
assert_equals "env var nonexistent → fallback works" "$TMP/file-plugin" "$(run_find "$TMP" "/nonexistent/env/path")"
rm -rf "$TMP"

# 11. plugins dict has unexpected shape (not a list value)
echo ""
echo "Case 11: malformed plugins value (not a list)"
TMP=$(mktemp -d); mkdir -p "$TMP/.claude/plugins"
echo '{"plugins": {"sweetclaude@sweetclaude": "not-a-list"}}' > "$TMP/.claude/plugins/installed_plugins.json"
# Should not crash. May return empty or fail gracefully.
RESULT=$(run_find "$TMP" 2>&1) || true
if [ -z "$RESULT" ]; then
    pass "malformed plugins value handled (returned empty)"
else
    fail "malformed plugins value: returned '$RESULT' (expected empty or graceful failure)"
fi
rm -rf "$TMP"

# 12. installPath is a file, not a directory
echo ""
echo "Case 12: installPath is a file, not a directory"
TMP=$(mktemp -d); mkdir -p "$TMP/.claude/plugins"
touch "$TMP/not-a-dir"
cat > "$TMP/.claude/plugins/installed_plugins.json" <<JSON
{"plugins": {"sweetclaude@sweetclaude": [{"scope": "user", "version": "4.0.0", "installPath": "$TMP/not-a-dir"}]}}
JSON
assert_empty "installPath is a file (not dir) → empty" "$(run_find "$TMP")"
rm -rf "$TMP"

echo ""
if [ "$FAILED" -gt 0 ]; then
    echo "=== FAILED: $FAILED check(s) ==="
    exit 1
else
    echo "=== ALL PASSED ==="
    exit 0
fi
