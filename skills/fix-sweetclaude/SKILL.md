---
spdx-license: AGPL-3.0-or-later
description: "Audit and repair SweetClaude's own configuration for this project. Checks CLAUDE.md accuracy, phase state vs reality, file locations, skills.yaml vs artifact parity, onboarding gaps, empty registers, and untracked files. Proposes fixes for user approval."
---

!`cat .sweetclaude/state/session-state.yaml 2>/dev/null || echo "STATE_NOT_FOUND"`

# SweetClaude Fix Config

Audit this project's SweetClaude setup. Fix what is broken.

**This skill changes SweetClaude configuration, not project code. Every change is proposed before applied.**

---

## Step 1: Check .sweetclaude/ state exists

If `.sweetclaude/state/phase.yaml` does not exist:
> "SweetClaude is not set up for this project. Run `/sweetclaude:on` first."

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
| `.sweetclaude/state/` | phase.yaml, project.yaml, skills.yaml, decision-log, assumption-register, improvement-register, scope-changes |
| `docs/` | product-brief, prd, architecture, tech-spec, data-model, api-design, workflows (if they exist anywhere in the project) |
| `.sweetclaude/stories/` | user stories and .feature files (if they exist) |
| `.sweetclaude/backlog/` | BACKLOG-INDEX.md and item detail files (if product-parking-lot has been used) |
| `.sweetclaude/milestones/` | milestone detail files (if product-milestones has been used) |
| `.sweetclaude/sprints/` | sprint files (if product-sprint-plan has been used) |
| `.sweetclaude/traceability/` | requirements-map, ripple-map |
| `strategy/` | concept, pain-thesis, ICP, competitive, etc. (at project root, NOT inside .sweetclaude/) |

If artifacts exist but in the wrong location (e.g., specs at `.sweetclaude/specs/` instead of `docs/`):

Use AskUserQuestion with these options:
- "Move it" — relocate {artifact} from {actual location} to {expected location}
- "Symlink it" — create a link at {expected location} pointing to {actual location}
- "Leave it" — update SweetClaude's reference to look at {actual location}

Do not assume. The user may have good reasons for the current location.

---

## Step 5: Audit skills.yaml and onboarding state

**5a: Resolve base_path**

Read `.sweetclaude/artifact-privacy.yaml` → `categories.product.base_path`. If absent, use `.sweetclaude/artifacts/product` as fallback.

**5b: Bootstrap skills.yaml if needed**

Read `.sweetclaude/state/skills.yaml` if it exists.

For each of the six data-owning skills, check whether it is present in `skills.yaml`. Use the following signals to infer state for any missing entry:

| Skill | Artifact signal (file exists → was in use) |
|---|---|
| `product-milestones` | `{base_path}/milestones/MILESTONES-INDEX.md` |
| `product-parking-lot` | `{base_path}/backlog/BACKLOG-INDEX.md` |
| `product-sprint-plan` | *(no inference — write `enabled: false` if absent)* |
| `product-user-personas` | `.sweetclaude/state/personas.yaml` |
| `product-user-stories` | any `US-*.md` under `{base_path}/stories/` |
| `document-corpus` | `.sweetclaude/state/corpus-pipeline.yaml` |

If `skills.yaml` is missing entirely: propose creating it (schema v2) with entries inferred from the above.
If entries are missing from an existing `skills.yaml`: propose adding them with the inferred state.
If `skills.yaml` is schema v1: propose migrating to v2 (same mapping as the update skill's 8e migration step).

> "skills.yaml is missing / has gaps / is schema v1. Based on artifacts on disk: backlog=active, milestones=uninitialized, … Write/migrate it?"

On user approval: write or update `skills.yaml` using atomic write (temp file → rename). Use v2 schema:
- Data file exists → `status: active`, `last_changed_at: {today}`, `last_changed_by: migrated`
- Data file missing → `status: uninitialized`, `last_changed_at: ~`, `last_changed_by: ~`
Do not remove or modify entries that are already present and consistent.

**5c: Flag remaining mismatches**

After bootstrap, re-read `skills.yaml` and check for inconsistencies:

| Situation | Flag |
|---|---|
| `status: active` but no artifacts on disk | "Skill marked active but no artifacts found — partial deletion or failed onboard. Re-run onboard?" |
| `status: uninitialized` or `status: paused` but artifacts clearly exist on disk | "Artifacts found but skill not active — skills.yaml may be stale. Mark active?" |
| `status: paused` — data intact | No flag needed. Paused is an intentional state. |

Propose a fix for each mismatch. Do not auto-apply.

**5d: Offer onboarding for unenabled skills**

After resolving all mismatches, check `skills.yaml` for any skill with `enabled: false`.

If any exist, ask:
> "These skills are not yet set up for this project: {list}. Would you like to onboard any of them now? Enter keywords (e.g. 'milestones backlog') or 'none' to skip."

| Keyword | Skill |
|---|---|
| `milestones` | `product-milestones` |
| `backlog` | `product-parking-lot` |
| `sprint` | `product-sprint-plan` |
| `personas` | `product-user-personas` |
| `stories` | `product-user-stories` |
| `corpus` | `document-corpus` |

For each skill the user enables, invoke it with argument `onboard`. Complete each onboard before starting the next.

---

## Step 6: Audit registers

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

## Step 7: Audit hook registrations

Read `~/.claude/hooks/sweetclaude/hooks-manifest.json`. For each entry with `"required": true`, verify that its `file` is referenced in `~/.claude/hooks/sweetclaude/hooks.json`.

```bash
python3 -c "
import json
manifest = json.load(open('$HOME/.claude/hooks/sweetclaude/hooks-manifest.json'))
hooks_json = open('$HOME/.claude/hooks/sweetclaude/hooks.json').read()
missing = [h['file'] for h in manifest['hooks'] if h.get('required') and h['file'] not in hooks_json]
print('\n'.join(missing) if missing else 'OK')
"
```

If any required hooks are missing:
> "These required hooks are not registered in hooks.json: {list}. Add them?"

If user says yes, add the missing entries to `hooks.json` using the `event`, `matcher`, and `file` fields from the manifest. Write atomically (temp file → rename).

Also check for hooks registered in `hooks.json` that have no corresponding entry in `hooks-manifest.json` (unrecognized hooks):
> "hooks.json has entries not in the manifest: {list}. These may be from another plugin or manually added. Review?"

Only flag — do not remove.

If `hooks-manifest.json` does not exist:
> "hooks-manifest.json is missing from the hooks directory. This file should have been installed with SweetClaude. Run `install.sh` from the SweetClaude repo to restore it."

---

## Step 8: Check for untracked SweetClaude files

Run `git status` on the project. Check if `.sweetclaude/` and `strategy/` have untracked or uncommitted files:

> "These SweetClaude files are not tracked in git: {list}. Commit them?"

---

## Step 9: Report

Present a summary:

```
SweetClaude Config Audit — {project}
═════════════════════════════════════

Phase state:    {✓ correct | ⚠ stale → recommended fix}
CLAUDE.md:      {✓ accurate | ⚠ {N} issues found}
File locations: {✓ correct | ⚠ {N} misplaced artifacts}
Skills / onboard: {✓ in sync | ⚠ {N} mismatches}
Registers:      {✓ populated | ⚠ empty on active project}
Hooks:          {✓ all registered | ⚠ {N} missing | hooks-manifest.json missing}
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
