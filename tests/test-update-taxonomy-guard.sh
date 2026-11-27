#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Guards the beta hotfix behavior: sweetclaude:update must not offer or run
# taxonomy/orphan migrations until the migrator supports all supported layouts.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UPDATE_SKILL="$REPO_ROOT/skill-library/configure/update/SKILL.md"
FAILED=0

fail() { echo "  FAIL: $1"; FAILED=$((FAILED + 1)); }
pass() { echo "  PASS: $1"; }

echo "=== update taxonomy guard tests ==="

if grep -q "migrate_taxonomy.py --project-dir" "$UPDATE_SKILL"; then
  fail "update skill still invokes migrate_taxonomy.py directly"
else
  pass "update skill does not invoke migrate_taxonomy.py directly"
fi

if grep -q "run taxonomy migration with dry-run preview" "$UPDATE_SKILL"; then
  fail "update skill still offers taxonomy migration"
else
  pass "update skill does not offer taxonomy migration"
fi

if grep -q "Include in migration.*copy each orphaned file" "$UPDATE_SKILL"; then
  fail "update skill still offers orphan file mutation"
else
  pass "update skill does not offer orphan file mutation"
fi

if grep -q "Update never mutates project work-item state" "$UPDATE_SKILL" \
   && grep -q "Do not write.*doctor-prompt-pending.json" "$UPDATE_SKILL"; then
  pass "update skill states the project safety contract"
else
  fail "update skill is missing the project safety contract"
fi

if python3 -m pytest -q "$REPO_ROOT/tests/test_update_project_check_safety.py"; then
  pass "project checks verify scan outcomes and preserve work items"
else
  fail "project-check safety regressions failed"
fi

echo ""
if [ "$FAILED" -gt 0 ]; then
  echo "=== FAILED: $FAILED check(s) ==="
  exit 1
else
  echo "=== ALL PASSED ==="
fi
