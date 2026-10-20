# Phase 0: Bootstrap

## B1 — Tracking mode (Interactive)

Update `john-wick.yaml`: set `status: waiting_for_user`, `interactive_gate_pending.step: B1`, `interactive_gate_pending.description: Choose tracking mode and phase check-in preference`.

Ask:
> "Should John Wick track issues in GitHub or locally?
> - **GitHub** — creates real GitHub issues, requires `gh` auth
> - **Local** — creates a local issue list in `.sweetclaude/state/issue-list.md`"

If GitHub selected: run `gh auth status`. If it exits non-zero, offer:
> "GitHub CLI is not authenticated. Want me to walk you through `gh auth login` now?"
Help the user authenticate before continuing. Do not advance until `gh auth status` succeeds.

Record `github_mode: true/false` in `john-wick.yaml`.

Ask: "Should phase check-ins be enabled? Recommended if the PRD will have more than 4 epics or if you expect more than 2 external service dependencies. Check-ins add lightweight drift detection at each phase transition."

Record `phase_checkins: true/false`.

Update `current_step: B2`.

## B2 — Feature branch name (Interactive)

Update `john-wick.yaml`: set `status: waiting_for_user`, `interactive_gate_pending.step: B2`, `interactive_gate_pending.description: Choose feature branch name`.

Ask:
> "What should the feature branch be named? (e.g. `payment-retry-logic`, `user-profile-v2`)"

Validate: lowercase, hyphens only, no spaces. If invalid format, ask again.

Record `feature_name` and `feature_branch` in `john-wick.yaml`. Update `current_step: B3`.

## B3 — Initialize branch (Autonomous)

```bash
git checkout -b {feature_branch}
```

Copy all discovery artifacts found during prerequisites into `docs/` on the branch. Commit:
```
chore: initialize john-wick pipeline for {feature_name}
```

Update `john-wick.yaml`: record discovery artifact paths in `discovery_artifacts`. Open a new session entry in `sessions`: `{started: {ISO timestamp}, ended: null, steps_completed: []}`. Update `current_step: B4`.

## B4 — Compliance context (Interactive, conditional)

If `.sweetclaude/state/compliance-context.yaml` already exists: skip. Log "Compliance context already present — skipping B4." Update `current_phase: DEFINE`, `current_step: D1`.

If it does not exist: invoke the compliance context interview from `sweetclaude:library-load product-discovery` (the three-question section: data categories, user geography, user type). That section writes `.sweetclaude/state/compliance-context.yaml`. After it completes, record the path in `john-wick.yaml compliance_context`. Update `current_phase: DEFINE`, `current_step: D1`.
