#!/bin/bash
# Verify the current migration safety contract against isolated project fixtures.
set -u
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAILED=0
run_suite() {
  local description="$1"
  shift
  echo "=== $description ==="
  if python3 -m pytest -q "$@"; then
    echo "PASS: $description"
  else
    echo "FAIL: $description"
    FAILED=$((FAILED + 1))
  fi
}

run_suite "Migration preflight, plan, approval, snapshot, and verification" \
  "$REPO_ROOT/tests/test_migrate_safety.py"
run_suite "Current bootstrap and work-item guards" \
  "$REPO_ROOT/tests/test_bootstrap_major_guard.py" \
  "$REPO_ROOT/tests/test_ep0085_verification.py"
run_suite "Counter drift detection" \
  "$REPO_ROOT/tests/test_doctor.py::TestStorageLint::test_counter_drift_detected_when_file_max_exceeds_cache_max"
run_suite "Cache recovery and rollback" \
  "$REPO_ROOT/tests/test_doctor.py::TestAutoFix::test_rebuild_cache_backs_up_and_restores_existing_cache"

echo "Interactive model-driven migration prompts are not covered by these tests."
if [ "$FAILED" -ne 0 ]; then
  echo "FAILED: $FAILED verification group(s)"
  exit 1
fi
echo "ALL VERIFICATION GROUPS PASSED"
