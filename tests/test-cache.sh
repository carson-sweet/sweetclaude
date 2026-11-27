#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Behavioral tests for scripts/cache.py — the roadmap SQLite cache.
# Creates isolated fixture environments with sample markdown files,
# builds the cache, and verifies query output.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CACHE_PY="$REPO_ROOT/scripts/cache.py"
FAILED=0
PASSED=0
fail() { echo "  FAIL: $1"; FAILED=$((FAILED + 1)); }
pass() { echo "  PASS: $1"; PASSED=$((PASSED + 1)); }

TMPROOT=$(mktemp -d)
trap "rm -rf $TMPROOT" EXIT

# --- Fixture: project with stories, epics, milestones (current ISSUE prefixes) ---
FX="$TMPROOT/project"
mkdir -p "$FX/.sweetclaude/product/backlog/stories/done"
mkdir -p "$FX/.sweetclaude/product/backlog/bugs"
mkdir -p "$FX/.sweetclaude/product/backlog/chores"
mkdir -p "$FX/.sweetclaude/product/roadmap/epics"
mkdir -p "$FX/.sweetclaude/product/roadmap/milestones"
mkdir -p "$FX/.sweetclaude/cache"

cat > "$FX/.sweetclaude/product/roadmap/milestones/MS-001-v41.md" << 'EOF'
---
id: MS-001
type: milestone
title: "v4.1"
status: active
created: 2026-05-15
updated: 2026-05-15
---
EOF

cat > "$FX/.sweetclaude/product/roadmap/epics/EP-001-workflow-engine.md" << 'EOF'
---
id: EP-001
type: epic
title: "Workflow Engine"
status: active
milestone: MS-001
objective: "Workflow state tracking for all execution types."
completion_criteria:
  - "Taxonomy finalized"
  - "State model designed"
  - "Implementation complete"
depends_on: []
created: 2026-05-15
updated: 2026-05-15
---
EOF

cat > "$FX/.sweetclaude/product/roadmap/epics/EP-002-release-primitive.md" << 'EOF'
---
id: EP-002
type: epic
title: "Release Primitive"
status: new
milestone: MS-001
objective: "Structured release management."
completion_criteria:
  - "Schema defined"
  - "Skills updated"
depends_on:
  - EP-001
created: 2026-05-15
updated: 2026-05-15
---
EOF

cat > "$FX/.sweetclaude/product/backlog/stories/ISSUE-020-upfront-assessment.md" << 'EOF'
---
id: ISSUE-020
type: story
title: "Upfront story assessment"
status: new
priority: now
effort: m
epic: EP-001
epic_sequence: 1
tags: [workflow]
created: 2026-05-15
updated: 2026-05-15
---
EOF

cat > "$FX/.sweetclaude/product/backlog/stories/ISSUE-018-phase-status-table.md" << 'EOF'
---
id: ISSUE-018
type: story
title: "Story phase-status table"
status: new
priority: now
effort: l
epic: EP-001
epic_sequence: 2
tags: [workflow, state]
created: 2026-05-15
updated: 2026-05-15
---
EOF

cat > "$FX/.sweetclaude/product/backlog/stories/ISSUE-015-model-enforcement.md" << 'EOF'
---
id: ISSUE-015
type: story
title: "planning-concepts.md model enforcement"
status: new
priority: soon
effort: xl
epic: EP-001
epic_sequence: 3
tags: [workflow]
created: 2026-05-15
updated: 2026-05-15
---
EOF

cat > "$FX/.sweetclaude/product/backlog/stories/done/ISSUE-010-horizon-taxonomy.md" << 'EOF'
---
id: ISSUE-010
type: story
title: "Document and refine horizon taxonomy"
status: done
priority: now
effort: m
epic: null
epic_sequence: null
tags: [docs]
created: 2026-05-13
updated: 2026-05-15
closed_date: 2026-05-15
---
EOF

cat > "$FX/.sweetclaude/product/backlog/stories/ISSUE-011-roadmap-system.md" << 'EOF'
---
id: ISSUE-011
type: story
title: "Roadmap system"
status: new
priority: now
effort: xl
epic: EP-002
epic_sequence: 1
tags: [roadmap]
created: 2026-05-13
updated: 2026-05-15
---
EOF

cat > "$FX/.sweetclaude/product/backlog/bugs/ISSUE-005-cache-test-bug.md" << 'EOF'
---
id: ISSUE-005
type: bug-fix
title: "Test bug for cache"
status: new
priority: now
effort: s
epic: null
epic_sequence: null
tags: [test]
created: 2026-05-15
updated: 2026-05-15
---
EOF

