---
id: BUG-006
type: bug
title: project-gh-import-issues and project-gh-sync-issues missing v4 migration guards
status: new
priority: soon
effort: s
epic: EP-001
epic_sequence: 7
milestone: null
sprint: null
tags: [v4, skills, migration-guard, ep-008-5]
origin: manual
created: 2026-05-13
updated: 2026-05-16
closed_date: null
---

## Description

The May 11 v4 assessment item B4 required: "every v4 skill rewritten in EP-005 needs an entry guard that surfaces the same hard-stop message if v3 BL files are still present at the configured product_base."

The 37350ed commit added the guard to:
- `skills/project-backlog/SKILL.md` ✓
- `skills/project-issues/SKILL.md` ✓
- `skills/project-backlog-triage/SKILL.md` ✓

But missed:
- `skills/project-gh-import-issues/SKILL.md` ✗
- `skills/project-gh-sync-issues/SKILL.md` ✗

Both jump straight into Python that reads `docs/product/backlog/INDEX.md`. On a pre-migration v3 project, the INDEX doesn't exist — they'd crash with FileNotFoundError or worse, write half-state into a directory the user didn't expect.

**Origin:** Surfaced during EP-008.5 STORY-046 work (cross-skill validation).

## Severity

`soon` priority. Real bug, narrow user population (anyone running the gh skills on a pre-migration v3 project), bounded fix.

## Proposed fix

Copy the migration guard block verbatim from `skills/project-backlog/SKILL.md` lines ~7–28 into the top of each affected skill, before any Python or other operations.

The guard block:
```bash
## MIGRATION GUARD

Before any other work, check for unmigrated v3 BL files:

\`\`\`bash
PRODUCT_BASE=$(python3 -c "
import yaml, pathlib
p = pathlib.Path('.sweetclaude/state/artifact-privacy.yaml')
if p.exists():
    d = yaml.safe_load(p.read_text()) or {}
    base = d.get('categories', {}).get('product', {}).get('base_path', '')
    if base:
        print(base.rstrip('/'))
        exit()
print('.sweetclaude/product')
" 2>/dev/null || echo '.sweetclaude/product')
V3_FILES=$(find "${PRODUCT_BASE}/backlog" -maxdepth 1 -name 'BL-*.md' 2>/dev/null | wc -l | tr -d ' ')
if [ "$V3_FILES" -gt 0 ]; then
  echo "This project has $V3_FILES v3 stories that need to be migrated first."
  echo "Run: /sweetclaude:migrate"
  exit 1
fi
\`\`\`

If the guard fires: print the message and stop. Do not proceed.
```

Same text as the other three; identical behavior; trivial copy-paste.

## Acceptance Criteria

- [ ] `project-gh-import-issues/SKILL.md` has the migration guard at the top
- [ ] `project-gh-sync-issues/SKILL.md` has the migration guard at the top
- [ ] `tests/test-ep-008-5-verifications.sh` (when written) covers the guard firing for all five skills (project-backlog, project-issues, project-backlog-triage, project-gh-import-issues, project-gh-sync-issues)

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
