---
spdx-license: AGPL-3.0-or-later
description: "Implement a GitHub issue end-to-end."
user-invocable: true
---


!`bash ${CLAUDE_SKILL_DIR}/../../hooks/read-state.sh session-state`

<preflight-guard>
STOP. Before executing this skill, check: does .sweetclaude/state/sweetclaude.yaml or .sweetclaude/state/phase.yaml exist in the project directory? If NEITHER, do not proceed. Tell the user: "This project is not set up for SweetClaude. Running the pre-flight check now." Then invoke the sweetclaude master skill (Skill tool, skill: "sweetclaude:master") and run its pre-flight. Return here only after the pre-flight passes.
</preflight-guard>

# Implement Issue

Implement GitHub issue $ARGUMENTS using the SweetClaude pipeline.

## Process Control Gate

Before invoking `sweetclaude:code-tdd` or any implementation subagent path,
read `skills/process-controls.md` and create or update
`.sweetclaude/state/process-control-ledger.yaml`. If the ledger is missing,
over budget, stale, or in a stop disposition, pause and ask the user for a
bounded decision before dispatching more agents or continuing a correction
loop.

For large/high-rigor issues, implementation may not begin until the issue or
calling workflow supplies a frozen `success_criteria_contract`. Preserve
`success_criteria_contract_hash` and `criterion_ids` through planning,
implementation, verification, and PR preparation. Completion requires
`success-criteria-ledger.json` with every frozen criterion evaluated and
`all_success_criteria_passed == true`. No review, caucus, verification,
release, or completion step may add completion criteria; concerns outside the
contract become backlog, amendment requests, split stories, or human
escalations.

## Process

0. **Story Branch Setup.**

   ```bash
   git branch --show-current
   ```

   If already on a branch matching an issue ID prefix (e.g., `issue-42/...`, `ISSUE-046/...`) — skip.

   Otherwise, derive the branch name: ID = `issue-{number}` from `$ARGUMENTS`; slug = issue title lowercased, non-alphanumeric → hyphens, collapsed + truncated to 40 chars. Branch name: `{ID}/{slug}`.

   Offer via AskUserQuestion:
   - **Create branch `{branch-name}`** (Recommended) — `git checkout -b {branch-name}`
   - **Stay on current branch** — I'll manage branches myself
   - **Something else**

1. **Explore.** Read the issue (`gh issue view $ARGUMENTS`). Follow linked docs (Notion, specs, ADRs). Read relevant source files. Summarize current behavior and risks. Do not change code yet.

2. **Ripple analysis.** Run `sweetclaude:design-change-impact-analysis` on the affected area. Present the impact assessment.

3. **Plan.** Propose a step-by-step plan with:
   - Files to modify
   - TDD level (bug fix → Level 1-2, feature → Level 2-3)
   - Test strategy: what test files, what assertions
   - Verification commands
   Wait for approval (respecting deference level).

4. **Implement with TDD.** Invoke `sweetclaude:code-tdd` at the planned level:
   - Bug fixes: Level 1-2 — regression test first, then fix
   - Features: Level 2-3 — depends on whether Gherkin specs exist

5. **Verify.** Run lint and tests for affected packages. Invoke `sweetclaude:code-verify`.

6. **Update docs.** Run `sweetclaude:documents-update-docs` to check if documentation needs updating.

7. **Completion.** Run `sweetclaude:code-testing` for the pre-PR checklist. Stage any unstaged changes. Draft a conventional commit message referencing the issue number. Then offer via AskUserQuestion:
   - **Open PR** (Recommended) — commit and open PR with `gh pr create`; fill the PR template completely, reference the issue number
   - **Commit, merge, and push** — commit to story branch, merge to main, push origin; confirm commit message before executing
   - **Commit only** — commit staged changes; I'll merge/push manually
   - **Leave as is** — I'll handle git myself

## Rules

- If acceptance criteria are unclear or missing, stop and ask before writing tests.
- Keep changes minimal. Follow existing patterns.
- Every behavior change needs a test.
- If you hit a blocker, report it. Do not work around it silently.
- Update traceability in `.sweetclaude/` after completion.
- **Direction change detection.** Watch for signals the scope has shifted: user says "actually, let me rethink" or "this is turning into something bigger"; issue scope changes materially mid-session; files well outside the original scope are touched. When detected, offer via AskUserQuestion: "Stash current work, create new story" (Recommended — `git stash push -m "WIP: {branch}"`, prompt for new backlog item + branch) / "Keep going on this branch" / "Something else".
