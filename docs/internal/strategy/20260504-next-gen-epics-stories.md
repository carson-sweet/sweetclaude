# Next-Gen Strategy: Epics and Stories

**Version:** 1.0
**Date:** 2026-05-04
**Source:** `/Users/carsonsweet/dev/sweetclaude/docs/internal/strategy/20260504-next-gen-strategy.md`
**Status:** Planning artifact — not yet imported into SweetClaude's issue store

---

## How to use this document

This is the work breakdown for the next-gen strategy. Three epics (one per wave) with stories that decompose the 15 recommendations (R1–R15) from the strategy report into INVEST-shaped chunks.

- **Epics** are the three waves. Each is independently shippable.
- **Stories** are concrete work items with acceptance criteria. Most map to one R-item; bigger R-items split into 2–4 stories.
- **Dependencies** are explicit per story. Read `Depends on` lines before starting.
- **Reference** field on each story points back to the R-item in the strategy report.
- **Persona** for every story is *framework maintainer* unless noted. The few user-facing stories are tagged as such.

No time estimates per project rule. Sizing is `S`, `M`, `L` only — relative effort, not duration.

If/when these get imported into SweetClaude's issue store, IDs become `I-NNN` and epic IDs become `EP-NNN`. The `E1-S1`-style IDs in this doc are planning IDs only.

---

## Summary

| Epic | Title | Stories | Sizing |
|---|---|---|---|
| **E1** | Plugin Re-Rooting | 13 stories | 1 L, 6 M, 6 S |
| **E2** | Skill Modernization | 12 stories | 2 L, 7 M, 3 S |
| **E3** | Self-Improvement Infrastructure | 11 stories | 3 L, 5 M, 3 S |

**Total: 36 stories across 3 epics.**

| Wave | Goal | Exit criteria |
|---|---|---|
| **Wave 1 (E1)** | SweetClaude installs as a real plugin via marketplace | `claude plugin install sweetclaude@<marketplace>` produces a working install with all hooks firing, no `install.sh` invocation needed |
| **Wave 2 (E2)** | Every skill uses the modern frontmatter contract | Listing budget under 6KB; trigger accuracy on top 20 skills tested at >90%; per-skill hook contracts declarative |
| **Wave 3 (E3)** | SweetClaude has a defensible eval harness and a self-audit skill | Eval harness runs in CI on each Anthropic model release; `skill-doctor` reports a clean audit |

---

# Epic E1 — Plugin Re-Rooting

**Wave:** 1
**Goal:** Stop treating SweetClaude as files copied into `~/.claude/`. Make it a real plugin with `${CLAUDE_PLUGIN_ROOT}`-rooted hooks, marketplace-driven installation, and `${CLAUDE_PLUGIN_DATA}`-managed persistent state.

**Why now:** Every other modernization (skill modernization, eval harness, monitor adoption) depends on the plugin being properly rooted. This epic unblocks the rest.

**Exit criteria:**
- All hook scripts in `hooks-manifest.json` reference `${CLAUDE_PLUGIN_ROOT}` (zero `~/.claude/...` paths)
- A clean machine can `claude plugin install sweetclaude@<marketplace>` and have all hooks fire correctly
- `marketplace.json` version matches `plugin.json` version
- Existing `install.sh` users have a documented migration path
- `${CLAUDE_PLUGIN_DATA}` is used for any state that needs to survive plugin updates
- `dependencies: [{ name: "superpowers", ... }]` declared in `plugin.json`

**Risks:** Existing 1.x installs break if pushed naively. Mitigation in story E1-S11.

| Story | Title | Size | Depends on |
|---|---|---|---|
| E1-S1 | Update `hooks-manifest.json` to use `${CLAUDE_PLUGIN_ROOT}` | M | — |
| E1-S2 | Re-root all hook script invocations in `session-preflight.sh` | M | E1-S1 |
| E1-S3 | Re-root master skill pre-flight checks | S | E1-S1 |
| E1-S4 | Move `version-bump.sh` write target to `${CLAUDE_PLUGIN_DATA}` | M | E1-S1 |
| E1-S5 | Sync `marketplace.json` version with `plugin.json` | S | — |
| E1-S6 | Add `CHANGELOG.md` and version-bump tooling | S | E1-S5 |
| E1-S7 | Document marketplace install as primary in `install.md` | S | E1-S1 |
| E1-S8 | Reduce `install.sh` to fallback wrapper | M | E1-S1, E1-S7 |
| E1-S9 | Add `dependencies` field for Superpowers | S | — |
| E1-S10 | Document self-hosted marketplace pattern | S | E1-S7 |
| E1-S11 | Build `sweetclaude:doctor` migration skill for 1.x → 2.x users | L | E1-S1, E1-S2, E1-S8 |
| E1-S12 | Add `InstructionsLoaded` hook for SweetClaude-active detection | M | E1-S1 |
| E1-S13 | Bump major version to `2.0.0` and tag release | S | All other E1 stories |

---

## E1-S1 — Update `hooks-manifest.json` to use `${CLAUDE_PLUGIN_ROOT}`

**Story:** As a framework maintainer, I want every hook entry in `hooks-manifest.json` to reference `${CLAUDE_PLUGIN_ROOT}/hooks/<file>` instead of absolute `~/.claude/hooks/sweetclaude/<file>` so that the plugin loader can resolve hook paths at runtime regardless of install location.

**Reference:** Strategy R1.

