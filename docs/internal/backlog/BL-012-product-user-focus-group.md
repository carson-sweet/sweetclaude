---
id: BL-012
title: New skill product-user-focus-group — synthetic panel research with hard gate
priority: P2
status: backlog
created: 2026-05-01
---

## Summary

New skill `product-user-focus-group` that runs synthetic panel research as a focus-group caucus. Three argument-routed modes: `ask` (open qualitative), `concept-test` (comparison), `message-test` (variant testing). Generates N synthetic *instances* of canonical persona archetypes from `state/personas.yaml`, dispatches them as parallel subagents via the Agent tool, validates per-instance JSON responses, and synthesizes findings with mandatory "synthetic" labeling.

Protected by a **hard gate** in `rules/phase-gates.md` that refuses entry without validated personas. Override requires explicit risk acceptance logged to the decision log — same pattern as data-migration integrity checks and security-patch reviews.

Fills a gap in DISCOVER and DEFINE phases for users who need pre-flight pressure-testing of concepts, messages, and framing before paying for fieldwork.

## The non-negotiable principle

Synthetic respondents must never bypass real discovery. The framework physically prevents the shortcut.

The failure mode: a founder runs synthetic concept tests, treats the results as user validation, ships the wrong product, retro-rationalizes. SweetClaude's discovery pipeline is built on "best concepts survive scrutiny" and "challenge before acceptance." A synthetic shortcut would undermine the entire premise.

The skill enforces this by:

1. **Hard-gating entry** on validated `state/personas.yaml` — see Hard gate section below
2. **Never writing synthetic instances to `state/personas.yaml`** — synthetic instances are ephemeral research artifacts, written only to `state/research/{study-id}/instances.json`
3. **Mandatorily labeling all outputs "synthetic"** — every report.md frontmatter, every assumption-register entry, every decision-log entry includes the label. The label cannot be suppressed.
4. **Explicit hypothesis-not-validation framing** in every output: "synthetic findings are hypotheses to validate with real users, not validation themselves"

## Architecture

Implements the **caucus pattern** (see BL-014 for formalization) — N parallel isolated subagents, each instantiating one synthetic persona, returning structured findings independently, synthesized by the orchestrator.

### Modes (`$ARGUMENTS`-routed)

| Mode | Invocation | Output schema |
|---|---|---|
| `ask` | `/sweetclaude:product-user-focus-group ask [question]` | Open responses with theme codes |
| `concept-test` | `/sweetclaude:product-user-focus-group concept-test [comparison]` | Per-instance ranked choice + purchase intent + verbatim |
| `message-test` | `/sweetclaude:product-user-focus-group message-test [variants]` | Per-instance preferred variant + sentiment + quote |

All three modes share the same caucus mechanics; only the response schema differs.

### Flow per study

1. **Entry check.** Read `state/personas.yaml`. Verify at least one persona has the required fields populated (real-world scenario, observable success criteria, deal-breakers, anti-profile defined). If not, refuse via hard gate.
2. **Persona archetype selection.** Default: all archetypes. User can scope to specific archetype IDs.
3. **Synthetic instance generation.** Default 3 instances per archetype (user override). Each instance is parameterized by the archetype with seeded variation within the archetype's defined ranges (age, tenure, geography, etc.). Diversity within an archetype comes from independent instances, not from inventing new archetypes.
4. **Instance dispatch.** Parallel subagents via the Claude Code Agent tool, one per instance, isolated context. Each subagent receives the archetype + instance parameters as system prompt and the research question / concepts / variants as the task.
5. **Per-instance validation.** Each response validated against the mode's response schema before synthesis. Invalid responses re-prompted up to a small retry limit, then flagged.
6. **Synthesis.** Orchestrator extracts themes (qualitative modes), runs cross-tabs (structured modes), selects representative verbatims, and produces a headline finding.
7. **Output.** Synthetic-labeled artifacts written to corpus and state.

### Outputs

