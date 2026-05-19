---
id: BL-008
title: Decide priorities for verified-clean syncog skill builds
priority: P2
status: backlog
created: 2026-05-01
---

## Summary

14 source skills from the syncog skills corpus passed verification as genuinely new with clean scope. PRDs and user stories are already written and live in `/Users/carsonsweet/dev/syncog-skills-corpus/{slug}/specs/`.

These skills fill real gaps in SweetClaude's pipeline — particularly the deferred `deploy/` bucket, security planning, external integrations, infrastructure changes, the mockup pipeline, init/adopt, and meta tooling.

User decision deferred per "I don't want to get into it now."

## The keepers — Plan 3 (named planned skills with fallbacks already routed in find-skill)

| Skill | Source spec dir | Replaces fallback |
|---|---|---|
| `sweetclaude:deploy-ship` | `/syncog-skills-corpus/deployment/specs/` | First skill in deferred deploy/ bucket |
| `sweetclaude:something-broke` | `/syncog-skills-corpus/diagnostics/specs/` | currently `code-issue` |
| `sweetclaude:dependency-upgrade` | `/syncog-skills-corpus/package-management/specs/` | currently `code-debt` |
| `sweetclaude:security-planning` | `/syncog-skills-corpus/threat_modeling/specs/` | currently `product-discovery` |
| `sweetclaude:data-migration` | `/syncog-skills-corpus/database/specs/` | currently `code-debt` |
| `sweetclaude:external-integration` | `/syncog-skills-corpus/integrations/specs/` + `external_apis/specs/` | currently `code-feature` |
| `sweetclaude:infrastructure-change` | `/syncog-skills-corpus/design-infra-design/specs/` | currently `code-debt` |
| `sweetclaude:init` | `/syncog-skills-corpus/init/specs/` | currently handled inside `on` |
| `sweetclaude:adopt` | `/syncog-skills-corpus/sherpa-adopt/specs/` | currently handled inside `on` (existing-project path) |

## The keepers — Plan 2 (new additions, not previously planned)

| Skill | Source spec dir |
|---|---|
| `sweetclaude:design-exploration` | `/syncog-skills-corpus/design-exploration/specs/` |
| `sweetclaude:follow-up-tasks` | `/syncog-skills-corpus/follow-up-tasks/specs/` |
| `sweetclaude:skill-authoring` | `/syncog-skills-corpus/skill-authoring/specs/` |
| `sweetclaude:skill-creator` | `/syncog-skills-corpus/skill-creator/specs/` |
| `sweetclaude:post-merge-setup` | `/syncog-skills-corpus/post_merge_setup/specs/` |
| `sweetclaude:mockup-sandbox` | `/syncog-skills-corpus/mockup-sandbox/specs/` |
| `sweetclaude:mockup-extract` | `/syncog-skills-corpus/mockup-extract/specs/` |
| `sweetclaude:mockup-graduate` | `/syncog-skills-corpus/mockup-graduate/specs/` |

## Enhancements (not new skills)

| Source | Target skill |
|---|---|
| `validation` | enhancement to `sweetclaude:code-testing` (adds persistent command registry) |
| `sherpa-start` | enhancement to `sweetclaude:on` (adds deep commercial start path) |
| `environment-secrets` | cross-cutting enforcement across `code-review`, `fix-sweetclaude`, `external-integration`, `on` |

## Decisions needed

1. Prioritize the 9 Plan 3 skills against current SweetClaude roadmap (`deploy/` bucket is highest-leverage gap; `init`/`adopt` are referenced everywhere but missing)
2. Prioritize the 8 Plan 2 skills (mockup pipeline is a natural 3-stage chunk; meta tooling is decoupled)
3. Decide whether the 3 enhancements ride along with their target skills' next update or get their own work item
4. For the mockup pipeline (sandbox → extract → graduate): build all 3 together or stage them?

## References

- Verification report: `/Users/carsonsweet/.claude/plans/delegated-forging-lerdorf.md`
- Inventory file: `/Users/carsonsweet/dev/syncog-skills-corpus/specs/inventory.md`
- Source specs: `/Users/carsonsweet/dev/syncog-skills-corpus/{slug}/specs/`

## Connection to other backlog items

- BL-005 (duplicates) — sibling cleanup
- BL-007 (partial overlaps) — different decision class
- BL-009 (find-skill routing bug) — `concept-framing` routing fix bundled with this work
