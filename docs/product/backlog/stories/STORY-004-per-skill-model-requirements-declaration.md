---
id: STORY-004
type: story
title: Per-skill model requirements declaration — reasoning level frontmatter for all skills
status: new
priority: later
effort: l
epic: null
milestone: null
sprint: null
tags: [skills, model-routing, metadata, documentation, reasoning]
origin: manual
created: 2026-05-13
updated: 2026-05-15
closed_date: null
---

## Description

As a SweetClaude user, I want every skill to declare the minimum model capability it requires — and why — so that I can route each skill invocation to the appropriately-capable (and cost-appropriate) model without guessing.

**Origin:** Filed 2026-05-13 by Carson Sweet. Derived from a multi-hour MS-003 replanning session where every step ran on Opus because there was no signal to drop to Sonnet — even the mechanical bits (file listing, state rendering, CRUD operations).

**The gap today:** SweetClaude has ~100 skills. Each is invoked at whatever model the user happens to be on. There is no signal that says "this skill needs reasoning capability X" or "this skill is mechanical and a small model is fine."

**This is the prerequisite for STORY-005** (model-aware skill execution spike). STORY-005 cannot ship without this data.

### Proposed: `requires:` block in skill frontmatter

Add a `requires:` block to every skill's frontmatter (or to a sidecar manifest):

```yaml
requires:
  reasoning: high | medium | low
  reasoning_rationale: "one-sentence why"
  context_window: small | medium | large
  output_complexity: structured-artifact | narrative | tool-call-sequence
```

`reasoning: high` = skill makes non-obvious decisions that affect downstream artifacts
`reasoning: medium` = follows a process with judgment calls
`reasoning: low` = mechanical CRUD against state

### Proposed classification (from the filed enhancement request)

**`reasoning: high` — Opus-grade or equivalent**

| Skill | Rationale |
|---|---|
| `design-architecture` | System decomposition under multi-axis constraints; tradeoff selection between non-comparable options |
| `design-tech-spec` | Producing specs that survive Sonnet implementation requires anticipating edge cases the spec must constrain |
| `design-api-design` | Contract design where small word choices propagate into wide blast radii |
| `design-data-model` | Schema decisions with denormalization tradeoffs and migration-path implications |
| `design-solutioning-gate` | Multi-criteria comparison under uncertainty, with go/no-go consequence |
| `design-change-impact-analysis` | Graph traversal + judgment on which effects matter |
| `design-ux-review` | Multi-perspective synthesis with aesthetic judgment |
| `design-manage-decisions` | ADR rationale must hold up to later challenge; framing is hard |
| `epic-design` | Story-list ordering under dependency + risk + capability constraints |
| `caucus` | Multi-perspective deliberation by design |
| `reasoning-frameworks` | The skill is reasoning |
| `ultraplan` | The skill is heavy planning |
| `plan-wave-sequencing` (STORY-003, proposed) | Dependency-graph reasoning + classification + sequencing |
| `product-positioning-statement` | Strategic framing; surface-level answers are wrong answers |
| `product-brief` / `product-prd` | Discovery-phase depth requires probing, gap-finding, challenge |
| `product-discovery` | Same — early-phase depth is the value |
| `product-competition` | Structured competitive analysis with synthesis |
| `product-roadmap-analysis` | RICE-style multi-criteria scoring |
| `product-user-personas` | Persona depth determines downstream quality |
| `product-user-stories` | Story scoping requires judgment about what to cleave vs combine |
| `product-user-tdd-tests` | Gherkin authoring is hard to do well |
| `design-user-flows` | Flow design carries product-level decisions |
| `design-wireframes` | UX judgment under constraints |

**`reasoning: medium` — Sonnet-grade appropriate**

| Skill | Rationale |
|---|---|
| `code-feature` / `code-issue` / `code-debt` | TDD against a locked spec; design is done, work is disciplined execution |
| `code-tdd` | Same |
| `code-testing` / `code-verify` | Structured execution |
| `code-review` | Pattern-matching against known antipatterns; high recall achievable at medium reasoning |
| `testing-plan` / `testing-session` / `testing-accessibility` / `testing-performance` / `testing-compliance` / `testing-security` | Defined methodology with judgment in finding triage |
| `documents-update-docs` | Disciplined editing against a change-set |
| `corpus-reconcile` / `corpus-consolidate` / `corpus-triage` / `corpus-promote` | Pipeline mechanics with classification judgment |
| `project-backlog-triage` | Classification with light judgment |

**`reasoning: low` — Haiku-grade appropriate**

| Skill | Rationale |
|---|---|
| `status` / `recap` / `big-picture` / `_health` | Read-only state surfaces; rendering known data |
| `help` / `find-skill` / `_route` | Classification against a known skill set |
| `project-issues` / `project-sprints` / `project-themes` / `project-epics` / `product-milestones` (CRUD invocations) | List/create/update CRUD against state files |
| `project-gh-import-issues` / `project-gh-sync-issues` | Mechanical sync |
| `project-backlog` (listing) | Reading and rendering |
| `corpus-status` / `corpus-rag-reindex` | Pipeline ops; no decisions |
| `fix-sweetclaude` / `setup` / `init` / `_migrate` | Mechanical configuration |
| `usage` / `_features` | Configuration display |
| `purge` / `hibernate` / `off` | Mechanical lifecycle |

Note: some skills are mixed-use — the right answer for those is `medium` with a `high`-reasoning sub-step declaration.

## Acceptance Criteria

- [ ] Every skill in the framework has a `requires.reasoning` declaration with a one-sentence rationale in its frontmatter (or sidecar manifest)
- [ ] The classification is documented in a single browsable index (`skills/REASONING-INDEX.md` or equivalent) that lists all skills, their reasoning level, and rationale
- [ ] `sweetclaude:help` surfaces the reasoning level for a skill when asked (e.g. `/sweetclaude:help design-architecture` shows `reasoning: high — System decomposition under multi-axis constraints`)
- [ ] The `requires:` block schema is documented so maintainers know how to classify new skills

## Sprint History

| Sprint | Added | Removed | Outcome |
|---|---|---|---|
