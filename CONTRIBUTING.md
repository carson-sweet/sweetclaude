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

**Don't add behavioral claims that aren't tested.** If you add a property like "always asks for a concrete example," verify it holds during testing. See `config/behavioral-contracts.md` for the contracts and `scripts/behavioral_judge.py` for scoring.

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
| `skills/update/SKILL.md` | Syncs framework files and plugin metadata; must not run project-state migrations inline |
| `skills/doctor/SKILL.md` and `scripts/doctor.py` | Diagnostic scan, repair menu, maintenance routing, prompted fixes |
| `skills/recover/SKILL.md` and `scripts/recovery/` | Snapshot-backed recovery for bad update, migration, doctor, or repair states |
| `skills/migrate/SKILL.md` and `scripts/migrate/` | Guarded taxonomy migration; must honor preflight and recovery routing |
| `skills/on/SKILL.md` | Bootstraps the entire `.sweetclaude/` state directory |
| `skills/master/SKILL.md` | Internal session orchestrator; pre-flight, routing, deference (invoked by the `/sweetclaude` front door in `skills/sweetclaude/SKILL.md`) |
| `hooks/*.sh` | Deterministic enforcement; bugs here affect every session |
| `config/migration-registry.yaml` | Pre-declares migrations; wrong entries cause update failures |

Don't start here unless you've already contributed to the simpler skill surface and understand how the state schema works.

---

## Running the Test Suite

Install the test dependencies once:

```
bash scripts/setup-dev.sh
```

Then:

```
python3 -m pytest tests/ -q
```

Use the setup script rather than plain `pip install`. Playwright pins an exact
browser revision per package release and will not fall back to an older build,
so installing the package without downloading the matching browser leaves
`tests/test_dashboard_ui.py` failing with "Executable doesn't exist". The script
does both. Re-run it after changing the pinned `playwright` version in
`requirements-dev.txt`.

---

## Linting

Ruff is the linter. The rule set and the test-tree exemptions live in
`ruff.toml`; the version is pinned in `requirements-dev.txt` (installed by
`scripts/setup-dev.sh`). Run it before submitting:

```
ruff check .
```

CI runs the same command on every pull request
(`tests/test_ci_workflows.py` holds that contract).

---

## Running the Behavioral Tests

If you change a router, a category command, or a library `INDEX.md`, run the routing suite. It sends real requests through `/sweetclaude:go` and checks which workflow each one reaches:

```
python3 scripts/routing_behavior.py --tier smoke   # 6 cases, about $0.90
python3 scripts/routing_behavior.py --tier full    # 33 cases, about $4.50
```

See `docs/testing/behavioral-e2e/README.md` for how cases are graded.

If you touched a skill with behavioral contracts, score a session transcript against the contract it affects:

```
python3 scripts/behavioral_judge.py score --transcript <session.jsonl> --contract CONTRACT-NN
```

The contracts are listed in `config/behavioral-contracts.md`. If your change causes a FAIL on a contract that was previously PASS, investigate before submitting.

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
4. Score a session with `python3 scripts/behavioral_judge.py score --transcript <session.jsonl> --contract CONTRACT-NN` if you touched a skill with behavioral contracts
5. Open a PR with: what you changed, why, and what you tested

PRs that include test results from a real session are much more likely to be merged quickly.

---

## Cutting a release

Releases are cut by hand from `main`. Nothing bumps the version automatically, and there is no release branch.

### 1. Write the changelog entry

Add a section to the top of `CHANGELOG.md`, above the previous release:

```markdown
## [5.1.3] — 2026-11-10

### Fixed — short description of the change

What was wrong, what changed, and anything users need to do.

---
```

The release workflow publishes this section as the GitHub release notes. It copies every line between the `## [x.y.z]` heading for the tagged version and the next `## ` heading, so the heading must match the tag's version exactly. If no section matches, the workflow falls back to GitHub's auto-generated notes.

### 2. Bump the version

Change the version in all three places:

- `package.json` (`"version"`)
- `.claude-plugin/plugin.json` (`"version"`)
- the version badge near the top of `README.md` (the badge text and its `releases/tag/vX.Y.Z` link)

Use semantic versioning with no prerelease suffix. The release workflow refuses `-beta`, `-rc` and `-alpha` tags.

### 3. Run the tests

Install the test dependencies with `bash scripts/setup-dev.sh`, then run each check. Each one passes or fails:

```bash
python3 -m pytest -q --ignore=tests/live
SWEETCLAUDE_LIVE=1 python3 -m pytest tests/live -q -rs
python3 scripts/routing_behavior.py --tier full
python3 scripts/docs_claims_check.py
```

The live suite and the routing suite drive real Claude Code sessions and cost money. Each caps its own spend: the live suite at 0.10 USD per case, and the routing suite at `--case-budget` per case and `--run-budget` per run. `tests/test_dashboard_ui.py` skips unless the checkout has `.sweetclaude/` project data, which this repository does not.

### 4. Commit, push and tag

```bash
git add package.json .claude-plugin/plugin.json README.md CHANGELOG.md
git commit -m 'chore(release): 5.1.3 — short summary'
git push origin main
```

The push runs `.github/workflows/test.yml`. Wait for it to pass, then tag:

```bash
git tag v5.1.3
git push origin v5.1.3
```

Pushing the tag triggers `.github/workflows/release.yml`, which refuses prerelease tags, runs `python3 scripts/docs_claims_check.py`, and creates the GitHub release from the changelog section. There is no receipt or evidence gate.
