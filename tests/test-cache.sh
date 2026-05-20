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

# --- Fixture: project with stories, epics, releases ---
FX="$TMPROOT/project"
mkdir -p "$FX/docs/product/backlog/stories/done"
mkdir -p "$FX/docs/product/backlog/bugs"
mkdir -p "$FX/docs/product/backlog/chores"
mkdir -p "$FX/docs/product/roadmap/epics"
mkdir -p "$FX/docs/product/roadmap/releases"
mkdir -p "$FX/.sweetclaude/cache"

cat > "$FX/docs/product/roadmap/releases/REL-001-v41.md" << 'EOF'
---
id: REL-001
type: release
title: "v4.1"
status: active
version: "4.1"
created: 2026-05-15
updated: 2026-05-15
---
EOF

cat > "$FX/docs/product/roadmap/epics/EP-001-workflow-engine.md" << 'EOF'
---
id: EP-001
type: epic
title: "Workflow Engine"
status: active
release: REL-001
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

cat > "$FX/docs/product/roadmap/epics/EP-002-release-primitive.md" << 'EOF'
---
id: EP-002
type: epic
title: "Release Primitive"
status: new
release: REL-001
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

cat > "$FX/docs/product/backlog/stories/STORY-020-upfront-assessment.md" << 'EOF'
---
id: STORY-020
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

cat > "$FX/docs/product/backlog/stories/STORY-018-phase-status-table.md" << 'EOF'
---
id: STORY-018
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

cat > "$FX/docs/product/backlog/stories/STORY-015-model-enforcement.md" << 'EOF'
---
id: STORY-015
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

cat > "$FX/docs/product/backlog/stories/done/STORY-010-horizon-taxonomy.md" << 'EOF'
---
id: STORY-010
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

cat > "$FX/docs/product/backlog/stories/STORY-011-roadmap-system.md" << 'EOF'
---
id: STORY-011
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

cat > "$FX/docs/product/backlog/bugs/BUG-005-cache-test-bug.md" << 'EOF'
---
id: BUG-005
type: bug
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
# Should be STORY-020 (seq 1), STORY-018 (seq 2), STORY-015 (seq 3)
FIRST=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['id'])" 2>/dev/null)
SECOND=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[1]['id'])" 2>/dev/null)
THIRD=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[2]['id'])" 2>/dev/null)
if [ "$FIRST" = "STORY-020" ] && [ "$SECOND" = "STORY-018" ] && [ "$THIRD" = "STORY-015" ]; then
  pass "stories in sequence order: 020, 018, 015"
else
  fail "wrong order: $FIRST, $SECOND, $THIRD"
fi

# ---------------------------------------------------------------------------
echo "[5] cache.py --query epic-stories excludes done stories by default"
# Mark STORY-020 as done in file and rebuild
sed -i.bak 's/status: new/status: done/' "$FX/docs/product/backlog/stories/STORY-020-upfront-assessment.md"
python3 "$CACHE_PY" --project-dir "$FX" --rebuild >/dev/null 2>&1
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query epic-stories --epic EP-001 2>&1)
COUNT=$(echo "$OUTPUT" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null)
if [ "$COUNT" = "2" ]; then
  pass "done stories excluded (2 remaining)"
else
  fail "expected 2 stories, got $COUNT"
fi
# Restore
mv "$FX/docs/product/backlog/stories/STORY-020-upfront-assessment.md.bak" "$FX/docs/product/backlog/stories/STORY-020-upfront-assessment.md"
python3 "$CACHE_PY" --project-dir "$FX" --rebuild >/dev/null 2>&1

# ---------------------------------------------------------------------------
echo "[6] cache.py --query backlog returns items sorted by priority"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query backlog 2>&1)
# now items should come before soon items
FIRST_PRI=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['priority'])" 2>/dev/null)
if [ "$FIRST_PRI" = "now" ]; then
  pass "backlog sorted by priority (now first)"
else
  fail "expected first item priority=now, got: $FIRST_PRI"
fi

# ---------------------------------------------------------------------------
echo "[7] cache.py --query backlog excludes done items"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query backlog 2>&1)
HAS_DONE=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(any(i['id']=='STORY-010' for i in d))" 2>/dev/null)
if [ "$HAS_DONE" = "False" ]; then
  pass "done items excluded from backlog"
else
  fail "STORY-010 (done) appeared in backlog"
fi

# ---------------------------------------------------------------------------
echo "[8] cache.py --query next-id --prefix STORY returns max+1"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query next-id --prefix STORY 2>&1)
if echo "$OUTPUT" | grep -q '"next_id": "STORY-021"'; then
  pass "next story ID is STORY-021"