# ---------------------------------------------------------------------------
echo "[1] cache.py --rebuild creates the database"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --rebuild 2>&1)
if [ -f "$FX/.sweetclaude/cache/roadmap.db" ]; then
  pass "database created"
else
  fail "database not found after rebuild"
fi

# ---------------------------------------------------------------------------
echo "[2] cache.py --query item-count returns correct counts"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query item-count 2>&1)
# 4 active stories + 1 done story + 1 bug + 2 epics + 1 release = 9
if echo "$OUTPUT" | grep -q '"total": 9'; then
  pass "item count is 9"
else
  fail "expected total=9, got: $OUTPUT"
fi

# ---------------------------------------------------------------------------
echo "[3] cache.py --query active-epic returns EP-001"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query active-epic 2>&1)
if echo "$OUTPUT" | grep -q '"id": "EP-001"'; then
  pass "active epic is EP-001"
else
  fail "expected EP-001, got: $OUTPUT"
fi

# ---------------------------------------------------------------------------
echo "[4] cache.py --query epic-stories --epic EP-001 returns stories in sequence order"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query epic-stories --epic EP-001 2>&1)
# Should be ISSUE-020 (seq 1), ISSUE-018 (seq 2), ISSUE-015 (seq 3)
FIRST=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['id'])" 2>/dev/null || true)
SECOND=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[1]['id'])" 2>/dev/null || true)
THIRD=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[2]['id'])" 2>/dev/null || true)
if [ "$FIRST" = "ISSUE-020" ] && [ "$SECOND" = "ISSUE-018" ] && [ "$THIRD" = "ISSUE-015" ]; then
  pass "stories in sequence order: 020, 018, 015"
else
  fail "wrong order: $FIRST, $SECOND, $THIRD"
fi

# ---------------------------------------------------------------------------
echo "[5] cache.py --query epic-stories excludes done stories by default"
# Mark ISSUE-020 as done in file and rebuild
sed -i.bak 's/status: new/status: done/' "$FX/.sweetclaude/product/backlog/stories/ISSUE-020-upfront-assessment.md"
python3 "$CACHE_PY" --project-dir "$FX" --rebuild >/dev/null 2>&1
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query epic-stories --epic EP-001 2>&1)
COUNT=$(echo "$OUTPUT" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || true)
if [ "$COUNT" = "2" ]; then
  pass "done stories excluded (2 remaining)"
else
  fail "expected 2 stories, got $COUNT"
fi
# Restore
mv "$FX/.sweetclaude/product/backlog/stories/ISSUE-020-upfront-assessment.md.bak" "$FX/.sweetclaude/product/backlog/stories/ISSUE-020-upfront-assessment.md"
python3 "$CACHE_PY" --project-dir "$FX" --rebuild >/dev/null 2>&1

# ---------------------------------------------------------------------------
echo "[6] cache.py --query backlog returns items sorted by priority"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query backlog 2>&1)
# now items should come before soon items
FIRST_PRI=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['priority'])" 2>/dev/null || true)
if [ "$FIRST_PRI" = "now" ]; then
  pass "backlog sorted by priority (now first)"
else
  fail "expected first item priority=now, got: $FIRST_PRI"
fi

# ---------------------------------------------------------------------------
echo "[7] cache.py --query backlog excludes done items"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query backlog 2>&1)
HAS_DONE=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(any(i['id']=='ISSUE-010' for i in d))" 2>/dev/null || true)
if [ "$HAS_DONE" = "False" ]; then
  pass "done items excluded from backlog"
else
  fail "ISSUE-010 (done) appeared in backlog"
fi

# ---------------------------------------------------------------------------
echo "[8] cache.py --query next-id --prefix ISSUE returns max+1"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query next-id --prefix ISSUE 2>&1)
if echo "$OUTPUT" | grep -q '"next_id": "ISSUE-021"'; then
  pass "next issue ID is ISSUE-021"
else
  fail "expected ISSUE-021, got: $OUTPUT"
fi

# ---------------------------------------------------------------------------
echo "[9] cache.py --query next-id --prefix EP returns max+1"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query next-id --prefix EP 2>&1)
if echo "$OUTPUT" | grep -q '"next_id": "EP-003"'; then
  pass "next epic ID is EP-003"
else
  fail "expected EP-003, got: $OUTPUT"
fi

# ---------------------------------------------------------------------------
echo "[10] cache.py --query releases returns milestone hierarchy"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query releases 2>&1)
MS_ID=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['id'])" 2>/dev/null || true)
EPIC_COUNT=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d[0]['epics']))" 2>/dev/null || true)
if [ "$MS_ID" = "MS-001" ] && [ "$EPIC_COUNT" = "2" ]; then
  pass "MS-001 has 2 epics"
