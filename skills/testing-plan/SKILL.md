---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:testing-plan
description: "Define and maintain a test strategy for a feature or release. Covers scope, test types, environments, entry/exit criteria, and ownership."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
ls .sweetclaude/testing/plans/TP-*.md 2>/dev/null | wc -l | xargs -I{} echo "PLAN_COUNT={}"
ls .sweetclaude/testing/plans/TP-*.md 2>/dev/null | head -10

source ~/.claude/hooks/sweetclaude/sc-artifact.sh
sc_artifact_query roadmap_item status=in_progress 2>/dev/null
sc_artifact_list release 2>/dev/null
```

# Testing Plan

Define and manage test strategies for features and releases. Arguments: `$ARGUMENTS`

---

## Routing

| Arguments | Operation |
|---|---|
| (empty) or `list` | → **List** all test plans |
| `view <TP-NNN>` | → **View** a test plan |
| `new` | → **Create** a new test plan |
| `update <TP-NNN>` | → **Update** an existing plan |

---

## List

Use shell output above. Present:

```
Test Plans
  TP-001  release   REL-002  v2.1.0 release test plan      draft
  TP-002  feature   RM-005   Bulk export QA                 active
  TP-003  feature   RM-001   Auth SSO integration testing   complete
```

If no plans: "No test plans yet. Run `testing-plan new` to create one."

---

## View

Read `.sweetclaude/testing/plans/<TP-NNN>.md` and present full contents.

---

## New

Ask one question at a time:

**1. Scope — what is being tested?**

"Is this a test plan for a feature, a release, or a standalone area?"
- `feature` — tied to a specific roadmap item or epic
- `release` — covers everything going out in a release
- `area` — standalone area (e.g. auth system, data pipeline) not tied to a specific delivery

If `feature`: "Which roadmap item or epic?" (show active ones from shell output)
If `release`: "Which release?" (show releases from shell output)
If `area`: "Describe the area in one line."

**2. Test types — what kinds of testing apply?**

Present checklist. Ask user to confirm or remove:

```
Applicable test types (remove any that don't apply):
  [x] Unit tests         — individual functions and components
  [x] Integration tests  — service interactions and data flows
  [x] End-to-end tests   — full user journeys
  [ ] Manual QA          — exploratory and scripted manual testing
  [ ] Performance        — load, latency, throughput
  [ ] Security           — auth, injection, data handling
  [ ] Accessibility      — keyboard, screen reader, contrast
  [ ] Contract tests     — API contract verification (if external consumers)
```

**3. Environments**

"Which environments will testing run in?"
- local, CI, staging, production (or custom)

For each environment: what test types run there?

**4. Entry criteria**

"What must be true before testing starts?"

Defaults (accept or adjust):
- Feature branch merged to staging
- All unit and integration tests passing in CI
- Smoke test passing in test environment
- Test data seeded

**5. Exit criteria**

"What must be true before testing is considered complete?"

Defaults (accept or adjust):
- All planned test cases executed
- No open P0 or P1 bugs
- Performance within defined thresholds (if applicable)
- Security review complete (if applicable)
- Accessibility WCAG 2.1 AA (if applicable)

Challenge if exit criteria are vague. "No critical bugs" is not measurable — "No open P0 or P1 issues" is.

**6. Ownership**

"Who is responsible for each test type?" (solo dev: "me" is fine)

**7. Out of scope**

"What are you explicitly NOT testing here? Minimum one item."

---

## Write plan

Assign TP-NNN (next sequential from existing plans).

```bash
mkdir -p .sweetclaude/testing/plans/
```

Write `.sweetclaude/testing/plans/TP-NNN.md`:

```markdown
---
id: TP-NNN
scope_type: feature | release | area
scope_ref: RM-NNN | REL-NNN | area description
status: draft
created_at: YYYY-MM-DD
---

# TP-NNN — {title}

## Scope
{scope description}

## Test Types
{confirmed test types with environments}

## Environments
{environment → test types mapping}

## Entry Criteria
{list}

## Exit Criteria
{list}

## Ownership
{list}

## Out of Scope
{list}
```

Confirm: `Created TP-NNN — {title}`

---

## Update

Read current plan. Show current content. Ask: "What's changing?"

Apply change, increment a `updated_at` field. Confirm.

---

## Rules

- Exit criteria must be evaluable as true/false. Challenge vague criteria ("good quality", "no major bugs") before accepting.
- A test plan with no exit criteria is not a test plan — it is a wish list.
- Out of scope is required. At least one item. It prevents testing sessions from expanding indefinitely.
- `status: complete` means exit criteria have been met — not that testing has been attempted.
