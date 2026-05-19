---
id: BL-010
title: Improve spec-writer agent briefings to detect mode consolidations
priority: P3
status: backlog
created: 2026-05-01
---

## Summary

A round of 8 parallel spec-writer agents produced 76 spec files (PRDs + user stories) for 38 syncog corpus skills. ~18 of those specs proposed skills that already exist as `$ARGUMENTS`-routed modes inside consolidated SweetClaude skills (`document-corpus`, `code-testing`).

Root cause: the briefings instructed agents to read existing skill *frontmatter* and *titles* but did not require reading skill *bodies*. Mode routing lives deep in skill body text (e.g., line 37 of `document-corpus`: *"If `$ARGUMENTS` was passed (e.g. `/sweetclaude:document-corpus triage`), skip the menu and route directly."*). Agents matched by skill directory name and missed the embedded modes.

Cost: roughly half the inventory was wrong, requiring a separate verification round to catch.

## Proposed briefing improvements

When spec-writer agents are launched against an unfamiliar skill set, the briefing should require:

1. **Read full text of every existing SweetClaude skill in the same domain bucket.** Not just the proposed-skill match — the entire bucket. Mode routing is invisible from outside.
2. **Grep for primary verbs/modes within skill bodies, not just slugs.** Example: before claiming "no skill exists for triage," grep `/sweetclaude/skills/*/SKILL.md` for `triage`, not just `ls skills/ | grep triage`.
3. **Flag any `$ARGUMENTS` mode-routing lines as evidence of consolidated skills.** Pattern: `If $ARGUMENTS was passed`, `route directly`, `skip the menu and route`. These are the architectural signals of a multi-mode skill.
4. **Compare against existing skill *menu sections*.** Several skills (`code-testing`, `code-review`, `document-corpus`) open with a numbered menu of internal modes. Reading just the first 30 lines of each existing skill in the bucket catches most consolidations.

## Decision needed

Before the next batch of spec-writer agents runs, update the briefing template to enforce the four checks above. Could be encoded as a checklist the agent must complete and return as part of its output.

## References

- Verification report: `/Users/carsonsweet/.claude/plans/delegated-forging-lerdorf.md`
- Example consolidations missed: `/Users/carsonsweet/dev/sweetclaude/skills/document-corpus/SKILL.md` (6 modes), `/Users/carsonsweet/dev/sweetclaude/skills/code-testing/SKILL.md` (4 modes)

## Connection to other backlog items

- BL-005 (duplicates) — direct consequence of this gap
- BL-006 (stale design doc) — exacerbating factor; agents trusted doc claims
