---
spdx-license: AGPL-3.0-or-later
user-invocable: false
description: "Find and start the right skill for any work."
---

!`bash ~/.claude/hooks/sweetclaude/record-event.sh skill_invoked "sweetclaude:find-skill" 2>/dev/null || true`

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Running pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Find Skill

Describe what you want to do. This skill figures out which skill fits, confirms, and starts it.

The full work-type → skill mapping lives in [routing-tables.md](routing-tables.md) (8 buckets: strategy, product, design, code, project, testing, operations, system). Read it when the algorithm tells you to in Step 4.

## Process

1. **Read version stage.** Read `.sweetclaude/state/phase.yaml`. Extract `version_stage` (default: PROTOTYPE if not set). This controls which buckets are surfaced — see the visibility note at the top of `routing-tables.md`.

1b. **Check structured state for starting phase.** Before classifying or prompting, read the authoritative state sources in order:

  1. **`phase.yaml` `active_work_item`** — already read in Step 1. If a work item is active and matches the request, use its `phase` directly. Do not re-derive.
  2. **Roadmap file** — if the request references a roadmap epic, find it in the roadmap file and read its `Status:` field:
     - `not_started` → `{starting_phase}` = first phase in the workflow
     - `in_progress` + a `Phase:` annotation → use that phase
     - `blocked` → note the blocker to the user; ask if they want to proceed anyway
  3. **Backlog file front matter** — if the request matches a backlog item, read its YAML front matter for any `phase:` or `status:` field.
  4. **No structured state found** → `{starting_phase}` = first phase in the workflow (genuine cold-start)

  Do NOT scan code directories, git history, or arbitrary doc files to infer phase. Structured state is the source of truth. If structured state is absent, ask the user: "Where are you in this work? (Not started / In design / Writing code / Ready for review)"

  Store the result as `{starting_phase}` — used in Step 7.

2. **Determine entry category** from context before asking anything:
   - `cold-start` — project has no prior `active_work_item` OR user is explicitly starting something new from scratch
   - `mid-project-reactive` — user describes something broken, failing, urgent, or in-progress emergency ("it's down", "something broke", "production issue", "need to hotfix")
   - `mid-project-planned` — all other cases: continuing work, planning next steps, choosing from backlog

3. **Ask or detect.** If the user has not stated the work type, ask:
   > "What do you want to work on?"

   If the user has described something, classify it and propose — using the assessed `{starting_phase}` from Step 1b:
   > "This looks like {work-type}. {If starting_phase != first phase: 'Found existing {artifacts} — picking up at {starting_phase}.' Else: 'Starting from {first phase}.'} Correct?"

   Wait for confirmation before proceeding.

4. **Classify into a work type.** Read [routing-tables.md](routing-tables.md). Find the row matching the user's intent. Note the work type (slug form like `bug-fix`), template phases, and target skill. Filter by `version_stage` per the visibility note at the top of that file.

5. **Apply entry category behavior:**

   **cold-start:**
   > "Starting fresh — full discovery pipeline. No prerequisites to check. Let's go."
   Proceed to invoke without any prerequisite checks.

   **mid-project-planned:**
   Check for prerequisites by reading `config/workflow-templates.yaml` and searching the `hard_gate_policy.hard_gate_tasks` list for an entry where the `task` field matches the current work type's YAML key (e.g., `infrastructure-change`, not `Infrastructure change` — use the hyphenated slug form that appears in `active_work_item.type`). If a matching entry is found, its `prerequisites` list contains the required artifacts. If no matching entry exists, no prerequisites apply — skip the check.
   If prerequisites are found and any appear missing:
   > "Before starting {work-type}, the usual prerequisites are: {list}. These look incomplete or missing. You can proceed anyway — or would you like to create any of them first?"
   This is advisory only (soft gate). The user can proceed regardless.

   **mid-project-reactive:**
   > "Got it — moving fast. Tell me: {triage question specific to work type, e.g. 'what exactly is broken?' for bug/hotfix, or 'which version is affected?' for security patch}."
   Skip all prerequisite checks. One triage question max before starting.

6. **Plan 3 guard.** Before writing state, check whether the matched skill is marked `*(Plan 3)*` in `routing-tables.md`.

   **If Plan 3:** Do NOT write state. Say:
   > "`sweetclaude:{skill}` is planned but not yet available. I can fall back to `{fallback}` (closest available skill in this bucket), or note this work type in the backlog and defer. Which would you prefer?"

   See the **Plan 3 fallbacks** table at the bottom of `routing-tables.md` for the bucket → fallback mapping.

   If the user chooses **defer**: add the work type to `docs/backlog/` and stop. Do not write state.
   If the user chooses **fallback**: substitute the fallback skill and proceed to step 7 with the fallback skill as the matched skill.

   **If not Plan 3:** Proceed to step 7.

7. **Update state and invoke.** Determine the next `id`: read `last_work_item_id` from phase.yaml (this persists across work item completions). If present (e.g., `WI-003`), parse the number and increment by 1. If absent, start at `WI-001`. Format as `WI-{NNN}` with three zero-padded digits. Write the new id to both `active_work_item.id` and `last_work_item_id`.

   Write `active_work_item` to `.sweetclaude/state/phase.yaml`:

   ```yaml
   last_work_item_id: WI-{NNN}

   active_work_item:
     id: WI-{NNN}
     type: {work_type_key}
     workflow: [{phases from routing-tables.md, comma-separated}]
     phase: {starting_phase — assessed in Step 1b, NOT assumed to be first phase}
     title: "{one-sentence description from user's request}"
     started: {YYYY-MM-DD today}
     entry_category: {cold-start|mid-project-planned|mid-project-reactive}
   ```

   If `{starting_phase}` differs from the first phase in the workflow, tell the user:
   > "Found existing {artifact type} — starting at {starting_phase} instead of {first phase}."

   Example for a bug fix entered reactively:
   ```yaml
   last_work_item_id: WI-003

   active_work_item:
     id: WI-003
     type: bug-fix
     workflow: [DIAGNOSE, IMPLEMENT, VERIFY, SHIP]
     phase: DIAGNOSE
     title: "Login fails when email contains uppercase letters"
     started: 2026-04-29
     entry_category: mid-project-reactive
   ```

   Then use the Skill tool to start the matched skill. Pass any relevant context from the user's description as the skill's starting input so the user does not have to repeat themselves.

8. **Escalation.** At any point, if the work reveals deeper issues:
   > "This {type} points to a deeper {gap}. Escalate to DISCOVER and investigate?"

## Backlog Guard

When adding to the backlog:
- **Technical items** (bugs, feature requests, tech debt) → `docs/backlog/`
- **Non-technical items** (product ideas, strategic initiatives) → redirect to `strategy/`:
  > "That is a strategic item, not a technical backlog item. Capturing it in strategy/ instead."

## Cross-Bucket Detection

If work shifts between buckets during a session:
- Detect the shift from conversation context
- Propose: "This is shifting to {type} ({bucket}). Switch?"
- Preserve previous work state on reroute

If strategy work reveals something that needs building:
> "This depends on a capability that does not exist yet. Create a code task for it?"

If code work reveals strategic prerequisites:
> "This needs strategic work first. Switch to strategy for {type}?"
