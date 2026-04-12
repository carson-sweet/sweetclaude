# Project-Level Claude Code Harness — Implementation Prompt

Run this prompt from inside your project repo in a fresh Claude Code session. It builds the full `.claude/` harness, GitHub templates, hooks, subagents, and CLAUDE.md for this specific project.

**Prerequisite:** The global environment optimization (user-level prompt) should already be complete. This prompt assumes `~/CLAUDE.md` is lean and the Don Cheli framework is removed.

---

## START OF PROMPT

You are going to build a complete Claude Code development harness for this project repository. This includes the project-level CLAUDE.md, skills, subagents, hooks, rules, GitHub templates, and CODEOWNERS.

### Operating rules for this entire task

1. **Start by exploring the project.** Before creating anything, you need to understand the codebase: language, framework, build system, test runner, directory structure, existing CI/CD, existing `.claude/` or `.github/` config.
2. **Work phase by phase.** Complete one phase, report what you did, STOP and wait for my approval before the next.
3. **Before creating or modifying any file, show me the full contents** you plan to write. Wait for my "go."
4. **After each file creation, verify it** — re-read it to confirm it was written correctly.
5. **Everything you create should be committed to git.** This harness is shared with the team. At the end, we will review and commit together.
6. **Ask me when you need information you can't infer** — co-founder GitHub usernames, deployment targets, environment names, Notion workspace details, domain-specific invariants.
7. **Keep a running log** after each phase for session recovery.

### Target file structure

When done, the repo should have these new or updated files:

```
.
├─ CLAUDE.md                          # Project-specific (100-120 lines)
├─ .claude/
│  ├─ settings.json                   # Hooks configuration
│  ├─ skills/
│  │  ├─ fix-issue/SKILL.md
│  │  ├─ pr-ready/SKILL.md
│  │  ├─ qa-sweep/SKILL.md
│  │  ├─ migration-safe/SKILL.md      # If project uses a database
│  │  └─ actions-review/SKILL.md
│  ├─ agents/
│  │  ├─ code-reviewer.md
│  │  ├─ security-reviewer.md
│  │  ├─ test-runner.md
│  │  └─ workflow-guardian.md
│  └─ rules/
│     ├─ [area-specific rules files]
├─ .github/
│  ├─ ISSUE_TEMPLATE/
│  │  ├─ config.yml
│  │  ├─ feature.md
│  │  ├─ bug.md
│  │  └─ tech-debt.md
│  ├─ pull_request_template.md
│  └─ CODEOWNERS
├─ scripts/
│  └─ claude-hooks/
│     ├─ format-touched-files.sh
│     └─ block-protected-paths.sh
└─ docs/
   └─ adr/                            # Create directory if absent
```

Not every file above is needed for every project. You will determine which are relevant during Phase 1.

---

## PHASE 1: Explore the project

**Goal:** Build a complete picture of the codebase so every file you create is tailored, not generic.

Investigate and report ALL of the following:

### 1a. Codebase fundamentals
- What language(s) and framework(s) does this project use?
- Is this a monorepo or single-service? If monorepo, list the packages/services.
- What is the primary entrypoint?
- What package manager is used (npm, yarn, pnpm, pip, cargo, etc.)?
- What is the directory structure? (`ls` top-level, then one level into `src/` or equivalent)

### 1b. Build and test toolchain
- What are the install, build, lint, typecheck, and test commands? (Check `package.json` scripts, `Makefile`, `pyproject.toml`, `Cargo.toml`, or equivalent)
- What test framework is used? (Jest, Vitest, pytest, Go test, etc.)
- Is there a formatter configured? (Prettier, Black, rustfmt, etc.) What's the command?
- Can you run the linter and tests successfully right now? Try it and report.

### 1c. Database and migrations
- Does this project use a database? Which one?
- Is there a migrations directory? What migration tool? (Prisma, Drizzle, Alembic, Knex, ActiveRecord, etc.)
- Any ORM or query builder?

### 1d. Existing configuration
- Does a `CLAUDE.md` already exist at project root? If so, read it and report contents and line count.
- Does `.claude/` already exist? If so, list everything in it.
- Does `.github/` exist? List contents (templates, workflows, CODEOWNERS).
- Does `.claude/settings.json` exist with any hooks?
- Is there an `.mcp.json` for shared MCP server config?

