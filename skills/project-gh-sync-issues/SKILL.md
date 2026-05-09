---
spdx-license: AGPL-3.0-or-later
user-invocable: true
description: "Bidirectional status sync between local I-NNN issues and GitHub Issues."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
```

# GitHub Issues — Sync

Bidirectional status sync between local issues and GitHub. Run anytime to keep the two in sync. Arguments: `$ARGUMENTS`

---

## Prerequisites

```bash
gh auth status 2>/dev/null && echo "GH_OK" || echo "GH_NOT_AUTH"
git remote get-url origin 2>/dev/null || echo "NO_REMOTE"
```

If `GH_NOT_AUTH`: "GitHub CLI is not authenticated. Run `gh auth login` first." Stop.
If `NO_REMOTE`: "No git remote found. Sync requires a GitHub remote." Stop.

---

## Pass 1 — GitHub closed → update local

```bash
gh issue list --state closed --limit 500 --json number,state 2>/dev/null
```

For each closed GitHub issue, find the matching local issue by `github_issue_number`:

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_query issue github_issue_number=<number>
```

If the local issue's status is not `done` or `cancelled`, mark it done:

```bash
sc_artifact_write <ID> '{"status": "done"}'
```

---

## Pass 2 — Local done → close on GitHub

```bash
_sc_hooks="${CLAUDE_PLUGIN_ROOT:+${CLAUDE_PLUGIN_ROOT}/hooks}"; _sc_hooks="${_sc_hooks:-$HOME/.claude/hooks/sweetclaude}"; source "${_sc_hooks}/sc-artifact.sh"
sc_artifact_query issue status=done
```

For each local issue with `status: done` that has a `github_issue_number` field, check if the GitHub issue is still open:

```bash
gh issue view <github_issue_number> --json state 2>/dev/null
```

If GitHub state is `open`, close it:

```bash
gh issue close <github_issue_number> 2>/dev/null && echo "closed"
```

---

## Report

```
GitHub Issues sync complete
  Local closed from GitHub: {N}
  GitHub issues closed from local: {N}
  No action needed: {N}
```

If any `gh issue close` fails (e.g., permissions): note the ID and continue. List all failures at the end. Do not stop on individual failures.