else
  fail "expected MS-001 with 2 epics, got ms=$MS_ID epics=$EPIC_COUNT"
fi

# ---------------------------------------------------------------------------
echo "[11] cache.py --query epic-stories --epic EP-001 --include-done includes done stories"
sed -i.bak 's/status: new/status: done/' "$FX/.sweetclaude/product/backlog/stories/ISSUE-020-upfront-assessment.md"
python3 "$CACHE_PY" --project-dir "$FX" --rebuild >/dev/null 2>&1
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query epic-stories --epic EP-001 --include-done 2>&1)
COUNT=$(echo "$OUTPUT" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || true)
if [ "$COUNT" = "3" ]; then
  pass "include-done returns all 3 stories"
else
  fail "expected 3 stories with include-done, got $COUNT"
fi
mv "$FX/.sweetclaude/product/backlog/stories/ISSUE-020-upfront-assessment.md.bak" "$FX/.sweetclaude/product/backlog/stories/ISSUE-020-upfront-assessment.md"
python3 "$CACHE_PY" --project-dir "$FX" --rebuild >/dev/null 2>&1

# ---------------------------------------------------------------------------
echo "[12] cache.py --query tags returns items by tag"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query tags --tag workflow 2>&1)
COUNT=$(echo "$OUTPUT" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || true)
if [ "$COUNT" = "3" ]; then
  pass "3 items tagged 'workflow'"
else
  fail "expected 3 items with tag=workflow, got $COUNT"
fi

# ---------------------------------------------------------------------------
echo "[13] cache.py handles missing roadmap directory gracefully"
FX2="$TMPROOT/project-no-roadmap"
mkdir -p "$FX2/.sweetclaude/product/backlog/stories"
mkdir -p "$FX2/.sweetclaude/cache"
cat > "$FX2/.sweetclaude/product/backlog/stories/ISSUE-001-test.md" << 'STEOF'
---
id: ISSUE-001
type: story
title: "Test story"
status: new
priority: now
created: 2026-05-15
updated: 2026-05-15
---
STEOF
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX2" --rebuild 2>&1)
if [ -f "$FX2/.sweetclaude/cache/roadmap.db" ]; then
  pass "cache built without roadmap directory"
else
  fail "cache not built when roadmap dir missing"
fi

# ---------------------------------------------------------------------------
echo "[14] cache.py --query active-epic returns null when no active epic"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX2" --query active-epic 2>&1)
if echo "$OUTPUT" | grep -q "null"; then
  pass "no active epic returns null"
else
  fail "expected null, got: $OUTPUT"
fi