### 1e. Git and CI/CD
- What branches exist? Which is the default/protected branch?
- Are there existing GitHub Actions workflows? Read them and summarize what they do.
- Are third-party actions pinned to SHAs or tags?
- What are the `GITHUB_TOKEN` permissions set to in workflows?
- Are there GitHub environments configured? (Check workflow files for `environment:` keys)

### 1f. Team context
**Ask me:**
- Who are the GitHub usernames for CODEOWNERS? (You and Greg at minimum)
- What Notion workspace do you use for PRDs/specs? (For template links)
- Are there any project-specific invariants or "never do this" rules I should know about?
- Any deployment targets I should know about? (AWS, Cloudflare, Vercel, etc.)
- Any existing style guide or architectural documentation?

**Output:** A structured summary of all findings, organized by section. Flag anything surprising or concerning. Then STOP.

---

## PHASE 2: Write project CLAUDE.md

**Goal:** Create a project-specific CLAUDE.md that gives Claude everything it needs to work in this repo, and nothing it doesn't.

### Design principles
- **100-120 lines maximum.** The user-level `~/CLAUDE.md` already covers universal rules (git workflow, invariants, session discipline). This file covers only what's specific to THIS project.
- **Commands must be copy-paste runnable.** Every build/test/lint command should work exactly as written.
- **No documentation of Claude Code behavior.** Claude already knows how it works.
- **No duplication of `~/CLAUDE.md`.** Don't repeat universal rules — they merge automatically.
- **Every line must pass:** "Would removing this cause Claude to make mistakes in this repo specifically?"

### Required sections

```markdown
# [Project name]

## What this is
[One-paragraph description: what the project does, who it's for, what the tech stack is]

## Repo structure
[Brief map: key directories, entrypoints, config locations. For monorepos, list each package/service with a one-line description]

## Build / test / lint
- Install: [exact command]
- Build: [exact command]
- Lint: [exact command]
- Typecheck: [exact command]
- Format: [exact command]
- Unit tests (all): [exact command]
- Unit tests (single file): [exact command with placeholder]
- Integration tests: [exact command]
- E2E tests: [exact command, if applicable]
- Local dev server: [exact command]

## Project-specific rules
[Things unique to this project that Claude would get wrong without guidance]
- [Architectural patterns to follow]
- [Naming conventions]
- [Import conventions]
- [Error handling patterns]
- [Any "we do X instead of Y" deviations from framework defaults]

## Database and migrations
[If applicable]
- Migration tool: [name]
- Create migration: [exact command]
- Run migrations: [exact command]
- IMPORTANT: Never write destructive migrations (DROP COLUMN, DROP TABLE) directly. Use expand/contract — see the migration-safe skill.

## Key dependencies and patterns
[2-5 bullet points about non-obvious architectural decisions Claude needs to respect]

## Where to find design intent
- PRDs and tech specs: [Notion workspace or URL pattern]
- ADRs: docs/adr/
- If an Issue lacks a Notion link or clear acceptance criteria, stop and ask.
```

### Steps
1. Draft the complete CLAUDE.md using everything discovered in Phase 1
2. Show me the full draft with line count
3. Wait for my approval (I will likely edit — project-specific rules require my domain knowledge)
4. Write the file
5. Verify: re-read it, confirm line count

**Output:** The written file with line count. Then STOP.

---

## PHASE 3: Create project-level skills

**Goal:** Create skills in `.claude/skills/` tailored to this project's toolchain.

### Skill 1: `fix-issue`

Adapt to this project's specific test/lint/build commands. If the user-level `~/.claude/skills/fix-issue/` already exists, the project-level version should be MORE specific (exact commands, exact file patterns).

`.claude/skills/fix-issue/SKILL.md`:

