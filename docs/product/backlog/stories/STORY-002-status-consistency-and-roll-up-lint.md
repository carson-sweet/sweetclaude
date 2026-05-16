---
id: STORY-002
type: story
title: Status consistency — canonical vocabulary, roll-up lint, and propagation prompts
status: new
priority: soon
effort: l
epic: EP-002
sprint: null
tags:
- health
- big-picture
- status
- lint
- hierarchy
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: null
epic_sequence: 4
---

## Description

As a user running `big-picture`, `status`, or `recap`, I want the project view to reflect coherent, trustworthy state across the milestone → epic → backlog hierarchy, so that I don't have to manually audit files to determine whether the displayed state is real.

**Observed in `~/dev/syncog` (mid-MS-003, v3.52.14):**
- `big-picture` showed BL-082 unchecked under a ✓ milestone because its status was `closed` (a valid but unrecognized synonym)
- Five epics remained `active` with every member BL done and parent milestones complete — nothing prompted to close them
- Two epics had no BLs but were bound to MS-003 — back-reference gaps are unrecoverable from artifacts alone
- Milestone files used three different "done" words (`complete`, `achieved`, `done`); `closed` is not recognized
- Some BLs use markdown `**Status:**`, others use YAML frontmatter `status:` — parsers cope but authoring is ambiguous

The framework has a coherent artifact model and parseable files. The gap is in the maintenance loop: nothing closes the gap between "this BL is done" and "this epic/milestone should also be done."

**Five proposed changes (filed 2026-05-13 by Carson Sweet):**

1. **Canonical status vocabulary** — define one set per artifact type, map legacy synonyms on read, emit a one-time migration nudge per stale file
2. **Roll-up lint in `_health`** — flag: done milestone with open BLs/epics; active epic with all BLs done; back-reference mismatches between BL `Epic:` field and epic `Issues` section; informational only, not blocking
3. **Propagation prompts** — when closing the last open BL in an epic, prompt to close the epic; same when closing the last epic in a milestone; same in reverse on reopen
4. **Renderer hardening** — `big-picture` recognizes `closed` as a done synonym; logs `WARN:` for unrecognized status values instead of silent fallback; applies same status mapping to epics as to BLs
5. **Format consistency check** — `_health` flags projects mixing markdown `**Status:**` and YAML `status:` and offers to normalize

## Acceptance Criteria

- [ ] A project with BL-082 at `status: closed`, five `active`-but-done epics, and mixed milestone vocabulary runs `sweetclaude:_health` and sees every drift item listed with a specific suggested remedy
- [ ] A user closing the final open BL in an epic is prompted to close the epic in the same skill invocation (no separate step required)
- [ ] `big-picture` renders a BL with `status: closed` as ✓ with no other code changes needed
- [ ] Framework documentation declares canonical status values per artifact type, and the documentation matches what parsers treat as canonical (not merely tolerate as legacy)
- [ ] Unrecognized status values produce a visible `WARN:` in `big-picture` output rather than silently rendering as open

## Out of scope

- Renaming existing status vocabulary in-place across all projects (disruptive, low value — legacy mapping is sufficient)
- Hard gates blocking phase advancement on roll-up coherence (informational only)
- Back-reference reconstruction from git history

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
