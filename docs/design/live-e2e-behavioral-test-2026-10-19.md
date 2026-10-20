# Live Mutating E2E Behavioral Test — 2026-10-19

## Scope

Executed against a disposable local Git project and a uniquely created private
GitHub repository. Claude Code 2.1.303 ran the checkout via `--plugin-dir` with
Sonnet, project/local settings only, and write authority.

## Verified outcomes

| Step | Evidence | Result |
|---|---|---|
| Existing-code onboarding | `framework.setup_complete: true`, `project.mode: flow`, `.sweetclaude/product` tree, traceability files, plans directory, and session state created | Pass |
| GitHub tracker selection | `project.issue_tracker` changed from `local` to `github` only after `gh auth status` and an `origin` check | Pass |
| GitHub issue mutation | Private test repository issue #1 created with the requested title and body; no local `ISSUE-*.md` files created | Pass with workflow-boundary concern |
| Product brief mutation | Product brief Markdown, `state/brief.yaml`, and `.sweetclaude/log.md` created; brief contains requested audience, bullets, scope, success criteria, risks, and assumptions | Pass |
| Build mutation | Local commit `0edfa53 feat: validate inventory imports and report counts` modified `inventory.py` and added `test_inventory.py` | Pass |
| Verification | `python3 -m unittest -v`: 4 tests passed | Pass |

## Behavioral failure to fix

The issue-creation response reported that it did **not** run the full
SweetClaude bootstrap/library-loader routing and instead invoked `gh issue
create` directly. The remote issue was correct, but this is a behavioral
workflow-boundary failure: the system must execute the selected
`project-issues` workflow rather than merely reproduce one of its commands.

## Coverage limits

This run did not exercise a successful issue close/reopen/update path, a
deployment, rollback, multi-turn approval gates, or repeatability across
multiple model versions. After the test, the authenticated GitHub token was
refreshed with `delete_repo`; the private temporary repository
`carson-sweet/sweetclaude-e2e-f713daa1` was deleted and its absence was
verified. The local disposable test project was retained only as local test
evidence.