```markdown
---
name: fix-issue
description: Implement a single GitHub issue end-to-end with exploration, planning, TDD, verification, and a PR. Tailored to [project name].
---
Fix GitHub issue $ARGUMENTS.

Process:
1. Explore: Read the Issue (use `gh issue view $ARGUMENTS`). Follow any linked Notion docs. Read relevant source files. Summarize current behavior and risks. Do not change code yet.
2. Plan: Propose a stepwise plan with:
   - Files to modify
   - Test strategy (which test files, what assertions)
   - Verification commands: `[PROJECT-SPECIFIC lint command]`, `[PROJECT-SPECIFIC test command]`
   Wait for approval.
3. Implement: Write tests first where possible. Change minimal code to satisfy acceptance criteria. Follow patterns in CLAUDE.md.
4. Verify: Run:
   - `[PROJECT-SPECIFIC lint command]`
   - `[PROJECT-SPECIFIC typecheck command]`
   - `[PROJECT-SPECIFIC test command for affected files]`
   Capture and report results. Iterate until green.
5. PR: Create branch, commit, and open PR using `gh pr create`. Fill the PR template completely.

Rules:
- If acceptance criteria are unclear or missing, stop and ask.
- Keep changes minimal and aligned to existing patterns.
- Every behavior change needs a test.
```

**Replace all `[PROJECT-SPECIFIC ...]` placeholders with actual commands from Phase 1 discovery.**

### Skill 2: `pr-ready`

`.claude/skills/pr-ready/SKILL.md` — adapt the verification commands to this project.

### Skill 3: `qa-sweep`

`.claude/skills/qa-sweep/SKILL.md`:

```markdown
---
name: qa-sweep
description: Run the full test suite for a specific package or service and report only failures. Use when you need a clean pass/fail summary without verbose output in the main context.
---
Run QA sweep for: $ARGUMENTS (package name, service name, or "all")

Steps:
1. Run the relevant test suite: [PROJECT-SPECIFIC commands, parameterized by $ARGUMENTS]
2. If all pass: report "[N] tests passed, 0 failed"
3. If any fail: report each failure with:
   - Test name
   - Assertion that failed
   - Relevant file and line
4. Do NOT dump full stdout/stderr — summarize failures only
```

### Skill 4: `migration-safe` (only if project uses a database)

Adapt to the project's specific migration tool (Prisma, Drizzle, Alembic, Knex, etc.).

### Skill 5: `actions-review`

`.claude/skills/actions-review/SKILL.md`:

```markdown
---
name: actions-review
description: Review GitHub Actions workflow changes for security best practices — SHA pinning, least-privilege tokens, safe triggers, environment protections.
---
Review workflow changes in the current diff or in $ARGUMENTS.

Check for:
1. Third-party actions pinned to full commit SHAs (not tags like @v4)
2. GITHUB_TOKEN permissions set at job level with least privilege
3. No dangerous patterns: `pull_request_target` checking out PR code, `workflow_run` without restrictions
4. Production deployments use environment protection rules (required reviewers, wait timers)
5. No secrets exposed in forked PR contexts
6. OIDC preferred over long-lived cloud credentials

Output: Prioritized findings (Critical / Warning / Info) with specific fix suggestions including exact SHAs where possible.
```

### Steps
1. Show me all skill files with project-specific commands filled in
2. Wait for my approval
3. Create the directories and files
4. Verify: `ls .claude/skills/` and read back each file

**Output:** List of created skills. Then STOP.

---

## PHASE 4: Create subagents

**Goal:** Create subagents in `.claude/agents/` tailored to this project.

### Agent 1: `code-reviewer`

`.claude/agents/code-reviewer.md`:

```markdown
---
name: code-reviewer
description: Adversarial code review for [project name]. Focuses on logic errors, edge cases, regressions, and [PROJECT-SPECIFIC concerns like tenant isolation, API backward compatibility, etc.].
tools: Read, Glob, Grep
model: sonnet
---
You are a senior code reviewer for [brief project description].

Focus areas:
- Logic errors and off-by-one mistakes
- Unhandled edge cases (null, empty, boundary values, [PROJECT-SPECIFIC edge cases])
- Regressions to existing behavior
- Missing error handling
- [PROJECT-SPECIFIC: e.g., "Tenant isolation violations — every data query must scope to the authenticated tenant"]
- [PROJECT-SPECIFIC: e.g., "API backward compatibility — no breaking changes to public endpoints"]
- Performance concerns (N+1 queries, unbounded loops, missing pagination)

Output: Prioritized findings with severity (Critical / Warning / Nit) and suggested fixes.
Do NOT flag style issues — the formatter and linter handle that.
```

### Agent 2: `security-reviewer`