| Path | Content | Persistence |
|---|---|---|
| `corpus/raw/inbox/research-{study-id}.md` | Narrative report — flows through the corpus pipeline | Permanent |
| `.sweetclaude/research/{study-id}/instances.json` | Ephemeral synthetic instances used in this study | Permanent (study record) |
| `.sweetclaude/research/{study-id}/raw.json` | Per-instance JSON responses | Permanent (study record) |
| `state/assumption-register.md` | Each finding becomes an assumption tagged `synthetic-pending-validation` | Appended |
| `state/decision-log.md` | If a mode drives a decision, entry includes mandatory "synthetic" label and warning | Appended (conditional) |

The corpus pipeline reference is deliberate: research findings flow through triage and reconcile like any other document, ensuring they are evaluated for retention and integrated into canonical truth (or archived) rather than accumulating as scattered files.

## Hard gate

Entry in `rules/phase-gates.md`:

```
product-user-focus-group ENTRY (HARD GATE):
  Required state:
    - state/personas.yaml exists
    - At least one persona contains:
        - real-world scenario populated
        - observable success criteria (binary, measurable)
        - deal-breakers populated
        - anti-profile defined
  On failure:
    - Skill refuses entry
    - Routes user to /sweetclaude:user-personas with the specific gap explained
  Override:
    - Requires user to explicitly state:
      "I understand synthetic findings are not validated user research"
    - Override logged to decision-log.md with risk acceptance rationale
    - Output still mandatorily labeled "synthetic" — override does not change labeling
```

The gate is enforced at two layers:

1. `find-skill` blocks routing to `product-user-focus-group` if the gate fails
2. The skill itself re-checks at entry (defense in depth)

## Find-skill routing additions

Routing patterns that should map to `product-user-focus-group`:

- "test a concept" / "concept test" / "concept testing"
- "test messaging" / "message test" / "test copy variants"
- "synthetic research" / "synthetic interviews"
- "ask my personas" / "what would users say"
- "pressure-test before fieldwork"

Routing must verify the hard gate before suggesting the skill — if personas are not validated, route to `user-personas` first with explanation.

## Decisions needed

1. **Default instance count per archetype.** Lean: 3. Higher counts increase robustness but also context cost.
2. **Retry budget per instance.** Lean: 2 retries on validation failure, then flag the instance as defective and continue.
3. **Persistence policy for raw.json.** Lean: keep indefinitely under `research/{study-id}/`. Useful for re-synthesis if the analysis approach changes. Could be aggressive about archive.
4. **Should the skill allow specifying a market or geography that overrides persona defaults?** Lean: yes (e.g., a `--market jp` flag) with the override recorded in the study metadata. Caveat: overriding too aggressively dilutes the linkage to canonical personas.

## Implementation outline

1. Create `skills/product-user-focus-group/SKILL.md` with mode-routed flow
2. Create response schemas in `skills/product-user-focus-group/schemas/{ask,concept-test,message-test}.json`
3. Add hard-gate entry to `rules/phase-gates.md`
4. Update `config/phase-skills.yaml` — add to `product.skills`
5. Update `find-skill` routing
6. Update `documents-update-docs` and `corpus/raw/inbox/` integration so research reports flow through the corpus pipeline naturally
7. Add to `docs/user-guide/skills-reference.md` (Product section) with mandatory synthetic-labeling note
8. Add a walkthrough in `docs/user-guide/walkthroughs.md`

## Connection to other backlog items

- **BL-011** (personas promote) — required prerequisite. The focus group reads from the renamed skill's output.
- **BL-013** (discovery handoff) — independent but improves the upstream input that personas depend on.
- **BL-014** (caucus pattern formalization) — this skill is the second instance of the caucus pattern (after QA caucus). Cross-reference once the architecture doc paragraph lands.

## Branch

`feat/user-focus-group`

## References

- Caucus pattern (architectural primitive): see BL-014
- QA caucus prior art: `agents/sweetclaude/qa-caucus-{service,component,integration}.md`
- Hard gate pattern: `rules/phase-gates.md` (data-migration VERIFY, security-patch VERIFY entries)
- Subagent dispatch: `superpowers:dispatching-parallel-agents`
