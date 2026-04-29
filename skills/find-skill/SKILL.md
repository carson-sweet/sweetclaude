---
description: "Find and start the right skill for any work. Describe what you want to do — this skill classifies it, confirms the match, updates project state, and invokes the correct skill to begin the work."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Running pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Find Skill

Describe what you want to do. This skill figures out which skill fits, confirms, and starts it.

## Process

1. **Read version stage.** Read `.sweetclaude/state/phase.yaml`. Extract `version_stage` (default: PROTOTYPE if not set). This controls which work types are surfaced.

2. **Determine entry category** from context before asking anything:
   - `cold-start` — project has no prior `active_work_item` OR user is explicitly starting something new from scratch
   - `mid-project-reactive` — user describes something broken, failing, urgent, or in-progress emergency ("it's down", "something broke", "production issue", "need to hotfix")
   - `mid-project-planned` — all other cases: continuing work, planning next steps, choosing from backlog

3. **Ask or detect.** If the user has not stated the work type, ask:
   > "What do you want to work on?"

   If the user has described something, classify it and propose:
   > "This looks like {work-type} — I'll set up the {workflow-shape} pipeline and start `sweetclaude:{skill}`. Correct?"

   Wait for confirmation before proceeding.

4. **Classify into a work type.** Use the tables below. Only surface work types appropriate for the current `version_stage`:
   - **PROTOTYPE**: discovery and definition work only (net-new-feature, security-planning)
   - **ALPHA**: add design, planning, core implementation (net-new-feature, bug-fix, external-integration, enhancement)
   - **BETA+**: full catalog

### strategy/ — why it matters and to whom

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| Concept articulation | DISCOVER, DEFINE, SHIP | `sweetclaude:documents-narrative-arc` |
| Pain analysis | DISCOVER, DEFINE, SHIP | `sweetclaude:product-discovery` |
| Customer profiling | DISCOVER, DEFINE, SHIP | `sweetclaude:product-user-personas` |
| Competitive landscape | DISCOVER, DEFINE, SHIP | `sweetclaude:product-competition` |
| Research / deep research | DISCOVER, DEFINE, SHIP | `sweetclaude:documents-academic-research` |
| Meeting preparation | DEFINE | `sweetclaude:misc-meeting-prep` |
| Market messaging | DEFINE | `sweetclaude:product-market-messaging` |
| Security planning | DISCOVER, DEFINE, SHIP | `sweetclaude:security-planning` *(Plan 3)* |
| Course correction | DISCOVER, DEFINE, TRIAGE, SHIP | `sweetclaude:course-correction` *(Plan 3)* |

### product/ — what to build and why

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| Net-new feature | DISCOVER, DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:product-discovery` |
| Enhancement / iteration | DEFINE, DESIGN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:product-prd` |
| Product brief | DEFINE | `sweetclaude:product-brief` |
| Requirements / PRD | DEFINE | `sweetclaude:product-prd` |
| User stories | PLAN | `sweetclaude:product-user-stories` |
| Test specs from stories | PLAN | `sweetclaude:product-user-tdd-tests` |
| Scope change | any | `sweetclaude:product-manage-scope` |
| Backlog management | any | `sweetclaude:product-backlog` |
| Sprint / release planning | DEFINE, PLAN, SHIP | `sweetclaude:product-sprint-plan` |
| Market / technical research | DISCOVER | `sweetclaude:product-research` |
| Release planning | DEFINE, PLAN, SHIP | `sweetclaude:release-planning` *(Plan 3)* |