Adapt to the project's specific security concerns (multi-tenant? API auth model? sensitive data types?).

### Agent 3: `test-runner`

Adapt to the project's test commands and framework.

### Agent 4: `workflow-guardian`

This one is mostly generic — use the template from the optimization guide, but reference this project's deployment targets if known.

### Steps
1. Show me all agent files with project-specific details filled in
2. Wait for my approval
3. Create the files
4. Verify: `ls .claude/agents/` and read back each file

**Output:** List of created agents. Then STOP.

---

## PHASE 5: Create rules files

**Goal:** Create `.claude/rules/` files for area-specific conventions that would bloat CLAUDE.md.

The exact rules files depend on what you found in Phase 1. Common patterns:

- **`backend.md`** — API conventions, error response format, auth middleware patterns, database access patterns, logging conventions
- **`frontend.md`** — Component patterns, state management, styling approach, accessibility requirements
- **`migrations.md`** — Migration naming, expand/contract enforcement, rollback requirements, lock-time limits
- **`api.md`** — Endpoint naming, request/response schemas, versioning strategy, pagination patterns
- **`testing.md`** — Test organization, fixture patterns, mock conventions, what requires integration vs unit tests

**Only create rules files for areas where this project has non-obvious conventions that Claude would get wrong.** Don't create a rules file that just restates framework defaults.

### Steps
1. Based on Phase 1 findings, propose which rules files are needed and a brief outline of each
2. Wait for my approval
3. Draft the files (each should be 20-50 lines — short and actionable)
4. Show me the drafts
5. Wait for my approval
6. Create the files
7. Verify

**Output:** List of created rules files. Then STOP.

---

## PHASE 6: Configure hooks

**Goal:** Add deterministic hooks to `.claude/settings.json` for this project.

### Hook 1: PostToolUse — Auto-format after edits

Create `scripts/claude-hooks/format-touched-files.sh` using the project's actual formatter:

```bash
#!/bin/bash
# Adapt to this project's formatter
# Examples:
#   npx prettier --write "$CLAUDE_FILE_PATH"
#   black "$CLAUDE_FILE_PATH"
#   rustfmt "$CLAUDE_FILE_PATH"
#   gofmt -w "$CLAUDE_FILE_PATH"
```

### Hook 2: PreToolUse — Block writes to protected paths

Create `scripts/claude-hooks/block-protected-paths.sh`:

```bash
#!/bin/bash
FILE="$CLAUDE_FILE_PATH"
BLOCKED_PATTERNS=(
  ".github/workflows/"
  ".env"
  "*.pem"
  "*.key"
)
# Add migrations/ to BLOCKED_PATTERNS if project uses a database
# Add any other project-specific protected paths

for pattern in "${BLOCKED_PATTERNS[@]}"; do
  if [[ "$FILE" == *"$pattern"* ]]; then
    echo '{"ok": false, "reason": "Protected path: '"$pattern"'. Create changes in a working file first and request human review."}'
    exit 0
  fi
done
echo '{"ok": true}'
```

### Hook 3: Stop — Completeness check

A prompt-type hook that checks acceptance criteria before Claude declares itself done.

### Hooks configuration

Write `.claude/settings.json` (or merge into existing if one already exists):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "scripts/claude-hooks/format-touched-files.sh"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "scripts/claude-hooks/block-protected-paths.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Before finishing: (1) Are all acceptance criteria from the Issue met? (2) Do lint and tests pass? (3) Is verification evidence ready for the PR? If any answer is no, say what remains and keep working."
          }
        ]
      }
    ]
  }
}
```

### Steps
1. Determine the correct formatter command from Phase 1
2. Determine project-specific protected paths
3. Show me the complete hook scripts and settings.json
4. Wait for my approval
5. Create the scripts directory, scripts (with `chmod +x`), and settings.json
6. Verify: read back all files, confirm scripts are executable

**IMPORTANT:** If `.claude/settings.json` already exists with other configuration, MERGE the hooks into it rather than overwriting.

**Output:** Created files and their contents. Then STOP.

---

## PHASE 7: Create GitHub templates

**Goal:** Create Issue templates and PR template that are "Claude-ready" — clear scope, explicit verification, strong constraints.

### Issue templates

Create `.github/ISSUE_TEMPLATE/config.yml`:
```yaml
blank_issues_enabled: false
contact_links: []
```

Create `.github/ISSUE_TEMPLATE/feature.md`:
```markdown
---
name: Feature
about: Deliver a user-visible feature or capability.
title: "[Feature] "
labels: ["feature"]
assignees: []
---