**Acceptance criteria:**
- Every entry in `/Users/carsonsweet/dev/sweetclaude/hooks/hooks-manifest.json` that names a script uses `${CLAUDE_PLUGIN_ROOT}/hooks/<script>` form
- A registered hook in a fresh marketplace install fires correctly (verified via test session)
- A grep for `~/.claude/hooks/sweetclaude` in the entire repo returns zero results in `hooks/` and `skills/` directories
- The hook registration shape in `~/.claude/settings.json` after install resolves correctly via `claude --debug`
- Hooks-manifest schema_version bumped if the field shape changed

**Notes:** This is the foundation story. Every subsequent E1 story depends on this being correct.

---

## E1-S2 — Re-root all hook script invocations in `session-preflight.sh`

**Story:** As a framework maintainer, I want `session-preflight.sh` to use `${CLAUDE_PLUGIN_ROOT}` for any helper script invocations so that the pre-flight runs correctly under the cached plugin layout.

**Reference:** Strategy R1, current code at `/Users/carsonsweet/dev/sweetclaude/hooks/session-preflight.sh` lines 99–100, 145–148.

**Acceptance criteria:**
- `HOOK_DIR` resolution uses `${CLAUDE_PLUGIN_ROOT}` when set, with realpath fallback for `--plugin-dir` sessions
- `HOOKS_MANIFEST` and any helper script invocations resolve via `${CLAUDE_PLUGIN_ROOT}`
- A `--plugin-dir` install still works (no marketplace required for testing)
- A marketplace install (cache-rooted) still works
- Pre-flight emits no errors under either install path

**Depends on:** E1-S1.

---

## E1-S3 — Re-root master skill pre-flight checks

**Story:** As a framework maintainer, I want the master skill's Step 1 pre-flight checks to verify plugin presence via `${CLAUDE_PLUGIN_ROOT}` and the runtime plugin loader, not via hard-coded `~/.claude/skills/sweetclaude/` paths.

**Reference:** Strategy R1, current code at `/Users/carsonsweet/dev/sweetclaude/skills/master/SKILL.md` lines 26–34.

**Acceptance criteria:**
- Master skill no longer references `~/.claude/skills/sweetclaude/`, `~/.claude/config/sweetclaude/`, etc. for installation verification
- Pre-flight uses the plugin manifest declarations (e.g. via `claude plugin list --json`) or `${CLAUDE_PLUGIN_ROOT}` to verify health
- Error messages updated to reflect marketplace-install fix path, not "run install.sh"
- Synced to all installed locations

**Depends on:** E1-S1.

---

## E1-S4 — Move `version-bump.sh` write target to `${CLAUDE_PLUGIN_DATA}`

**Story:** As a framework maintainer, I want the auto-version-bump hook to write its state to `${CLAUDE_PLUGIN_DATA}` instead of the source repo's `package.json` so that runtime state writes don't fail under the read-only cache.

**Reference:** Strategy R1 (Risks section), R9.

**Acceptance criteria:**
- `version-bump.sh` no longer writes to `${CLAUDE_PLUGIN_ROOT}/package.json` (read-only under cache)
- Bump state lives in `${CLAUDE_PLUGIN_DATA}/version.json` or equivalent
- The user-facing version display (e.g. in `/sweetclaude:status`) reads from the new location
- Migration: existing project-side version state continues to work
- Hook runs cleanly under both `--plugin-dir` and marketplace install

**Depends on:** E1-S1.

---

## E1-S5 — Sync `marketplace.json` version with `plugin.json`

**Story:** As a framework maintainer, I want `marketplace.json` to declare the same version as `plugin.json` so that consumers using marketplace metadata see the correct version.

**Reference:** Strategy section 3.1.

**Acceptance criteria:**
- `/Users/carsonsweet/dev/sweetclaude/.claude-plugin/marketplace.json` `plugins[0].version` matches the current `plugin.json` `version`
- A small CI check (or pre-commit hook) catches future drift
- Plugin description in `plugin.json` updated from "60 skills" to actual count (currently 89)

**Notes:** Per Anthropic spec, `plugin.json.version` wins, so this is a smell-fix not a behavior-fix. Bundle with description correction.

---

## E1-S6 — Add `CHANGELOG.md` and version-bump tooling

**Story:** As a framework maintainer, I want a `CHANGELOG.md` that tracks version-bump rationale, and tooling that prompts for a changelog entry on every version bump, so that consumers can see what changed between versions.

**Reference:** Strategy section 3.1, 3.7.

**Acceptance criteria:**
- `/Users/carsonsweet/dev/sweetclaude/CHANGELOG.md` exists, follows Keep-a-Changelog format
- Entries cover at least the last 5 versions, reconstructed from git log
- The version-bump flow (whether hook or skill) prompts for or auto-drafts a changelog entry
- README links to changelog
- Marketplace.json optionally references it

**Depends on:** E1-S5.

---

## E1-S7 — Document marketplace install as primary in `install.md`

**Story:** As a SweetClaude user, I want `docs/user-guide/install.md` to show the marketplace install flow first, with `install.sh` clearly labeled as a fallback for users without marketplace access, so I install the plugin the supported way.

**Reference:** Strategy R7.

**Persona:** SweetClaude user.

**Acceptance criteria:**
- Marketplace install flow is the first install option presented
- `install.sh` is clearly labeled "Fallback: no marketplace available"
- Both paths are tested on a clean machine and produce equivalent installs
- Quickstart, getting-started, and README updated to match
- Update flow (`claude plugin update`) documented

**Depends on:** E1-S1 (so the marketplace install actually works).

---

## E1-S8 — Reduce `install.sh` to fallback wrapper

