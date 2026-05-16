# Artifact Privacy Manifest — Design v1.0
**Date:** 2026-05-01  
**Status:** Draft

---

## Problem

SweetClaude writes planning artifacts (milestones, backlog, user stories, product briefs, architecture docs, competitive analysis) to paths that may be tracked in git. The framework has no mechanism to ask the user where these should go. A default of `docs/` is a data breach risk — business strategy, competitive positioning, and roadmap decisions could be silently published if the repo is public or becomes public.

There is no reliable proxy for intent. A private repo today may become public tomorrow. A public repo may have been private when planning started. SweetClaude must ask explicitly and document the answer.

---

## Design Goals

1. **Privacy by documented consent.** No artifact is written to a tracked path unless the user has explicitly confirmed that category is public.
2. **Granular, not binary.** Technical docs (architecture) and strategy docs (competitive analysis) have very different sensitivity. Users choose per category.
3. **Future-proof.** The user's stated future intent is recorded alongside current state. If they say "I plan to open-source this," that informs the decision.
4. **Auditable.** A human-readable document records what was decided and why. Not just config — a record.
5. **Machine-readable.** A companion YAML file gives skills a clean routing table without parsing markdown.
6. **Hard block on missing manifest.** Skills refuse to write artifacts if the manifest does not exist. No silent fallback to a default path.

---

## Artifact Categories

Four categories requiring user decisions. Internal state is always private — no decision needed.

| Category | What it contains | Skills that write here |
|----------|-----------------|----------------------|
| **strategy** | Competitive analysis, market messaging, positioning, narrative arc, personas (strategic tier) | `product-competition`, `product-market-messaging`, `documents-narrative-arc`, `product-user-personas` (when strategic) |
| **product** | Product brief, PRD, milestones, roadmap, backlog, user stories, personas (product tier) | `product-brief`, `product-prd`, `product-milestones`, `product-backlog`, `product-user-stories`, `product-user-personas` (when product) |
| **technical** | Architecture, tech spec, data model, API design | `design-architecture`, `design-tech-spec`, `design-data-model`, `design-api-design` |
| **design** | UX flows, wireframes, UX definitions | `design-user-flows`, `design-wireframes`, `design-ux`, `design-ux-review` outputs |
| **internal** *(no choice)* | Phase state, decision logs, improvement register, assumption register, scope changes, traceability | All — always `.sweetclaude/state/` |

---

## Manifest Files

Two files are written together. Neither can exist without the other.

### `.sweetclaude/artifact-privacy.md` — Human record

```markdown
# Artifact Privacy Manifest
**Recorded:** {date}
**Schema:** 1

This document records where SweetClaude stores planning artifacts for this project.
It was created during setup and reflects explicit choices made at that time.
Review and update this document if repo visibility changes.

---

## Repository Visibility

**Current:** {Public | Private}
**Future intent:** {user's verbatim statement}

---

## Category Decisions

### Strategy Documents
*Competitive analysis, market messaging, positioning, narrative arc, personas (strategic tier)*

**Decision:** {Public | Private}
**Rationale:** {user's stated rationale}
**Location:** {resolved path}

---

### Product Definition
*Product brief, PRD, milestones, roadmap, backlog, user stories, personas (product tier)*

**Decision:** {Public | Private}
**Rationale:** {user's stated rationale}
**Location:** {resolved path}

---

### Technical Documents
*Architecture, tech spec, data model, API design*

**Decision:** {Public | Private}
**Rationale:** {user's stated rationale}
**Location:** {resolved path}

---

### Design Artifacts
*UX flows, wireframes, UX definitions*

**Decision:** {Public | Private}
**Rationale:** {user's stated rationale}
**Location:** {resolved path}

---

## Internal State
*Phase tracking, decision logs, improvement register, assumption register*

Always private — stored in `.sweetclaude/state/` (gitignored by default).
No decision required.

---

## Changelog
| Date | Change |
|------|--------|
| {date} | Initial manifest created during sweetclaude:on |
```

### `.sweetclaude/artifact-privacy.yaml` — Machine routing table

```yaml
# artifact-privacy.yaml — machine-readable routing for SweetClaude skills
# Do not edit manually. Update by re-running /sweetclaude:on → artifact privacy section.
schema_version: 1
recorded: {date}

repo:
  current_visibility: public | private
  future_intent: "{verbatim}"

categories:
  strategy:
    privacy: public | private
    base_path: "{confirmed path — e.g. strategy or .sweetclaude/strategy}"
  product:
    privacy: public | private
    base_path: "{confirmed path — e.g. docs or .sweetclaude/product}"
  technical:
    privacy: public | private
    base_path: "{confirmed path — e.g. docs or .sweetclaude/technical}"
  design:
    privacy: public | private
    base_path: "{confirmed path — e.g. docs/design or .sweetclaude/design}"
```

`base_path` is always the resolved, user-confirmed path. Skills read `base_path` directly — they never re-derive it from the privacy field. For private categories the path is always `.sweetclaude/{category}/`. For public categories it is whatever the user confirmed during setup (default `docs/` or `docs/design/` for design; `strategy/` for strategy).

