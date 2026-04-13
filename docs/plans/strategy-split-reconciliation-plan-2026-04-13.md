# Strategy Split Reconciliation Plan — 2026-04-13

**Goal:** Bring the SweetClaude repo in sync with the installed state at `~/.claude/`, then complete the remaining strategy-track work from the design spec.

**Design spec:** `docs/strategy-split-design-v1-2026-04-13.md`
**Product brief:** `docs/strategy-split-brief-v1-2026-04-13.md`
**Original restructure plan:** `docs/strategy-split-restructure-plan-2026-04-13.md`

---

## Current Situation

The design spec was partially executed directly on `~/.claude/` during a sweet-crm session but never committed to the SweetClaude repo. The repo is now behind the installed state in every dimension:

| Area | Repo State | Installed State |
|---|---|---|
| Skill directory | Flat (all skills at root) | Reorganized: `code/`, `strategy/`, `shared/`, `parked/` |
| phase-skills.yaml | Single `phases:` key | Dual-track: `code:` + `strategy:` |
| Skill frontmatter | Old names (`sweetclaude-tdd`) | Namespaced (`sweetclaude-code-tdd`) |
| phase-gates.md | Code-only, no strategy note | Strategy-track note added, skill refs updated |
| Master SKILL.md | No track concept | Dual-track routing, strategy work types |
| Work router | 4 code work types | 4 code + 7 strategy work types, backlog guard |
| Init skill | Single scenario | Three scenarios (code+strategy, code-only, strategy-only) |
| Hibernate skill | Does not exist | Built and working |
| Strategy skills | Do not exist | `strategy/academic` and `strategy/reconciliation` built |

---

## Phase A: Sync Repo to Installed State

Capture everything that was built live into the repo so the repo becomes the source of truth. Pure file operations — no new design work.

### A1: Restructure framework/skills/ directory

Move existing skills into `code/` subdirectory. Create `strategy/`, `shared/`, `parked/` directories.

**From:**
```
framework/skills/
  SKILL.md, auto-docs/, discover-deep/, fix-issue/, gherkin-bridge/,
  init/, mutation-testing/, notion-scaffold/, pr-ready/, ripple/,
  scope-tracker/, tdd/, work-router/
```

**To:**
```
framework/skills/
  SKILL.md                    # Master router (update from installed)
  discover-deep/              # Stays at root (orchestration)
  work-router/                # Stays at root (orchestration)
  init/                       # Stays at root (orchestration)
  hibernate/                  # NEW — copy from installed
  code/
    auto-docs/
    fix-issue/
    gherkin-bridge/
    mutation-testing/
    pr-ready/
    ripple/
    scope-tracker/
    tdd/
  strategy/
    academic/                 # NEW — copy from installed
    reconciliation/           # NEW — copy from installed
  shared/
    README.md                 # NEW — copy from installed
  parked/
    notion-scaffold/          # Moved from root
```

### A2: Copy new/changed skill content from installed to repo

These files exist only in `~/.claude/skills/sweetclaude/` and need to land in the repo:

- `hibernate/SKILL.md` → `framework/skills/hibernate/SKILL.md`
- `strategy/academic/SKILL.md` → `framework/skills/strategy/academic/SKILL.md`
- `strategy/reconciliation/SKILL.md` → `framework/skills/strategy/reconciliation/SKILL.md`
- `shared/README.md` → `framework/skills/shared/README.md`

These files diverged and the installed version should overwrite the repo:

- `SKILL.md` (master router — dual-track routing added)
- `work-router/SKILL.md` (strategy routing + backlog guard added)
- `init/SKILL.md` (three-scenario model added)
- `code/fix-issue/SKILL.md` (cross-refs updated)
- `code/pr-ready/SKILL.md` (cross-refs updated)
- `code/tdd/SKILL.md` (cross-refs updated)

### A3: Update all code-skill frontmatter names

Apply the naming convention from the restructure:

| Skill | Repo name → New name |
|---|---|
| auto-docs | `auto-docs` → `sweetclaude-code-auto-docs` |
| fix-issue | `sweetclaude-fix-issue` → `sweetclaude-code-fix-issue` |
| gherkin-bridge | `gherkin-bridge` → `sweetclaude-code-gherkin-bridge` |
| mutation-testing | `mutation-testing` → `sweetclaude-code-mutation-testing` |
| pr-ready | `sweetclaude-pr-ready` → `sweetclaude-code-pr-ready` |
| ripple | `ripple` → `sweetclaude-code-ripple` |
| scope-tracker | `scope-tracker` → `sweetclaude-code-scope-tracker` |
| tdd | `sweetclaude-tdd` → `sweetclaude-code-tdd` |
| discover-deep | `sweetclaude:discover-deep` → `sweetclaude-discover-deep` |
| work-router | `work-router` → `sweetclaude-work-router` |

Skip if already correct from the installed copy in A2.

### A4: Update framework/config/phase-skills.yaml

Replace repo's flat `phases:` structure with installed dual-track `code:` + `strategy:` structure. Copy installed version as-is.

### A5: Update framework/rules/phase-gates.md

Copy installed version — has strategy-track note, updated skill references with `code/` prefix, cross-phase skills section, and `sweetclaude:hibernate` references.

### A6: Update install.sh

The installer copies `framework/` to `~/.claude/`. After the directory restructure, verify:
- `cp -r` commands handle the new subdirectory depth (`code/`, `strategy/`, `shared/`, `parked/`)
- Conflict scan knows about the new skill paths
- Uninstaller cleans up the new paths

### A7: Verify and commit

- Diff installed vs repo for every file — confirm parity
- Run `install.sh` on a test path to verify it produces the correct structure
- Commit: `feat: sync repo with strategy-split restructure`

