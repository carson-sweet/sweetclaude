---
description: "Find and start the right skill for any work. Describe what you want to do — this skill classifies it, confirms the match, updates project state, and invokes the correct skill to begin the work."
---

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/phase.yaml exist in the project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Running pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Find Skill

Describe what you want to do. This skill figures out which skill fits, confirms, and starts it.

## Process

1. **Ask or detect.** If the user has not stated the work type, ask:
   > "What do you want to work on?"

   If the user has described something, classify it and propose:
   > "This looks like {type} ({bucket}) — I'll start `sweetclaude:{skill}`. Correct?"

   Wait for confirmation before invoking.

2. **Classify into a bucket:**

### strategy/ — why does this matter and to whom

| Work Type | Entry Phase | Skill to invoke |
|---|---|---|
| Concept articulation | DISCOVER | `sweetclaude:misc-narrative-arc` |
| Pain analysis | DISCOVER | `sweetclaude:product-discovery` |
| Customer profiling | DISCOVER | `sweetclaude:product-user-personas` |
| Competitive landscape | DISCOVER | `sweetclaude:product-competition` |
| Research paper | DISCOVER | `sweetclaude:misc-academic-research` |
| Meeting preparation | DEFINE | `sweetclaude:misc-meeting-prep` |
| Market messaging | DEFINE | `sweetclaude:product-market-messaging` |

### product/ — what to build and why

| Work Type | Entry Phase | Skill to invoke |
|---|---|---|
| Net-new product/feature | DISCOVER | `sweetclaude:product-discovery` |
| Product positioning | DEFINE | `sweetclaude:product-positioning-statement` |
| Product brief | DEFINE | `sweetclaude:product-brief` |
| Requirements / PRD | DEFINE | `sweetclaude:product-prd` |
| User stories | PLAN | `sweetclaude:product-user-stories` |
| Test specs from stories | PLAN | `sweetclaude:product-user-tdd-tests` |
| UX flows | PLAN | `sweetclaude:design-user-flows` |
| Scope change | any | `sweetclaude:product-manage-scope` |
| Backlog management | any | `sweetclaude:product-backlog` |
| Sprint planning | PLAN | `sweetclaude:product-sprint-plan` |
| Market/technical research | DISCOVER | `sweetclaude:product-research` |
| Feature comparison | DISCOVER | `sweetclaude:product-competition` |

### design/ — how it's structured

| Work Type | Entry Phase | Skill to invoke |
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

### code/ — writing and verifying code

| Work Type | Entry Phase | Skill to invoke |
|---|---|---|
| New feature | IMPLEMENT | `sweetclaude:code-tdd` |
| Feature enhancement | IMPLEMENT | `sweetclaude:code-work-issue` |
| Bug fix | IMPLEMENT | `sweetclaude:code-work-issue` |
| Chore / tech debt | IMPLEMENT | `sweetclaude:code-work-debt` |
| Testing | any | `sweetclaude:code-testing` |
| Code review | VERIFY | `sweetclaude:code-review` |

3. **Update state.** Write work type, bucket, and entry phase to `.sweetclaude/state/phase.yaml`:
   ```yaml
   phase: IMPLEMENT
   work_type: bug-fix
   bucket: code
   ```

4. **Invoke.** Use the Skill tool to start the matched skill. Pass any relevant context from the user's description as the skill's starting input so the user does not have to repeat themselves.

5. **Escalation.** At any point, if the work reveals deeper issues:
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