## Summary
What are we building? One paragraph.

## User value / problem
Why does this matter? Who benefits?

## Scope
### In scope
- 

### Out of scope
- 

## Acceptance criteria
- [ ] 
- [ ] 

## Design references
- Notion PRD: 
- Notion Tech Spec: 
- ADRs: 

## Constraints / invariants
- Tenancy boundary rules:
- Backward compatibility:
- Performance/SLO:

## Verification
### Local
- [ ] `...` (command)
- [ ] `...`

### CI expectations
- [ ] Unit tests
- [ ] Integration tests
- [ ] Security scans (if applicable)

## Rollout / rollback
- Feature flag? (yes/no)
- Migration required? (yes/no)
- Rollback plan:
```

Create `.github/ISSUE_TEMPLATE/bug.md`:
```markdown
---
name: Bug report
about: Something is broken; requires fix with regression coverage.
title: "[Bug] "
labels: ["bug"]
assignees: []
---

## Symptom
What is happening vs what should happen?

## Impact
Who is affected? Severity? Frequency?

## Reproduction steps
1.
2.
3.

## Expected behavior
Describe the correct behavior.

## Suspected area
Paths/files/services if known.

## Logs / screenshots
Paste minimal relevant excerpts.

## Acceptance criteria
- [ ] Regression test that fails before fix and passes after
- [ ] Root cause fixed (not symptom suppression)
- [ ] Verified with commands below

## Verification commands
- [ ] `...`
- [ ] `...`
```

Create `.github/ISSUE_TEMPLATE/tech-debt.md`:
```markdown
---
name: Tech debt / refactor
about: Refactor, cleanup, performance, maintainability work.
title: "[TechDebt] "
labels: ["tech-debt"]
assignees: []
---

## Motivation
Why now? What risk or cost does this reduce?

## Target outcome
What will be different when done?

## Non-goals
What are we explicitly not changing?

## Constraints
Backward compatibility, APIs, migrations, performance.

## Acceptance criteria
- [ ] No behavior change (unless explicitly stated)
- [ ] Tests updated/added to preserve behavior
- [ ] Performance not worse (add benchmark if needed)

## Verification
- [ ] `...`
```

Create `.github/pull_request_template.md`:
```markdown
## What
Concise description of what this PR does.

## Why
User value and/or engineering reason.

## Linked work
- Issue: #
- Notion PRD:
- Notion Tech Spec:

## Scope
### In scope
- 

### Out of scope
- 

## How it works
Short explanation + notes on risky areas.

## How to verify
### Local
- `...`

### Tests added/updated
- [ ] Unit
- [ ] Integration
- [ ] E2E
- [ ] Visual (if UI)

## Rollout plan
- Feature flag:
- Migration:
- Staging validation:
- Production steps:

## Security / privacy checklist
- [ ] No secrets in code/logs
- [ ] Input validation for new endpoints
- [ ] AuthZ checked for tenant boundaries
- [ ] Least-privilege changes only

## Screenshots / logs (if applicable)
```

### Steps
1. Check if `.github/ISSUE_TEMPLATE/` or `.github/pull_request_template.md` already exist. If so, show me their current contents so we can decide whether to replace or merge.
2. Show me all template files (adapt wording if needed for this project's domain)
3. Wait for my approval
4. Create the files
5. Verify

**Output:** List of created templates. Then STOP.

---

## PHASE 8: Create CODEOWNERS

**Goal:** Require review for security-sensitive paths.

**Ask me** for GitHub usernames if you don't have them yet.

Create `.github/CODEOWNERS`:

```
# Require review for CI/CD and infrastructure
.github/workflows/    @[owner1] @[owner2]
.claude/              @[owner1]