Subdirectory structure is preserved under whichever base is used. Example: milestones always live in `{product_base}/milestones/MS-XXX.md` regardless of whether `product_base` is `docs` or `.sweetclaude/product`.

Private paths are covered by `.sweetclaude/*` in `.gitignore`. Public paths that differ from `docs/` or `strategy/` may require a gitignore carve-out if the root path is otherwise excluded — skills should check and warn if the chosen public path appears to be gitignored.

---

## Interview Flow — Addition to `sweetclaude:on`

Insert as **Step 2.5** in both New Project and Existing Project paths, after state directory creation and before product discovery.

### Step 2.5: Artifact privacy setup

#### Q1 — Repo visibility

Ask:
> "Before SweetClaude writes any planning documents, I need to know where to put them. First: is this repo currently public, or do you plan to make it public in the future?"

Options (require explicit choice — do not accept vague answers):
- **A** — "It's public now"
- **B** — "It's private now, but I plan to make it public"
- **C** — "It's private and will stay private"

Record the verbatim answer. Do not infer — if the user gives an unclear answer, ask again.

#### Q2–Q5 — Per category (one at a time)

For each category, ask one question. Present what the category contains so the user knows what they're deciding about.

For each category, the question is two parts: visibility, then (if public) location.

**Strategy:**
> "Strategy documents — competitive analysis, market messaging, positioning research, persona research. Should these be tracked in the repo (visible to anyone with access) or kept private?"

If public: "Where should they live? Default is `strategy/`."
If private: location is `.sweetclaude/strategy/` — no question needed.

**Product:**
> "Product definition documents — product brief, PRD, milestones/roadmap, backlog, user stories. Should these be tracked in the repo or kept private?"

If public: "Where should they live? Default is `docs/`."
If private: location is `.sweetclaude/product/` — no question needed.

**Technical:**
> "Technical documents — architecture, tech spec, data model, API design. Should these be tracked in the repo or kept private?"

If public: "Where should they live? Default is `docs/`."
If private: location is `.sweetclaude/technical/` — no question needed.

**Design:**
> "Design artifacts — UX flows, wireframes. Should these be tracked in the repo or kept private?"

If public: "Where should they live? Default is `docs/design/`."
If private: location is `.sweetclaude/design/` — no question needed.

For each: accept "public" or "private." Ask for a brief rationale (one sentence). Record both the decision and the rationale.

#### After all questions

Write both manifest files. Tell the user:
> "Artifact privacy configured. {N} categories private, {M} public.
> Recorded in `.sweetclaude/artifact-privacy.md`.
> Skills will use these paths from now on."

If any category is public AND the user said repo is/will be public: note it explicitly:
> "Note: {category} documents will be visible publicly once the repo is public. That's what you chose — just confirming."

---

## Path Resolution Protocol

This section is added to every skill that writes an artifact. It is identical across all skills.

```
## Artifact Path Resolution

Before writing any file, resolve the destination:

1. Read `.sweetclaude/artifact-privacy.yaml`.
   - If the file does not exist: STOP. Say:
     > "No artifact privacy manifest found. SweetClaude cannot write planning artifacts without knowing where to put them. Run `/sweetclaude:on` to configure artifact privacy, then return here."
   - Do not fall back to a default path. Do not guess.

2. Find the `base_path` for this skill's category (see skill header for category).

3. Construct the full path: `{base_path}/{artifact_filename}`.

4. Write to that path.
```

Each skill's YAML header gains a `category:` field:

```yaml
---
category: product   # or: strategy | technical | design
---
```

---

## Affected Skills

Every skill that writes a planning artifact needs:
- `category:` field in YAML header
- Path Resolution Protocol section added
- Default path references updated to use resolved path

### Full impact list

| Skill | Category | Current default path | Artifact filename |
|-------|----------|---------------------|------------------|
| `product-milestones` | product | `docs/milestones/` | `MS-XXX-slug.md`, `MILESTONES-INDEX.md` |
| `product-backlog` | product | `docs/backlog/` | `BL-XXX-slug.md`, `BACKLOG-INDEX.md` |
| `product-user-stories` | product | `.sweetclaude/stories/` | `EPIC-XXX/US-XXX-slug.md` |
| `product-brief` | product | `docs/product-brief.md` | `product-brief.md` |
| `product-prd` | product | `docs/prd.md` | `prd.md` |
| `product-user-personas` | product | `docs/personas.md` | `personas.md` |
| `product-competition` | strategy | `strategy/competitive-analysis/` | `competitive-analysis-*.md` |
| `product-market-messaging` | strategy | `strategy/market-messaging/` | `market-messaging-*.md` |
| `product-positioning-statement` | strategy | `strategy/` | `positioning-statement-*.md` |
| `documents-narrative-arc` | strategy | `strategy/narrative-arc/` | various |
| `design-architecture` | technical | `docs/architecture.md` | `architecture.md` |
| `design-tech-spec` | technical | `docs/tech-spec.md` | `tech-spec-*.md` |
| `design-data-model` | technical | `docs/data-model.md` | `data-model.md` |
| `design-api-design` | technical | `docs/api-design.md` | `api-design-*.md` |
| `design-user-flows` | design | `docs/user-flows/` | `user-flows-*.md` |
| `design-wireframes` | design | `{design_base}/wireframes/` (was `scratch/wireframes/`) | `wireframe-*.html` |
| `design-ux` | design | `docs/ux.md` | `ux.md` |
| `design-ux-review` | design | `docs/ux-review.md` | `ux-review-*.md` |