### design/ — how it's structured

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| System architecture | DESIGN | `sweetclaude:design-architecture` |
| Technical specification | DESIGN | `sweetclaude:design-tech-spec` |
| UX/UI design | DESIGN | `sweetclaude:design-ux` |
| Solution validation | DESIGN | `sweetclaude:design-solutioning-gate` |
| Impact analysis | any | `sweetclaude:design-change-impact-analysis` |
| Doc updates | VERIFY | `sweetclaude:documents-update-docs` |
| Data model / schema | DESIGN | `sweetclaude:design-data-model` |
| API design | DESIGN | `sweetclaude:design-api-design` |
| Record a decision | any | `sweetclaude:design-manage-decisions` |
| Onboarding flow design | DEFINE, DESIGN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:onboarding-flow-design` *(Plan 3)* |

### code/ — writing and verifying code

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| Net-new feature (implement) | IMPLEMENT | `sweetclaude:code-feature` |
| Bug fix | DIAGNOSE, IMPLEMENT, VERIFY, SHIP | `sweetclaude:code-issue` |
| Enhancement | IMPLEMENT | `sweetclaude:code-issue` |
| Tech debt / refactor | DEFINE, SCOPE, IMPLEMENT, VERIFY, SHIP | `sweetclaude:code-debt` |
| Hotfix | DIAGNOSE, IMPLEMENT, SHIP, POST-MORTEM | `sweetclaude:hotfix` *(Plan 3)* |
| Security patch | DIAGNOSE, IMPLEMENT, VERIFY, SHIP | `sweetclaude:security-patch` *(Plan 3)* |
| Performance optimization | DIAGNOSE, DESIGN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:code-issue` |
| External integration | DISCOVER, DEFINE, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:external-integration` *(Plan 3)* |
| Technology migration | ASSESS, DESIGN, PLAN, IMPLEMENT, VERIFY, CUTOVER, CLEANUP | `sweetclaude:code-debt` |
| Data migration | ASSESS, DESIGN, PLAN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:code-debt` |
| API deprecation | ASSESS, DEFINE, IMPLEMENT, VERIFY, SHIP, CLEANUP | `sweetclaude:code-feature` |
| Dependency upgrade | ASSESS, IMPLEMENT, VERIFY, SHIP | `sweetclaude:code-debt` |
| Infrastructure change | DEFINE, DESIGN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:code-debt` |
| Rollback / revert | DIAGNOSE, SHIP | `sweetclaude:code-issue` |
| Testing | any | `sweetclaude:code-testing` |
| Code / security / compliance review | VERIFY | `sweetclaude:code-review` |
| Compliance requirement | ASSESS, DEFINE, DESIGN, IMPLEMENT, VERIFY, SHIP | `sweetclaude:code-feature` |

### operations/ — keeping it running

| Work Type | Template Phases | Skill to invoke |
|---|---|---|
| Something broke | DIAGNOSE, SHIP, POST-MORTEM | `sweetclaude:something-broke` *(Plan 3)* |
| Postmortem | DIAGNOSE, SHIP | `sweetclaude:postmortem` *(Plan 3)* |
| Break-glass notes | DEFINE, SHIP | `sweetclaude:break-glass-notes` *(Plan 3)* |
| Onboarding playbook | DEFINE, IMPLEMENT, SHIP | `sweetclaude:code-feature` |

5. **Apply entry category behavior:**

   **cold-start:**
   > "Starting fresh — full discovery pipeline. No prerequisites to check. Let's go."
   Proceed to invoke without any prerequisite checks.

   **mid-project-planned:**
   Check for prerequisites by reading `config/workflow-templates.yaml` and searching the `hard_gate_policy.hard_gate_tasks` list for an entry where the `task` field matches the current work type key. If a matching entry is found, its `prerequisites` list contains the required artifacts. If no matching entry exists, no prerequisites apply — skip the check.
   If prerequisites are found and any appear missing:
   > "Before starting {work-type}, the usual prerequisites are: {list}. These look incomplete or missing. You can proceed anyway — or would you like to create any of them first?"
   This is advisory only (soft gate). The user can proceed regardless.

   **mid-project-reactive:**
   > "Got it — moving fast. Tell me: {triage question specific to work type, e.g. 'what exactly is broken?' for bug/hotfix, or 'which version is affected?' for security patch}."
   Skip all prerequisite checks. One triage question max before starting.

6. **Plan 3 guard.** Before writing state, check whether the matched skill is marked `*(Plan 3)*` in the routing table above.

   **If Plan 3:** Do NOT write state. Say:
   > "`sweetclaude:{skill}` is planned but not yet available. I can fall back to `{fallback}` (closest available skill in this bucket), or note this work type in the backlog and defer. Which would you prefer?"

   Use these fallbacks by bucket:
   - **strategy/** Plan 3 → `sweetclaude:product-discovery`
   - **product/** Plan 3 → `sweetclaude:product-sprint-plan`
   - **design/** Plan 3 → `sweetclaude:design-ux`
   - **code/** Plan 3 hotfix/security-patch → `sweetclaude:code-issue`; external-integration → `sweetclaude:code-feature`
   - **operations/** Plan 3 → `sweetclaude:code-issue`

   If the user chooses **defer**: add the work type to `docs/backlog/` and stop. Do not write state.
   If the user chooses **fallback**: substitute the fallback skill and proceed to step 7 with the fallback skill as the matched skill.

   **If not Plan 3:** Proceed to step 7.

7. **Update state and invoke.** Determine the next `id`: read the current `active_work_item.id` from phase.yaml (e.g., `WI-003`), parse the number, and increment by 1. If no existing id, start at `WI-001`. Format as `WI-{NNN}` with three zero-padded digits.

   Write `active_work_item` to `.sweetclaude/state/phase.yaml`:

   ```yaml
   active_work_item:
     id: WI-{NNN}
     type: {work_type_key}
     workflow: [{phases from table above, comma-separated}]
     phase: {first phase in workflow}
     title: "{one-sentence description from user's request}"
     started: {YYYY-MM-DD today}
     entry_category: {cold-start|mid-project-planned|mid-project-reactive}
   ```

   Example for a bug fix entered reactively:
   ```yaml
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