# Require review for security-sensitive paths
*.pem                 @[owner1]
*.key                 @[owner1]
.env*                 @[owner1]
```

If the project has a database, add:
```
migrations/           @[owner1] @[owner2]
```

### Steps
1. Ask me for GitHub usernames if needed
2. Propose the CODEOWNERS file based on project structure
3. Wait for my approval
4. Create the file
5. Verify

**Output:** The CODEOWNERS file. Then STOP.

---

## PHASE 9: Audit existing GitHub Actions workflows

**Goal:** If CI/CD workflows already exist, review them against security best practices. If none exist, skip this phase.

For each workflow file in `.github/workflows/`:

1. **SHA pinning:** Are third-party actions pinned to full commit SHAs? If using tags like `@v4`, flag and propose the pinned SHA.
2. **Token permissions:** Is `permissions:` set explicitly at workflow or job level? Flag any that use the broad default.
3. **Dangerous triggers:** Flag any use of `pull_request_target` or `workflow_run` without restrictions.
4. **Secrets in fork context:** Flag any secrets used in workflows triggered by external PRs.
5. **Environment protections:** Are production deployments gated by environment approval rules?
6. **OIDC vs long-lived keys:** Flag any long-lived cloud credentials that could be replaced with OIDC.

### Steps
1. Read all workflow files and present findings in a table: workflow name, finding, severity, recommended fix
2. Wait for my approval on which fixes to apply
3. Apply approved fixes
4. Verify

**If no workflows exist:** Propose a minimal CI workflow (lint + typecheck + test on PR) using this project's toolchain. Show me the draft. Wait for approval.

**Output:** Findings table and any changes made. Then STOP.

---

## PHASE 10: Create docs/adr directory

**Goal:** Establish the ADR (Architecture Decision Record) directory and a template.

Create `docs/adr/` if it doesn't exist.

Create `docs/adr/000-template.md`:
```markdown
# [ADR-NNN] [Title]

**Status:** Proposed | Accepted | Deprecated | Superseded by ADR-NNN
**Date:** YYYY-MM-DD
**Decision makers:** [names]

## Context
What is the situation? What forces are at play?

## Decision
What did we decide?

## Consequences
What are the positive and negative outcomes of this decision?

## Alternatives considered
What other options were evaluated and why were they rejected?
```

### Steps
1. Check if `docs/adr/` exists
2. Create directory and template if needed
3. Verify

**Output:** Confirmation. Then STOP.

---

## PHASE 11: Final verification and commit preparation

**Goal:** Verify everything is consistent, then prepare for a single commit of the entire harness.

### Verification checklist
1. `cat CLAUDE.md | wc -l` — confirm 100-120 lines
2. `ls .claude/skills/` — list all project skills
3. `ls .claude/agents/` — list all subagents
4. `ls .claude/rules/` — list all rules files (if any)
5. `cat .claude/settings.json | python3 -m json.tool` — confirm valid JSON with hooks
6. `ls scripts/claude-hooks/` — confirm hook scripts exist and are executable
7. `ls .github/ISSUE_TEMPLATE/` — confirm templates
8. `cat .github/pull_request_template.md | head -5` — confirm PR template
9. `cat .github/CODEOWNERS` — confirm CODEOWNERS
10. `ls docs/adr/` — confirm ADR directory
11. Dry-run: can you successfully run the lint command from CLAUDE.md? Try it.
12. Dry-run: can you successfully run the test command from CLAUDE.md? Try it.

### Prepare commit
Show me the full list of new and modified files with `git status`. Propose a commit message.

**Do NOT commit yet.** Wait for my explicit approval to commit.

### Final summary report
Output:
- Complete inventory of everything created
- Any files that were modified (vs created from scratch)
- Any phases that were skipped and why
- Follow-up items that require manual action:
  - Branch protection rules (must be set in GitHub UI or via API)
  - Environment protection rules (GitHub UI)
  - Secret scanning / push protection (GitHub UI)
  - Dependabot enablement (GitHub UI)
  - Any MCP server decisions deferred

**Output:** Verification results, file list, commit message, and follow-up items. Then STOP and wait for my "commit" instruction.

---

## NOTES FOR SESSION RECOVERY

If this task spans multiple sessions, each phase summary is the recovery log. At the start of a new session, say:

> "I'm continuing the project-level harness setup. The last completed phase was Phase [N]. Let me verify current state before starting Phase [N+1]."

Then re-check relevant file state before proceeding.

## END OF PROMPT