### Skills that read (not write) artifacts and need path resolution

| Skill | What it reads | Resolution needed |
|-------|--------------|------------------|
| `go` | milestones, backlog | Read `artifact-privacy.yaml`, construct scan paths |
| `status` | milestones | Read `artifact-privacy.yaml`, construct milestone path |
| `product-milestones` `link`, `status`, `blockers`, `complete` ops | milestone files, work item files | Use resolved paths for both |
| `master` | state directory docs | Update state directory map |

---

## Updates to `go` and `status`

### `go` — Step 1 replacement

Replace the current hardcoded `ls docs/milestones/MS-*.md` with:

```bash
# Read privacy manifest
milestone_base=$(python3 -c "import yaml,sys; d=yaml.safe_load(open('.sweetclaude/artifact-privacy.yaml')); print(d['categories']['product']['base_path'])" 2>/dev/null || echo "MISSING")
backlog_base=$(python3 -c "import yaml,sys; d=yaml.safe_load(open('.sweetclaude/artifact-privacy.yaml')); print(d['categories']['product']['base_path'])" 2>/dev/null || echo "MISSING")

# If manifest missing, use placeholder
ls ${milestone_base}/milestones/MS-*.md 2>/dev/null | head -10
grep -h "\*\*Status:\*\*" ${milestone_base}/milestones/MS-*.md 2>/dev/null | head -10
ls ${backlog_base}/backlog/*.md 2>/dev/null | head -10
```

If `milestone_base` is `MISSING`: show a warning in status output but do not block operation.

### `status` — Same replacement for milestone scan

Same logic as above for milestone path resolution.

---

## `sweetclaude:on` — Existing Project Handling

For existing projects, after the interview:

1. **Do not move files.** Existing docs stay where they are.
2. Record in the manifest:
   ```
   ## Migration Note
   This manifest was created for an existing project. Existing artifacts at their current locations
   were not moved. New artifacts will be written to the configured paths going forward.
   Existing locations: [list what was found and where]
   ```
3. If existing docs are in a public location and the user chose private for that category: flag it:
   > "I found existing {category} docs at {path}. You chose private for this category, but these files are currently tracked. You may want to move them to {private_path} and update your gitignore. I can do that now if you'd like."

---

## `master` Skill — State Directory Update

Update the state directory map in the master skill to show that docs/strategy paths are now dynamic:

```
.sweetclaude/
  state/           → always private — phase.yaml, decision-log.md, etc.
  artifact-privacy.md    → privacy manifest (human-readable)
  artifact-privacy.yaml  → privacy routing table (machine-readable)
  product/         → if product category is private
  strategy/        → if strategy category is private
  technical/       → if technical category is private
  design/          → if design category is private

docs/              → if category is public (technical and/or design)
strategy/          → if strategy category is public
```

---

## Guard: Missing Manifest

If a skill that writes artifacts encounters a missing `.sweetclaude/artifact-privacy.yaml`, it must stop and say:

> "No artifact privacy manifest found. SweetClaude cannot write planning artifacts without knowing where to put them — this prevents accidental publication of sensitive documents.
>
> Run `/sweetclaude:on` to configure artifact privacy, then return here."

No silent default. No "I'll just use docs/." Hard stop.

---

## Implementation Order

1. **Manifest format** — finalize `.md` and `.yaml` schemas (this doc)
2. **`sweetclaude:on`** — add Step 2.5 interview
3. **Path resolution protocol** — write the standard text block
4. **Skills** — add `category:` header + path resolution to all 18 affected skills
5. **`go` + `status`** — update to read `artifact-privacy.yaml` for scan paths
6. **`master`** — update state directory documentation
7. **This project** — run the interview for sweetclaude itself, configure manifest, migrate existing `docs/internal/backlog/` items

---

## Resolved Design Decisions

1. **`product-user-personas` category:** `product`.

2. **`design-wireframes` category:** `design`. Moves from `scratch/wireframes/` to the design base path.

3. **Re-running the interview:** When `/sweetclaude:on` detects an existing `.sweetclaude/artifact-privacy.yaml`, it asks: "You already have artifact privacy settings configured — want to update them?" before running the interview again. Does not overwrite without explicit yes.

4. **Public artifact location:** For public categories, the default base is `docs/` but the user is asked to confirm or specify a different location during the interview. The confirmed path is stored in `base_path` in the YAML. For private categories, the path is always `.sweetclaude/{category}/` — no location question, no variation. Subdirectory structure (e.g., `milestones/`, `backlog/`) is preserved under whichever base is chosen.