---

## Phase B: Complete Strategy Skills

Two of four priority skills from the design spec exist (`academic`, `reconciliation`). Two remain.

### B1: Review existing strategy skills against design spec

Read the installed `strategy/academic/SKILL.md` and `strategy/reconciliation/SKILL.md`. Compare against the design spec's requirements:

**Reconciliation-v2 checklist (from design spec section 2):**
- [ ] Inventory creation (file catalogue with type, topic, category, date, summary, recommendation)
- [ ] Per-file plan with user approval
- [ ] Versioning scheme (canonical-draft / canonical / historical)
- [ ] Deprecation frontmatter on archived originals (bidirectional lineage)
- [ ] Synthesis process with user opt-in
- [ ] RAG ingestion of canonical docs
- [ ] Does NOT delete, only copies/moves/adds frontmatter

**Academic checklist (from design spec section 3):**
- [ ] Phase 0: First Principles (key concepts, thesis, novelty, objections)
- [ ] Phase 1: Literature & Positioning (multi-round review, gap ID, SWOT)
- [ ] Phase 2: Structure & Venue (venue selection, writing norms, outline)
- [ ] Phase 3: Modular Drafting (section-by-section, quality rubrics)
- [ ] Phase 4: Review & Revision (reviewer simulation, caucus, revision loop)
- [ ] Phase 5: Submission (formatting, abstract, checklist, post-submission tracking)
- [ ] Narrative arc integration (read-only check against arc objectives)
- [ ] Reconciliation-v2 integration (reads existing canonical materials as starting context)

Flag gaps. These may need iteration before moving to Phase C.

### B2: Build narrative-arc skill

Design spec section 4 explicitly says "full design deferred to its own DESIGN cycle" — the interface contract is locked but internals are not designed. This needs its own mini-cycle:

1. **DISCOVER/DESIGN:** Ground the knowledge graph design in the SynCog arc as first instance. Decide: node types, credibility scoring model, graph storage format (must be human-readable + AI-parseable), traversal logic.
2. **IMPLEMENT:** Build `framework/skills/strategy/narrative-arc/SKILL.md`
3. **VERIFY:** Test against SynCog arc — can it answer "what supports this claim" and "what would strengthen this objective"?

Interface contract (already locked):
- Given document/claim → objectives served, strengthens, weakens
- Given objective → supports, opposes, gaps
- Given topic → credibility assessment

Storage: `strategy/narrative-arc/` in project repo. Format TBD.

### B3: Build meeting-prep skill

Design spec section 5. Depends on narrative-arc (reads confidence levels from arc).

1. **IMPLEMENT:** Build `framework/skills/strategy/meeting-prep/SKILL.md`
2. Stakeholder profiles in `strategy/meeting-prep/{name}.md`
3. Post-meeting debrief → arc updates via narrative-arc skill
4. **VERIFY:** Test with a real SynCog meeting scenario

### B4: Update phase-skills.yaml for new skills

Add `sweetclaude:strategy/narrative-arc` and `sweetclaude:strategy/meeting-prep` to appropriate strategy phases.

---

## Phase C: Remaining Design Spec Items

Lower-priority items from the design spec that aren't blocking but should be tracked.

### C1: Backlog guard enforcement

Design spec mentions the work router prevents non-technical items from landing in `docs/backlog/`. The installed work-router has the text but no hook enforcement. Decide: is prompt-based guidance sufficient, or does this need a PreToolUse hook?

### C2: Strategy-track phase gate documentation

Phase-gates.md currently says "strategy-track skills will be documented here as they are built." After all four strategy skills exist, add strategy-specific exit criteria per phase.

### C3: Model routing for strategy skills

Design spec notes "conceptual brainstorming should use a higher-performance model when available." Update `framework/config/model-routing.yaml` to route strategy skills appropriately:
- `strategy/academic` Phase 0 and Phase 3 → opus
- `strategy/narrative-arc` → opus
- `strategy/reconciliation` → sonnet
- `strategy/meeting-prep` → sonnet

### C4: Remaining strategy skills (build when needed)

Per the brief's scope, these are out of scope for now and built when the need activates:
- `strategy/positioning` — when active positioning work begins
- `strategy/competitive` — when next competitive scan needed
- `strategy/market-messaging` — when there's an audience to message to
- `strategy/biz-planning` — when active deals require planning

### C5: Update README.md

The repo README describes SweetClaude as a code-only framework. After strategy-track is complete, update to reflect the dual-track capability.

---

## Execution Order

```
Phase A (sync)         → can start immediately, no design work needed
  A1-A5 in sequence    → directory moves, file copies, config updates
  A6                   → installer update
  A7                   → verify + commit

Phase B (strategy skills)
  B1 first             → assess what exists before building new
  B2                   → narrative-arc needs own design cycle
  B3 after B2          → meeting-prep depends on narrative-arc
  B4 last              → config update after skills exist

Phase C (polish)       → after B is complete, lower priority
  C1-C5 independent    → can be done in any order
```

---

## Dependencies

- Phase A has no external dependencies — pure repo housekeeping
- B2 (narrative-arc) needs a concrete instance to ground the design — SynCog arc is the intended first use
- B3 (meeting-prep) depends on B2 (reads from narrative-arc)
- C2 depends on all of Phase B (need strategy skills to exist before documenting their gates)

---

## Success Criteria

1. `framework/` directory structure matches `~/.claude/skills/sweetclaude/` after install
2. Running `install.sh` produces a working installation identical to current installed state
3. All four priority strategy skills exist and are referenced in phase-skills.yaml
4. Work router correctly classifies strategy work types and surfaces strategy-track skills
5. A fresh session on a project with `strategy/` directory surfaces strategy skills, not code skills
