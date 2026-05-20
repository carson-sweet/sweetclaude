---
id: DEBT-001
type: debt
title: Architectural rule — every "✓ done" report must follow an explicit verification step
status: new
priority: later
effort: s
epic: null
milestone: null
sprint: null
tags: [architecture, pattern, success-reporting, verification, framework-discipline]
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: null
---

## Description

BUG-002 was the second "framework claims success while state is broken" defect in the 3.68.x series:

- **3.68.0:** `ensure-global-hooks.py` reported "registered" while writing literal `${CLAUDE_PLUGIN_ROOT}` strings that don't resolve in settings.json
- **3.68.2:** `sweetclaude:update` reported "✓ Drift: none in this project" while the marker check it relied on was structurally divorced from the runner that produced the data

Both were caused by the same anti-pattern: **a "done" message printed without a verification step that actually checks the post-condition.**

The 3.68.3 fix restructured update Step 6 → 6 + 6c so the success report is structurally gated on verification. But that's a one-off fix for one flow. The underlying problem — that other skills and scripts emit success reports without verification — is unaddressed.

**Origin:** Identified during BUG-002 work. The pattern was named explicitly in the 3.68.3 commit message: "the original BUG-002 was 'report printed before verification'; the new bug is..."

## Severity

`later` priority. This is preventive architectural debt — addressing it prevents the next bug in this family, but doesn't fix anything currently broken. The 3.68.3 fix already eliminated the specific instance.

## Proposed approach

Two parts:

**1. Documented rule** in framework-internal docs (e.g. `docs/internal/framework-discipline.md` or a new section in CONTRIBUTING):

> Any user-facing "✓ done" / "complete" / "success" / "updated" message must immediately follow a verification step that checks the post-condition. The message and the check live in the same skill step, and the check must use the AUTHORITATIVE data source (e.g. runner stdout, not derived marker files; live filesystem state, not cached lookups).
>
> If a skill cannot verify the post-condition cheaply, it must say "submitted" / "queued" / "requested" — never "done."

**2. Lint/audit** that flags skill files containing success-report patterns (`✓`, `═══`, "complete", "updated") without an adjacent verification step. Run in CI or as part of `_health`. False positives are acceptable — the goal is to surface the pattern for review.

## Acceptance Criteria

- [ ] Framework-discipline rule is documented and discoverable to contributors
- [ ] Lint exists (CI or `_health`) that flags skill files with success-report patterns lacking adjacent verification
- [ ] Existing skills are audited against the rule; violations filed as separate tickets
- [ ] The rule is referenced in the post-mortem section of any future "framework lied about success" bug

## Out of scope

- Refactoring every existing skill that violates the pattern (file individual tickets as found)
- Runtime enforcement (this is a code-review-time and CI-time rule, not a runtime guard)

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