else
  fail "expected STORY-021, got: $OUTPUT"
fi

# ---------------------------------------------------------------------------
echo "[9] cache.py --query next-id --prefix BUG returns max+1"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query next-id --prefix BUG 2>&1)
if echo "$OUTPUT" | grep -q '"next_id": "BUG-006"'; then
  pass "next bug ID is BUG-006"
else
  fail "expected BUG-006, got: $OUTPUT"
fi

# ---------------------------------------------------------------------------
echo "[10] cache.py --query releases returns hierarchy"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query releases 2>&1)
REL_ID=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['id'])" 2>/dev/null)
EPIC_COUNT=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d[0]['epics']))" 2>/dev/null)
if [ "$REL_ID" = "REL-001" ] && [ "$EPIC_COUNT" = "2" ]; then
  pass "REL-001 has 2 epics"
else
  fail "expected REL-001 with 2 epics, got rel=$REL_ID epics=$EPIC_COUNT"
fi

# ---------------------------------------------------------------------------
echo "[11] cache.py --query epic-stories --epic EP-001 --include-done includes done stories"
sed -i.bak 's/status: new/status: done/' "$FX/docs/product/backlog/stories/STORY-020-upfront-assessment.md"
python3 "$CACHE_PY" --project-dir "$FX" --rebuild >/dev/null 2>&1
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query epic-stories --epic EP-001 --include-done 2>&1)
COUNT=$(echo "$OUTPUT" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null)
if [ "$COUNT" = "3" ]; then
  pass "include-done returns all 3 stories"
else
  fail "expected 3 stories with include-done, got $COUNT"
fi
mv "$FX/docs/product/backlog/stories/STORY-020-upfront-assessment.md.bak" "$FX/docs/product/backlog/stories/STORY-020-upfront-assessment.md"
python3 "$CACHE_PY" --project-dir "$FX" --rebuild >/dev/null 2>&1

# ---------------------------------------------------------------------------
echo "[12] cache.py --query tags returns items by tag"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query tags --tag workflow 2>&1)
COUNT=$(echo "$OUTPUT" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null)
if [ "$COUNT" = "3" ]; then
  pass "3 items tagged 'workflow'"
else
  fail "expected 3 items with tag=workflow, got $COUNT"
fi

# ---------------------------------------------------------------------------
echo "[13] cache.py handles missing roadmap directory gracefully"
FX2="$TMPROOT/project-no-roadmap"
mkdir -p "$FX2/docs/product/backlog/stories"
mkdir -p "$FX2/.sweetclaude/cache"
cat > "$FX2/docs/product/backlog/stories/STORY-001-test.md" << 'STEOF'
---
id: STORY-001
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
echo "[15] cache.py --query releases-compact returns compact hierarchy under 10KB"
OUTPUT=$(python3 "$CACHE_PY" --project-dir "$FX" --query releases-compact 2>&1)
REL_ID=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['id'])" 2>/dev/null)
EPIC_COUNT=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d[0]['epics']))" 2>/dev/null)
STORY_COUNT=$(echo "$OUTPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d[0]['epics'][0]['stories']))" 2>/dev/null)
HAS_CRITERIA=$(echo "$OUTPUT" | python3 -c "import sys,json; ep=json.load(sys.stdin)[0]['epics'][0]; print('criteria_done' in ep and 'criteria_total' in ep)" 2>/dev/null)
BYTE_SIZE=$(echo -n "$OUTPUT" | wc -c | tr -d ' ')
NO_EXTRA_FIELDS=$(echo "$OUTPUT" | python3 -c "
import sys,json
data = json.load(sys.stdin)
ep = data[0]['epics'][0]
allowed = {'id','title','status','criteria_done','criteria_total','stories'}
extra = set(ep.keys()) - allowed
print('none' if not extra else ','.join(sorted(extra)))
" 2>/dev/null)
if [ "$REL_ID" = "REL-001" ] && [ "$EPIC_COUNT" = "2" ] && [ "$STORY_COUNT" -gt 0 ] && \
   [ "$HAS_CRITERIA" = "True" ] && [ "$BYTE_SIZE" -lt 10240 ] && [ "$NO_EXTRA_FIELDS" = "none" ]; then
  pass "releases-compact: correct structure, criteria fields present, no extra fields, under 10KB (${BYTE_SIZE}B)"
else
  fail "releases-compact failed: rel=$REL_ID epics=$EPIC_COUNT stories=$STORY_COUNT criteria=$HAS_CRITERIA size=${BYTE_SIZE}B extra=$NO_EXTRA_FIELDS"
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
