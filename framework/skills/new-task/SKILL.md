---
name: sweetclaude-new-task
description: "Start a new task. Asks what you want to do, classifies the work into one of five domain buckets (strategy, product, design, code, deploy), and routes to the correct pipeline entry point. Use when beginning any new work."
---

<preflight-guard>
STOP. Before executing this skill, check: does state/phase.yaml exist in the project working repo or project directory? If NO, do not proceed. Instead say: "This project is not configured for SweetClaude. Let me run the pre-flight check." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# New Task

Classify the work, pick the right bucket and phase, surface the right skills.

## Process

1. **Ask or detect.** If the user hasn't stated the work type, propose:
   > "This looks like {type} ({bucket}) based on {reasoning}. That means we'd start at {phase}. Sound right?"

2. **Classify into a bucket:**

### strategy/ — why does this matter and to whom

| Work Type | Entry Phase | First Skill |
|---|---|---|
| Concept articulation | DISCOVER | strategy/concept |
| Pain analysis | DISCOVER | strategy/pain-thesis |
| Customer profiling | DISCOVER | strategy/ideal-customer-profile |
| Competitive landscape | DISCOVER | strategy/competitive-analysis |
| Research paper | DISCOVER | strategy/academic-research |
| Meeting preparation | DEFINE | strategy/meeting-prep |
| Strategic narrative | DISCOVER | strategy/narrative-arc |
| Market messaging | DEFINE | strategy/market-messaging |

### product/ — what to build and why

| Work Type | Entry Phase | First Skill |
|---|---|---|
| Net-new product/feature | DISCOVER | product/discovery |
| Product positioning | DEFINE | product/positioning-statement |
| Product definition | DEFINE | product/product-brief |
| Requirements | DEFINE | product/prd |
| User stories | PLAN | product/user-story |
| Test specs from stories | PLAN | product/user-tdd-tests |
| Success criteria | DEFINE | product/user-success-criteria |
| UX flows | PLAN | product/user-workflows |
| Scope change | any | product/manage-scope |
| Backlog management | any | product/backlog |
| Sprint planning | PLAN | product/sprint-plan |
| Market/technical research | DISCOVER | product/research |
| Feature comparison | DISCOVER | product/feature-competitive |

### design/ — how it's structured

| Work Type | Entry Phase | First Skill |
|---|---|---|
| System architecture | DESIGN | design/architecture |
| Technical specification | DESIGN | design/tech-spec |
| UX/UI design | DESIGN | design/ux |
| Solution validation | DESIGN | design/solutioning-gate |
| Impact analysis | any | design/change-impact-analysis |
| Doc updates | VERIFY | design/update-docs |
| Data model / schema | DESIGN | design/data-model |
| API design | DESIGN | design/api-design |
| Service boundaries | DESIGN | design/services-design |
| Infrastructure | DESIGN | design/infra-design |
| Record a decision | any | design/manage-decisions |

### code/ — writing and verifying code

| Work Type | Entry Phase | First Skill |
|---|---|---|
| Implement with TDD | IMPLEMENT | code/tdd |
| GitHub issue | IMPLEMENT | code/work-issue |
| Tech debt cleanup | IMPLEMENT | code/work-debt |
| Pre-PR check | VERIFY | code/pr-precheck |
| Run tests | any | code/qa-testing |
| Mutation testing | VERIFY | code/mutation-testing |
| Security review | VERIFY | code/security-testing |
| Code review | VERIFY | code/code-review |

3. **Update state.** Write work type, bucket, and entry phase to `state/phase.yaml`:
   ```yaml
   phase: DISCOVER
   work_type: research-paper
   bucket: strategy
   ```

4. **Surface skills.** Read `phase-skills.yaml` and surface skills from the appropriate bucket for the current phase.

5. **Escalation.** At any point, if the work reveals deeper issues:
   > "This {type} seems to point to a deeper {gap}. Want to escalate to DISCOVER and investigate?"

## Backlog Guard

When adding to the backlog:
- **Technical items** (bugs, feature requests, tech debt) → `docs/backlog/`
- **Non-technical items** (product ideas, strategic initiatives) → redirect to `strategy/`:
  > "That's a strategic item, not a technical backlog item. I'll capture it in strategy/ instead."

## Cross-Bucket Detection

If work shifts between buckets during a session:
- Detect the shift from conversation context
- Propose: "This is becoming {type} ({bucket}). Want to shift?"
- Preserve previous work state on reroute

If strategy work reveals something that needs building:
> "This depends on a capability we haven't built. Want to create a code task for it?"

If code work reveals strategic prerequisites:
> "This needs strategic work first. Want to switch to strategy for {type}?"