# ---------------------------------------------------------------------------
echo "[15] cache.py --query releases-compact returns compact milestone hierarchy under 10KB"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query releases-compact 2>&1)
MS_ID=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['id'])" 2>/dev/null || true)
EPIC_COUNT=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d[0]['epics']))" 2>/dev/null || true)
STORY_COUNT=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d[0]['epics'][0]['stories']))" 2>/dev/null || true)
HAS_CRITERIA=$(echo "$OUTPUT" | python3 -c "import sys,json; ep=json.load(sys.stdin)[0]['epics'][0]; print('criteria_done' in ep and 'criteria_total' in ep)" 2>/dev/null || true)
BYTE_SIZE=$(echo -n "$OUTPUT" | wc -c | tr -d ' ')
NO_EXTRA_FIELDS=$(echo "$OUTPUT" | python3 -c "
import sys,json
data = json.load(sys.stdin)
ep = data[0]['epics'][0]
allowed = {'id','title','status','derived_status','source','criteria_done','criteria_total','stories'}
extra = set(ep.keys()) - allowed
print('none' if not extra else ','.join(sorted(extra)))
" 2>/dev/null || true)
if [ "$MS_ID" = "MS-001" ] && [ "$EPIC_COUNT" = "2" ] && [ "$STORY_COUNT" -gt 0 ] && \
   [ "$HAS_CRITERIA" = "True" ] && [ "$BYTE_SIZE" -lt 10240 ] && [ "$NO_EXTRA_FIELDS" = "none" ]; then
  pass "releases-compact: correct structure, criteria fields present, no extra fields, under 10KB (${BYTE_SIZE}B)"
else
  fail "releases-compact failed: ms=$MS_ID epics=$EPIC_COUNT stories=$STORY_COUNT criteria=$HAS_CRITERIA size=${BYTE_SIZE}B extra=$NO_EXTRA_FIELDS"
fi

# ---------------------------------------------------------------------------
# --- Fixture: project with ISSUE-NNN taxonomy (current format) ---
FX3="$TMPROOT/project-issue-taxonomy"
mkdir -p "$FX3/.sweetclaude/product/backlog/done"
mkdir -p "$FX3/.sweetclaude/product/roadmap/epics"
mkdir -p "$FX3/.sweetclaude/product/roadmap/milestones"
mkdir -p "$FX3/.sweetclaude/cache"

cat > "$FX3/.sweetclaude/product/roadmap/milestones/MS-001-first-release.md" << 'EOF'
---
id: MS-001
type: milestone
title: "First Release"
status: active
created: 2026-05-21
updated: 2026-05-21
---
EOF

cat > "$FX3/.sweetclaude/product/roadmap/epics/EP-001-core-feature.md" << 'EOF'
---
id: EP-001
type: epic
title: "Core Feature"
status: active
milestone: MS-001
objective: "Deliver the core feature set."
completion_criteria:
  - "Backend complete"
  - "Frontend complete"
depends_on: []
created: 2026-05-21
updated: 2026-05-21
---
EOF

cat > "$FX3/.sweetclaude/product/backlog/ISSUE-001-implement-api.md" << 'EOF'
---
id: ISSUE-001
type: story
title: "Implement API"
status: new
priority: now
effort: m
epic: EP-001
epic_sequence: 1
tags: [backend]
created: 2026-05-21
updated: 2026-05-21
---
EOF

cat > "$FX3/.sweetclaude/product/backlog/ISSUE-002-fix-login-bug.md" << 'EOF'
---
id: ISSUE-002
type: bug-fix
title: "Fix login bug"
status: new
priority: now
effort: s
epic: EP-001
epic_sequence: 2
tags: [auth]
created: 2026-05-21
updated: 2026-05-21
---
EOF

cat > "$FX3/.sweetclaude/product/backlog/ISSUE-003-update-docs.md" << 'EOF'
---
id: ISSUE-003
type: tech-debt
title: "Update documentation"
status: new
priority: soon
effort: s
epic: null
epic_sequence: null
tags: [docs]
created: 2026-05-21
updated: 2026-05-21
---
EOF

cat > "$FX3/.sweetclaude/product/backlog/done/ISSUE-004-setup-ci.md" << 'EOF'
---
id: ISSUE-004
type: tech-debt
title: "Set up CI pipeline"
status: done
priority: now
effort: m
epic: EP-001
tags: [infra]
created: 2026-05-20
updated: 2026-05-21
closed_date: 2026-05-21
---
EOF

echo "[16] cache.py --rebuild works with ISSUE-NNN taxonomy"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX3" --rebuild 2>&1)
if [ -f "$FX3/.sweetclaude/cache/roadmap.db" ]; then
  pass "ISSUE-NNN: database created"
else
  fail "ISSUE-NNN: database not found after rebuild"
fi

# ---------------------------------------------------------------------------
echo "[17] cache.py --query backlog returns ISSUE-NNN items"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX3" --query backlog 2>&1)
COUNT=$(echo "$OUTPUT" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || true)
HAS_ISSUE=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(any(i['id']=='ISSUE-001' for i in d))" 2>/dev/null || true)
NO_DONE=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(all(i['id']!='ISSUE-004' for i in d))" 2>/dev/null || true)
if [ "$COUNT" = "3" ] && [ "$HAS_ISSUE" = "True" ] && [ "$NO_DONE" = "True" ]; then
  pass "ISSUE-NNN: backlog has 3 open items, excludes done"
else
  fail "ISSUE-NNN: expected 3 open items, got count=$COUNT has_issue=$HAS_ISSUE no_done=$NO_DONE"
fi

# ---------------------------------------------------------------------------
echo "[18] cache.py --query next-id --prefix ISSUE returns ISSUE-005"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX3" --query next-id --prefix ISSUE 2>&1)
if echo "$OUTPUT" | grep -q '"next_id": "ISSUE-005"'; then
  pass "ISSUE-NNN: next ID is ISSUE-005"
else
  fail "ISSUE-NNN: expected ISSUE-005, got: $OUTPUT"
fi

# ---------------------------------------------------------------------------
echo "[19] cache.py --query active-epic returns EP-001 with ISSUE-NNN taxonomy"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX3" --query active-epic 2>&1)
if echo "$OUTPUT" | grep -q '"id": "EP-001"'; then
  pass "ISSUE-NNN: active epic is EP-001"
else
  fail "ISSUE-NNN: expected EP-001, got: $OUTPUT"
fi

# ---------------------------------------------------------------------------
echo ""
echo "=============================="
echo "Results: $PASSED passed, $FAILED failed"
if [ "$FAILED" -gt 0 ]; then
  echo "SOME TESTS FAILED"
  exit 1
else
  echo "ALL TESTS PASSED"
  exit 0
fi
