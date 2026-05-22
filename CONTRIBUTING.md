# Contributing to SweetClaude

SweetClaude is AGPL-3.0. Contributions are welcome.

---

## Where to Start

The lowest-friction contribution surface is the **product and design skills** (`skills/product-*/SKILL.md`, `skills/design-*/SKILL.md`). These skills have isolated state footprints — they read and write their own data files, don't modify shared state like `sweetclaude.yaml`, and don't require knowledge of the hook system or subagent architecture to improve.

**Good first contributions:**

| Area | What to work on | State footprint |
|---|---|---|
| `skills/product-user-personas/SKILL.md` | Interview flow improvements, persona template structure | `state/personas.yaml` only |
| `skills/product-competition/SKILL.md` | Competitive analysis depth, SWOT structure | `strategy/` directory only |
| `skills/design-manage-decisions/SKILL.md` | Decision log format, query interface | `state/decision-log.md` only |
| `skills/misc-meeting-prep/SKILL.md` | Meeting types, debrief capture | No persistent state |
| `docs/user-guide/` | Clarifications, walkthroughs, examples | Docs only |

Start here. You don't need to understand the phase pipeline, the hook system, or the migration architecture to improve these.

---

## Skill File Structure

Every skill is a single `SKILL.md` file in `skills/{name}/`:

```
skills/
└── product-user-personas/
    └── SKILL.md
```

A skill file has YAML frontmatter and markdown body:

```markdown
---
spdx-license: AGPL-3.0-or-later
name: sweetclaude:product-user-personas
description: "One-line description — appears in /sweetclaude:help and the skills catalog"
---

# Skill Title

Brief description of what this skill does.

## Step 1: ...
## Step 2: ...
```

The body is instruction text that Claude follows when the skill is invoked. No code, no compiled artifacts. The skill is the instructions.

---

## Contribution Guidelines

**Skills are instructions, not programs.** Claude follows them; they don't run deterministically. Write clearly, be specific, and test against the actual model.

**Test your skill before submitting.** Run it in a real Claude Code session. Check that the behavior matches what the SKILL.md describes. If it doesn't, the skill is wrong — update it.

**Don't touch `sweetclaude.yaml` from product or design skills.** Those skills have isolated state footprints by design. Phase state is managed by the orchestration layer (the `/sweetclaude` front door and its internal sub-skills).

**Don't add behavioral claims that aren't tested.** If you add a property like "always asks for a concrete example," verify it holds during testing. See `skills/behavioral-regression/SKILL.md` for the test protocol.

**Sync to installed locations after editing.** Skills in the repo are not automatically live. After editing, run:

```bash
bash scripts/sync-to-installed.sh
```

This syncs hooks, skills, scripts, and config to all installed locations with safety gates (phase check, test validation, backup). Installed hooks are backed up to `hooks.bak/` before overwriting — if a sync breaks your hooks, recover with `cp hooks.bak/<hook>.sh hooks/<hook>.sh` at the installed path. Use `--dry-run` to preview without syncing. See `scripts/sync-to-installed.sh` for details.

---

## What Requires Full Framework Knowledge

These areas touch shared infrastructure and are higher-risk:

| Area | Why it's complex |
|---|---|
| `skills/update/SKILL.md` | Touches migration logic, all state files, installed plugin metadata |
| `skills/on/SKILL.md` | Bootstraps the entire `.sweetclaude/` state directory |
| `skills/master/SKILL.md` | Internal session orchestrator; pre-flight, routing, deference (invoked by the `/sweetclaude` front door in `skills/sweetclaude/SKILL.md`) |
| `hooks/*.sh` | Deterministic enforcement; bugs here affect every session |
| `config/migration-registry.yaml` | Pre-declares migrations; wrong entries cause update failures |

Don't start here unless you've already contributed to the simpler skill surface and understand how the state schema works.

---

## Running the Behavioral Regression Tests

After any significant skill edit, run the behavioral regression tests to check that the change doesn't break existing contracts:

```
/sweetclaude:behavioral-regression
```

This runs 15 tests against the current model version. If your change causes a FAIL on a contract that was previously PASS, investigate before submitting.

---

## Dev Setup

After cloning, activate the pre-commit hook that blocks gitignored files from entering history:

```bash
git config core.hooksPath .githooks
```

---

## Submitting

1. Fork the repo
2. Make your change in a branch
3. Test in a real Claude Code session
4. Run `/sweetclaude:behavioral-regression` if you touched a skill with behavioral contracts
5. Open a PR with: what you changed, why, and what you tested

PRs that include test results from a real session are much more likely to be merged quickly.

---

## Cutting a release

Version bumping is operator-driven, not automated. There is no commit hook that bumps `package.json` automatically.

To bump the version:

```bash
scripts/bump-version.sh patch   # 4.0.9-beta → 4.0.10-beta
scripts/bump-version.sh minor   # 4.0.9-beta → 4.1.0-beta
scripts/bump-version.sh major   # 4.0.9-beta → 5.0.0-beta
```

The script:

- Updates `package.json` with the new version.
- Converts the `[Unreleased]` section in `CHANGELOG.md` to the new version heading and adds a fresh `[Unreleased]` section.
- Preserves any prerelease suffix (e.g., `-beta`).
- Does **not** commit or tag. Review the changes, then commit and push yourself:

```bash
git add package.json CHANGELOG.md
git commit -m 'chore(release): v4.0.10-beta'
git push origin main
```

Use `--dry-run` to preview the version change without modifying files.
