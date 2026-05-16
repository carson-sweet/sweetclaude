---
id: STORY-016
type: story
title: User guide for v4.1
status: new
priority: soon
effort: m
epic: EP-001
sprint: null
tags:
- docs
- user-guide
- planning-concepts
- skills-reference
- migration
- v4-phase2
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: null
epic_sequence: 5
---

## Description

As a SweetClaude user upgrading from v3 to v4, I want accurate, up-to-date documentation in `docs/user-guide/` that describes the v4 planning model, all new and changed skills, and the migration path, so that I can understand and use the framework without reading skill source files.

**This story gates the v4.0.0 full release.** v4 must not ship without documentation that reflects its actual behavior. Documentation that describes v3 behavior as if it's v4 is worse than no documentation — it creates false confidence.

### Documents to update or create

**`docs/user-guide/planning-concepts.md`** (exists, ~233 lines as of 2026-05-13)
- Add or update section: v4 data model (typed frontmatter, `docs/product/` directory tree)
- Add or update section: operating modes with enforcement behavior (once STORY-013 ships)
- Add or update section: Status state machine (valid transitions per artifact type, once STORY-015 ships)
- Add or update section: Milestone lifecycle (once STORY-012 ships)
- Confirm all examples reference v4 file paths and status vocabulary
- Remove or archive v3-specific patterns that no longer apply

**`docs/user-guide/skills-reference.md`** (exists)
- Add `sweetclaude:milestones` (once STORY-012 ships)
- Add `sweetclaude:migrate` and `sweetclaude:migrate-diagnose` (Phase 1 skills)
- Update entries for all 10 native-consolidated skills (once STORY-014 ships)
- Remove or mark legacy any v3-only skill entries

**`docs/user-guide/v4-migration.md`** (created in Phase 1 as STORY-040A)
- Verify still accurate post-Phase 2 changes
- Add section: roadmap migration (if users have existing `docs/product/roadmap/` content from prior formats)
- Add section: "what changed in v4.0.0 full release vs beta"

**`docs/user-guide/index.md`** (if it exists)
- Ensure v4 guides are linked and v3-only guides are clearly labeled

### Sequencing

This story cannot close until STORY-012, STORY-013, STORY-014, and STORY-015 are all complete — the docs must describe the shipped behavior, not aspirational behavior. Track the open sections as checklist items below.

## Acceptance Criteria

- [ ] `planning-concepts.md` has an accurate "v4 data model" section describing `docs/product/` tree and typed frontmatter
- [ ] `planning-concepts.md` has an accurate "Operating modes" section describing enforcement behavior for all four modes (written after STORY-013 ships)
- [ ] `planning-concepts.md` has an accurate "Status state machine" section with valid transitions per artifact type (written after STORY-015 ships)
- [ ] `skills-reference.md` includes entries for `sweetclaude:milestones`, `sweetclaude:migrate`, and `sweetclaude:migrate-diagnose`
- [ ] `skills-reference.md` entries for all 10 natively consolidated skills are accurate (updated after STORY-014 ships)
- [ ] `v4-migration.md` includes a "v4.0.0 full release vs beta" section
- [ ] No user-guide page references a file path, skill name, or status value that no longer exists in v4

## Out of scope

- New tutorials or walkthroughs (post-4.0 work)
- Video or screencast documentation
- Non-English localization

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
