---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Produce a complete, ordered story list for an epic."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# Epic Design

Produce a complete, ordered story list for an epic. Follows a fixed design-first sequence — no implementation stories are written until all design stories are complete and their outputs are on disk.

**Arguments:** `EP-NNN` (existing epic) · `new <title>` (create then design) · (empty = ask which epic)

---

## Step 0: Resolve paths

```bash
product_base=$(python3 -c "
import yaml,sys
d=yaml.safe_load(open('.sweetclaude/state/session-state.yaml'))
print(d.get('paths',{}).get('product_base','.sweetclaude/product'))
" 2>/dev/null || echo ".sweetclaude/product")
corpus_base="corpus/canonical"
echo "stories: ${product_base}/stories"
echo "corpus: $corpus_base"
ls ${product_base}/stories/ 2>/dev/null | head -5
```

Stories write to `{product_base}/stories/`. Promise and contract artifacts write to `corpus/canonical/promises/` and `corpus/canonical/contracts/`.

---

## Step 1: Load the epic

| Arguments | Action |
|---|---|
| `EP-NNN` | List artifacts and locate the epic; if not found, ask the user to describe it |
| `new <title>` | Invoke `sweetclaude:project-epics new` to create the epic, then continue |
| (empty) | Ask: "Which epic are we designing stories for? (EP-NNN, or `new <title>` to create one)" |

For `EP-NNN`: try loading via the artifact system:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"
[ -f "${_sc_hooks}/sc-artifact.sh" ] && source "${_sc_hooks}/sc-artifact.sh" && sc_artifact_view epic "$ARGUMENTS" 2>/dev/null || echo "ARTIFACT_SYSTEM_UNAVAILABLE"
```

If `ARTIFACT_SYSTEM_UNAVAILABLE`, ask the user: "Describe the epic in one sentence — what does it ship and for whom?"

---

## Step 2: User and system promise (always Story 1)

Ask:

> "Before we write any stories, let's define the promise this epic makes. When [epic title] ships:
>
> 1. **User promise** — What can a user do or experience that they cannot do today? Walk me through it as a narrative, step by step.
> 2. **System promise** — What does the platform guarantee at each step? (data integrity, telemetry, recovery on failure)"

Do not proceed until both promises are stated.

**Watch for gaps.** As the user describes the user promise, check each step against known design docs, ADRs, and backlog items. If a step assumes something that has not been designed, flag it:

> "You mentioned [X]. That doesn't appear to be designed yet. We should add a design story for it — scope into this epic, or file a separate backlog item?"

Surface every gap before moving on. This is the primary purpose of the promise step.

Write Story 1:
```
Story 1: Formalize user and system promises
Type:    design
Output:  corpus/canonical/promises/{EP-NNN}-promise.md
Content: user promise narrative, system promise guarantees, acceptance criteria derived from both
```

---

## Step 3: Integration design pass (Stories 2–3)

Identify every inter-service call required to fulfill the user promise. For each boundary: caller, callee, purpose, data in/out, auth model, error conditions.

Confirm the boundary map with the user before proceeding.

Write Story 2:
```
Story 2: Map service boundaries
Type:    design
Output:  boundary map document — every inter-service call, auth model, gaps found
```

Write Story 3:
```
Story 3: Write formal service contracts
Type:    design
Output:  one contract document per boundary in corpus/canonical/contracts/
         Each contract: request/response shapes, auth model, error codes, versioning, behavioral guarantees
```

Gaps found during this work become new backlog items — do not defer them silently.

---

## Step 4: Remaining design stories

For each open design question surfaced in Steps 2–3 and the promise step, write a numbered design story starting at 4. Each story must name its output artifact.

Common examples: resolving open design questions in existing backlog items, defining data models for new entities, designing new concepts surfaced by the promise.

---

## Step 5: Prerequisite debt stories

Identify tech debt or type-safety gaps that must be resolved before implementation can start. Write one story per gap. These come after design stories and before implementation stories.

---

## Step 6: Implementation stories

Present the checklist and confirm which sections apply. Write one or more stories per applicable section. Sections that do not apply must be explicitly noted as out of scope — do not silently skip them.

| Section | What to cover |
|---|---|
| Data model | Schema changes, migration path, retention policy |
| API | Endpoint contracts, auth model, backward compatibility |
| Implementation | Core feature code — data model, API, UI, prompt architecture (if language model calls are involved) |
| Security | Auth model verified, data isolation, secrets handling, top-ten vulnerability review |
| Observability | Telemetry events at key lifecycle points, logging, health checks |
| Error handling | All failure modes handled, retry/timeout/circuit-breaker strategy, rollback plan |
| Integration and contract testing | Service boundary contracts tested end-to-end, not just unit tests |
| Tier-1 invariant coverage | Any change touching cognition, safety, identity, or action scope needs explicit Tier-1 tests |

---

## Step 7: Test and review stories

Always include these at the end, in this order:

```
Story N:   Tier-1 invariant test coverage (if applicable)
Story N+1: Security review
Story N+2: End-to-end integration test — full user promise, including failure and recovery scenarios
```

The end-to-end integration test story is the **milestone criterion gate** for this epic.

---

## Step 8: Present and confirm

Present all stories in a numbered table:

| # | Title | Type | Description |
|---|---|---|---|

Show dependency order: design and debt stories are sequential prerequisites; implementation stories may run in parallel where dependencies allow.

If the story count exceeds 14, surface this and propose splitting the epic before proceeding.

Wait for user confirmation before writing anything to disk.

---

## Step 9: Write to disk

On confirmation, create each story as a user story file in `{product_base}/stories/`. Check `{product_base}/stories/` for an existing format to match. Link each story back to the epic.

---

## Rules

- **Promise before code.** Story 1 is always the user and system promise. Never skip it.
- **Gaps are backlog items.** Any gap found during promise or contract writing becomes a new backlog item immediately — do not defer silently or fold it into an existing story without naming it.
- **Formal contracts, not notes.** Service contracts are first-class artifacts in `corpus/canonical/contracts/`, not inline notes or footnotes.
- **Design before implementation.** All design stories must be complete and their outputs on disk before any implementation story.
- **Every template section is a conscious decision.** Silence is not "not applicable."
- **Maximum 14 stories.** If the story list exceeds 14, propose splitting the epic before proceeding.
- **No unexplained abbreviations.** Use plain language in all story titles and descriptions.
