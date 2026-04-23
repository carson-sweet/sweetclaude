---
description: "Audit and repair SweetClaude's own configuration for this project. Checks CLAUDE.md accuracy, phase state vs reality, file locations, stale references, empty registers, untracked files. Proposes fixes for user approval."
---

# SweetClaude Fix Config

Audit this project's SweetClaude setup. Fix what is broken.

**This skill changes SweetClaude configuration, not project code. Every change is proposed before applied.**

---

## Step 1: Check .sweetclaude/ state exists

If `.sweetclaude/state/phase.yaml` does not exist:
> "SweetClaude is not set up for this project. Run `/sweetclaude:init` or `/sweetclaude:sherpa-adopt` first."

Stop. Do not proceed.

---

## Step 2: Audit phase state vs reality

Read `.sweetclaude/state/phase.yaml`. Then assess the actual project state:

1. Check git log — how many commits? How recent? What kind of work?
2. Check for implementation artifacts — source code, tests, builds
3. Check for product artifacts — PRD, product brief, specs, stories
4. Check for design artifacts — architecture docs, tech specs, ADRs
5. Check for strategy artifacts — concept, pain thesis, competitive analysis

Compare what the phase says vs what actually exists:

| phase.yaml says | Project actually has | Assessment |
|---|---|---|
| DISCOVER | Substantial code, tests, deployed | Phase is stale — should be IMPLEMENT or later |
| DISCOVER | PRD and architecture but no code | Phase should be PLAN or DESIGN |
| IMPLEMENT | Only a concept doc | Phase is ahead of reality |

If phase does not match reality, propose the correction:
> "phase.yaml says {current}. The project is actually in {recommended} based on: {evidence}. Update?"

---

## Step 3: Audit CLAUDE.md

Read the project's CLAUDE.md. Check:

1. **Repo structure section** — does it list directories that actually exist? Does it omit directories that do exist?
   - `ls` key directories and compare against what CLAUDE.md claims
   - Flag: directories listed but missing, directories that exist but are not listed

2. **Build/test/lint commands** — are they accurate?
   - Check package.json scripts, Makefile, pyproject.toml against what CLAUDE.md says
   - Try running the test command to see if it works

3. **SweetClaude section** — is it present and correct?
   - Should reference `.sweetclaude/state/phase.yaml`
   - Should have the pre-flight invocation instruction
   - Should NOT reference a "working repo"

4. **Project description** — is it still accurate?

For each issue found, propose a specific fix:
> "CLAUDE.md says {wrong thing}. Actual: {right thing}. Fix?"

---

## Step 4: Audit file locations

Check that artifacts are where SweetClaude expects them:

| Expected Location | Check |
|---|---|
| `.sweetclaude/state/` | phase.yaml, project.yaml, decision-log, assumption-register, improvement-register, scope-changes |
| `docs/` | product-brief, prd, architecture, tech-spec, data-model, api-design, workflows (if they exist anywhere in the project) |
| `.sweetclaude/stories/` | user stories and .feature files (if they exist) |
| `.sweetclaude/traceability/` | requirements-map, ripple-map |
| `strategy/` | concept, pain-thesis, ICP, competitive, etc. (at project root, NOT inside .sweetclaude/) |

If artifacts exist but in the wrong location (e.g., specs at `.sweetclaude/specs/` instead of `docs/`):

Use AskUserQuestion with these options:
- "Move it" — relocate {artifact} from {actual location} to {expected location}
- "Symlink it" — create a link at {expected location} pointing to {actual location}
- "Leave it" — update SweetClaude's reference to look at {actual location}

Do not assume. The user may have good reasons for the current location.

---

## Step 5: Audit registers

Check if SweetClaude's tracking registers have content:
- `.sweetclaude/state/decision-log.md` — any entries?
- `.sweetclaude/state/assumption-register.md` — any entries?
- `.sweetclaude/state/improvement-register.md` — any entries?
- `.sweetclaude/state/scope-changes.md` — any entries?

If all are empty on a project with substantial history:
> "All SweetClaude registers are empty. The project has {N} commits and existing docs. Populate them from git history and existing docs? This gives SweetClaude context about past decisions."

If user says yes, scan git log and existing docs for:
- Decisions: architecture choices, technology selections, scope changes visible in commits
- Assumptions: things implied by the current implementation
- Scope: features that were added or removed based on commit history

Populate as draft entries marked `[retroactive]` for user review.

---

## Step 6: Check for untracked SweetClaude files

Run `git status` on the project. Check if `.sweetclaude/` and `strategy/` have untracked or uncommitted files:

> "These SweetClaude files are not tracked in git: {list}. Commit them?"

---

## Step 7: Report

Present a summary:

```
SweetClaude Config Audit — {project}
═════════════════════════════════════

Phase state:    {✓ correct | ⚠ stale → recommended fix}
CLAUDE.md:      {✓ accurate | ⚠ {N} issues found}
File locations: {✓ correct | ⚠ {N} misplaced artifacts}
Registers:      {✓ populated | ⚠ empty on active project}
Git tracking:   {✓ clean | ⚠ {N} untracked files}

→ Proposed fixes: {N}
```

List each proposed fix. Wait for user to approve individually or as a batch.

---

## Rules

- **Propose, do not apply.** Every change needs user approval.
- **Do not move project files without asking.** The user may have reasons for current locations.
- **Retroactive register entries are drafts.** Mark them `[retroactive]` so the user knows they were not captured in real-time.
- **Do not judge the project.** This skill fixes SweetClaude configuration, not project quality.