**Story:** As a framework maintainer, I want `install.sh` to be a thin fallback that wraps `claude plugin install --plugin-dir .` (with the legacy file-copy logic preserved only for users on Claude Code versions that don't support local plugin installs) so that the install matrix shrinks.

**Reference:** Strategy R7.

**Acceptance criteria:**
- `install.sh` first attempts `claude plugin install --plugin-dir .`
- Falls back to legacy file-copy with a clear "WARN: legacy install path" message
- Generated `uninstall.sh` and `restore-config.sh` continue to work for legacy installs
- Documented in `install.md`
- Tested on the maintainer's machine

**Depends on:** E1-S1, E1-S7.

---

## E1-S9 — Add `dependencies` field for Superpowers

**Story:** As a SweetClaude user, I want SweetClaude to declare Superpowers as a formal dependency in `plugin.json` so that Claude Code resolves it automatically and version-pins the supported range.

**Reference:** Strategy R12.

**Persona:** SweetClaude user.

**Acceptance criteria:**
- `plugin.json` includes `"dependencies": [{ "name": "superpowers", "version": "~5.0.7" }]`
- Marketplace handles transitive install (or the install docs explain the constraint if not auto-resolvable)
- README's Dependencies table updated to reflect declarative dependency
- `--strategy-skills-only` install path documented as opting out of Superpowers (potentially via separate plugin or userConfig)

**Notes:** If the maintainer's marketplace doesn't mirror Superpowers, defer the auto-resolve part and ship just the declaration.

---

## E1-S10 — Document self-hosted marketplace pattern

**Story:** As a SweetClaude user, I want documentation showing how to host SweetClaude as a private/self-hosted marketplace (just a git repo with `marketplace.json`) so that I can install it without depending on a third party.

**Reference:** Strategy R7 (Caveat).

**Persona:** SweetClaude user.

**Acceptance criteria:**
- New section in `install.md` (or new `docs/user-guide/marketplace-self-host.md`) walks through the pattern
- Example marketplace.json provided
- Tested by following the docs end-to-end on a clean machine
- Install flow `claude marketplace add <git-url>` documented

**Depends on:** E1-S7.

---

## E1-S11 — Build `sweetclaude:doctor` migration skill for 1.x → 2.x users

> **⚠️ MODEL SWITCH BEFORE STARTING THIS STORY.** This is the L-sized keystone of E1 — detection logic for legacy installs has many edge cases, the migration is irreversible if wrong, and the interactive flow needs careful design. **Stop and tell the user to switch to Opus 4.7 (`/model`) before beginning. Do not start this story on Sonnet.**

**Story:** As a SweetClaude user upgrading from 1.x, I want a `sweetclaude:doctor` skill that detects the legacy layout (`~/.claude/hooks/sweetclaude/...` registrations, hard-coded paths in `settings.json`) and offers to migrate me to the 2.x marketplace install with a single confirmation, so I don't have to manually unwire the old install.

**Reference:** Strategy R1 (Risk), section 7.

**Persona:** SweetClaude user.

**Acceptance criteria:**
- Skill detects: legacy hook registrations in `~/.claude/settings.json`, presence of legacy file copies in `~/.claude/skills/sweetclaude/`, version mismatches
- Reports findings before changing anything
- Offers via AskUserQuestion: Migrate now · Show me the diff · Postpone · Something else
- On approval: cleans legacy registrations, runs `claude plugin install`, verifies hooks fire
- Idempotent — running on a clean install reports "already on 2.x"
- Listed in `fix-sweetclaude` as a related repair tool

**Size:** L. Largest story in E1.

**Depends on:** E1-S1, E1-S2, E1-S8.

---

## E1-S12 — Add `InstructionsLoaded` hook for SweetClaude-active detection

**Story:** As a framework maintainer, I want an `InstructionsLoaded` hook that fires when the project's CLAUDE.md loads and verifies whether SweetClaude should be active, so the session-preflight script doesn't have to do as much detection work and SweetClaude responds correctly when CLAUDE.md is loaded mid-session.

**Reference:** Strategy R13 (partial — Wave 1 piece).

**Acceptance criteria:**
- New hook script in `hooks/instructions-loaded.sh` (or equivalent)
- Registered for `InstructionsLoaded` event
- Detects whether the loaded file is a project CLAUDE.md and whether `.sweetclaude/` exists
- Surfaces appropriate state to Claude via `additionalContext`
- Doesn't duplicate work that session-preflight already does on session start
- Tested with both fresh-session and mid-session CLAUDE.md loads

**Depends on:** E1-S1.

---

## E1-S13 — Bump major version to `2.0.0` and tag release

**Story:** As a SweetClaude user, I want the marketplace to clearly signal that the re-rooted plugin is a new generation by bumping to `2.0.0`, so that I understand my install needs to be updated and I can opt in deliberately.

**Reference:** Strategy section 6, Wave 1 exit criteria.

**Persona:** SweetClaude user (signal recipient).

**Acceptance criteria:**
- `plugin.json` version = `2.0.0`
- `marketplace.json` version matches
- Git tag `v2.0.0` pushed
- `claude plugin tag --push` used (or equivalent)
- Release notes in `CHANGELOG.md` highlight breaking changes (legacy install layout no longer supported without doctor)
- README banner mentions migration path for 1.x users

**Depends on:** All other E1 stories. This is the wrap-up.

---

# Epic E2 — Skill Modernization

**Wave:** 2
**Goal:** Mass-modernize the frontmatter on every skill. Adopt the Anthropic-shipped fields (`when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation`, `allowed-tools`, `effort`, `paths`, `context: fork`, `agent`, per-skill `hooks`). Fix listing-budget pressure. Wire the 8 existing agents into skills via the `agent` field.

**Why now:** Independent of Wave 1 *technically*, but the frontmatter changes assume `${CLAUDE_PLUGIN_ROOT}`-aware hook references. Doing E2 before E1 forces a frontmatter rewrite later.

**Exit criteria:**
- Listing budget under 6KB total
- Trigger accuracy on top 20 user-facing skills tested at >90%
- All 89 skills carry an explicit `name` field
- All side-effect skills carry `disable-model-invocation: true`
- All argument-taking skills declare `argument-hint` and (where appropriate) named `arguments`
- 8 agents wired into corresponding `context: fork` skills via `agent:` field
- Heavy skills run forked

| Story | Title | Size | Depends on |
|---|---|---|---|
| E2-S1 | Build frontmatter audit and rewrite tooling | L | — |
| E2-S2 | Add explicit `name:` to all skills currently relying on dirname fallback | S | E2-S1 |
| E2-S3 | Add `when_to_use` to user-facing skills | M | E2-S1 |
| E2-S4 | Add `argument-hint` to all argument-taking skills | S | E2-S1 |
| E2-S5 | Replace inline `$ARGUMENTS` parsing with named `arguments` where appropriate | M | E2-S1, E2-S4 |
| E2-S6 | Audit and apply `disable-model-invocation` vs `user-invocable` correctly | M | E2-S1 |
| E2-S7 | Add `allowed-tools` to every skill | M | E2-S1 |
| E2-S8 | Add `effort` to high-cognition skills | S | E2-S1 |
| E2-S9 | Add `paths` activation to language- or file-specific skills | M | E2-S1 |
| E2-S10 | Convert heavy skills to `context: fork` with `agent:` pairing | L | E2-S1, E1-S1 |
| E2-S11 | Sweep skill bodies for text-imitation menus, replace with AskUserQuestion | M | — |
| E2-S12 | Listing-budget triage and verification | M | E2-S2 through E2-S10 |

---

## E2-S1 — Build frontmatter audit and rewrite tooling

**Story:** As a framework maintainer, I want a script (Python or Node) that audits every `SKILL.md` against the modern frontmatter contract and can apply mechanical rewrites in batch, so that the modernization is repeatable and verifiable.

**Reference:** Strategy R2, R6, section 6 Wave 2.

**Acceptance criteria:**
- Script lives in `scripts/skill-audit.{py,js}` (whichever fits existing tooling)
- Reads every `skills/*/SKILL.md`
- Reports per skill: missing fields, current description length, listing-budget contribution, conflicts with `name`/dirname
- Has a `--fix` mode for safe mechanical fixes (add `name:` from dirname, etc.)
- Has a `--dry-run` mode that prints proposed diffs
- Output usable as input for stories E2-S2 through E2-S9
- Idempotent — running twice produces no further changes

**Size:** L. Foundation story for the rest of E2.

---

## E2-S2 — Add explicit `name:` to all skills currently relying on dirname fallback

**Story:** As a framework maintainer, I want every `SKILL.md` to carry an explicit `name:` field set to `sweetclaude:<slug>` so that the slash-command identifier is stable even if directory names ever change.

**Reference:** Strategy section 3.2.

**Acceptance criteria:**
- Every `SKILL.md` in `skills/` has a `name:` field
- The value is `sweetclaude:<slug>` where `<slug>` matches the directory name
- `claude --debug` confirms each skill registers under the expected name
- Spot-check: typing `/sweetclaude:<name>` works for all 89 skills

**Depends on:** E2-S1.

---

## E2-S3 — Add `when_to_use` to user-facing skills

**Story:** As a SweetClaude user, I want every user-facing skill to carry a `when_to_use` block packed with trigger phrases and synonyms so that Claude reliably auto-invokes the right skill when I describe my work in plain English.

**Reference:** Strategy R2, R14.

**Persona:** SweetClaude user.

**Acceptance criteria:**
- Every skill not marked `user-invocable: false` carries a `when_to_use` field
- Each `when_to_use` includes ≥3 trigger phrases or synonyms
- Combined `description` + `when_to_use` length stays under 1,536 chars per skill
- For each top-20 user-facing skill, at least 6 user phrasings tested map to the right skill
- Test run via `find-skill` or a synthesized eval

**Depends on:** E2-S1.

---

## E2-S4 — Add `argument-hint` to all argument-taking skills

**Story:** As a SweetClaude user, I want every skill that accepts arguments to show an autocomplete hint like `[issue-number]`, `[mode]`, or `[type]` so that I know what to type after the skill name.

**Reference:** Strategy R2, section 3.2.

**Persona:** SweetClaude user.

**Acceptance criteria:**
- Every `SKILL.md` body that references `$ARGUMENTS` declares `argument-hint:`
- Hints are short, in square brackets, and reflect actual parsing logic
- `/sweetclaude:` autocomplete in Claude Code shows the hints
- Spot-check the top 10 argument-taking skills (`code-issue`, `code-testing`, `code-review`, `product-milestones`, `document-corpus`, etc.)

**Depends on:** E2-S1.

---

## E2-S5 — Replace inline `$ARGUMENTS` parsing with named `arguments` where appropriate

**Story:** As a framework maintainer, I want skills that take positional arguments to declare them as named `arguments` so that the skill bodies are cleaner and the argument contract is in the manifest layer.

**Reference:** Strategy R2.

**Acceptance criteria:**
- Skills with multi-positional arguments (`migrate-component`, `product-milestones [sub] [args...]`, `code-testing [mode]`, etc.) declare `arguments:` and use `$name` substitution
- Skill bodies no longer parse `$ARGUMENTS` ad-hoc when named args suffice
- Backward compatibility: if a user passes positional args that fit the old shape, still works
- Tested with realistic invocations

**Depends on:** E2-S1, E2-S4.

---

## E2-S6 — Audit and apply `disable-model-invocation` vs `user-invocable` correctly

**Story:** As a SweetClaude user, I want side-effect skills (`purge`, `deploy-ship`, `something-broke`, `update`, `off`, `john-wick`, `behavioral-regression`, `hibernate`) to require explicit user invocation so that Claude doesn't accidentally trigger destructive or expensive operations, while internal helper skills stay model-invocable but hidden from the slash menu.

**Reference:** Strategy R2, section 3.3.

**Persona:** SweetClaude user.

**Acceptance criteria:**
- Side-effect skills carry `disable-model-invocation: true` and remain user-invocable
- Internal helpers (`_route`, `_offer`, `_health`, `_migrate`, `master`, `find-skill`, `bootstrap`, `next-steps`) carry `user-invocable: false` only
- A documented matrix in `docs/internal/strategy/skill-invocation-matrix.md` shows the choice per skill
- Spot-check via Claude Code: `/sweetclaude:purge` works (user-invoked); Claude does not auto-trigger purge during a session

**Depends on:** E2-S1.

---

## E2-S7 — Add `allowed-tools` to every skill

**Story:** As a SweetClaude user, I want skills to pre-approve the tools they routinely need so that I'm not interrupted with permission prompts during normal flow.

**Reference:** Strategy R2.

**Persona:** SweetClaude user.

**Acceptance criteria:**
- Every skill carries an `allowed-tools` field appropriate to its work (e.g. TDD skills allow `Bash(npm *)`, `Bash(pytest *)`, etc.)
- Tools are scoped narrowly — no skill grants broad `Bash` without a matcher
- Permission prompts during a typical TDD session drop measurably (track before/after on a known feature workflow)
- Documented in skills-reference

**Depends on:** E2-S1.

---

## E2-S8 — Add `effort` to high-cognition skills

**Story:** As a framework maintainer, I want heavy reasoning skills (`code-feature`, `design-architecture`, `design-tech-spec`, `product-prd`, `code-issue`, `code-debt`) to declare `effort: high` so that Claude allocates appropriate reasoning budget per turn.

**Reference:** Strategy R2.

**Acceptance criteria:**
- Heavy skills declare `effort: high`
- Status/help/info skills declare `effort: low` where appropriate
- Default skills inherit the session level (no field set)
- Documented in a small effort matrix

**Depends on:** E2-S1.

---

## E2-S9 — Add `paths` activation to language- or file-specific skills

**Story:** As a SweetClaude user, I want skills that only make sense in specific file contexts (e.g. `code-tdd` for source/test files, `design-wireframes` for HTML/TSX, `mockup-extract` for component files) to declare `paths` glob patterns so that Claude doesn't auto-invoke them when I'm not in the right context.

**Reference:** Strategy R2.

**Persona:** SweetClaude user.

**Acceptance criteria:**
- Skills with clear file-pattern affinity declare `paths:`
- General-purpose skills (status, go, help, find-skill) leave `paths` unset
- Documented per-skill in skills-reference
- Verified by working in different file contexts and observing skill-listing changes

**Depends on:** E2-S1.

---

## E2-S10 — Convert heavy skills to `context: fork` with `agent:` pairing

**Story:** As a framework maintainer, I want skills with large bodies or strong isolation requirements to run in forked subagent contexts via `context: fork` and `agent: <name>`, so that the main conversation context isn't burned by inline skill bodies and the existing 8 agents are wired in declaratively.

**Reference:** Strategy R3, R4.

**Acceptance criteria:**
- The following skills run forked: `master`, `code-feature`, `code-issue`, `code-debt`, `document-corpus`, `find-skill`, `design-architecture`, `design-ux-review`, `code-review`, `code-testing`
- Each fork is paired with the right agent (`general-purpose`, `Plan`, `Explore`, `code-reviewer`, etc.)
- Skills that need conversational continuity (`go`, `status`, `help`, `next-steps`, `bootstrap`) stay inline
- Subagent isolation contracts (test-writer, implementer, qa-caucus-*) wired via `agent:` field
- Test: kicking off `code-feature` from main session no longer dumps the full body into context
- Pre/post token usage measured on a representative session — meaningful drop

**Size:** L.

**Depends on:** E2-S1, E1-S1.

---

## E2-S11 — Sweep skill bodies for text-imitation menus, replace with AskUserQuestion

**Story:** As a SweetClaude user, I want every skill that presents bounded choices to use the AskUserQuestion menu instead of writing a text line that imitates a menu, so that I can pick options interactively. "Something else" must always be one of the options.

**Reference:** Recent global feedback (interaction-model "Bounded Decisions Use the Menu" rule).

**Persona:** SweetClaude user.

**Acceptance criteria:**
- Grep for text-menu patterns (e.g. `"·"` separator with three or four short labels, "1 / option ... 2 / option") finds zero matches in `skills/`
- Every skill description that mentions "Opens a menu at start" or "Presents a menu" routes to AskUserQuestion when invoked
- Every menu has a "Something else" option (or equivalent escape)
- Specific candidates: `code-review` (mode menu), `code-testing` (mode menu), `document-corpus` (mode menu), `design-ux-review` (option menu)
- Tested by invoking each updated skill and confirming the menu renders interactively

**Notes:** This is also stated in `~/.claude/rules/sweetclaude/interaction-model.md` and saved as a persistent feedback memory. This story is the operationalization across the existing skill set.

---

## E2-S12 — Listing-budget triage and verification

**Story:** As a SweetClaude user, I want the cumulative skill description listing to fit comfortably under the default budget so that trigger phrases at the end of skill descriptions don't get silently truncated.

**Reference:** Strategy R6, section 3.2.

**Persona:** SweetClaude user.

**Acceptance criteria:**
- Total listing footprint measured (description + when_to_use across all listed skills) and < 6KB
- Side-effect skills with `disable-model-invocation: true` no longer count toward the listing
- Long descriptions trimmed to ~100 chars; trigger material moved to `when_to_use`
- Recommended `SLASH_COMMAND_TOOL_CHAR_BUDGET=20000` documented in install.md and getting-started.md
- A spot-check: `claude --debug` confirms no truncation warnings on a fresh session

**Depends on:** E2-S2 through E2-S10.

---

# Epic E3 — Self-Improvement Infrastructure

**Wave:** 3
**Goal:** Build the things that turn SweetClaude from "well-engineered framework" into "framework with a defensible eval moat." Structured eval harness, monitor-based test runner, `bin/` utilities, trigger-phrase optimization pass, `skill-doctor` skill, declarative user config, persistent data dir use, and the remaining lifecycle hooks.

**Why now / why last:** Highest leverage but lowest urgency. Wave 1 and 2 are about correctness; Wave 3 is about durability and defensibility. Sequencing this last means the eval harness gets to validate the modernizations.

**Exit criteria:**
- Eval harness runs in CI on each Anthropic model release; produces per-model report
- `auto-test-runner` available as a monitor (with hook fallback)
- `bin/` directory contains user-callable utilities
- `sweetclaude:skill-doctor` reports a clean audit of the current skill set
- Top 20 skills have been through a trigger-phrase optimization pass with measured improvement
- `userConfig` replaces the manual setup interview where appropriate
- `${CLAUDE_PLUGIN_DATA}` used for cross-version persistent state

| Story | Title | Size | Depends on |
|---|---|---|---|
| E3-S1 | Convert `behavioral-regression` contracts to fixture files | M | — |
| E3-S2 | Build eval driver script (Anthropic SDK harness) | L | E3-S1 |
| E3-S3 | Wire eval harness into CI with per-model history | M | E3-S2 |
| E3-S4 | Surface eval results in `behavioral-regression` skill | S | E3-S2 |
| E3-S5 | Convert `auto-test-runner` to a monitor with hook fallback | M | E1-S1 |
| E3-S6 | Populate `bin/` with user-callable utilities | S | E1-S1 |
| E3-S7 | Trigger-phrase optimization pass on top 20 skills | L | E2-S3, E3-S2 |
| E3-S8 | Build `sweetclaude:skill-doctor` skill | L | E2-S1 |
| E3-S9 | Add `userConfig` to plugin manifest | M | E1-S1 |
| E3-S10 | Migrate cross-version persistent state to `${CLAUDE_PLUGIN_DATA}` | M | E1-S1 |
| E3-S11 | Subscribe to `SubagentStart`/`SubagentStop` for TDD contract enforcement | M | E1-S1 |

---

## E3-S1 — Convert `behavioral-regression` contracts to fixture files

**Story:** As a framework maintainer, I want each of the 15 behavioral contracts to live as a fixture file with `input.md` (a triggering prompt) and `expected.json` (assertions about the response), so that the contracts are runnable as a deterministic suite rather than a self-report.

**Reference:** Strategy R5.

**Acceptance criteria:**
- Directory `evals/contracts/<contract-name>/` exists for each contract
- Each contract has `input.md` and `expected.json`
- Assertions are concrete: e.g., "response must not contain 'shall we proceed?' or its variants"; "response length < 500 chars"; "response references file at path X"
- The 15 existing contracts from `behavioral-regression` skill all converted
- Schema documented in `evals/README.md`

---

## E3-S2 — Build eval driver script (Anthropic SDK harness)

**Story:** As a framework maintainer, I want a driver script (Node or Python using the Anthropic SDK) that reads each fixture, invokes Claude via API with the configured target model, evaluates assertions, and produces a per-contract pass/fail report, so that the behavioral suite is auditable and reproducible.

**Reference:** Strategy R5.

**Acceptance criteria:**
- Script lives at `evals/run.{py,ts}`
- Uses Anthropic SDK with prompt caching enabled (per claude-api skill guidance)
- Reads fixtures, invokes API, evaluates assertions, writes JSON report
- Handles model selection via env var or arg (`--model claude-sonnet-4-7`)
- Includes failure-mode reporting (which contract failed, what assertion, what the response was)
- Documented in `evals/README.md`
- Cost-aware: caches per-fixture, supports `--limit N` for partial runs

**Size:** L.

**Depends on:** E3-S1.

---

## E3-S3 — Wire eval harness into CI with per-model history

**Story:** As a framework maintainer, I want the eval harness to run on a schedule (e.g. weekly) and on each Anthropic model release, with results stored in `evals/results/<model-id>-<date>.json` so that I can detect silent behavioral drift across model versions.

**Reference:** Strategy R5.

**Acceptance criteria:**
- GitHub Actions workflow (or equivalent) runs the harness on schedule and on `workflow_dispatch`
- Workflow accepts a model ID parameter
- Results committed to `evals/results/`
- A simple diff tool (`evals/diff.{py,ts}`) shows pass-rate changes between two reports
- Anthropic API key managed via secrets, never in repo
- README documents the schedule and how to interpret results
- Cost monitored — runs limited unless explicitly triggered

**Depends on:** E3-S2.

---

## E3-S4 — Surface eval results in `behavioral-regression` skill

**Story:** As a SweetClaude user, I want `/sweetclaude:behavioral-regression` to surface the latest eval-harness results (e.g. "13/15 passing on claude-sonnet-4-7. Failing: phase-dwelling, autonomous-respect.") so that I can see the actual pass-rate at a glance instead of running a self-report.

**Reference:** Strategy R5.

**Persona:** SweetClaude user.

**Acceptance criteria:**
- Skill body reads the latest results JSON from `${CLAUDE_PLUGIN_DATA}/evals/` or repo `evals/results/`
- Displays pass count, model ID, run date
- Lists failing contracts with one-line description
- Offers via AskUserQuestion: Run live · View detailed report · Compare across models · Something else
- README "behavioral contracts" line updated to reference live results

**Depends on:** E3-S2.

---

## E3-S5 — Convert `auto-test-runner` to a monitor with hook fallback

**Story:** As a SweetClaude user in IMPLEMENT phase, I want test results to stream as notifications from a background process rather than block on PostToolUse hooks, so that my edit→test feedback loop is faster and I see status changes between edits without blocking the next edit.

**Reference:** Strategy R10.

**Persona:** SweetClaude user.

**Acceptance criteria:**
- New `monitors/monitors.json` declares a `test-watcher` monitor with `when: on-skill-invoke:code-tdd`
- Wrapper script `scripts/test-watcher.sh` (or `bin/sc-test-watch`) wraps a project test runner with `--watch` and streams status changes
- Hook-based `auto-test-runner.sh` continues to work for users on Claude Code versions before v2.1.105 (documented version floor)
- README and getting-started note the version floor
- Tested with at least one Node and one Python project

**Depends on:** E1-S1.

---

## E3-S6 — Populate `bin/` with user-callable utilities

**Story:** As a SweetClaude user, I want utility commands like `sc-artifact`, `sc-test-watch`, and `sc-status` available on PATH when the plugin is enabled, so that I can call them in shell without remembering the full plugin path.

**Reference:** Strategy R11.

**Persona:** SweetClaude user.

**Acceptance criteria:**
- `bin/` directory created at plugin root with selected utilities
- `sc-artifact` (currently in `scripts/`) moved/symlinked here
- New convenience commands documented in skills-reference
- Skill bodies updated to use bare commands instead of `${CLAUDE_PLUGIN_ROOT}/scripts/...`
- Binaries are executable (`chmod +x`)
- Smoke-tested in a fresh session

**Depends on:** E1-S1.

---

## E3-S7 — Trigger-phrase optimization pass on top 20 skills

**Story:** As a SweetClaude user, I want the top 20 user-facing skills to have descriptions and `when_to_use` blocks rich with synonyms, file types, and natural phrasings so that Claude reliably auto-invokes the right skill when I describe my work in plain English.

**Reference:** Strategy R14.

**Persona:** SweetClaude user.

**Acceptance criteria:**
- Top 20 user-facing skills identified (by usage data if available, else by maintainer judgment)
- For each: 6–10 user phrasings brainstormed; baseline trigger accuracy measured against current frontmatter
- Frontmatter enriched per skill
- Re-test: trigger accuracy ≥90% per skill
- Pass-rate before/after recorded in `docs/internal/strategy/trigger-optimization-results.md`
- Process documented as a repeatable pattern for the remaining ~70 skills

**Size:** L.

**Depends on:** E2-S3, E3-S2 (the eval harness can drive trigger tests).

---

## E3-S8 — Build `sweetclaude:skill-doctor` skill

**Story:** As a framework maintainer, I want a `sweetclaude:skill-doctor` skill that audits the SweetClaude skill set against the modern frontmatter contract, flags trigger conflicts, reports listing-budget contribution, and suggests improvements, so that frontmatter discipline is maintained as the framework evolves.

**Reference:** Strategy R15.

**Acceptance criteria:**
- New skill `sweetclaude:skill-doctor` (or possibly `_skill-doctor` if internal-only)
- Reuses or extends the audit script from E2-S1
- Reports per skill: missing fields, description length, listing-budget contribution, name/dirname conflicts
- Detects trigger conflicts (two skills with overlapping when_to_use phrases)
- Suggests trigger-phrase improvements based on common patterns
- Listed in `fix-sweetclaude` and the skills-reference
- Tested on the current skill set; produces a useful audit

**Size:** L.

**Depends on:** E2-S1.

---

## E3-S9 — Add `userConfig` to plugin manifest

**Story:** As a SweetClaude user, I want plugin-level configuration (default deference, default mode, RAG endpoint, optional API key for evals) to be prompted at install time via the plugin's `userConfig` so that the manual setup interview is shorter and per-machine config is centralized.

**Reference:** Strategy R8.

**Persona:** SweetClaude user.

**Acceptance criteria:**
- `plugin.json` declares `userConfig` for: default_deference, default_mode, rag_endpoint, anthropic_api_key (sensitive)
- Skills consume values via `${user_config.KEY}` or `CLAUDE_PLUGIN_OPTION_KEY` env vars
- Setup interview in `sweetclaude:on` / `sweetclaude:setup` consumes these instead of asking from scratch (when present)
- Sensitive values stored in keychain, never in `settings.json`
- `/plugin reconfigure sweetclaude` updates values at runtime
- Documented in install.md

**Depends on:** E1-S1.

---

## E3-S10 — Migrate cross-version persistent state to `${CLAUDE_PLUGIN_DATA}`

**Story:** As a framework maintainer, I want plugin-level mutable state (eval results, usage tracking aggregates, cached metadata) to live in `${CLAUDE_PLUGIN_DATA}` so that plugin updates don't wipe accumulated state.

**Reference:** Strategy R9.

**Acceptance criteria:**
- Eval-harness historical results write to `${CLAUDE_PLUGIN_DATA}/evals/results/`
- Usage-tracking aggregates (if any plugin-level rollup exists) live in `${CLAUDE_PLUGIN_DATA}/usage/`
- Per-project state (`.sweetclaude/`) stays where it is (correct location)
- A small migration script handles 1.x → 2.x state location moves
- Tested by simulating a plugin update and verifying state survives

**Depends on:** E1-S1.

---

## E3-S11 — Subscribe to `SubagentStart`/`SubagentStop` for TDD contract enforcement

**Story:** As a framework maintainer, I want `SubagentStart` and `SubagentStop` hooks that snapshot test files when an `implementer` agent starts and diff them when it stops, so that the "implementer never touches tests" contract is enforced deterministically rather than just instructed.

**Reference:** Strategy R13 (full).

**Acceptance criteria:**
- New hook scripts subscribe to `SubagentStart` and `SubagentStop`
- On start (matcher: `implementer`): snapshot test files into a transient location
- On stop (matcher: `implementer`): diff against snapshot; if test files changed, log violation and surface to user
- Documented in tdd.md as a Tier-1 deterministic enforcement
- Tested with a deliberately-misbehaving implementer prompt; confirm violation surfaces

**Depends on:** E1-S1.

---

# Cross-cutting concerns

These apply across all three epics and don't fit neatly into a single story.

**Backward compatibility throughout the migration.** No epic should leave 1.x users with a broken install. Maintain `install.sh` as a fallback through the 2.x line. Mark for deprecation in 3.x. Document the migration path in `MIGRATION.md`.

**Documentation regeneration.** When E2 lands, `docs/user-guide/skills-reference.md` needs a regen pass to surface `argument-hint`, `paths`, and `when_to_use` content. Treat doc regen as part of the story that introduces the change, not a separate epic.

**Eval harness as a verification tool.** Once E3-S2 ships, every subsequent change should be eval-checked. Add a `make eval` (or equivalent) target that runs the harness against the current skill set. This is a reusable verification primitive for E2-S11 (menu sweep), E3-S7 (trigger optimization), and any future model-version migration.

**The ROADMAP file.** A new top-level `ROADMAP.md` (already exists per the directory listing — verify content) should reflect the 3-wave plan and link to this document. Keep this doc as the single planning truth; the roadmap surfaces wave-level milestones.

---

# Sequencing notes

The dependency graph below isn't strict — most stories can run in parallel within an epic — but these constraints matter:

- **E1-S1 is the keystone.** Most of E1 and several of E3 depend on it. Land it first.
- **E2 depends on E1.** Don't start E2 frontmatter rewrites until hooks are re-rooted, or you'll do the frontmatter work twice.
- **E2-S1 (audit tooling) gates the rest of E2.** Build the script first, run it on the current state to baseline, then use it to drive subsequent stories.
- **E3-S2 (eval driver) gates the rest of E3.** Without it, E3-S3, E3-S4, E3-S7 don't have anything to plug into.
- **E1-S11 (doctor migration skill) is the largest single E1 story.** Treat as the wave's keystone delivery.
- **E2-S10 (forking heavy skills) is large but parallelizable** per skill. Could ship one skill at a time once the pattern is set.
- **E3-S7 (trigger-phrase optimization) is large but content-driven.** Can run in parallel to E3-S5 (monitor), E3-S6 (bin/), E3-S9 (userConfig), E3-S10 (data dir), E3-S11 (subagent hooks).

**Recommended start order if a single person is doing the work:**
1. E1-S1, E1-S2, E1-S3, E1-S5, E1-S9 (quick wins to land the re-rooting)
2. E1-S7, E1-S8 (install path)
3. E1-S11, E1-S12, E1-S4, E1-S6, E1-S10
4. E1-S13 (tag 2.0.0)
5. E2-S1 (audit tooling)
6. E2-S2 through E2-S9 (mechanical frontmatter modernization, parallelizable)
7. E2-S10 (fork heavy skills, one at a time)
8. E2-S11 (menu sweep)
9. E2-S12 (listing budget verification)
10. E3-S1, E3-S2, E3-S3, E3-S4 (eval harness chain)
11. E3-S5, E3-S6, E3-S9, E3-S10, E3-S11 (parallel infra)
12. E3-S7, E3-S8 (the polish layer)

---

# Source links

- Strategy report: `/Users/carsonsweet/dev/sweetclaude/docs/internal/strategy/20260504-next-gen-strategy.md`
- Plugin manifest: `/Users/carsonsweet/dev/sweetclaude/.claude-plugin/plugin.json`
- Skills directory: `/Users/carsonsweet/dev/sweetclaude/skills/`
- Hooks directory: `/Users/carsonsweet/dev/sweetclaude/hooks/`
- Anthropic plugin reference: https://code.claude.com/docs/en/plugins-reference
- Anthropic skills documentation: https://code.claude.com/docs/en/skills
