---
closed_date: '2026-05-13'
created: 2026-05-13
effort: s
epic: null
id: DEBT-002
milestone: null
origin: manual
priority: later
sprint: null
status: done
tags:
- state-management
- dual-source-of-truth
- architecture
title: paths.product_base has two sources of truth (artifact-privacy.yaml + session-state.yaml)
type: debt
updated: 2026-05-13
---

## Description

The product_base path (where user product artifacts live: `.sweetclaude/product` vs `docs/product`) is recorded in TWO places:

1. `.sweetclaude/state/artifact-privacy.yaml` → `categories.product.base_path`
2. `.sweetclaude/state/session-state.yaml` → `paths.product_base`

The session-state file is regenerated each session (it's a pre-loaded state for skills). But the artifact-privacy.yaml is the source of truth that user-driven configuration writes to.

**Origin:** May 11 v4 assessment item D5. Carried forward.

## Why this matters

- If the two diverge, downstream skills don't know which to trust.
- The session-state regeneration logic must read from artifact-privacy.yaml and write to session-state.yaml. If it ever reverses (writes to artifact-privacy via session-state), the source of truth flips and breaks the model.
- Currently the migrate skill and bootstrap Step 5b both read from artifact-privacy.yaml directly (consistent). But the `/sweetclaude:go` skill's pre-loaded state header reads from session-state. If a skill makes decisions based on session-state's snapshot but artifact-privacy has been mutated by another skill, results diverge.

## Severity

`later` priority. No user-visible bug today — the session-state regeneration correctly mirrors artifact-privacy. But it's architectural debt that will bite the next time someone touches the regen logic.

## Proposed fix

Pick one authoritative source. Recommended:

1. **artifact-privacy.yaml is authoritative.** session-state.yaml is a read-only derived snapshot for skill-prelude consumption only.
2. Document this in `hooks/generate-session-state.sh` header: "READS artifact-privacy.yaml, DERIVES session-state.yaml. NEVER write back to artifact-privacy from this hook."
3. Add a `_health` check that compares the two values on every session start and warns if they diverge.

## Acceptance Criteria

- [ ] Documentation in `hooks/generate-session-state.sh` declares artifact-privacy.yaml as authoritative
- [ ] `_health` check flags `paths.product_base` mismatch between the two files
- [ ] No skill writes to `session-state.yaml` directly — only the regeneration hook produces it

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
